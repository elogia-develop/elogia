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

    @api.depends('start_datetime', 'end_datetime', 'employee_id.resource_calendar_id',
                 'company_id.resource_calendar_id', 'allocated_percentage', 'role_id', 'project_id', 'task_id')
    def _compute_allocated_hours(self):
        percentage_field = self._fields['allocated_percentage']
        self.env.remove_to_compute(percentage_field, self)
        for slot in self:
            if slot.start_datetime and slot.end_datetime:
                ratio = slot.allocated_percentage / 100.0 or 1
                if slot.allocation_type == 'planning':
                    slot.allocated_hours = slot._get_slot_duration() * ratio
                else:
                    calendar = slot.employee_id.resource_calendar_id or slot.company_id.resource_calendar_id
                    hours = calendar.get_work_hours_count(slot.start_datetime,
                                                          slot.end_datetime) if calendar else slot._get_slot_duration()
                    slot.allocated_hours = hours * ratio
            else:
                slot.allocated_hours = 0.0
            if slot.allocated_hours > 0:
                calendar_combine = slot.employee_id.resource_calendar_id or slot.company_id.resource_calendar_id
                hours_by_combine = calendar_combine.get_work_hours_count(slot.start_datetime, slot.end_datetime) \
                    if calendar_combine else slot._get_slot_duration()
                if slot.allocated_hours > hours_by_combine:
                    raise UserError(_("The maximum limit for this planning must not exceed %s hours per day.")
                                    % slot.resource_id.calendar_id.hours_per_day)

    def _get_slot_duration(self):
        """Return the slot (effective) duration expressed in hours.
        """
        self.ensure_one()
        if (self.end_datetime - self.start_datetime).days < 1 and self.company_id.resource_calendar_id:
            return self.company_id.resource_calendar_id.hours_per_day
        else:
            return (self.end_datetime - self.start_datetime).total_seconds() / 3600.0


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.constrains('unit_amount', 'employee_id')
    def _check_unit_amount(self):
        for record in self:
            if record.unit_amount and record.employee_id.resource_calendar_id:
                if record.unit_amount > record.employee_id.resource_calendar_id.hours_per_day:
                    raise UserError(_("The maximum limit for this timesheet must not exceed %s hours per day.")
                                    % record.employee_id.resource_calendar_id.hours_per_day)
