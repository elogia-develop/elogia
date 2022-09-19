# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, tools, api, _
from odoo.exceptions import UserError
from collections import defaultdict

from datetime import date
from dateutil.relativedelta import relativedelta


class ApplyChangeWizard(models.TransientModel):
    _name = 'apply.change.wizard'
    _description = 'Apply Change Wizard'
    _rec_name = 'effective_date'

    effective_date = fields.Date('Effective date', default=lambda self: fields.Date.today())

    def action_create_records(self):
        for planning_id in self.env['employee.change.planning'].search([('state', '=', 'not_processed')]):
            planning_id.update_list_action()


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
        ('quotation', 'Quotation'),
        ('type_c', 'Type Contract'),
        ('date_finish', 'Date Finish'),
        ('type_scholarship', 'Scholarship'),
        ('departure_date', 'Departure date'),
        ('departure_reason', 'Departure reason'),
        ('wage_normal', 'Salary'),
        ('wage_variable', 'Salary V'),
        ], string='Action', default='employee', required=True,
        help="Type action to update in Contract or Employee History")
    type_model = fields.Selection([
        ('employee', 'Employee'),
        ('contract', 'Contract'),
    ], string='Model', default='employee', required=True,
        help="Type model to update in Contract or Employee History")


class ListActionChange(models.Model):
    _name = 'list.action.change'
    _description = 'List Action Change'
    _rec_name = 'planning_id'

    planning_id = fields.Many2one('employee.change.planning', 'Employee Change', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', related='planning_id.employee_id', string='Employee')
    effective_date = fields.Date('Effective date', states={'not_processed': [('readonly', False)],
                                                           'processed': [('readonly', True)]})
    last_date = fields.Date('Last date')
    type_model = fields.Selection([
        ('employee', 'Employee'),
        ('contract', 'Contract'),
    ], string='Model', default='employee', required=True,
        help="Type model to update in Contract or Employee History", states={'not_processed': [('readonly', False)],
                                                                             'processed': [('readonly', True)]})
    state = fields.Selection([
        ('not_processed', 'Not processed'),
        ('processed', 'Processed'),
    ], string='Status', default='not_processed', required=True)
    type_action = fields.Selection([
        ('employee', '-'),
        ('responsible', 'Responsible'),
        ('company', 'Company'),
        ('department', 'Department'),
        ('rol', 'Job'),
        ('hub', 'Hub'),
        ('contract', 'Contratation Type'),
        ('type_c', 'Type Contract'),
        ('type_scholarship', 'Scholarship'),
        ('departure_reason', 'Departure reason'),
        ('departure_date', 'Departure date'),
        ('wage_normal', 'Salary'),
        ('wage_variable', 'Salary V'),
    ], string='Action', default='employee', required=True,
        help="Type action to update in Contract or Employee History")

    @api.constrains('type_model')
    def check_contact(self):
        for record in self:
            if record.type_model == 'contract' and not record.employee_id.contract_id:
                raise UserError(_('The employee %s does not have an active contract.') % record.employee_id.name)

    @api.constrains('state')
    def onchange_state_planning(self):
        for record in self:
            if record.state == 'processed':
                if not any(item for item in record.planning_id.list_ids if item.state == 'not_processed'):
                    record.planning_id.state = 'processed'


class EmployeeChangePlanning(models.Model):
    _name = "employee.change.planning"
    _description = "Employee Change"
    _rec_name = 'employee_id'

    def _get_company_currency(self):
        self.currency_id = self.env.user.company_id.currency_id

    employee_id = fields.Many2one('hr.employee', 'Employee', index=True, required=True, ondelete='restrict')
    state = fields.Selection([
        ('not_processed', 'Not processed'),
        ('processed', 'Processed'),
    ], string='Status', default='not_processed', required=True)
    list_ids = fields.One2many('list.action.change', 'planning_id', 'List Action')
    check_company = fields.Boolean('Company?')
    process_company = fields.Boolean('Process Company')
    company_id = fields.Many2one('res.company', 'Company', ondelete='restrict')
    department_id = fields.Many2one('hr.department', 'Department', ondelete='restrict')
    check_department = fields.Boolean('Department?')
    process_department = fields.Boolean('Process Department')
    parent_id = fields.Many2one('hr.employee', 'Responsible', ondelete='restrict')
    check_parent = fields.Boolean('Responsible?')
    process_parent = fields.Boolean('Process Parent')
    hub_id = fields.Many2one('planning.role', 'Rol/Hub', ondelete='restrict')
    check_hub = fields.Boolean('Rol/Hub?')
    process_hub = fields.Boolean('Process Hub')
    job_id = fields.Many2one('hr.job', 'Job', ondelete='restrict')
    check_job = fields.Boolean('Job?')
    process_job = fields.Boolean('Process Job')
    structure_type_id = fields.Many2one('hr.payroll.structure.type', 'Contratation Type', ondelete='restrict')
    check_structure = fields.Boolean('Contratation Type?')
    process_structure = fields.Boolean('Process Structure')
    contract_type_id = fields.Many2one('hr.contract.type', 'Type Contract', ondelete='restrict')
    check_contract = fields.Boolean('Type Contract?')
    process_contract = fields.Boolean('Process Contract')
    scholarship_id = fields.Many2one('type.scholarship', 'Type Scholarship', ondelete='restrict')
    check_scholarship = fields.Boolean('Type Scholarship?')
    process_scholarship = fields.Boolean('Process Scholarship')
    departure_id = fields.Many2one('hr.departure.reason', 'Departure Reason', ondelete='restrict')
    check_departure = fields.Boolean('Departure Reason?')
    process_departure = fields.Boolean('Process Departure')
    departure_date = fields.Date('Departure Date')
    check_departure_date = fields.Boolean('Departure Date?')
    process_departure_date = fields.Boolean('Process Departure Date')
    wage = fields.Float('Fixed wage', tracking=True, help="Employee's annually gross wage fixed.")
    check_wage = fields.Boolean('Wage?')
    process_wage = fields.Boolean('Process Wage')
    wage_variable = fields.Float('Variable Wage', tracking=True, help="Employee's annually gross wage variable.")
    check_wage_variable = fields.Boolean('Wage V.?')
    process_wage_v = fields.Boolean('Process Wage V')
    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True, string="Currency",
                                  help='Utility field to express amount currency')

    def action_open_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Apply changes for %s.' % self.employee_id.name,
            'res_model': 'apply.change.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'origin_view': 'wizard_filter'}
        }

    @api.model
    def create(self, vals_list):
        list_field = []
        res = super(EmployeeChangePlanning, self).create(vals_list)
        if res.check_company:
            list_field.append({'planning_id': res.id, 'effective_date': fields.Date.today(), 'type_action': 'company'})
        if res.check_department:
            list_field.append({'planning_id': res.id, 'effective_date': fields.Date.today(),
                               'type_action': 'department'})
        if res.check_parent:
            list_field.append({'planning_id': res.id, 'effective_date': fields.Date.today(),
                               'type_action': 'responsible'})
        if res.check_hub:
            list_field.append({'planning_id': res.id, 'effective_date': fields.Date.today(), 'type_action': 'hub'})
        if res.check_job:
            list_field.append({'planning_id': res.id, 'effective_date': fields.Date.today(), 'type_action': 'rol'})
        if res.check_structure:
            list_field.append({'planning_id': res.id, 'effective_date': fields.Date.today(), 'type_action': 'contract'})
        if res.check_contract:
            list_field.append({'planning_id': res.id, 'effective_date': fields.Date.today(), 'type_action': 'type_c'})
        if res.check_scholarship:
            list_field.append({'planning_id': res.id, 'effective_date': fields.Date.today(),
                               'type_action': 'type_scholarship'})
        if res.check_departure:
            list_field.append({'planning_id': res.id, 'effective_date': fields.Date.today(),
                               'type_action': 'departure_reason'})
        if res.check_departure_date:
            list_field.append({'planning_id': res.id, 'effective_date': fields.Date.today(),
                               'type_action': 'departure_date'})
        if res.check_wage:
            list_field.append({'planning_id': res.id, 'effective_date': fields.Date.today(),
                               'type_action': 'wage_normal'})
        if res.check_wage_variable:
            list_field.append({'planning_id': res.id, 'effective_date': fields.Date.today(),
                               'type_action': 'wage_variable'})
        if list_field:
            for item in list_field:
                self.env['list.action.change'].create(item)
        return res

    def write(self, vals):
        list_action = []
        list_field = []
        if 'check_company' in vals:
            if not vals.get('check_company'):
                list_action.append('company')
            else:
                list_field.append({'planning_id': self.id, 'effective_date': fields.Date.today(),
                                   'type_action': 'company'})
        if 'check_department' in vals:
            if not vals.get('check_department'):
                list_action.append('department')
            else:
                list_field.append({'planning_id': self.id, 'effective_date': fields.Date.today(),
                                   'type_action': 'department'})
        if 'check_parent' in vals:
            if not vals.get('check_parent'):
                list_action.append('responsible')
            else:
                list_field.append({'planning_id': self.id, 'effective_date': fields.Date.today(),
                                   'type_action': 'responsible'})
        if 'check_hub' in vals:
            if not vals.get('check_hub'):
                list_action.append('hub')
            else:
                list_field.append({'planning_id': self.id, 'effective_date': fields.Date.today(),
                                   'type_action': 'hub'})
        if 'check_job' in vals:
            if not vals.get('check_job'):
                list_action.append('rol')
            else:
                list_field.append({'planning_id': self.id, 'effective_date': fields.Date.today(),
                                   'type_action': 'rol'})
        if 'check_structure' in vals:
            if not vals.get('check_structure'):
                list_action.append('contract')
            else:
                list_field.append({'planning_id': self.id, 'effective_date': fields.Date.today(),
                                   'type_action': 'contract'})
        if 'check_contract' in vals:
            if not vals.get('check_contract'):
                list_action.append('type_c')
            else:
                list_field.append({'planning_id': self.id, 'effective_date': fields.Date.today(),
                                   'type_action': 'type_c'})
        if 'check_scholarship' in vals:
            if not vals.get('check_scholarship'):
                list_action.append('type_scholarship')
            else:
                list_field.append({'planning_id': self.id, 'effective_date': fields.Date.today(),
                                   'type_action': 'type_scholarship'})
        if 'check_departure' in vals:
            if not vals.get('check_departure'):
                list_action.append('departure_reason')
            else:
                list_field.append({'planning_id': self.id, 'effective_date': fields.Date.today(),
                                   'type_action': 'departure_reason'})
        if 'check_departure_date' in vals:
            if not vals.get('check_departure_date'):
                list_action.append('departure_date')
            else:
                list_field.append({'planning_id': self.id, 'effective_date': fields.Date.today(),
                                   'type_action': 'departure_date'})
        if 'check_wage' in vals:
            if not vals.get('check_wage'):
                list_action.append('wage_normal')
            else:
                list_field.append({'planning_id': self.id, 'effective_date': fields.Date.today(),
                                   'type_action': 'wage_normal'})
        if 'check_wage_variable' in vals:
            if not vals.get('check_wage_variable'):
                list_action.append('wage_variable')
            else:
                list_field.append({'planning_id': self.id, 'effective_date': fields.Date.today(),
                                   'type_action': 'wage_variable'})
        if list_action:
            action_ids = self.env['list.action.change'].search([('type_action', 'in', list_action),
                                                                ('planning_id', '=', self.id)])
            for element in action_ids:
                element.unlink()
        if list_field:
            for item in list_field:
                if item['type_action'] not in self.list_ids.mapped('type_action'):
                    self.env['list.action.change'].create(item)
        return super(EmployeeChangePlanning, self).write(vals)

    def unlink(self):
        if any(item for item in self.list_ids if item.state == 'processed'):
            raise UserError(_('This record cannot be deleted, there are elements that have already been processed.'))
        res = super(EmployeeChangePlanning, self).unlink()
        return res

    def update_dates(self, planning, list_actions):
        if self.env.context.get('origin_view') and self.env.context.get('origin_view') == 'wizard_filter':
            for item in list_actions:
                item.last_date = item.effective_date
                item.effective_date = date.today()
        else:
            list_actions = [item for item in planning.list_ids if item.state == 'not_processed' and
                            item.effective_date <= date.today()]
        return list_actions

    def write_values(self, item, dict_write):
        if item.type_model == 'employee':
            if item.type_action == 'responsible':
                dict_write['parent_id'] = item.planning_id.parent_id.id
            if item.type_action == 'hub':
                dict_write['default_planning_role_id'] = item.planning_id.hub_id.id
            item.employee_id.write(dict_write)
            item.state = 'processed'
        if item.type_model == 'contract':
            if item.type_action == 'responsible':
                dict_write['hr_responsible_id'] = item.planning_id.parent_id.user_id.id
            if item.type_action == 'hub':
                dict_write['hub_id'] = item.planning_id.hub_id.id
            item.employee_id.contract_id.write(dict_write)
            item.state = 'processed'
        return False

    @api.model
    def update_list_action(self):
        dict_write = {}
        dict_init = {}
        planning_ids = self.search([('state', '=', 'not_processed')])
        for planning in planning_ids:
            list_actions = [item for item in planning.list_ids if item.state == 'not_processed']
            if list_actions:
                obj_update = self.update_dates(planning, list_actions)
                if obj_update:
                    for item in obj_update:
                        if item.type_action == 'company' and planning.check_company:
                            dict_write['company_id'] = planning.company_id.id
                            self.write_values(item, dict_write)
                            planning.process_company = True
                            dict_write = dict_init
                        if item.type_action == 'department' and planning.check_department:
                            dict_write['department_id'] = planning.department_id.id
                            self.write_values(item, dict_write)
                            planning.process_department = True
                            dict_write = dict_init
                        if item.type_action == 'responsible' and planning.check_parent:
                            self.write_values(item, dict_write)
                            planning.process_parent = True
                            dict_write = dict_init
                        if item.type_action == 'hub' and planning.check_hub:
                            self.write_values(item, dict_write)
                            planning.process_hub = True
                            dict_write = dict_init
                        if item.type_action == 'rol' and planning.check_job:
                            dict_write['job_id'] = planning.job_id.id
                            self.write_values(item, dict_write)
                            planning.process_job = True
                            dict_write = dict_init
                        if item.type_action == 'contract' and planning.check_structure:
                            dict_write['structure_type_id'] = planning.structure_type_id.id
                            self.write_values(item, dict_write)
                            planning.process_structure = True
                            dict_write = dict_init
                        if item.type_action == 'type_c' and planning.check_contract:
                            dict_write['contract_type_id'] = planning.contract_type_id.id
                            self.write_values(item, dict_write)
                            planning.process_contract = True
                            dict_write = dict_init
                        if item.type_action == 'type_scholarship' and planning.check_scholarship:
                            dict_write['type_scholarship'] = planning.scholarship_id.id
                            self.write_values(item, dict_write)
                            planning.process_scholarship = True
                            dict_write = dict_init
                        if item.type_action == 'departure_reason' and planning.check_departure:
                            dict_write['departure_reason_id'] = planning.departure_id.id
                            self.write_values(item, dict_write)
                            planning.process_departure = True
                            dict_write = dict_init
                        if item.type_action == 'departure_date' and planning.check_departure_date:
                            dict_write['departure_date'] = planning.departure_date
                            self.write_values(item, dict_write)
                            planning.process_departure_date = True
                            dict_write = dict_init
                        if item.type_action == 'wage_normal' and planning.check_wage:
                            dict_write['wage'] = planning.wage
                            self.write_values(item, dict_write)
                            planning.process_wage = True
                            dict_write = dict_init
                        if item.type_action == 'wage_variable' and planning.check_wage_variable:
                            dict_write['wage_variable'] = planning.wage_variable
                            self.write_values(item, dict_write)
                            planning.process_wage_v = True
                            dict_write = dict_init
        return False


