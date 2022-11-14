import frappe
from frappe import _
from frappe import utils


def setup(expense_entry, method):
    # add expenses up and set the total field
    # add default project and cost center to expense items

    make_journal_entry(expense_entry)


@frappe.whitelist()
def initialise_journal_entry(expense_entry_name):
    # make JE from javascript form Make JE button

    make_journal_entry(
        frappe.get_doc('Expense Entry', expense_entry_name)
    )


def make_journal_entry(expense_entry):
        pr_name = frappe.db.get_value("Journal Entry",{"bill_no": expense_entry.name}, "name")
        
        pr = frappe.get_doc("Journal Entry", pr_name)
        pr.cancel()

   
