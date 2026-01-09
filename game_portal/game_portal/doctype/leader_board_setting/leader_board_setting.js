// Copyright (c) 2025, hailemaryam and contributors
// For license information, please see license.txt

frappe.ui.form.on("Leader Board Setting", {
	refresh(frm) {
		// Add click handler for Clear Point button
		if (frm.fields_dict.clear_points_button) {
			frm.fields_dict.clear_points_button.$input.on("click", function() {
				// Show confirmation dialog
				frappe.confirm(
					__("Are you sure you want to clear all subscription points? This action cannot be undone."),
					function() {
						// User confirmed
						frappe.call({
							method: "game_portal.game_portal.doctype.leader_board_setting.leader_board_setting.clear_all_points",
							callback: function(r) {
								if (r.message && r.message.success) {
									frappe.show_alert({
										message: __(r.message.message),
										indicator: "green"
									}, 5);
									frm.reload_doc();
								} else {
									frappe.show_alert({
										message: __(r.message.message || "Failed to clear points"),
										indicator: "red"
									}, 5);
								}
							},
							error: function(r) {
								frappe.show_alert({
									message: __("An error occurred while clearing points"),
									indicator: "red"
								}, 5);
							}
						});
					},
					function() {
						// User cancelled - do nothing
					}
				);
			});
		}
	},
});
