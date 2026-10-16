# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class IrModel(models.Model):
    _inherit = "ir.model"

    @api.ondelete(at_uninstall=False)
    def _unlink_auditlog_rule_actions(self):
        """Remove the 'View logs' actions of the rules on the deleted models.

        Both the action (binding_model_id, cascade) and the rule (model_id,
        set null) are affected by the same DELETE on ir_model, which makes
        PostgreSQL fail on the rule's action_id foreign key.
        """
        rules = self.env["auditlog.rule"].sudo().search([("model_id", "in", self.ids)])
        rules.action_id.unlink()
