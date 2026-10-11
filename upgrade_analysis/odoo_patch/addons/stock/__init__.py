# flake8: noqa: B902
from typing import ClassVar

from odoo.addons import stock
from ...odoo_patch import OdooPatch


class PreInitHookPatch(OdooPatch):
    target = stock
    method_names: ClassVar[list[str]] = ["pre_init_hook"]

    def pre_init_hook(cr):
        """Don't unlink stock data on reinstall"""
