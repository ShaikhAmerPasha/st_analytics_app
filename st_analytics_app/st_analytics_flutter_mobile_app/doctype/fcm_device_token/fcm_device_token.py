import frappe
from frappe.model.document import Document


class FCMDeviceToken(Document):
	def before_save(self):
		self.last_updated = frappe.utils.now_datetime()