class TypeScholarship(models.Model):
    _name = "type.scholarship"
    _description = "Type Scholarship"

    name = fields.Char('Name', required=True, index=True)
    description = fields.Char('Description')


class Employee(models.Model):
    _inherit = "hr.employee"

    def _get_company_currency(self):
        self.currency_id = self.env.user.company_id.currency_id

    employee_number = fields.Char('Employee number', tracking=1)
    history_ids = fields.One2many('employee.history', 'employee_id', string='Employee History')
    date_init = fields.Date('Fecha ingreso grupo', help='Fecha ingreso en el grupo',
                            default=lambda self: fields.Date.today(), tracking=1)
    date_init_mark = fields.Date('Fecha ingreso marca', help='Fecha ingreso en la marca',
                                 default=lambda self: fields.Date.today(), tracking=1)
    date_finish = fields.Date('Fecha vencimiento', help='Fecha vencimiento periodo de prueba',
                              default=lambda self: fields.Date.today(), tracking=1)
    default_planning_role_id = fields.Many2one('planning.role', string="Hub", groups='hr.group_hr_user', tracking=1)
    quotation_code = fields.Char('Code quot.', help='Account code quotation', tracking=1)
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Contratation Type", tracking=1)
    contract_type_id = fields.Many2one('hr.contract.type', "Contract Type", tracking=1)
    date_finish_ctt = fields.Date('Proximo vencimiento', help='Fecha proximo vencimiento contrato/beca', tracking=1)
    type_scholarship = fields.Many2one('type.scholarship', string='Type scholarship', tracking=1)
    wage = fields.Float('Fixed wage', help="Employee's annually gross wage fixed.", tracking=1)
    wage_variable = fields.Float('Variable Wage', help="Employee's annually gross wage variable.", tracking=1)
    resource_calendar_id = fields.Many2one('resource.calendar', string="Agreement",
                                           domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    job_title = fields.Char()
    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True, string="Currency",
                                  help='Utility field to express amount currency')
    change_ids = fields.One2many('employee.change.planning', 'employee_id', string='Employee Change')
    count_changes = fields.Integer('Changes', compute='_calc_count_changes')

    def _calc_count_changes(self):
        for obj_employee in self:
            obj_employee.count_changes = len(obj_employee.change_ids) if obj_employee.change_ids else 0

    def write(self, vals):
        history_env = self.env['employee.history']
        company_env = self.env['res.company']
        department_env = self.env['hr.department']
        employee_env = self.env['hr.employee']
        hub_env = self.env['planning.role']
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
            if 'company_id' in vals:
                value_company = company_env.search([('id', '=', vals['company_id'])], limit=1)
                if value_company != record.company_id:
                    list_field.append({'value_before': record.company_id.name, 'value_actual':
                        value_company.name, 'type_action': 'company', 'type_model': type_model,
                                       'employee_id': record.id})
            if 'department_id' in vals:
                value_department = department_env.search([('id', '=', vals['department_id'])], limit=1)
                if value_department != record.department_id:
                    list_field.append({'value_before': record.department_id.name, 'value_actual':
                        value_department.name, 'type_action': 'department', 'type_model': type_model,
                                       'employee_id': record.id})
            if 'parent_id' in vals:
                value_parent = employee_env.search([('id', '=', vals['parent_id'])], limit=1)
                if value_parent != record.parent_id:
                    list_field.append({'value_before': record.parent_id.name, 'value_actual':
                        value_parent.name, 'type_action': 'responsible', 'type_model': type_model,
                                       'employee_id': record.id})
            if 'default_planning_role_id' in vals:
                value_hub = hub_env.search([('id', '=', vals['default_planning_role_id'])], limit=1)
                if value_hub != record.default_planning_role_id:
                    list_field.append({'value_before': record.default_planning_role_id.name, 'value_actual':
                        value_hub.name, 'type_action': 'hub', 'type_model': type_model,
                                       'employee_id': record.id})
            if 'job_id' in vals:
                value_job = job_env.search([('id', '=', vals['job_id'])], limit=1)
                if value_job != record.job_id:
                    list_field.append({'value_before': record.job_id.name, 'value_actual':
                        value_job.name, 'type_action': 'rol', 'type_model': type_model,
                                       'employee_id': record.id})
            if 'quotation_code' in vals:
                list_field.append({'value_before': record.quotation_code, 'value_actual':
                    vals['quotation_code'], 'type_action': 'quotation', 'type_model': type_model,
                                   'employee_id': record.id})
            if 'structure_type_id' in vals:
                value_struct = struct_env.search([('id', '=', vals['structure_type_id'])], limit=1)
                if value_struct != record.structure_type_id:
                    list_field.append({'value_before': record.structure_type_id.name, 'value_actual':
                        value_struct.name, 'type_action': 'contract', 'type_model': type_model,
                                       'employee_id': record.id})
            if 'contract_type_id' in vals:
                value_contract = contract_env.search([('id', '=', vals['contract_type_id'])], limit=1)
                if value_contract != record.contract_type_id:
                    list_field.append({'value_before': record.contract_type_id.name, 'value_actual':
                        value_contract.name, 'type_action': 'type_c', 'type_model': type_model,
                                       'employee_id': record.id})
            if 'date_finish_ctt' in vals:
                list_field.append({'value_before': record.date_finish_ctt, 'value_actual':
                    vals['date_finish_ctt'], 'type_action': 'date_finish', 'type_model': type_model,
                                   'employee_id': record.id})
            if 'type_scholarship' in vals:
                value_scholarship = scholarship_env.search([('id', '=', vals['type_scholarship'])], limit=1)
                if value_scholarship != record.type_scholarship:
                    list_field.append({'value_before': record.type_scholarship.name, 'value_actual':
                        value_scholarship.name, 'type_action': 'type_scholarship', 'type_model': type_model,
                                       'employee_id': record.id})
            if 'departure_date' in vals:
                list_field.append({'value_before': record.departure_date, 'value_actual':
                    vals['departure_date'], 'type_action': 'departure_date', 'type_model': type_model,
                                   'employee_id': record.id})
            if 'departure_reason_id' in vals:
                value_departure = departure_env.search([('id', '=', vals['departure_reason_id'])], limit=1)
                if value_departure != record.departure_reason_id:
                    list_field.append({'value_before': record.departure_reason_id.name, 'value_actual':
                        value_departure.name, 'type_action': 'departure_reason', 'type_model': type_model,
                                       'employee_id': record.id})
            if 'wage' in vals:
                list_field.append({'value_before': record.wage, 'value_actual': vals['wage'], 'type_model':
                    type_model, 'type_action': 'wage_normal', 'employee_id': record.id})
            if 'wage_variable' in vals:
                list_field.append({'value_before': record.wage_variable, 'value_actual':
                    vals['wage_variable'], 'type_model': type_model, 'type_action': 'wage_variable',
                                   'employee_id': record.id})
            if list_field:
                for item in list_field:
                    history_env.create(item)
        return super(Employee, self).write(vals)

    def action_view_history(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'History',
            'res_model': 'employee.history',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'new',
            'domain': [('employee_id', '=', self.id)]
        }

    def action_view_changes(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Changes',
            'res_model': 'employee.change.planning',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }


