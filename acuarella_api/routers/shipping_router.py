from fastapi import APIRouter, HTTPException, Depends
from odoo.addons.fastapi.dependencies import odoo_env
from odoo.api import Environment

from ..schemas.shipping_schema import ShippingUpdateSchema, StatusUpdateSchema
from ..dependencies import get_current_user

router = APIRouter(tags=["shipping"], dependencies=[Depends(get_current_user)])


@router.post("/update_info")
def update_shipping_info(
    data: ShippingUpdateSchema, env: Environment = Depends(odoo_env)
):
    picking = env["stock.picking"].search([("origin", "=", data.order_name)], limit=1)
    if not picking:
        raise HTTPException(status_code=404, detail="Picking not found for this Order")

    values = {}
    if data.carrier_tracking_ref:
        values["x_carrier_tracking_ref"] = data.carrier_tracking_ref
    if data.carrier_partner_name:
        values["x_carrier_partner_name"] = data.carrier_partner_name
    if data.carrier_identity_document:
        values["x_carrier_identity_document"] = data.carrier_identity_document
    if data.carrier_delivery_address:
        values["x_carrier_delivery_address"] = data.carrier_delivery_address
    if data.carrier_state:
        values["x_carrier_state"] = data.carrier_state

    if values:
        picking.write(values)

    return {"status": "success", "message": "Shipping info updated"}


@router.post("/update_status")
def update_shipping_status(
    data: StatusUpdateSchema, env: Environment = Depends(odoo_env)
):
    picking = env["stock.picking"].search([("origin", "=", data.order_name)], limit=1)
    if not picking:
        raise HTTPException(status_code=404, detail="Picking not found for this Order")

    picking.write({"x_carrier_state": data.carrier_state})

    return {"status": "success", "message": "Shipping status updated"}

