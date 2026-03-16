# -*- coding: utf-8 -*-

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class SaleIntegration(models.Model):
    _inherit = 'sale.integration'

    @api.model
    def _cron_reconcile_shopify(self):
        """
        Daily cron job to detect configuration drifts and overselling between Odoo and Shopify.
        """
        # RE-CRITICO-01: Correct field name is type_api, not provider
        integrations = self.search([('state', '=', 'active'), ('type_api', '=', 'shopify')])
        for integration in integrations:
            _logger.info("Starting Daily Reconciliation for Shopify Integration: %s", integration.name)
            try:
                integration._reconcile_inventory()
                integration._reconcile_products()
                integration._reconcile_orders()
            except Exception as e:
                _logger.error("Error during reconciliation for %s: %s", integration.name, str(e), exc_info=True)

    def _reconcile_inventory(self):
        """
        RE-CRITICO-02: Option A - Internal Drift Check.
        Compares Odoo's current Free to Use stock against the last value stored in the integration's sync field.
        This detects drift without needing to query Shopify directly, avoiding adapter issues.
        """
        self.ensure_one()
        _logger.info("Reconciling Inventory for %s (Internal Drift Check)", self.name)
        
        locations = self.get_integration_location()
        if not locations:
            _logger.warning("No locations configured for integration %s. Skipping reconciliation.", self.name)
            return

        MappingModel = self.env['integration.product.product.mapping']
        mappings = MappingModel.search([('integration_id', '=', self.id)])
        if not mappings:
            _logger.info("No product mappings found for integration %s.", self.name)
            return

        # MEDIO-02: Batch prefetch products and stock quantities
        products = mappings.mapped('product_id')
        products_ctx = products.with_context(location=locations.ids)
        products_ctx.mapped('qty_available')
        products_ctx.mapped('outgoing_qty')

        discrepancies = []
        for mapping in mappings:
            product = mapping.product_id
            # MEDIO-01: Filter for storable products
            if not (product.type == 'consu' and product.is_storable):
                continue
                
            p_ctx = product.with_context(location=locations.ids)
            odoo_free = max(0, p_ctx.qty_available - p_ctx.outgoing_qty)
            
            # Compare against what the integration engine last calculated
            # This detects drift relative to Odoo's tracking of the external state
            last_qty = getattr(p_ctx, self.synchronise_qty_field, None)
            
            if last_qty is not None:
                diff = abs(odoo_free - last_qty)
                # Tolerance of difference > 1
                if diff > 1:
                    discrepancies.append({
                        'product': product.default_code or product.name,
                        'odoo_free': odoo_free,
                        'last_synced_qty': last_qty,
                        'diff': diff
                    })
                
        if discrepancies:
            _logger.warning(
                "Detected %d inventory drift items for integration %s:\n%s", 
                len(discrepancies), 
                self.name, 
                discrepancies
            )
        else:
            _logger.info("Inventory is consistent for integration %s. No drift detected.", self.name)

    def _reconcile_products(self):
        """
        Hook for reconciling products.
        """
        # MEDIO-04: Implement stub warning
        self.ensure_one()
        _logger.warning("Method '_reconcile_products' is currently a stub and performs no action for integration %s.", self.name)
        pass

    def _reconcile_orders(self):
        """
        Hook for reconciling orders.
        """
        # MEDIO-04: Implement stub warning
        self.ensure_one()
        _logger.warning("Method '_reconcile_orders' is currently a stub and performs no action for integration %s.", self.name)
        pass
