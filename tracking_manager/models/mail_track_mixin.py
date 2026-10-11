# Copyright 2025 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models
from odoo.tools import html2plaintext


class MailTrackMixin(models.AbstractModel):
    _inherit = "mail.track.mixin"

    def _create_mail_tracking_values(
        self, initial_value, new_value, col_name, col_info
    ):
        try:
            return super()._create_mail_tracking_values(
                initial_value, new_value, col_name, col_info
            )
        except NotImplementedError:
            if col_info["type"] == "html":
                field = self.env["ir.model.fields"]._get(self._name, col_name)
                old_value = html2plaintext(initial_value) or ""
                new_value = html2plaintext(new_value) or ""
                return {
                    "field_id": field.id,
                    "field_name": col_name,
                    "field_label": col_info.get("string") or field.field_description,
                    "field_type": col_info["type"],
                    "old_value": old_value or "None",
                    "new_value": new_value or "None",
                    "old_value_char": old_value,
                    "new_value_char": new_value,
                }
            raise
