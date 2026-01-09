# Copyright (c) 2025, hailemaryam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class LeaderBoardSetting(Document):
	pass


@frappe.whitelist()
def clear_all_points():
	"""Clear all point values in Subscription doctype to 0"""
	try:
		# Update all subscription records to set point = 0
		frappe.db.sql("""
			UPDATE `tabSubscription`
			SET point = 0
		""")
		frappe.db.commit()
		
		return {
			"success": True,
			"message": "All subscription points have been cleared successfully."
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Clear Points Error")
		return {
			"success": False,
			"message": f"Failed to clear points: {str(e)}"
		}
