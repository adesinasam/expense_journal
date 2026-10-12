import frappe


def execute():
	"""Clearance Date used to hold the payment reference date.

	Copy it into the new Reference Date field, then empty Clearance Date on
	entries that have not been matched to a bank transaction, so they show up
	as uncleared in Mint.
	"""
	if not frappe.db.has_column("Expense Entry", "reference_date"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabExpense Entry`
		SET reference_date = clearance_date
		WHERE reference_date IS NULL AND clearance_date IS NOT NULL
		"""
	)

	frappe.db.sql(
		"""
		UPDATE `tabExpense Entry` ee
		SET ee.clearance_date = NULL
		WHERE ee.clearance_date IS NOT NULL
		AND NOT EXISTS (
			SELECT 1 FROM `tabBank Transaction Payments` btp
			WHERE btp.payment_document = 'Expense Entry'
			AND btp.payment_entry = ee.name
		)
		"""
	)
