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
        # Note: The connector uses provider='shopify' field to identify Shopify instances (as seen in is_shopify())
        integrations = self.search([('state', '=', 'active'), ('provider', '=', 'shopify')])
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
        Fetches inventory from Shopify and compares it against Odoo's Free to Use calculation.
        """
        self.ensure_one()
        _logger.info("Reconciling Inventory for %s", self.name)
        
        try:
            # As per requirements, we expect self.adapter.fetch_all_inventory() to return a dict mapping external references/codes to quantity.
            # E.g. {'SKU-123': 100, ...} or {variant_id: qty} depending on adapter implementation.
            shopify_inventory = self.adapter.fetch_all_inventory()
        except AttributeError:
            _logger.warning(
                "Adapter for %s does not implement 'fetch_all_inventory'. "
                "Please ensure the adapter provides this method. Skipping inventory reconciliation.", 
                self.name
            )
            return

        discrepancies = []
        
        # We iterate over all products mapped to this integration
        ProductProductExternal = self.env['integration.product.product.external'].with_context(
            company_id=self.company_id.id
        )
        external_mappings = ProductProductExternal.search([('integration_id', '=', self.id)])
        
        # MEDIO-02: Prefetch all products in a single operation to avoid N+1 queries
        products = external_mappings.mapped('product_id')
        # Trigger mass prefetch of inventory fields for all products in this batch
        products.mapped('qty_available')
        products.mapped('outgoing_qty')

        for mapping in external_mappings:
            product = mapping.product_id
            # MEDIO-01: Fix filter logic and Odoo 18 compatibility
            if not (product.type == 'consu' and product.is_storable):
                continue
                
            # Shopify returns inventory by code or by variant id based on fetch_all_inventory implementation
            # We assume it maps to mapping.code (Variant ID or SKU depending on the adapter implementation)
            shopify_qty = shopify_inventory.get(mapping.code)
            if shopify_qty is None:
                # Could be missed or not tracked
                continue
                
            # Odoo "Free to Use" quantity calculation
            odoo_qty = max(0, product.qty_available - product.outgoing_qty)
            
            diff = abs(odoo_qty - shopify_qty)
            
            # Tolerance of difference > 1
            if diff > 1:
                discrepancies.append({
                    'product': product.default_code or product.name,
                    'odoo_qty': odoo_qty,
                    'shopify_qty': shopify_qty,
                    'diff': diff
                })
                
        if discrepancies:
            _logger.warning(
                "Detected %d inventory discrepancies for integration %s.\nDiscrepancies detail:\n%s", 
                len(discrepancies), 
                self.name, 
                discrepancies
            )
        else:
            _logger.info("Inventory is perfectly reconciled for integration %s. No drift detected within tolerance.", self.name)

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
