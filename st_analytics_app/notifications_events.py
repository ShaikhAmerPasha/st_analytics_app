import frappe


def _enqueue(job_id, title, body, data, target_users=None):
	frappe.enqueue(
		"st_analytics_app.notifications.send_fcm_notification",
		queue="short",
		timeout=45,
		job_id=job_id,
		deduplicate=True,
		title=title,
		body=body,
		data=data,
		target_users=target_users,
	)


def on_employee_checkin(doc, method=None):
	is_in = doc.log_type == "IN"
	_enqueue(
		f"fcm-checkin-{doc.name}",
		title="Checked In" if is_in else "Checked Out",
		body=f"{doc.employee_name} has checked {'in' if is_in else 'out'}",
		data={
			"type": "checkin" if is_in else "checkout",
			"employee": doc.employee or "",
			"employee_name": doc.employee_name or "",
			"time": str(doc.time or ""),
		},
	)


def on_daily_task_created(doc, method=None):
	desc = (doc.description or "").strip()[:80]
	_enqueue(
		f"fcm-task-created-{doc.name}",
		title="New Task",
		body=f"{doc.employee_name}: {desc}" if desc else f"New task assigned to {doc.employee_name}",
		data={
			"type": "task_created",
			"task_id": doc.name or "",
			"employee": doc.employee or "",
			"employee_name": doc.employee_name or "",
			"status": doc.status or "",
		},
	)


def on_daily_task_status_change(doc, method=None):
	before = doc.get_doc_before_save()
	if not before or before.status == doc.status:
		return

	desc = (doc.description or "").strip()[:60]
	_enqueue(
		f"fcm-task-status-{doc.name}-{doc.modified}",
		title="Task Status Updated",
		body=f"{doc.employee_name}: {desc} -> {doc.status}" if desc else f"Task updated for {doc.employee_name}",
		data={
			"type": "task_status",
			"task_id": doc.name or "",
			"employee": doc.employee or "",
			"employee_name": doc.employee_name or "",
			"status": doc.status or "",
		},
	)


def on_daily_task_deleted(doc, method=None):
	desc = (doc.description or "").strip()[:60]
	_enqueue(
		f"fcm-task-deleted-{doc.name}",
		title="Task Removed",
		body=f"Task '{desc}' assigned to {doc.employee_name} was removed",
		data={
			"type": "task_deleted",
			"task_id": doc.name or "",
			"employee": doc.employee or "",
			"employee_name": doc.employee_name or "",
		},
	)


def on_attendance_submit(doc, method=None):
	date_str = str(doc.attendance_date or "")

	if doc.status == "Absent":
		_enqueue(
			f"fcm-attendance-absent-{doc.name}",
			title="Attendance: Absent",
			body=f"{doc.employee_name} marked absent for {date_str}",
			data={
				"type": "absent",
				"employee": doc.employee or "",
				"employee_name": doc.employee_name or "",
				"date": date_str,
			},
		)
	elif doc.late_entry:
		_enqueue(
			f"fcm-attendance-late-{doc.name}",
			title="Attendance: Late",
			body=f"{doc.employee_name} arrived late on {date_str}",
			data={
				"type": "late",
				"employee": doc.employee or "",
				"employee_name": doc.employee_name or "",
				"date": date_str,
			},
		)


def on_leave_application_submit(doc, method=None):
	if doc.status != "Approved":
		return

	from_date = str(doc.from_date or "")
	_enqueue(
		f"fcm-leave-approved-{doc.name}",
		title="Leave Approved",
		body=f"{doc.employee_name}'s {doc.leave_type} leave was approved",
		data={
			"type": "leave",
			"employee": doc.employee or "",
			"employee_name": doc.employee_name or "",
			"leave_type": doc.leave_type or "",
			"date": from_date,
		},
	)
