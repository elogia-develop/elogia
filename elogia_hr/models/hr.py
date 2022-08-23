# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from datetime import date
from dateutil.relativedelta import relativedelta


class EmployeeHistory(models.Model):
    _name = "employee.history"
    _description = "Employee History"
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', 'Employee', index=True)
    value_before = fields.Char('Value before')
    value_actual = fields.Char('Value now')
    type_action = fields.Selection([
        ('employee', 'Employee'),
        ('responsible', 'Responsible'),
        ('company', 'Company'),
        ('rol', 'Rol'),
        ('department', 'Department'),
        ('hub', 'Hub'),
        ('contract', 'Contract'),
        ], string='Action', default='employee', required=True,
        help="Type action to update in Contract or Employee History")
    type_model = fields.Selection([
        ('employee', 'Employee'),
        ('contract', 'Contract'),
    ], string='Model', default='employee', required=True,
        help="Type model to update in Contract or Employee History")


class EmployeeHub(models.Model):
    _name = "employee.hub"
    _description = "Employee Hub"

    name = fields.Char('Name', required=True, index=True)
    description = fields.Char('Description')


class TypeScholarship(models.Model):
    _name = "type.scholarship"
    _description = "Type Scholarship"

    name = fields.Char('Name', required=True, index=True)
    description = fields.Char('Description')


