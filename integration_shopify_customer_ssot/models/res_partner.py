# -*- coding: utf-8 -*-

import uuid
from odoo import models, api
from odoo.addons.integration_shopify_observability.tools.logging_helper import StructuredLogger, correlation_id_var

_logger = StructuredLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _should_sync_to_shopify(self):
        """
        Determines if a partner should be synchronized to Shopify.
        Basically any contact can be synced but Email is required for Shopify.
        """
        self.ensure_one()
        return True

    def _enqueue_shopify_sync(self):
        """
        Creates a queue_job to sync this partner to all active Shopify integrations.
        """
        integrations = self.env['sale.integration'].search([('state', '=', 'active'), ('type_api', '=', 'shopify')])
        if not integrations:
            return

        for partner in self:
            if not partner._should_sync_to_shopify():
                continue

            for integration in integrations:
                if not partner.email:
                    _logger.warning("Partner %s missing email. Skipped Shopify sync.", partner.name, integration_id=integration.id, entity_type='partner', entity_id=partner.id)
                    continue

                # Generate a Correlation ID if not present
                corr_id = correlation_id_var.get()
                if not corr_id:
                    corr_id = str(uuid.uuid4())
                    correlation_id_var.set(corr_id)
                
                # We enqueue the job on the integration model to utilize its context
                # Odoo's queue_job automatically captures the context
                job = integration.with_context(correlation_id=corr_id).with_delay().sync_shopify_customer(partner.id)
                partner.with_context(default_integration_id=integration.id).job_log(job)

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ResPartner, self).create(vals_list)
        records._enqueue_shopify_sync()
        return records

    def write(self, vals):
        # Fields that should trigger a sync
        sync_fields = {'name', 'email', 'phone', 'is_company', 'active'}
        should_sync = any(field in vals for field in sync_fields)
        
        res = super(ResPartner, self).write(vals)
        
        if should_sync:
            self._enqueue_shopify_sync()
        
        return res

    def unlink(self):
        # RN-04 Unlink Strategy: Fetch Shopify IDs before the records are deleted
        integrations = self.env['sale.integration'].search([('state', '=', 'active'), ('type_api', '=', 'shopify')])
        
        if integrations:
            MappingModel = self.env['integration.res.partner.mapping']
            # We group deletions by integration
            integration_to_deletes = {}
            for integration in integrations:
                mappings = MappingModel.search([
                    ('integration_id', '=', integration.id),
                    ('partner_id', 'in', self.ids)
                ])
                if mappings:
                    codes = mappings.mapped('external_customer_id.code')
                    if codes:
                        integration_to_deletes[integration] = codes
            
            # Now we enqueue the deletions
            # We must do this before super().unlink() because after that we cannot reference self easily if we needed it,
            # though here we are just grabbing external string codes which is safe.
            for integration, codes in integration_to_deletes.items():
                corr_id = correlation_id_var.get() or str(uuid.uuid4())
                correlation_id_var.set(corr_id)
                
                _logger.info("Enqueuing deletion of Shopify customers: %s", codes, integration_id=integration.id)
                job = integration.with_context(correlation_id=corr_id).with_delay().delete_shopify_customer(codes)
                integration.job_log(job)

        return super(ResPartner, self).unlink()
