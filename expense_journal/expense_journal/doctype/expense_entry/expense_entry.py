# -*- coding: utf-8 -*-
# Copyright (c) 2020, Bantoo and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

import erpnext
from erpnext.accounts.utils import (
	get_account_currency,
	get_balance_on,
)

class ExpenseEntry(Document):
	def validate(self):
		validate_cost_center_company()
		validate_account_companies()

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
				cost_center_company = frappe.db.get_value("Account", item.cost_center, "company")

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
