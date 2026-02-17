from odoo.tests.common import TransactionCase
from fastapi import HTTPException, status
from unittest.mock import MagicMock
from ..routers.shipping_router import update_shipping_info, update_shipping_status
from ..schemas.shipping_schema import ShippingUpdateSchema, StatusUpdateSchema


class TestShippingApi(TransactionCase):
    def setUp(self):
        super().setUp()
        self.picking = self.env["stock.picking"].create(
            {
                "name": "TEST-PICKING-001",
                "origin": "SO001",
                "picking_type_id": self.env.ref("stock.picking_type_out").id,
                "location_id": self.env.ref("stock.stock_location_stock").id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
            }
        )
        # Mock auth dependency implicitly (dependencies are usually bypassed in direct function calls, 
        # but since we added `dependencies=[Depends(get_current_user)]` to the router, 
        # calling the function directly *bypasses* the router-level dependencies in unit tests.
        # So we just verify the logic works. To test auth, we would need TestClient or mock the dependency.)
    
    def test_update_shipping_info(self):
        # Direct function call bypasses the router-level dependency, 
        # validating the logic itself. Auth is handled by FastAPI framework.
        payload = ShippingUpdateSchema(
            order_name="SO001",
            carrier_tracking_ref="TRACK-12345",
            carrier_partner_name="John Doe",
            carrier_identity_document="123456789",
            carrier_delivery_address="123 Main St",
            carrier_state="Initial Carrier State",
        )
        response = update_shipping_info(payload, env=self.env)
        self.assertEqual(response["status"], "success")

        # Refresh picking
        self.picking.invalidate_recordset()
        self.assertEqual(self.picking.x_carrier_tracking_ref, "TRACK-12345")
        self.assertEqual(self.picking.x_carrier_partner_name, "John Doe")
        self.assertEqual(self.picking.x_carrier_identity_document, "123456789")
        self.assertEqual(self.picking.x_carrier_delivery_address, "123 Main St")
        self.assertEqual(self.picking.x_carrier_state, "Initial Carrier State")

    def test_update_shipping_status(self):
        payload = StatusUpdateSchema(
            order_name="SO001",
            carrier_state="Delivered",
        )
        response = update_shipping_status(payload, env=self.env)
        self.assertEqual(response["status"], "success")

        self.picking.invalidate_recordset()
        self.assertEqual(self.picking.x_carrier_state, "Delivered")
