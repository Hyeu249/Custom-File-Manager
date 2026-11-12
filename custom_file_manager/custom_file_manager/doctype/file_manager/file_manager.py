# Copyright (c) 2026, freelancer and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
import boto3

class FileManager(Document):

    def before_save(self):
        frappe.msgprint(
            f"""
            <b>Boto3 hoạt động thành công!</b><br>
            Version: {boto3.__version__}
            """,
            title="Wasabi Integration",
            indicator="green"
        )
