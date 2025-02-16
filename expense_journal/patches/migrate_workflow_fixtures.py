# patches/migrate_workflow_fixtures.py
import frappe

def execute():
    # Define the Workflow fixtures you want to add
    workflows = [
        {"name": "Expense Approval"},  # Replace with your workflow name
    ]

    for workflow in workflows:
        # Check if the workflow already exists
        if not frappe.db.exists("Workflow", workflow["name"]):
            # Load the workflow fixture if it doesn't exist
            frappe.get_doc({
                "doctype": "Fixture",
                "app": "expense_journal",  # Replace with your app name
                "fixture": "Workflow",
                "filters": [["name", "=", workflow["name"]]]
            }).insert()
            frappe.db.commit()