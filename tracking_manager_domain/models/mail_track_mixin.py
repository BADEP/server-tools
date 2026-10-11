# Copyright 2025 glueckkanja AG (<https://www.glueckkanja.com>) - Christopher Rogos
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from ast import literal_eval

from odoo import models


class MailTrackMixin(models.AbstractModel):
    _inherit = "mail.track.mixin"

    def _mail_track(self, tracked_fields_get, initial_values):
        changes, tracking_values = super()._mail_track(
            tracked_fields_get, initial_values
        )

        # TODO: add properties support on domain filters
        tracking_value_field_ids = [
            tracking_value["field_id"]
            for tracking_value in tracking_values
            if "field_id" in tracking_value
        ]
        if tracking_value_field_ids:
            all_tracking_domain_fields = self._tm_all_tracking_domain_fields()[
                self._name
            ]

            if all_tracking_domain_fields:
                # remove entries that are not matching the tracking_domain of the field
                fields_to_remove = {}
                for field_name in tracked_fields_get:
                    field_data = all_tracking_domain_fields.get(field_name, False)
                    if field_data and not self.filtered_domain(
                        literal_eval(field_data["tracking_domain"])
                    ):
                        fields_to_remove[field_data["id"]] = field_name
                # remove values from tracking result
                changes = {
                    change
                    for change in changes
                    if change not in fields_to_remove.values()
                }
                tracking_values = [
                    tracking_value
                    for tracking_value in tracking_values
                    if tracking_value.get("field_id") not in fields_to_remove
                ]
        return changes, tracking_values
