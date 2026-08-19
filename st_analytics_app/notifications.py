import frappe
import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
FCM_CHANNEL_ID = "st_tracker_alerts"


def _get_access_token():
	sa_path = frappe.conf.get("firebase_service_account_path")
	if not sa_path:
		frappe.throw("firebase_service_account_path not configured in site_config.json")

	creds = service_account.Credentials.from_service_account_file(sa_path, scopes=[FCM_SCOPE])
	creds.refresh(Request())
	return creds.token, creds.project_id


def _send_to_token(token, title, body, data, access_token, project_id):
	url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
	payload = {
		"message": {
			"token": token,
			"notification": {"title": title, "body": body},
			"data": {str(k): str(v) for k, v in (data or {}).items()},
			"android": {
				"priority": "high",
				"notification": {
					"channel_id": FCM_CHANNEL_ID,
					"sound": "default",
					"default_vibrate_timings": True,
				},
			},
			"apns": {
				"headers": {"apns-priority": "10"},
				"payload": {
					"aps": {
						"alert": {"title": title, "body": body},
						"sound": "default",
						"content-available": 1,
					}
				},
			},
		}
	}
	resp = requests.post(
		url,
		json=payload,
		headers={
			"Authorization": f"Bearer {access_token}",
			"Content-Type": "application/json; charset=UTF-8",
		},
		timeout=10,
	)
	if resp.status_code in (400, 404):
		return False
	if resp.status_code >= 400:
		frappe.log_error("FCM Send Error", f"token={token} status={resp.status_code} body={resp.text[:1000]}")
	return True


def send_fcm_notification(title, body, data=None, target_users=None):
	filters = {}
	if target_users:
		if isinstance(target_users, str):
			target_users = [target_users]
		filters["user"] = ["in", target_users]

	rows = frappe.get_all("FCM Device Token", filters=filters, fields=["name", "token"])
	if not rows:
		return

	try:
		access_token, project_id = _get_access_token()
	except Exception:
		frappe.log_error("FCM Auth Error", frappe.get_traceback())
		return

	dead_rows = []
	for row in rows:
		try:
			if not _send_to_token(row.token, title, body, data, access_token, project_id):
				dead_rows.append(row.name)
		except Exception:
			frappe.log_error("FCM Send Exception", frappe.get_traceback())

	for name in dead_rows:
		frappe.delete_doc("FCM Device Token", name, ignore_permissions=True, force=True)
	if dead_rows:
		frappe.db.commit()
