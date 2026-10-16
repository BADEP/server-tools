import logging

# ruff: noqa
from odoo import models

from odoo.addons.base.models import ir_model

from ...... import upgrade_log
from .....odoo_patch import OdooPatch

_logger = logging.getLogger(__name__)


class IrModelConstraintPatch(OdooPatch):
    target = ir_model.IrModelConstraint
    method_names = ["_reflect_table_object"]

    def _reflect_table_object(self, model):
        """Reflect the _table_objects of the given model."""
        data_list = []
        for conname, cons in model._table_objects.items():
            module = cons._module
            if not conname or not module:
                _logger.warning("Missing module or constraint name for %s", cons)
                continue
            definition = cons.get_definition(model.pool)
            message = cons.message
            if not isinstance(message, str) or not message:
                message = None
            typ = "i" if isinstance(cons, models.Index) else "u"
            record = self._reflect_constraint(
                model, conname, typ, definition, module, message
            )
            xml_id = "%s.constraint_%s" % (module, conname)
            if record:
                data_list.append(dict(xml_id=xml_id, record=record))
            # Begin OpenUpgrade addition
            upgrade_log.log_xml_id(self.env.cr, module, xml_id)
            # End OpenUpgrade addition
        return data_list
