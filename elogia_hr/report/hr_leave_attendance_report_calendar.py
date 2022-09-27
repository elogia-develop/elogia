# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo import api, fields, models, tools, SUPERUSER_ID, _

from odoo.addons.base.models.res_partner import _tz_get


class LeaveAttendanceReportCalendar(models.Model):
    _name = "hr.leave.attendance.report.calendar"
    _description = 'Time Off Attendance Calendar'
    _auto = False
    _order = "start_datetime DESC, employee_id"

    name = fields.Char(string='Name', readonly=True)
    start_datetime = fields.Datetime(string='From', readonly=True)
    stop_datetime = fields.Datetime(string='To', readonly=True)
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
            em.id AS employee_id,
            em.department_id as department_id,
            em.job_id as job_id,
            em.company_id as company_id,
            CONCAT(em.name, ': ', em.employee_number) AS name,
            (CASE WHEN (hl.date_from is NOT NULL) THEN hl.date_from ELSE NOW() END) AS start_datetime,
            (CASE WHEN (hl.date_to is NOT NULL) THEN hl.date_to ELSE NOW() END) AS stop_datetime,
            hl.date_from is NOT NULL or hl.date_to is NOT NULL AS on_holiday,
            hl.date_from is NULL or hl.date_to is NULL AS on_attendance,
            CASE
                WHEN hl.holiday_type = 'employee' THEN rr.tz
                ELSE %s
            END AS tz
        FROM hr_employee em
            LEFT JOIN hr_leave hl
                ON hl.employee_id = em.id
            LEFT JOIN resource_resource rr
                ON rr.id = em.resource_id
        ORDER BY id);
        """, [self.env.company.resource_calendar_id.tz or self.env.user.tz or 'UTC'])

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env.user.employee_id._get_unusual_days(date_from, date_to)