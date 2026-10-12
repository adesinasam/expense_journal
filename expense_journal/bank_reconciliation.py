"""
Makes submitted Expense Entries visible to ERPNext bank reconciliation,
and therefore to the Mint app (which uses ERPNext's matching under the hood).

Wired up in hooks.py:
    bank_reconciliation_doctypes
    get_matching_queries
    get_entries_for_bank_clearance_summary
    get_entries_for_bank_reconciliation_statement
    get_amounts_not_reflected_in_system_for_bank_reconciliation_statement

An Expense Entry pays money OUT of the Mode of Payment account, so it can only
match a bank WITHDRAWAL. The bank amount is read from the GL Entries the
Expense Entry posted, so it is always what actually hit the bank account.
"""

import frappe
from frappe.query_builder import Case
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import Sum
from frappe.utils import cint, flt

DOCTYPE = "Expense Entry"


def _wants_expense_entries(document_types):
	"""Mint sends the match-filter toggles as document_types.

	Show Expense Entries when the "expense_entry" toggle is on, or when the
	"Journal Entry" toggle is on, so they appear in Mint without any change
	to Mint's screens.
	"""
	if not document_types:
		return False
	return "expense_entry" in document_types or "journal_entry" in document_types


# ---------------------------------------------------------------------------
# 1. Matching: suggest Expense Entries for a bank transaction in Mint
# ---------------------------------------------------------------------------
def get_matching_queries(
	bank_account,
	company,
	transaction,
	document_types=None,
	exact_match=None,
	account_from_to=None,
	from_date=None,
	to_date=None,
	filter_by_reference_date=None,
	from_reference_date=None,
	to_reference_date=None,
	common_filters=None,
):
	if not _wants_expense_entries(document_types):
		return []

	# Expense Entries only pay money out
	if flt(transaction.withdrawal) <= 0:
		return []

	ee = frappe.qb.DocType(DOCTYPE)
	gle = frappe.qb.DocType("GL Entry")

	if cint(filter_by_reference_date) and from_reference_date and to_reference_date:
		date_condition = ee.reference_date.between(from_reference_date, to_reference_date)
	elif from_date and to_date:
		date_condition = ee.posting_date.between(from_date, to_date)
	else:
		date_condition = ee.docstatus == 1

	subquery = (
		frappe.qb.from_(gle)
		.join(ee)
		.on((gle.voucher_type == DOCTYPE) & (gle.voucher_no == ee.name))
		.select(
			Sum(gle.credit_in_account_currency - gle.debit_in_account_currency).as_("paid_amount"),
			ConstantColumn(DOCTYPE).as_("doctype"),
			ee.name,
			ee.payment_reference.as_("reference_no"),
			ee.reference_date.as_("reference_date"),
			ee.payment_to.as_("party"),
			ConstantColumn(None).as_("party_type"),
			ee.posting_date,
			gle.account_currency.as_("currency"),
		)
		.where(ee.docstatus == 1)
		.where(ee.company == company)
		.where(ee.clearance_date.isnull())
		.where(gle.account == bank_account)  # GL account of the Mint bank account
		.where(gle.is_cancelled == 0)
		.where(date_condition)
		.groupby(ee.name, gle.account_currency)
	)

	if frappe.flags.auto_reconcile_vouchers is True:
		subquery = subquery.where(ee.payment_reference == transaction.reference_number)

	ref_rank = Case().when(subquery.reference_no == transaction.reference_number, 1).else_(0)
	amount_equality = subquery.paid_amount == transaction.unallocated_amount
	amount_rank = Case().when(amount_equality, 1).else_(0)

	query = (
		frappe.qb.from_(subquery)
		.select("*", (ref_rank + amount_rank + 1).as_("rank"))
		.where(amount_equality if exact_match else subquery.paid_amount > 0.0)
	)

	return [query]


# ---------------------------------------------------------------------------
# 2. Reports Mint shows: Bank Clearance Summary & Bank Reconciliation Statement
# ---------------------------------------------------------------------------
def _bank_gl_rows(account):
	ee = frappe.qb.DocType(DOCTYPE)
	gle = frappe.qb.DocType("GL Entry")
	query = (
		frappe.qb.from_(gle)
		.join(ee)
		.on((gle.voucher_type == DOCTYPE) & (gle.voucher_no == ee.name))
		.where(ee.docstatus == 1)
		.where(gle.is_cancelled == 0)
		.where(gle.account == account)
	)
	return ee, gle, query


def get_entries_for_bank_clearance_summary(filters):
	ee, gle, query = _bank_gl_rows(filters.account)
	return (
		query.select(
			ConstantColumn(DOCTYPE).as_("payment_document"),
			ee.name.as_("payment_entry"),
			ee.posting_date,
			ee.payment_reference.as_("cheque_no"),
			ee.clearance_date,
			gle.against.as_("against_account"),
			(gle.debit_in_account_currency - gle.credit_in_account_currency).as_("amount"),
		)
		.where(ee.posting_date >= filters.from_date)
		.where(ee.posting_date <= filters.to_date)
		.run(as_list=True)
	)


def get_entries_for_bank_reconciliation_statement(filters):
	ee, gle, query = _bank_gl_rows(filters.account)
	return (
		query.select(
			ConstantColumn(DOCTYPE).as_("payment_document"),
			ee.name.as_("payment_entry"),
			ee.posting_date,
			gle.debit_in_account_currency.as_("debit"),
			gle.credit_in_account_currency.as_("credit"),
			gle.against.as_("against_account"),
			ee.payment_reference.as_("reference_no"),
			ee.reference_date.as_("ref_date"),
			ee.clearance_date,
			gle.account_currency,
		)
		.where(ee.company == filters.company)
		.where(ee.posting_date <= filters.report_date)
		.where(ee.clearance_date.isnull() | (ee.clearance_date > filters.report_date))
		.run(as_dict=True)
	)


def get_amounts_not_reflected_in_system_for_bank_reconciliation_statement(filters):
	ee, gle, query = _bank_gl_rows(filters.account)
	result = (
		query.select(
			Sum(gle.debit_in_account_currency - gle.credit_in_account_currency).as_("amount")
		)
		.where(ee.company == filters.company)
		.where(ee.posting_date > filters.report_date)
		.where(ee.clearance_date <= filters.report_date)
		.run(as_dict=True)
	)
	return flt(result[0].amount) if result else 0.0
