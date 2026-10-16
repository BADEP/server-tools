# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from contextlib import contextmanager
from unittest.mock import patch

import odoo
from odoo.tests import common
from odoo.tests.common import BaseCase, tagged

ADMIN_USER_ID = common.ADMIN_USER_ID


@contextmanager
def environment():
    """Return an environment with a new cursor for the current database; the
    cursor is committed and closed after the context block.
    """
    registry = odoo.modules.registry.Registry(common.get_db_name())
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, ADMIN_USER_ID, {})
        env.user.group_ids |= env.ref("base.group_system")
        yield env


# Use post_install to get all models loaded more info: odoo/odoo#13458
@tagged("post_install", "-at_install")
class Common(BaseCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Odoo 20 forbids reloading the registry during tests: simulate the
        # inter-process signaling like TransactionCase does, as these tests
        # use real (committed) cursors.
        registry = odoo.modules.registry.Registry(common.get_db_name())

        def signal_changes(cr, names):
            if "registry" in names:
                registry.registry_sequence += 1
                for key, (seq, _data) in registry.registry_caches__.items():
                    registry.registry_caches__[key] = (seq + 1, {})
            else:
                for name in names:
                    seq = registry.registry_caches__[name][0]
                    registry.registry_caches__[name] = (seq + 1, {})

        def get_sequences(cr):
            return registry.registry_sequence, {
                name: val[0] for name, val in registry.registry_caches__.items()
            }

        cls.startClassPatcher(patch.object(registry, "_signal_changes", signal_changes))
        cls.startClassPatcher(patch.object(registry, "get_sequences", get_sequences))
