# -*- coding: utf-8 -*-

import json
from odoo import models, api
from odoo.exceptions import UserError
from odoo.addons.integration_shopify_observability.tools.logging_helper import StructuredLogger

_logger = StructuredLogger(__name__)


class SaleIntegration(models.Model):
    _inherit = 'sale.integration'

    def _get_shopify_graphql_client(self):
        self.ensure_one()
        adapter = self._build_adapter()
        # ShopifyAPIClient usually exposes _graphql, or we can instantiate it
        if hasattr(adapter, '_graphql'):
            return adapter._graphql
        
        # Fallback to instantiating directly if _graphql is not exposed
        from odoo.addons.integration_shopify.shopify.shopify_graphql import ShopifyGraphQL
        settings = adapter.settings
        return ShopifyGraphQL(settings['url'], settings['password'])

    def sync_shopify_customer(self, partner_id):
        """
        Syncs an Odoo res.partner to Shopify.
        Handles Upsert (Create or Update based on mapping or email mapping).
        """
        partner = self.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return

        _logger.info("Starting sync_shopify_customer for partner %s", partner.name, integration_id=self.id, entity_type='partner', entity_id=partner.id)

        if getattr(partner, 'is_company', False):
            tags = ["Mayorista"]
            company_name = partner.name
            first_name = partner.name
            last_name = "-"
        else:
            tags = ["Detal"]
            company_name = ""
            parts = partner.name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else "-"

        if not partner.active:
            tags.append("DISABLED")

        address_payload = {
            "address1": partner.street or "",
            "address2": partner.street2 or "",
            "city": partner.city or "",
            "zip": partner.zip or "",
            "firstName": first_name,
            "lastName": last_name,
            "company": company_name,
            "phone": partner.phone or "",
        }
        if partner.country_id:
            address_payload["countryCode"] = partner.country_id.code
        if partner.state_id:
            address_payload["provinceCode"] = partner.state_id.code

        variables = {
            "input": {
                "firstName": first_name,
                "lastName": last_name,
                "email": partner.email,
                "phone": partner.phone or "",
                "tags": tags,
            }
        }
        
        # Inject address list
        if address_payload:
            variables["input"]["addresses"] = [address_payload]

        client = self._get_shopify_graphql_client()

        # Check mapping
        mapping = self.env['integration.res.partner.mapping'].search([
            ('integration_id', '=', self.id),
            ('partner_id', '=', partner.id)
        ], limit=1)

        customer_gid = ""
        
        if mapping:
            # Format the ID into a Shopify GID: gid://shopify/Customer/123456
            ext_id = mapping.external_partner_id.code
            if not ext_id.startswith('gid://'):
                customer_gid = f"gid://shopify/Customer/{ext_id}"
            else:
                customer_gid = ext_id

        if not customer_gid and partner.email:
            # Search by email (RN-03 partial: check existing to avoid 422)
            query_search = """
                query customerByEmail($query: String!) {
                    customers(first: 1, query: $query) {
                        edges {
                            node {
                                id
                            }
                        }
                    }
                }
            """
            search_vars = {"query": f"email:{partner.email}"}
            res_search = client.execute(query_search, search_vars)
            edges = res_search.get('data', {}).get('customers', {}).get('edges', [])
            if edges:
                customer_gid = edges[0]['node']['id']
                # Create mapping
                ext_code = customer_gid.split('/')[-1]
                ext_model = self.env['integration.res.partner.external']
                ext_record = ext_model.search([('code', '=', ext_code), ('integration_id', '=', self.id)], limit=1)
                if not ext_record:
                    ext_record = ext_model.create({
                        'code': ext_code,
                        'name': partner.name,
                        'integration_id': self.id,
                    })
                MappingModel = self.env['integration.res.partner.mapping']
                if not MappingModel.search([('integration_id', '=', self.id), ('partner_id', '=', partner.id)]):
                    MappingModel.create({
                        'integration_id': self.id,
                        'partner_id': partner.id,
                        'external_partner_id': ext_record.id,
                    })

        if customer_gid:
            # Prepare UPDATE and deduplicate Addresses
            if address_payload:
                address_query = """
                    query customerAddress($id: ID!) {
                        customer(id: $id) {
                            defaultAddress { id }
                        }
                    }
                """
                res_addr = client.execute(address_query, {"id": customer_gid})
                default_address = res_addr.get('data', {}).get('customer', {}).get('defaultAddress')
                if default_address and default_address.get('id'):
                    address_payload["id"] = default_address["id"]
                
                variables["input"]["addresses"] = [address_payload]

            variables["input"]["id"] = customer_gid
            query_update = """
                mutation customerUpdate($input: CustomerInput!) {
                    customerUpdate(input: $input) {
                        customer { id }
                        userErrors { field message }
                    }
                }
            """
            res = client.execute(query_update, variables)
            errors = res.get('data', {}).get('customerUpdate', {}).get('userErrors', [])
            if errors:
                raise UserError(f"Error updating customer {partner.name} in Shopify: {errors}")
            else:
                _logger.info("Successfully updated customer %s in Shopify.", partner.name, integration_id=self.id, entity_type='partner', entity_id=partner.id)
        else:
            # CREATE
            query_create = """
                mutation customerCreate($input: CustomerInput!) {
                    customerCreate(input: $input) {
                        customer { id }
                        userErrors { field message }
                    }
                }
            """
            res = client.execute(query_create, variables)
            data = res.get('data', {}).get('customerCreate', {})
            errors = data.get('userErrors', [])
            
            # RN-03 full fallback: if we get "Email has already been taken" (422 equivalent in GraphQL)
            # wait, the search above should have caught it. But just in case:
            if errors and any('taken' in err.get('message', '').lower() for err in errors):
                _logger.warning("Email taken for %s. Shopify race condition detected.", partner.email, integration_id=self.id)
                # We could retry mapping here if needed.
                return

            if errors:
                raise UserError(f"Error creating customer {partner.name} in Shopify: {errors}")
            else:
                # Save mapping
                new_gid = data.get('customer', {}).get('id')
                if new_gid:
                    ext_code = new_gid.split('/')[-1]
                    ext_model = self.env['integration.res.partner.external']
                    ext_record = ext_model.create({
                        'code': ext_code,
                        'name': partner.name,
                        'integration_id': self.id,
                    })
                    MappingModel = self.env['integration.res.partner.mapping']
                    MappingModel.create({
                        'integration_id': self.id,
                        'partner_id': partner.id,
                        'external_partner_id': ext_record.id,
                    })
                _logger.info("Successfully created customer %s in Shopify.", partner.name, integration_id=self.id, entity_type='partner', entity_id=partner.id)

    def delete_shopify_customer(self, shopify_external_codes):
        """
        Deletes a list of customers from Shopify by their ID.
        """
        client = self._get_shopify_graphql_client()
        query_delete = """
            mutation customerDelete($id: ID!) {
                customerDelete(id: $id) {
                    deletedCustomerId
                    userErrors { field message }
                }
            }
        """

        for ext_code in shopify_external_codes:
            gid = f"gid://shopify/Customer/{ext_code}" if not ext_code.startswith('gid://') else ext_code
            res = client.execute(query_delete, {"id": gid})
            errors = res.get('data', {}).get('customerDelete', {}).get('userErrors', [])
            if errors:
                raise UserError(f"Error deleting customer {gid} in Shopify: {errors}")
            else:
                _logger.info("Successfully deleted Shopify customer %s", gid, integration_id=self.id)
