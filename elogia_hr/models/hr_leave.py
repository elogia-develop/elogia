# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    calendar_id = fields.Many2one('resource.calendar', 'Agreement', index=True)


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    type_leave_ids = fields.Many2many('hr.leave.type', 'rel_agreement_leave', 'agreement_id', 'leave_id')


class AccrualSeniorityPlan(models.Model):
    _name = "hr.leave.accrual.seniority.plan"
    _description = "Accrual Seniority Plan"

    name = fields.Char('Name', index=True, required=True)
    normal_days = fields.Float('Work days', help='Holiday working days')
    discretionary_days = fields.Float('Discretionary days', help='Discretionary days by the manager based on '
                                                                 'individual performance')
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.company)


class HolidaysAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    @api.constrains('employee_ids')
    def check_employee_ids(self):
        for record in self:
            if record.employee_ids:
                for item in record.employee_ids:
                    if item.seniority_plan_id:
                        record.number_of_days = record.number_of_days + record.employee_id.seniority_plan_id.normal_days\
                                                + record.employee_id.seniority_plan_id.discretionary_days