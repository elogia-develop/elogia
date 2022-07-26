# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class Task(models.Model):
    _inherit = "project.task"

    action_id = fields.Many2one('res.users', string="Action required by", help='Action required by any user', tracking=1)
