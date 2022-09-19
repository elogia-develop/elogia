# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from calendar import monthrange
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_utils, format_datetime


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
    hours_available = fields.Float('Hours available')

    @api.model
    def create(self, vals):
        res = super(Planning, self).create(vals)
        calendar_combine = res.employee_id.resource_calendar_id or res.company_id.resource_calendar_id
        hours_by_combine = calendar_combine.get_work_hours_count(res.start_datetime, res.end_datetime) \
            if calendar_combine else res._get_slot_duration()
        res.hours_available = hours_by_combine if hours_by_combine else 0
        return res

    @api.model
    def action_copy_previous_month(self, date_start_week, view_domain):
        date_end_copy = datetime.strptime(date_start_week, DEFAULT_SERVER_DATETIME_FORMAT)
        daysInMonth = monthrange(date_end_copy.year, date_end_copy.month)[1]
        date_start_copy = date_end_copy - relativedelta(days=daysInMonth)
        domain = [
            ('recurrency_id', '=', False),
            ('was_copied', '=', False)
        ]
        for dom in view_domain:
            if dom in ['|', '&', '!']:
                domain.append(dom)
            elif dom[0] == 'start_datetime':
                domain.append(('start_datetime', '>=', date_start_copy))
            elif dom[0] == 'end_datetime':
                domain.append(('end_datetime', '<=', date_end_copy))
            else:
                domain.append(tuple(dom))
        slots_to_copy = self.search(domain)
        new_slot_values = []
        new_slot_values = slots_to_copy._copy_slots(date_start_copy, date_end_copy, relativedelta(days=daysInMonth))
        slots_to_copy.write({'was_copied': True})
        if new_slot_values:
            self.create(new_slot_values)
            return True
        return False

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
            if (slot.employee_id.resource_calendar_id or slot.company_id.resource_calendar_id) and slot.allocated_hours > 0:
                calendar_combine = slot.employee_id.resource_calendar_id or slot.company_id.resource_calendar_id
                hours_by_combine = calendar_combine.get_work_hours_count(slot.start_datetime, slot.end_datetime) \
                    if calendar_combine else slot._get_slot_duration()
                if slot.allocated_hours > hours_by_combine:
                    raise UserError(_("The maximum limit for this planning must not exceed %s hours per day.")
                                    % hours_by_combine)

    def _get_slot_duration(self):
        """Return the slot (effective) duration expressed in hours.
        """
        self.ensure_one()
        if (self.end_datetime - self.start_datetime).days < 1 and self.resource_id.calendar_id or \
                self.company_id.resource_calendar_id:
            if self.resource_id.calendar_id:
                return self.resource_id.calendar_id.get_work_hours_count(self.start_datetime, self.end_datetime)
            elif self.company_id.resource_calendar_id:
                return self.company_id.resource_calendar_id.hours_per_day
            else:
                pass
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
