# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Task(models.Model):
    _inherit = "project.task"

    action_user_id = fields.Many2one('res.users', string="Action required by", help='Action required by any user',
                                     tracking=1)

    @api.constrains('timesheet_ids', 'parent_id')
    def _check_subtask(self):
        for record in self:
            if record.timesheet_ids and record.parent_id:
                raise UserError(_('You cannot charge hours into a child task. Contact with an Administrator.'))
            if any(item for item in record.timesheet_ids if not item.employee_id.timesheet_cost):
                raise UserError(_('You cannot charge hours because the Employee does not have a Cost. '
                                  'Contact with an Administrator.'))


class Planning(models.Model):
    _inherit = 'planning.slot'

    role_id = fields.Many2one('planning.role', string="Hub", compute="_compute_role_id", store=True, readonly=False,
                              copy=True, group_expand='_read_group_role_id')

    def _read_group_role_id(self, roles, domain, order):
        res = super(Planning, self)._read_group_role_id(roles, domain, order)
        return res

    @api.depends('employee_id', 'template_id')
    def _compute_role_id(self):
        res = super(Planning, self)._compute_role_id()
        return res
