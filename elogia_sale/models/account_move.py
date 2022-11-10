# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    campaign_elogia_id = fields.Many2one('campaign.marketing.elogia', 'Campaigns', ondelete='restrict', tracking=1)
    control_id = fields.Many2one('control.campaign.marketing', 'Control', ondelete='restrict', tracking=1)


class AccountMoveLine(models.Model):
    """ Override AccountInvoice_line to add the link to the purchase order line it is related to"""
    _inherit = 'account.move.line'

    campaign_elogia_id = fields.Many2one('campaign.marketing.elogia', 'Campaigns', ondelete='set null', index=True, copy=True)
    control_id = fields.Many2one('control.campaign.marketing', 'Control', ondelete='set null', index=True, copy=True)
