from odoo import fields, models
from fastapi import APIRouter
from ..routers.sorting import router as sorting_router


class FastapiEndpoint(models.Model):
    _inherit = "fastapi.endpoint"

    app = fields.Selection(
        selection_add=[("sorter", "WMS Sorter API")],
        ondelete={"sorter": "cascade"},
    )

    def _get_fastapi_routers(self) -> list[APIRouter]:
        if self.app == "sorter":
            return [sorting_router]
        return super()._get_fastapi_routers()
