# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

    # @api.onchange('name', 'holiday_status_id')
    # def onchange_time_off_id(self):
    #     agreement_ids = self.env['agreement.hr'].search([('active', '=', True)])
    #     domain = {
    #         'holiday_status_id': False,
    #     }
    #     values = {
    #         'holiday_status_id': False,
    #     }
    #     self.update(values)
    #     if self.env.user and self.employee_id and (self.employee_id.coach_id or self.employee_id.parent_id):
    #         if self.env.user.company_id.id in [item.id for item in agreement_ids.mapped('company_ids')]:
    #             list_type_holiday = [item.id for item in agreement_ids.mapped('type_leave_ids')]
    #             domain = {'holiday_status_id': [('id', 'in', list_type_holiday)]}
    #     return {'domain': domain}
