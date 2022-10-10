# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from calendar import monthrange
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_utils, format_datetime


class CopyMonthWizard(models.TransientModel):
    _name = 'copy.month.wizard'
    _description = 'Copy Month Wizard'

    name = fields.Char('Name', index=True, default='/')
    slot_ids = fields.Many2many('planning.slot', 'copy_planning_rel', 'copy_id', 'slot_id', string='Planning slot')
    start_datetime = fields.Datetime('Start date')
    end_datetime = fields.Datetime('End date')
    more_info = fields.Text('Error info.')

    def check_any_value(self, list_error):
        value_slot_ids = [item['item'].id for item in list_error]
        return value_slot_ids

    def remove_slot(self, slot, list_ok):
        if slot.id in list_ok:
            list_ok.remove(slot.id)

    def check_create_slot(self, view_slot, init_date, end_date, view_slot_origin):
        slot_filters = False
        slot_errors = ''
        list_ok = []
        list_error = []
        val_errors = ''
        env_leave = self.env['hr.leave'].search([('state', 'not in', ['draft', 'refuse']),
                                                 ('date_from', '>=', init_date), ('date_to', '<=', end_date)])
        for slot in view_slot:
            next_month = slot.end_datetime.date() + relativedelta(months=1)
            leave_filter = env_leave.filtered(lambda e: e.date_from.date() <= next_month <= e.date_to.date())
            contract = slot.employee_id.contract_id
            if contract:
                list_ok.append(slot.id)
                if contract.state in ['close', 'cancel']:
                    if slot.id not in self.check_any_value(list_error):
                        list_error.append({'error': 'contract_valid', 'item': slot})
                    self.remove_slot(slot, list_ok)
                if contract.date_start > init_date.date():
                    if slot.id not in self.check_any_value(list_error):
                        list_error.append({'error': 'date_init', 'item': slot})
                    self.remove_slot(slot, list_ok)
                if contract.date_end < end_date.date() and next_month > contract.date_end:
                    if slot.id not in self.check_any_value(list_error):
                        list_error.append({'error': 'date_end', 'item': slot})
                    self.remove_slot(slot, list_ok)
            else:
                if slot.id not in self.check_any_value(list_error):
                    list_error.append({'error': 'not_contract', 'item': slot})
                self.remove_slot(slot, list_ok)
            slot_filter_duple = view_slot_origin.filtered(lambda e: e.end_datetime.date() == next_month)
            if slot_filter_duple:
                if slot.id not in self.check_any_value(list_error):
                    list_error.append({'error': 'duplicity', 'item': slot})
                self.remove_slot(slot, list_ok)
            if any(employee for employee in leave_filter.mapped('employee_ids') if leave_filter and employee == slot.employee_id):
                if slot.id not in self.check_any_value(list_error):
                    list_error.append({'error': 'time', 'item': slot})
                self.remove_slot(slot, list_ok)
            if slot.project_id:
                contact = slot.employee_id.address_home_id
                if contact.id not in slot.project_id.message_follower_ids.mapped('partner_id').ids:
                    if slot.id not in self.check_any_value(list_error):
                        list_error.append({'error': 'not_project', 'item': slot})
                    self.remove_slot(slot, list_ok)
                if slot.project_id.date < next_month:
                    if slot.id not in self.check_any_value(list_error):
                        list_error.append({'error': 'not_project_date', 'item': slot})
                    self.remove_slot(slot, list_ok)
            if slot.task_id:
                user = slot.employee_id.user_id
                if user.id not in slot.task_id.user_ids.ids:
                    if slot.id not in self.check_any_value(list_error):
                        list_error.append({'error': 'not_task', 'item': slot})
                    self.remove_slot(slot, list_ok)
                if slot.task_id.date_deadline < next_month:
                    if slot.id not in self.check_any_value(list_error):
                        list_error.append({'error': 'not_task_date', 'item': slot})
                    self.remove_slot(slot, list_ok)
        if list_ok:
            slot_filters = view_slot.filtered(lambda e: e.id in list_ok)
        if list_error:
            for item in list_error:
                if item['error'] == 'not_contract':
                    for i in item['item']:
                        val_errors += '[{}:{}] - {} does not have an associated contract. \n' \
                            .format(i.start_datetime.date(), i.end_datetime.date(), i.employee_id.name)
                if item['error'] == 'contract_valid':
                    for i in item['item']:
                        val_errors += '[{}:{}] - Its required that the contract associated with ' \
                                      'the employee {} is not Expired or Cancelled.\n' \
                            .format(i.start_datetime.date(), i.end_datetime.date(), i.employee_id.name)
                if item['error'] == 'date_init':
                    for i in item['item']:
                        val_errors += '[{}:{}] - The employee/resource {} should not be working in this period. ' \
                                      'Check the start date of the Contract.\n' \
                            .format(i.start_datetime.date(), i.end_datetime.date(), i.employee_id.name)
                if item['error'] == 'date_end':
                    for i in item['item']:
                        val_errors += '[{}:{}] - The employee/resource {} should not be working in this period. ' \
                                      'Check end date of the Contract.\n' \
                            .format(i.start_datetime.date(), i.end_datetime.date(), i.employee_id.name)
                if item['error'] == 'duplicity':
                    for i in item['item']:
                        val_errors += '[{}:{}] - There are planning for {} at the same time.\n' \
                            .format(i.start_datetime.date(), i.end_datetime.date(), i.employee_id.name)
                if item['error'] == 'duplicity':
                    for i in item['item']:
                        val_errors += '[{}:{}] - {} has requested time off in this period.\n' \
                            .format(i.start_datetime.date(), i.end_datetime.date(), i.employee_id.name)
                if item['error'] == 'not_project':
                    for i in item['item']:
                        val_errors += '[{}:{}] - {} cannot have planning on project {}.\n' \
                            .format(i.start_datetime.date(), i.end_datetime.date(), i.employee_id.name,
                                    i.project_id.name)
                if item['error'] == 'not_task':
                    for i in item['item']:
                        val_errors += '[{}:{}] - {} cannot have planning on this task {}.\n' \
                            .format(i.start_datetime.date(), i.end_datetime.date(), i.employee_id.name,
                                    i.task_id.name)
                if item['error'] == 'not_project_date':
                    for i in item['item']:
                        val_errors += '[{}:{}] - Expiration date of the project {} is {}.\n' \
                            .format(i.start_datetime.date(), i.end_datetime.date(), i.project_id.name,
                                    i.project_id.date)
                if item['error'] == 'not_task_date':
                    for i in item['item']:
                        val_errors += '[{}:{}] - Expiration date of the task {} is {}.\n' \
                            .format(i.start_datetime.date(), i.end_datetime.date(), i.task_id.name,
                                    i.task_id.date_deadline)
            slot_errors = val_errors
        return slot_filters, slot_errors

    @api.onchange('start_datetime', 'end_datetime', 'slot_ids')
    def onchange_dates(self):
        env_planning = self.env['planning.slot']
        init_date = self.start_datetime
        end_date = self.end_datetime
        if (init_date or end_date) and not self.slot_ids:
            view_slot_origin = env_planning.search([('start_datetime', '>=', init_date),
                                                    ('end_datetime', '<=', end_date),
                                                    ('recurrency_id', '=', False), ('was_copied', '=', False)])
            view_slot = env_planning.search([('start_datetime', '>=', init_date - relativedelta(months=1)),
                                             ('end_datetime', '<=', end_date - relativedelta(months=1)),
                                             ('recurrency_id', '=', False), ('was_copied', '=', False)])
            if view_slot:
                slot_filters = self.check_create_slot(view_slot, init_date, end_date, view_slot_origin)
                self.slot_ids = slot_filters[0]
                self.more_info = slot_filters[1]

    def action_copy_previous_month(self):
        new_slot_values = []
        slots_to_copy = self.slot_ids
        for slot in slots_to_copy:
            if not slot.was_copied:
                values = slot.copy_data()[0]
                if values.get('start_datetime'):
                    values['start_datetime'] += relativedelta(months=1)
                if values.get('end_datetime'):
                    values['end_datetime'] += relativedelta(months=1)
                new_slot_values.append(values)
        if new_slot_values:
            slots_to_copy.write({'was_copied': True})
            self.slot_ids.with_context({'wizard_origin': 'wizard'}).create(new_slot_values)
            return True
        return False


