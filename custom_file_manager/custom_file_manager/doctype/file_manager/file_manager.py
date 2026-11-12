
# Copyright (c) 2026, freelancer and contributors
# For license information, please see license.txt

import os
import frappe
import boto3
import mimetypes

from botocore.exceptions import ClientError
from frappe.model.document import Document


class FileManager(Document):

    def on_update(self):
        """
        Upload file lên Wasabi sau khi lưu File Manager.
        Sau khi upload thành công, xóa file local.
        """

        if self.source_type != "Upload File":
            return

        if not self.attachment:
            return

        # Kiểm tra attachment có thay đổi hay không
        previous = self.get_doc_before_save()

        if previous and previous.attachment == self.attachment:
            if self.file_url:
                return

        # Tìm File DocType tương ứng
        file_name = frappe.db.get_value(
            "File",
            {"file_url": self.attachment},
            "name"
        )

        if not file_name:
            frappe.throw("Cannot find attachment in File DocType.")

        file_doc = frappe.get_doc("File", file_name)
        file_path = file_doc.get_full_path()

        if not os.path.isfile(file_path):
            frappe.throw("Local attachment file does not exist.")

        # Tạo object key riêng cho từng tenant
        site_name = frappe.local.site

        object_key = (
            f"{site_name}/"
            f"{self.file_name}"
        )

        content_type, _ = mimetypes.guess_type(file_path)

        # Upload lên Wasabi
        wasabi_url = self.upload_file(
            file_path=file_path,
            object_key=object_key,
            content_type=content_type
        )

        # Chỉ dọn dẹp sau khi upload thành công
        frappe.db.set_value(
            self.doctype,
            self.name,
            {
                "file_url": wasabi_url,
                "attachment": None
            },
            update_modified=False
        )

        self.file_url = wasabi_url
        self.attachment = None

        # Xóa File DocType và file vật lý local
        frappe.delete_doc(
            "File",
            file_doc.name,
            ignore_permissions=True
        )

        frappe.msgprint(
            "File uploaded to Wasabi successfully. "
            "Local attachment has been removed.",
            title="Wasabi Integration",
            indicator="green"
        )

    def get_wasabi_client(self):

        access_key = frappe.conf.get("wasabi_access_key")
        secret_key = frappe.conf.get("wasabi_secret_key")
        region = frappe.conf.get("wasabi_region")
        endpoint_url = frappe.conf.get("wasabi_endpoint_url")

        if not all([access_key, secret_key, region, endpoint_url]):
            frappe.throw("Wasabi configuration is incomplete.")

        return boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            endpoint_url=endpoint_url
        )

    def upload_file(self, file_path, object_key, content_type=None):

        bucket_name = frappe.conf.get("wasabi_bucket_name")

        if not bucket_name:
            frappe.throw("Wasabi bucket name is missing.")

        client = self.get_wasabi_client()

        extra_args = {}

        if content_type:
            extra_args["ContentType"] = content_type

        try:
            client.upload_file(
                file_path,
                bucket_name,
                object_key,
                ExtraArgs=extra_args
            )

            endpoint = frappe.conf.get(
                "wasabi_endpoint_url"
            ).rstrip("/")

            return f"{endpoint}/{bucket_name}/{object_key}"

        except ClientError:
            frappe.log_error(
                frappe.get_traceback(),
                "Wasabi Upload Error"
            )
            frappe.throw("Failed to upload file to Wasabi.")
