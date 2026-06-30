# -*- coding: utf-8 -*-
# Copyright (c) 2020, Bantoo and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _, throw  # Add this import
from frappe.utils import flt
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts.utils import get_account_currency
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
    get_accounting_dimensions,
)

import erpnext
from erpnext.accounts.utils import get_balance_on

class ExpenseEntry(Document):
	def validate(self):
		self.validate_cost_center_company()
		self.validate_account_companies()


    def on_submit(self):
        self.make_gl_entries()

    def on_cancel(self):
        frappe.db.sql(
            """
            DELETE FROM `tabGL Entry`
            WHERE voucher_type=%s AND voucher_no=%s
            """,
            (self.doctype, self.name),
        )

	def validate_cost_center_company(self):
		"""Validate that the selected Cost Center belongs to the document's company"""
		if self.default_cost_center:
			cost_center_company = frappe.db.get_value("Cost Center", self.default_cost_center, "company")

			if cost_center_company != self.company:
				frappe.throw(_("Cost Center {0} does not belong to company {1}. It belongs to {2}.").format(
					frappe.bold(self.default_cost_center),
					frappe.bold(self.company),
					frappe.bold(cost_center_company)
				))

	def validate_account_companies(self):
		"""Validate that all accounts in items belong to the document's company"""
		for item in self.get("expenses", []):
			if item.expense_account:
				account_company = frappe.db.get_value("Account", item.expense_account, "company")
				cost_center_company = frappe.db.get_value("Cost Center", item.cost_center, "company")

				if account_company != self.company:
					frappe.throw(_("Row #{0}: Account {1} does not belong to company {2}. It belongs to {3}.").format(
						item.idx,
						frappe.bold(item.expense_account),
						frappe.bold(self.company),
						frappe.bold(account_company)
					))

				if cost_center_company != self.company:
					frappe.throw(_("Row #{0}: Cost Center {1} does not belong to company {2}. It belongs to {3}.").format(
						item.idx,
						frappe.bold(item.cost_center),
						frappe.bold(self.company),
						frappe.bold(cost_center_company)
					))

    @frappe.whitelist()
    def get_gl_preview(self):
        return self.build_gl_entries(preview=True)

    def make_gl_entries(self):
        gl_entries = self.build_gl_entries(preview=False)
        make_gl_entries(gl_entries, cancel=False, adv_adj=False)

    def build_gl_entries(self, preview=False):
        gl_entries = []
        # total_tax = 0
        expense_accounts = []

        pay_account = None
        if (self.mode_of_payment != "Cash" and (not 
        	self.payment_reference or not self.clearance_date)):
        	frappe.throw(
        		title="Enter Payment Reference",
        		msg="Payment Reference and Date are Required for all non-cash payments."
        	)

        pay_account = frappe.db.get_value('Mode of Payment Account', {'parent' : self.mode_of_payment, 'company' : self.company}, 'default_account')

        if not pay_account or pay_account == "":
        	frappe.throw(
        		title="Error",
        		msg="The selected Mode of Payment has no linked account."
        	)
        

        for row in self.expenses:
            expense_accounts.append(row.expense_account)

            gl_entries.append(
                self.get_gl_dict(
                    account=row.expense_account,
                    debit=row.amount,
                    credit=0,
                    against_account=pay_account,
                    remarks=row.description or self.remarks or "Expense",
                    cost_center=row.cost_center or self.default_cost_center,
                    project=row.project or self.default_project or "",
                )
            )

        gl_entries.append(
            self.get_gl_dict(
                account=pay_account,
                debit=0,
                credit=self.total,
                against_account=", ".join(expense_accounts),
                remarks=self.remarks or "Expense Settlement",
                cost_center=self.default_cost_center or "",
                project=self.default_project or "",
            )
        )


        return gl_entries

    def get_gl_dict(
        self,
        account,
        debit=0,
        credit=0,
        against_account=None,
        remarks=None,
        cost_center=None,
        project=None,
    ):

        account_type, is_group = frappe.db.get_value(
            "Account", account, ["account_type", "is_group"]
        )

        if is_group:
            frappe.throw(f"Account {account} is a Group Account")

        account_currency = get_account_currency(account)

        debit = flt(debit)
        credit = flt(credit)

        gl = frappe._dict({
            "posting_date": self.posting_date,
            "company": self.company,
            "voucher_type": self.doctype,
            "voucher_subtype": self.doctype,
            "voucher_no": self.name,

            "account": account,

            "debit": debit,
            "credit": credit,

            "account_currency": account_currency,
            "debit_in_account_currency": debit,
            "credit_in_account_currency": credit,

            "against": against_account,
            "against_account": against_account,

            "cost_center": cost_center,
            "project": project,

            "remarks": remarks,
            "is_opening": "No",
        })

        # Copy every Accounting Dimension from the parent document
        for dimension in get_accounting_dimensions():
            if self.meta.has_field(dimension):
                gl[dimension] = self.get(dimension)

        return gl


@frappe.whitelist()
def get_account_details(mode_of_payment,company,date):
    
    account = frappe.db.get_value(
        "Mode of Payment Account", {"parent": mode_of_payment, "company": company}, "default_account"
    )

    if not account:
        frappe.throw(
            _("Please set default Cash or Bank account in Mode of Payment {0}").format(
                get_link_to_form("Mode of Payment", mode_of_payment)
            ),
            title=_("Missing Account"),
        )

    account_balance = get_balance_on(account, date, ignore_account_permission=True)

    expensesetting = frappe.get_doc('Accounts Settings')

    return {
        'show_balance': expensesetting.show_mode_of_payment_bal,
        'account': account,
        'account_balance': account_balance
    }  
