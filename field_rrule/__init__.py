# -*- coding: utf-8 -*-
# © 2016 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import socket
from .field_rrule import FieldRRule
if socket.getfqdn().endswith('odoo-community.org'):
    import demo
