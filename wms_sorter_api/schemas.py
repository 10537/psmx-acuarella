from pydantic import BaseModel
from typing import Optional, List


# ──────────────────────────────────────────────
# Request Schemas
# ──────────────────────────────────────────────

class WaveSortingRequest(BaseModel):
    """Endpoint 1: Wave Sorting API request."""
    wave_No: str


class RealtimeDataRequest(BaseModel):
    """Endpoint 3: Real-time acquisition by barcode."""
    Sn: str


class SortingStatusPushRequest(BaseModel):
    """Endpoint 5: Equipment pushes sorting result to Odoo."""
    order: str      # SKU / default_code
    sn: str         # Barcode
    num: int        # Quantity
    chute: str      # Chute / destination
    status: str     # e.g. "Sorting Completed" | "Goods Jammed at Chute 0"


# ──────────────────────────────────────────────
# Response Schemas
# ──────────────────────────────────────────────

class SortingItem(BaseModel):
    """A single sorting data record returned in responses."""
    order: str      # SKU
    sn: str         # Barcode
    num: int        # Quantity
    chute: str      # Chute


class SortingDataResponse(BaseModel):
    """Standard multi-item response (Endpoints 1, 2, 3)."""
    code: int       # 0 = success, 1 = error
    data: List[SortingItem]
    msg: str


class AckResponse(BaseModel):
    """Simple acknowledgement response (Endpoint 5)."""
    code: int       # 0 = success, 1 = error
    msg: str
