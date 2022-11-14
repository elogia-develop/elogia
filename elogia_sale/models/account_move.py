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