class Task(models.Model):
    _inherit = "project.task"

    action_user_id = fields.Many2one('res.users', string="Action required by", help='Action required by any user',
                                     tracking=1)

    @api.constrains('timesheet_ids', 'parent_id')
    def _check_subtask(self):
        for record in self:
            if record.parent_id:
                if not record.project_id:
                    record.project_id = record.parent_id.project_id.id
                if not record.display_project_id:
                    record.display_project_id = record.parent_id.project_id.id
                if not record.partner_id:
                    record.partner_id = record.parent_id.partner_id.id
                if record.timesheet_ids:
                    raise UserError(_('You cannot charge hours into a child task. Contact with an Administrator.'))
            if any(item for item in record.timesheet_ids if not item.employee_id.timesheet_cost):
                raise UserError(_('You cannot charge hours because the Employee does not have a Cost. '
                                  'Contact with an Administrator.'))

    @api.model
    def create(self, vals_list):
        res = super(Task, self).create(vals_list)
        if res.parent_id:
            if not res.project_id:
                res.project_id = res.parent_id.project_id.id
            if not res.display_project_id:
                res.display_project_id = res.parent_id.project_id.id
            if not res.partner_id:
                res.partner_id = res.parent_id.partner_id.id
        return res


class Planning(models.Model):
    _inherit = 'planning.slot'

    role_id = fields.Many2one('planning.role', string="Hub", compute="_compute_role_id", store=True, readonly=False,
                              copy=True, group_expand='_read_group_role_id')
    hours_available = fields.Float('Hours available')
    total_hours = fields.Float('Total Hours')

    @api.constrains('employee_id', 'employee_id.contract_id', 'overlap_slot_count', 'allocated_hours', 'start_datetime',
                    'end_datetime', 'project_id', 'project_id.date', 'task_id', 'task_id.date_end')
    def _check_employee_amount(self):
        env_planning = self.env['planning.slot']
        val_total = 0
        for record in self:
            calendar_combine = record.employee_id.resource_calendar_id or record.company_id.resource_calendar_id
            hours_by_combine = calendar_combine.get_work_hours_count(record.start_datetime, record.end_datetime,
                                                                     compute_leaves=True) if calendar_combine else \
                record._get_slot_duration()
            first_day = record.start_datetime.replace(day=1)
            daysInMonth = monthrange(first_day.year, first_day.month)[1]
            last_day = record.start_datetime.replace(day=daysInMonth)
            total_hours_by_combine = calendar_combine.get_work_hours_count(first_day, last_day,
                                                                     compute_leaves=True) if calendar_combine else \
                record._get_slot_duration()

            obj_planning = env_planning.search([('employee_id', '=', record.employee_id.id),
                                                ('start_datetime', '>=', first_day), ('end_datetime', '<=', last_day)])
            if obj_planning:
                val_total = total_hours_by_combine - sum(obj_planning.mapped('allocated_hours'))
            record.total_hours = val_total
            record.hours_available = record.total_hours - record.allocated_hours
            if 'wizard_origin' not in self._context:
                if record.employee_id:
                    if not record.employee_id.contract_id:
                        raise UserError(_('Employee {} does not have an associated contract.' .format(record.employee_id.name)))
                    else:
                        if record.employee_id.contract_id.state in ['close', 'cancel']:
                            raise UserError(_('It is required that the contract associated with the employee {} is not '
                                              'Expired or Cancelled.'.format(record.employee_id.name)))
                        if record.employee_id.contract_id.date_start > record.start_datetime.date():
                            raise UserError(_('The employee/resource should not be working in this period. \n Check the '
                                              'start date/end date of the Contract or contact an Administrator.'))
                    if record.overlap_slot_count:
                        raise UserError(_('There are {} planning for this resource at the same time.'
                                          .format(record.overlap_slot_count)))
                    if record.is_absent:
                        raise UserError(_('{} has requested time off in this period.' .format(record.employee_id.name)))
                    if record.allocated_hours > hours_by_combine:
                        raise UserError(_("The planning for this resource exceed in {} hours."
                                          .format(record.allocated_hours - hours_by_combine)))
                    if record.project_id:
                        contact = record.employee_id.address_home_id
                        if contact.id not in record.project_id.message_follower_ids.mapped('partner_id').ids:
                            raise UserError(_('{} cannot have planning on this project.' .format(record.employee_id.name)))
                        if record.project_id.date < record.end_datetime.date():
                            raise UserError(_('The expiration date of the project is {}.' .format(record.project_id.date)))
                    if record.task_id:
                        user = record.employee_id.user_id
                        if user.id not in record.task_id.user_ids.ids:
                            raise UserError(_('{} cannot have planning on this task.' .format(record.employee_id.name)))
                        if record.task_id.date_deadline < record.end_datetime.date():
                            raise UserError(_('The expiration date of the task is {}.' .format(record.task_id.date_deadline)))

    @api.depends('start_datetime', 'end_datetime', 'employee_id.resource_calendar_id',
                 'company_id.resource_calendar_id', 'allocated_percentage', 'role_id', 'project_id',
                 'task_id')
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
