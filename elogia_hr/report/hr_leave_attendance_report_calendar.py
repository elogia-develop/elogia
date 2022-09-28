# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.addons.base.models.res_partner import _tz_get

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

MONTHS = ("Enero",
          "Febrero",
          "Marzo",
          "Abril",
          "Mayo",
          "Junio",
          "Julio",
          "Agosto",
          "Septiembre",
          "Octubre",
          "Noviembre",
          "Diciembre")


class LeaveAttendanceReport(models.Model):
    _name = "hr.leave.attendance.report"
    _description = 'Time Off Attendance Report'

    name = fields.Char(string='Name', index=True, required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee')
    start_datetime = fields.Date(string='From')
    stop_datetime = fields.Date(string='To')
    on_holiday = fields.Boolean('On holiday')
    on_attendance = fields.Boolean('On attendance')
    actual_year = fields.Integer('Actual Year')
    actual_month = fields.Integer('Actual Month')
    actual_day = fields.Integer('Actual Day')

    @api.model
    def update_calendar_by_year(self):
        init_date = date.today()
        finish_date = datetime.strptime('31-12-' + str(date.today().year), '%d-%m-%Y').date()
        date_list = [init_date + relativedelta(days=d) for d in range((finish_date - init_date).days + 1)]
        obj_employee_ids = self.env['hr.employee'].search([('active', '=', True)])
        list_employee = [employee for employee in obj_employee_ids]
        attendances = self.search([('actual_year', '=', date.today().year)])
        list_attendance = [employee for employee in obj_employee_ids if employee.id in
                           attendances.mapped('employee_id').ids and attendances]
        if list_attendance:
            for item in list_attendance:
                list_employee.remove(item)
        if date_list and list_employee:
            for employee in list_employee:
                list_create = [{'name': MONTHS[day.month - 1] + ' ' + str(day.day), 'employee_id': employee.id,
                                'start_datetime': day, 'stop_datetime': day, 'on_holiday': False,
                                'on_attendance': True, 'actual_year': date.today().year,
                                'actual_month': day.month, 'actual_day': day.day} for day in date_list
                               if day.weekday() < 5]
                if list_create:
                    self.env['hr.leave.attendance.report'].create(list_create)


class LeaveAttendanceReportCalendar(models.Model):
    _name = "hr.leave.attendance.report.calendar"
    _description = 'Time Off Attendance Calendar'
    _auto = False
    _order = "start_datetime DESC, employee_id"

    name = fields.Char(string='Name', readonly=True)
    start_datetime = fields.Date(string='From', readonly=True)
    stop_datetime = fields.Date(string='To', readonly=True)
    tz = fields.Selection(_tz_get, string="Timezone", readonly=True)
    employee_id = fields.Many2one('hr.employee', readonly=True)
    department_id = fields.Many2one('hr.department', readonly=True)
    job_id = fields.Many2one('hr.job', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    on_holiday = fields.Boolean('On holiday', readonly=True)
    on_attendance = fields.Boolean('On attendance', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_leave_attendance_report_calendar')
        self._cr.execute("""CREATE OR REPLACE VIEW hr_leave_attendance_report_calendar AS
        (SELECT
            row_number() OVER() AS id,
            lar.employee_id AS employee_id,
            em.name AS name,
            lar.start_datetime as start_datetime,
            lar.stop_datetime as stop_datetime,
            lar.on_holiday as on_holiday,
            lar.on_attendance as on_attendance,
            em.department_id as department_id,
            em.job_id as job_id,
            em.company_id as company_id
        FROM hr_leave_attendance_report lar
            LEFT JOIN hr_employee em
                ON em.id = lar.employee_id
        ORDER BY id);""", [self.env.company.resource_calendar_id.tz or self.env.user.tz or 'UTC'])

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env.user.employee_id._get_unusual_days(date_from, date_to)
