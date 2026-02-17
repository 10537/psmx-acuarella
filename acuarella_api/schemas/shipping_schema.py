from pydantic import BaseModel


class ShippingUpdateSchema(BaseModel):
    order_name: str
    carrier_tracking_ref: str | None = None
    carrier_partner_name: str | None = None
    carrier_identity_document: str | None = None
    carrier_delivery_address: str | None = None
    carrier_state: str | None = None


class StatusUpdateSchema(BaseModel):
    order_name: str
    carrier_state: str
