# -*- coding: utf-8 -*-

from odoo import models
import logging

_logger = logging.getLogger(__name__)


class SaleIntegration(models.Model):
    _inherit = 'sale.integration'

    def _prepare_inventory_data(self, product, ext_product, ext_location_id):
        """
        Override to inject the "Free to Use" calculation and prevent overselling
        by reserving the stock that is currently strictly reserved (outgoing_qty) in Odoo.
        """
        res = super(SaleIntegration, self)._prepare_inventory_data(product, ext_product, ext_location_id)

        if self.is_shopify():
            # Only calculate specifically for storable products
            if product.type == 'consu' or product.type == 'product':
                # The 'product' recordset already contains the correct location context
                # passed by the integration engine (e.g. location=locations.ids).
                on_hand = product.qty_available
                reserved = product.outgoing_qty
                
                # Formula: max(0, On Hand - Reserved)
                free_to_use = max(0, on_hand - reserved)

                _logger.info(
                    "Shopify Inventory SSOT | SKU: %s | On Hand: %s | Reserved (Outgoing): %s | Free to Use: %s | Original Qty: %s",
                    product.default_code or ext_product.external_reference,
                    on_hand,
                    reserved,
                    free_to_use,
                    res.get('qty', 0.0)
                )

                res['qty'] = free_to_use

        return res
