import frappe
from frappe import _


@frappe.whitelist()
def register_fcm_token(token):
	token = (token or "").strip()
	if not token:
		frappe.throw(_("token is required"))
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required"), frappe.PermissionError)

	user = frappe.session.user

	if frappe.db.exists("FCM Device Token", token):
		doc = frappe.get_doc("FCM Device Token", token)
		doc.user = user
		doc.save(ignore_permissions=True)
		action = "updated"
	else:
		doc = frappe.get_doc(
			{
				"doctype": "FCM Device Token",
				"token": token,
				"user": user,
			}
		)
		doc.insert(ignore_permissions=True)
		action = "created"

	frappe.db.commit()
	return {"status": "registered", "action": action}


@frappe.whitelist()
def delete_fcm_token(token):
	token = (token or "").strip()
	if not token:
		frappe.throw(_("token is required"))
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required"), frappe.PermissionError)

	row = frappe.db.get_value("FCM Device Token", token, ["name", "user"], as_dict=True)
	if not row:
		return {"status": "not_found"}

	is_owner = row.user == frappe.session.user
	is_sysmanager = "System Manager" in frappe.get_roles(frappe.session.user)
	if not (is_owner or is_sysmanager):
		frappe.throw(_("Not permitted to delete this token"), frappe.PermissionError)

	frappe.delete_doc("FCM Device Token", row.name, ignore_permissions=True)
	frappe.db.commit()
	return {"status": "deleted"}
