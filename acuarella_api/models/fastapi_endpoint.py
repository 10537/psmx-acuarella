from odoo import fields, models
from fastapi import APIRouter
from ..routers.shipping_router import router as shipping_router


class FastapiEndpoint(models.Model):
    _inherit = "fastapi.endpoint"

    app = fields.Selection(
        selection_add=[("shipping", "Shipping API")],
        ondelete={"shipping": "cascade"},
    )

    def _get_fastapi_routers(self) -> list[APIRouter]:
        if self.app == "shipping":
            return [shipping_router]
        return super()._get_fastapi_routers()
