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

    @api.depends('start_datetime', 'end_datetime', 'employee_id.resource_calendar_id', 'allocated_hours')
    def _compute_allocated_percentage(self):
        res = super(Planning, self)._compute_allocated_percentage()
        for slot in self:
            if slot.allocated_percentage > 100:
                raise UserError(_("The maximum limit for this planning must not exceed 100%."))
            # list_slots = [item for item in self.search([('employee_id', '=', slot.employee_id.id)])]
            # if slot.start_datetime.date() in [item.start_datetime.date() for item in list_slots]:
            #     if sum([item.allocated_percentage for item in list_slots]) > 100:
            #         check_process = True
        return res


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.constrains('unit_amount', 'employee_id')
    def _check_unit_amount(self):
        for record in self:
            if record.unit_amount and record.employee_id.resource_calendar_id:
                if record.unit_amount > record.employee_id.resource_calendar_id.hours_per_day:
                    raise UserError(_("The maximum limit for this timesheet must not exceed %s hours per day.")
                                    % record.employee_id.resource_calendar_id.hours_per_day)
