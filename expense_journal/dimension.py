import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def create_dimension_fields(doc=None, method=None):
    dimensions = frappe.get_all(
        "Accounting Dimension",
        fields=["fieldname", "label", "document_type"]
    )

    if not dimensions:
        return

    custom_fields = {"Expense Entry": []}

    existing = frappe.get_all(
        "Custom Field",
        filters={"dt": "Expense Entry"},
        pluck="fieldname"
    )

    for d in dimensions:
        if d.fieldname not in existing:
            custom_fields["Expense Entry"].append({
                "fieldname": d.fieldname,
                "label": d.label,
                "fieldtype": "Link",
                "options": d.document_type,
                "insert_after": "default_project",
            })

    if custom_fields["Expense Entry"]:
        create_custom_fields(custom_fields)