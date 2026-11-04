"""Durable Data Request notification-intent record.

Delivery and retry processing are implemented separately.
No ticket hook or email dispatch is activated by this controller.
"""

from frappe.model.document import Document


class TELECTRODataRequestNotificationIntent(Document):
    pass
