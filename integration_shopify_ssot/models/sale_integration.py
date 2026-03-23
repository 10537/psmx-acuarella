# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleIntegration(models.Model):
    _inherit = 'sale.integration'
    
    enforce_ssot = fields.Boolean(
        string='Enforce SSOT (Odoo)',
        default=True,
        help="If enabled, Odoo is strictly enforced as the single source of truth. Destructive webhooks and unmapped locations are blocked."
    )

    @api.constrains('webhook_line_ids', 'enforce_ssot')
    def _check_ssot_webhooks(self):
        """
        Prevent destructive webhooks (products/update, products/delete)
        if SSOT is enforced.
        """
        for record in self:
            if record.is_shopify() and record.enforce_ssot:
                for webhook in record.webhook_line_ids:
                    if webhook.is_active and webhook.technical_name in ('products/update', 'products/delete'):
                        raise ValidationError(
                            f"SSOT is enforced for integration {record.name}. "
                            f"Destructive webhooks like '{webhook.technical_name}' are not allowed "
                            f"as they could overwrite changes made in Odoo. Please deactivate them."
                        )

    @api.constrains('location_line_ids', 'enforce_ssot')
    def _check_location_mapping(self):
        """
        Ensure all active external locations are mapped to an Odoo warehouse/location.
        """
        for record in self:
            if record.is_shopify() and record.enforce_ssot:
                for loc_line in record.location_line_ids:
                    if not loc_line.erp_location_id:
                        raise ValidationError(
                            f"Unmapped Shopify Location detected: {loc_line.external_location_id.name or 'Unknown'}. "
                            "Please ensure all external locations have an Odoo location assigned."
                        )
