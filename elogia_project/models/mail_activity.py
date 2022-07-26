# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    action_required = fields.Boolean('Action required?', default=False)

    def action_close_dialog(self):
        obj_task = self.env['project.task']
        active_id = False
        if self.env.context.get('default_res_model'):
            if self._context['default_res_model'] == 'project.task' and self.action_required:
                active_id = self._context['default_res_id']
        if active_id:
            if obj_task.search([('id', '=', self._context['default_res_id'])], limit=1):
                obj_task_write = obj_task.search([('id', '=', self._context['default_res_id'])], limit=1)
                obj_task_write.write({'action_id': self.user_id.id})
        return {'type': 'ir.actions.act_window_close'}