class Employee(models.Model):
    _inherit = "hr.employee"

    employee_number = fields.Char('Employee number', tracking=1)
    history_ids = fields.One2many('employee.history', 'employee_id', string='Employee History')
    date_init = fields.Date('Fecha ingreso grupo', help='Fecha ingreso en el grupo',
                            default=lambda self: fields.Date.today(), tracking=1)
    date_init_mark = fields.Date('Fecha ingreso marca', help='Fecha ingreso en la marca',
                                 default=lambda self: fields.Date.today(), tracking=1)
    date_finish = fields.Date('Fecha vencimiento', help='Fecha vencimiento periodo de prueba',
                              default=lambda self: fields.Date.today(), tracking=1)
    hub_id = fields.Many2one('employee.hub', 'Hub')
    quotation_code = fields.Char('Code quot.', help='Account code quotation', tracking=1)
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Contratation Type", tracking=1)
    contract_type_id = fields.Many2one('hr.contract.type', "Contract Type", tracking=1)
    date_finish_ctt = fields.Date('Proximo vencimiento', help='Fecha proximo vencimiento contrato/beca', tracking=1)
    type_scholarship = fields.Many2one('type.scholarship', string='Type scholarship', tracking=1)
    wage = fields.Monetary('Fixed wage', help="Employee's annually gross wage fixed.", tracking=1)
    wage_variable = fields.Monetary('Variable Wage', help="Employee's annually gross wage variable.", tracking=1)
    resource_calendar_id = fields.Many2one('resource.calendar', string="Agreement",
                                           domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    def write(self, vals):
        history_env = self.env['employee.history']
        company_env = self.env['res.company']
        department_env = self.env['hr.department']
        employee_env = self.env['hr.employee']
        hub_env = self.env['employee.hub']
        job_env = self.env['hr.job']
        struct_env = self.env['hr.payroll.structure.type']
        contract_env = self.env['hr.contract.type']
        scholarship_env = self.env['type.scholarship']
        departure_env = self.env['hr.departure.reason']
        list_field = []
        for record in self:
            if self.env.context.get('from_model'):
                type_model = 'contract'
            else:
                type_model = 'employee'
            if vals and 'company_id' in vals:
                value_company = company_env.search([('id', '=', vals['company_id'])], limit=1)
                if value_company != record.company_id:
                    list_field.append({'value_before': record.company_id.name, 'value_actual':
                        value_company.name, 'type_action': 'company', 'type_model': type_model, 'employee_id': record.id})
            if vals and 'department_id' in vals:
                value_department = department_env.search([('id', '=', vals['department_id'])], limit=1)
                if value_department != record.department_id:
                    list_field.append({'value_before': record.department_id.name, 'value_actual':
                        value_department.name, 'type_action': 'department', 'type_model': type_model, 'employee_id': record.id})
            if vals and 'parent_id' in vals:
                value_parent = employee_env.search([('id', '=', vals['parent_id'])], limit=1)
                if value_parent != record.parent_id:
                    list_field.append({'value_before': record.parent_id.name, 'value_actual':
                        value_parent.name, 'type_action': 'responsible', 'type_model': type_model, 'employee_id': record.id})
            if vals and 'hub_id' in vals:
                value_hub = hub_env.search([('id', '=', vals['hub_id'])], limit=1)
                if value_hub != record.hub_id:
                    list_field.append({'value_before': record.hub_id.name, 'value_actual':
                        value_hub.name, 'type_action': 'hub', 'type_model': type_model, 'employee_id': record.id})
            if vals and 'job_id' in vals:
                value_job = job_env.search([('id', '=', vals['job_id'])], limit=1)
                if value_job != record.job_id:
                    list_field.append({'value_before': record.job_id.name, 'value_actual':
                        value_job.name, 'type_action': 'rol', 'type_model': type_model, 'employee_id': record.id})
            if vals and 'quotation_code' in vals:
                list_field.append({'value_before': record.quotation_code, 'value_actual':
                    vals['quotation_code'], 'type_model': type_model, 'employee_id': record.id})
            if vals and 'structure_type_id' in vals:
                value_struct = struct_env.search([('id', '=', vals['structure_type_id'])], limit=1)
                if value_struct != record.structure_type_id:
                    list_field.append({'value_before': record.structure_type_id.name, 'value_actual':
                        value_struct.name, 'type_action': 'contract', 'type_model': type_model, 'employee_id': record.id})
            if vals and 'contract_type_id' in vals:
                value_contract = contract_env.search([('id', '=', vals['contract_type_id'])], limit=1)
                if value_contract != record.contract_type_id:
                    list_field.append({'value_before': record.contract_type_id.name, 'value_actual':
                        value_contract.name, 'type_action': 'contract', 'type_model': type_model, 'employee_id': record.id})
            if vals and 'date_finish_ctt' in vals:
                list_field.append({'value_before': record.date_finish_ctt, 'value_actual':
                    vals['date_finish_ctt'], 'type_action': 'contract', 'type_model': type_model, 'employee_id': record.id})
            if vals and 'type_scholarship' in vals:
                value_scholarship = scholarship_env.search([('id', '=', vals['type_scholarship'])], limit=1)
                if value_scholarship != record.type_scholarship:
                    list_field.append({'value_before': record.type_scholarship.name, 'value_actual':
                        value_scholarship.name, 'type_action': 'contract', 'type_model': type_model, 'employee_id': record.id})
            if vals and 'departure_date' in vals:
                list_field.append({'value_before': record.departure_date, 'value_actual':
                    vals['departure_date'], 'type_model': type_model, 'employee_id': record.id})
            if vals and 'departure_reason_id' in vals:
                value_departure = departure_env.search([('id', '=', vals['departure_reason_id'])], limit=1)
                if value_departure != record.departure_reason_id:
                    list_field.append({'value_before': record.departure_reason_id.name, 'value_actual':
                        value_departure.name, 'type_model': type_model, 'employee_id': record.id})
            if vals and 'wage' in vals:
                list_field.append({'value_before': record.wage, 'value_actual': vals['wage'], 'type_model':
                    type_model, 'type_action': 'contract', 'employee_id': record.id})
            if vals and 'wage_variable' in vals:
                list_field.append({'value_before': record.wage_variable, 'value_actual':
                    vals['wage_variable'], 'type_model': type_model, 'type_action': 'contract', 'employee_id': record.id})
            if list_field:
                for item in list_field:
                    history_env.create(item)
        return super(Employee, self).write(vals)


class Contract(models.Model):
    _inherit = 'hr.contract'

    hub_id = fields.Many2one('employee.hub', 'Hub', tracking=1)
    location_id = fields.Many2one('hr.work.location', 'Location ref.', tracking=1)
    quotation_code = fields.Char('Code quot.', help='Account code quotation', tracking=1)
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Contratation Type", tracking=1)
    date_finish_ctt = fields.Date('Proximo vencimiento', help='Fecha proximo vencimiento contrato/beca', tracking=1)
    departure_date = fields.Date(string="Departure Date", tracking=True)
    departure_reason_id = fields.Many2one("hr.departure.reason", string="Departure Reason", tracking=True,
                                          ondelete='restrict')
    type_scholarship = fields.Many2one('type.scholarship', string='Type scholarship', tracking=1)
    wage = fields.Monetary('Fixed wage', required=True, tracking=True, help="Employee's annually gross wage fixed.")
    wage_variable = fields.Monetary('Variable Wage', required=True, tracking=True,
                                    help="Employee's annually gross wage variable.")
    first_notification = fields.Boolean('First notification')
    second_notification = fields.Boolean('Second notification')

    @api.onchange('company_id', 'department_id', 'job_id', 'hub_id', 'quotation_code', 'structure_type_id',
                  'contract_type_id', 'date_finish_ctt', 'type_scholarship', 'departure_date', 'departure_reason_id',
                  'wage', 'wage_variable')
    def onchange_fields_employee(self):
        if self.state not in ['close', 'cancel']:
            contract = self.with_context({'from_model': 'contract'})
            if self.company_id and self.employee_id.company_id != self.company_id:
                contract.employee_id.company_id = self.company_id.id
            if self.department_id and self.employee_id.department_id != self.department_id:
                contract.employee_id.department_id = self.department_id.id
            if self.job_id and self.employee_id.job_id != self.job_id:
                contract.employee_id.job_id = self.job_id.id
            if self.hub_id and self.employee_id.hub_id != self.hub_id:
                contract.employee_id.hub_id = self.hub_id.id
            if self.quotation_code and self.employee_id.quotation_code != self.quotation_code:
                contract.employee_id.quotation_code = self.quotation_code
            if self.structure_type_id and self.employee_id.structure_type_id != self.structure_type_id:
                contract.employee_id.structure_type_id = self.structure_type_id.id
            if self.contract_type_id and self.employee_id.contract_type_id != self.contract_type_id:
                contract.employee_id.contract_type_id = self.contract_type_id.id
            if self.date_finish_ctt and self.employee_id.date_finish_ctt != self.date_finish_ctt:
                contract.employee_id.date_finish_ctt = self.date_finish_ctt
            if self.type_scholarship and self.employee_id.type_scholarship != self.type_scholarship:
                contract.employee_id.type_scholarship = self.type_scholarship.id
            if self.departure_date and self.employee_id.departure_date != self.departure_date:
                contract.employee_id.departure_date = self.departure_date
            if self.departure_reason_id and self.employee_id.departure_reason_id != self.departure_reason_id:
                contract.employee_id.departure_reason_id = self.departure_reason_id.id
            if self.wage and self.employee_id.wage != self.wage:
                contract.employee_id.wage = self.wage
            if self.wage_variable and self.employee_id.wage_variable != self.wage_variable:
                contract.employee_id.wage_variable = self.wage_variable

    @api.model
    def update_state(self):
        res = super(Contract, self).update_state()
        contracts = self.search([('state', '=', 'open'), '|', ('first_notification', '!=', True),
                                 ('second_notification', '!=', True)])
        for contract in contracts:
            if contract.date_end == date.today() + relativedelta(days=60):
                contract.first_notification = True
            elif contract.date_end == date.today() + relativedelta(days=30):
                contract.second_notification = True
            contract.activity_schedule('mail.mail_activity_data_todo', contract.date_end,
                                       _("The contract of %s is about to expire.", contract.employee_id.name),
                                       user_id=contract.hr_responsible_id.id or self.env.uid)
            mail_template = self.env['ir.model.data']._xmlid_to_res_id('elogia_hr.notification_email_contract_template')
            self._create_mail_begin(mail_template, contract)
        return res

    def compose_email_message(self, contract):
        obj_partner_id = self.env['res.partner'].search([('name', 'like', 'Admin')], limit=1)
        email_from = obj_partner_id.email if obj_partner_id else 'admin@email.com'
        email_to = contract.employee_id.user_id.email_formatted if contract.employee_id.user_id else 'user@email.com'
        mail_data = {
            'email_from': email_from,
            'email_to': email_to,
            'res_id': contract.id
        }
        return mail_data

    def _create_mail_begin(self, template, contract):
        template_browse = self.env['mail.template'].browse(template)
        data_compose = self.compose_email_message(contract)
        if template_browse and data_compose:
            values = template_browse.generate_email(contract.id, ['subject', 'body_html', 'email_from', 'email_to',
                                                                  'partner_to', 'reply_to'])
            values['email_to'] = data_compose['email_to']
            values['email_from'] = data_compose['email_from']
            values['reply_to'] = data_compose['email_from']
            values['res_id'] = data_compose['res_id']
            msg_id = self.env['mail.mail'].sudo().create(values)
            if msg_id:
                msg_id.send()
        return True


class ContractHistory(models.Model):
    _inherit = 'hr.contract.history'

    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Contratation Type", readonly=True)
    date_finish_ctt = fields.Date('Proximo vencimiento', related='contract_id.date_finish_ctt', help='Fecha proximo vencimiento contrato/beca')
    hub_id = fields.Many2one('employee.hub', 'Hub', related='contract_id.hub_id')
    type_scholarship = fields.Many2one('type.scholarship', string='Type scholarship',  related='contract_id.type_scholarship')
    wage = fields.Monetary('Fixed wage', related='contract_id.wage', help="Employee's annually gross wage fixed.")
    wage_variable = fields.Monetary('Variable wage', related='contract_id.wage_variable', help="Employee's annually gross wage variable.")