class Contract(models.Model):
    _inherit = 'hr.contract'

    def _get_company_currency(self):
        self.currency_id = self.env.user.company_id.currency_id

    hub_id = fields.Many2one('planning.role', 'Hub', tracking=1)
    location_id = fields.Many2one('hr.work.location', 'Location ref.', tracking=1)
    quotation_code = fields.Char('Code quot.', help='Account code quotation', tracking=1)
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Contratation Type", tracking=1)
    date_finish_ctt = fields.Date('Proximo vencimiento', help='Fecha proximo vencimiento contrato/beca', tracking=1)
    departure_date = fields.Date(string="Departure Date", tracking=True)
    departure_reason_id = fields.Many2one("hr.departure.reason", string="Departure Reason", tracking=True,
                                          ondelete='restrict')
    type_scholarship = fields.Many2one('type.scholarship', string='Type scholarship', tracking=1)
    wage = fields.Float('Fixed wage', required=True, tracking=True, help="Employee's annually gross wage fixed.")
    wage_variable = fields.Float('Variable Wage', tracking=True,
                                    help="Employee's annually gross wage variable.")
    first_notification = fields.Boolean('First notification')
    second_notification = fields.Boolean('Second notification')
    state = fields.Selection([
        ('draft', 'New'),
        ('open', 'Running'),
        ('close', 'Expired'),
        ('cancel', 'Cancelled')
    ], string='Status', group_expand='_expand_states', copy=False,
        tracking=True, help='Status of the contract', default='open')
    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True, string="Currency",
                                  help='Utility field to express amount currency')

    @api.onchange('company_id', 'department_id', 'hub_id', 'job_id', 'quotation_code', 'structure_type_id',
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
                contract.employee_id.job_title = self.job_id.name
            if self.hub_id and self.employee_id.default_planning_role_id != self.hub_id:
                contract.employee_id.default_planning_role_id = self.hub_id.id
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

    def _get_company_currency(self):
        self.currency_id = self.env.user.company_id.currency_id

    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Contratation Type", readonly=True)
    date_finish_ctt = fields.Date('Proximo vencimiento', related='contract_id.date_finish_ctt', help='Fecha proximo vencimiento contrato/beca')
    hub_id = fields.Many2one('planning.role', 'Hub', related='contract_id.hub_id')
    type_scholarship = fields.Many2one('type.scholarship', string='Type scholarship',  related='contract_id.type_scholarship')
    wage = fields.Float('Fixed wage', related='contract_id.wage', help="Employee's annually gross wage fixed.")
    wage_variable = fields.Float('Variable wage', related='contract_id.wage_variable', help="Employee's annually gross wage variable.")
    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True, string="Currency",
                                  help='Utility field to express amount currency')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        # Reference contract is the one with the latest start_date.
        self.env.cr.execute("""CREATE or REPLACE VIEW %s AS (
            WITH contract_information AS (
                SELECT DISTINCT employee_id,
                                company_id,
                                FIRST_VALUE(id) OVER w_partition AS id,
                                MAX(CASE
                                    WHEN state='open' THEN 1
                                    WHEN state='draft' AND kanban_state='done' THEN 1
                                    ELSE 0 END) OVER w_partition AS is_under_contract
                FROM   hr_contract AS contract
                WHERE  contract.active = true
                WINDOW w_partition AS (
                    PARTITION BY contract.employee_id
                    ORDER BY
                        CASE
                            WHEN contract.state = 'open' THEN 0
                            WHEN contract.state = 'draft' THEN 1
                            WHEN contract.state = 'close' THEN 2
                            ELSE 3 END,
                        contract.date_start DESC
                    RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                )
            )
            SELECT     employee.id AS id,
                       employee.id AS employee_id,
                       employee.active AS active_employee,
                       contract.id AS contract_id,
                       contract_information.is_under_contract::bool AS is_under_contract,
                       employee.first_contract_date AS date_hired,
                       %s
            FROM       hr_contract AS contract
            INNER JOIN contract_information ON contract.id = contract_information.id
            RIGHT JOIN hr_employee AS employee
                ON  contract_information.employee_id = employee.id
                AND contract.company_id = employee.company_id
            WHERE   employee.employee_type IN ('employee', 'student')
        )""" % (self._table, self._get_fields()))

    @api.depends('employee_id.contract_ids')
    def _compute_contract_ids(self):
        sorted_contracts = self.mapped('employee_id.contract_ids').sorted('date_start', reverse=True)

        mapped_employee_contracts = defaultdict(lambda: self.env['hr.contract'])
        for contract in sorted_contracts:
            mapped_employee_contracts[contract.employee_id] |= contract
        for history in self:
            history.contract_ids = mapped_employee_contracts[history.employee_id]
