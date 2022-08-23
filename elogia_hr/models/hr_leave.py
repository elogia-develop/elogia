# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    calendar_id = fields.Many2one('resource.calendar', 'Agreement', index=True)
