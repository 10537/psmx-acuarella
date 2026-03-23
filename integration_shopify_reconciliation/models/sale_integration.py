# -*- coding: utf-8 -*-

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class SaleIntegration(models.Model):
    _inherit = 'sale.integration'

    reconciliation_email_list = fields.Char(
        string='Reconciliation Notify Emails',
        help='Comma-separated list of email addresses to notify when inventory drift is detected.'
    )
    reconciliation_admin_id = fields.Many2one(
        'res.users',
        string='Integration Admin',
        help='Administrator to assign mail activities for reconciliation.'
    )

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
        RE-CRITICO-02: Compare Odoo's current Free to Use stock against Shopify's actual stock.
        """
        self.ensure_one()
        _logger.info("Reconciling Inventory for %s", self.name)
        
        locations = self.get_integration_location()
        if not locations:
            _logger.warning("No locations configured for integration %s. Skipping reconciliation.", self.name)
            return

        MappingModel = self.env['integration.product.product.mapping']
        mappings = MappingModel.search([('integration_id', '=', self.id)])
        if not mappings:
            _logger.info("No product mappings found for integration %s.", self.name)
            return

        # Fetch actual stock from Shopify
        try:
            adapter = self._build_adapter()
            shopify_inventory = adapter.fetch_all_inventory()
        except Exception as e:
            _logger.error("Failed to fetch inventory from Shopify for integration %s: %s", self.name, str(e))
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
            
            # Compare against Shopify's actual stock
            # Try to get by variant ID first, then by SKU
            variant_id = mapping.external_product_id.code.split('-')[-1] if mapping.external_product_id.code else None
            sku = product.default_code
            
            shopify_qty = shopify_inventory.get(variant_id)
            if shopify_qty is None and sku:
                shopify_qty = shopify_inventory.get(sku)
                
            if shopify_qty is not None:
                diff = abs(odoo_free - shopify_qty)
                # Tolerance of exactly 1
                if diff > 1:
                    discrepancies.append({
                        'product': sku or product.name,
                        'odoo_free': odoo_free,
                        'shopify_qty': shopify_qty,
                        'diff': diff
                    })

        if discrepancies:
            msg = f"Detected {len(discrepancies)} inventory drift items for integration {self.name}:\n"
            msg += "\n".join([f"- {d['product']}: Odoo: {d['odoo_free']}, Shopify: {d['shopify_qty']} (Diff: {d['diff']})" for d in discrepancies])
            _logger.warning(msg)
            self._notify_discrepancies("Inventory Reconciliation", msg)
        else:
            _logger.info("Inventory is consistent for integration %s. No drift detected.", self.name)

    def _notify_discrepancies(self, summary, detailed_msg):
        self.ensure_one()
        # 1. Enviar un correo a la lista configurable
        if self.reconciliation_email_list:
            mail_values = {
                'subject': f"[{self.name}] {summary} Alert",
                'body_html': f"<pre>{detailed_msg}</pre>",
                'email_to': self.reconciliation_email_list,
                'email_from': self.env.company.email or self.env.user.email,
            }
            self.env['mail.mail'].create(mail_values).send()

        # 2. Crear una mail.activity asignada al administrador
        if self.reconciliation_admin_id:
            self.activity_schedule(
                'mail.mail_activity_data_warning',
                user_id=self.reconciliation_admin_id.id,
                summary=f"{summary} Discrepancies",
                note=f"<pre>{detailed_msg}</pre>"
            )

        # 3. Publicar un resumen detallado en el chatter del registro
        self.message_post(body=f"<b>{summary} Alert</b><br/><pre>{detailed_msg}</pre>")

    def _reconcile_products(self):
        """
        Hook for reconciling products.
        """
        self.ensure_one()
        _logger.info("Method '_reconcile_products' execution for integration %s.", self.name)
        # For now, minimal implementation as per requirements (checking basic state integrity)
        # This will be refined as per gap analysis
        pass

    def _reconcile_orders(self):
        """
        Hook for reconciling orders.
        """
        self.ensure_one()
        _logger.info("Method '_reconcile_orders' execution for integration %s.", self.name)
        # For now, minimal implementation as per requirements
        pass
