# -*- coding: utf-8 -*-
# import json
# from lxml import etree
# from datetime import datetime, timedelta, date
# from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
# from odoo.tools import float_is_zero, float_compare
# from odoo.tools.misc import formatLang
# from odoo.exceptions import UserError, RedirectWarning, ValidationError
# import odoo.addons.decimal_precision as dp
#from cStringIO import StringIO
# import os
# import re
# import hashlib
# import tempfile
# import pytz
# import logging
# _logger = logging.getLogger(__name__)


class BimAccountMove(models.Model):
    _inherit = "account.move"
    
    #presupuesto_id = fields.Many2one('bim.presupuesto','Presupuesto', ondelete="restrict")
    project_id = fields.Many2one('bim.project','Obra', track_visibility='onchange')
    workorder_id = fields.Many2one('bim.work.order', 'Pedido de Trabajo')
    maintenance_id = fields.Many2one('bim.maintenance','Mantenimiento', track_visibility='onchange')
