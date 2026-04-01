from unittest.mock import patch
from odoo.tests.common import TransactionCase
from ..routers.sorting import wave_end
from ..schemas import WaveEndRequest


class TestWaveEnd(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env = self.env(context=dict(self.env.context, tracking_disable=True))
        self.product = self.env["product.product"].create({
            "name": "Test Product",
            "type": "product",
        })
        self.batch = self.env["stock.picking.batch"].create({
            "name": "TEST-WAVE-001",
        })
        self.batch.state = "in_progress"

        self.picking = self.env["stock.picking"].create({
            "picking_type_id": self.env.ref("stock.picking_type_internal").id,
            "location_id": self.env.ref("stock.stock_location_stock").id,
            "location_dest_id": self.env.ref("stock.stock_location_stock").id,
            "batch_id": self.batch.id,
        })
        self.move_line_1 = self.env["stock.move.line"].create({
            "picking_id": self.picking.id,
            "product_id": self.product.id,
            "quantity": 1,
            "sorter_state": "draft",
        })
        self.move_line_2 = self.env["stock.move.line"].create({
            "picking_id": self.picking.id,
            "product_id": self.product.id,
            "quantity": 1,
            "sorter_state": "draft",
        })

    def test_wave_end_not_found(self):
        request = WaveEndRequest(wave_No="NON_EXISTENT")
        response = wave_end(body=request, env=self.env)
        self.assertEqual(response.code, 1)
        self.assertIn("not found", response.msg)

    def test_wave_end_not_in_progress(self):
        self.batch.state = "draft"
        request = WaveEndRequest(wave_No="TEST-WAVE-001")
        response = wave_end(body=request, env=self.env)
        self.assertEqual(response.code, 1)
        self.assertIn("not in progress", response.msg)

    def test_wave_end_not_collected(self):
        request = WaveEndRequest(wave_No="TEST-WAVE-001")
        response = wave_end(body=request, env=self.env)
        self.assertEqual(response.code, 1)
        self.assertIn("not collected", response.msg)

    def test_wave_end_success(self):
        self.move_line_1.sorter_state = "collected"
        self.move_line_2.sorter_state = "collected"

        request = WaveEndRequest(wave_No="TEST-WAVE-001")

        # Mock action_done to avoid complex picking validation in test
        BatchModel = type(self.env["stock.picking.batch"])
        with patch.object(BatchModel, "action_done", return_value=True) as mock_action_done:
            response = wave_end(body=request, env=self.env)

        self.assertEqual(response.code, 0)
        self.assertEqual(response.msg, "Wave validated successfully.")
        mock_action_done.assert_called_once()
