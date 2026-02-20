# -*- coding: utf-8 -*-

from odoo import models, api
from ..tools.logging_helper import StructuredLogger, correlation_id_var
import uuid

# Replace standard logger with StructuredLogger
_logger = StructuredLogger(__name__)


class SaleIntegration(models.Model):
    _inherit = 'sale.integration'

    def _prepare_inventory_data(self, product, ext_product, ext_location_id):
        """
        Override to inject StructuredLogger logging with tracking data.
        """
        res = super(SaleIntegration, self)._prepare_inventory_data(product, ext_product, ext_location_id)
        
        _logger.info(
            "Exporting inventory for Shopify.",
            integration_id=self.id,
            entity_type='product',
            entity_id=product.id
        )
        return res

    @api.model
    def _cron_reconcile_shopify(self):
        """
        Override cron entrypoint to always generate a root correlation_id.
        """
        # Set a parent correlation_id for the entire cron run
        cron_corr_id = str(uuid.uuid4())
        correlation_id_var.set(cron_corr_id)
        
        # Propagate to context so jobs launched from cron inherit it
        self = self.with_context(correlation_id=cron_corr_id)
        
        _logger.info(
            "Starting Shopify Daily Reconciliation Motor.",
            entity_type='cron',
        )
        
        return super(SaleIntegration, self)._cron_reconcile_shopify()

