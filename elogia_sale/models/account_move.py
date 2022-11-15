# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    """ Override AccountInvoice_line to add the link to the purchase order line it is related to"""
    _inherit = 'account.move'

    type_move = fields.Selection(selection=[
        ('null', 'Null'),
        ('accounting', 'Accounting'),
        ('provision', 'Provision'),
    ], string='Type move', default='null', tracking=1)


class AccountMoveLine(models.Model):
    """ Override AccountInvoice_line to add the link to the purchase order line it is related to"""
    _inherit = 'account.move.line'

    campaign_elogia_id = fields.Many2one('campaign.marketing.elogia', 'Campaigns', ondelete='restrict', index=True)
    control_id = fields.Many2one('control.campaign.marketing', 'Control', ondelete='restrict', index=True)

    @api.constrains('parent_state')
    def check_state_by_order_line(self):
        env_control = self.env['control.campaign.marketing']
        for record in self:
            if record.parent_state == 'cancel':
                obj_control_ids = env_control.search([('id', '=', record.control_id.id)])
                if obj_control_ids:
                    if any(obj_control_ids.filtered(lambda e: e.state == 'both')):
                        raise UserError(_('Account move cannot be cancelled. \n '
                                          'The related control is in "Processed" state!'))
                    else:
                        for control in obj_control_ids:
                            if control.type_invoice == 'account':
                                if control.show_purchase:
                                    control.write({'state': 'pending'})
                                else:
                                    if control.state not in ['cancel', 'pending', 'draft']:
                                        control.write({'state': 'purchase'})
