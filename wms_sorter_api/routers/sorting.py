import logging

from fastapi import APIRouter, Depends
from odoo.addons.fastapi.dependencies import odoo_env
from odoo.api import Environment

from ..dependencies import get_current_user

from ..schemas import (
    WaveSortingRequest,
    RealtimeDataRequest,
    SortingStatusPushRequest,
    SortingDataResponse,
    SortingItem,
    AckResponse,
)

_logger = logging.getLogger(__name__)

router = APIRouter(tags=["sorter"], dependencies=[Depends(get_current_user)])


# ──────────────────────────────────────────────────────────────────────────── #
# Helpers                                                                       #
# ──────────────────────────────────────────────────────────────────────────── #

def _move_lines_to_items(move_lines) -> list[SortingItem]:
    """Convert stock.move.line records into SortingItem objects."""
    items = []
    for line in move_lines:
        product = line.product_id
        chute = (
            line.picking_id.assigned_chute_id.name
            if line.picking_id.assigned_chute_id
            else ""
        )
        items.append(
            SortingItem(
                order=line.picking_id.sale_id.name or "",
                sn=product.barcode or "",
                num=int(line.quantity or line.qty_done or 0),
                chute=chute,
            )
        )
    return items


# ──────────────────────────────────────────────────────────────────────────── #
# Endpoint 1: Wave Sorting API – POST /wave-sorting                            #
# ──────────────────────────────────────────────────────────────────────────── #

@router.post("/wave-sorting", response_model=SortingDataResponse)
def wave_sorting(
    body: WaveSortingRequest,
    env: Environment = Depends(odoo_env),
):
    """
    Retrieve all sorting data for a given wave / picking batch.

    The sorter equipment sends a ``wave_No`` and Odoo returns the list of
    SKU / barcode / quantity / chute assignments for that batch.
    """
    batch = env["stock.picking.batch"].search(
        [("name", "=", body.wave_No)], limit=1
    )
    if not batch:
        return SortingDataResponse(
            code=1,
            data=[],
            msg=f"Wave '{body.wave_No}' not found.",
        )

    move_lines = batch.move_line_ids
    items = _move_lines_to_items(move_lines)
    return SortingDataResponse(code=0, data=items, msg="OK")


# ──────────────────────────────────────────────────────────────────────────── #
# Endpoint 2: Scheduled Acquisition – GET /scheduled-data                      #
# ──────────────────────────────────────────────────────────────────────────── #

@router.get("/scheduled-data", response_model=SortingDataResponse)
def scheduled_data(env: Environment = Depends(odoo_env)):
    """
    Return sorting data for ALL active / in-progress picking batches.

    Intended for periodic polling by the sorter equipment.
    """
    batches = env["stock.picking.batch"].search(
        [("state", "in", ("in_progress", "ready"))],
        order="id asc",
    )
    if not batches:
        return SortingDataResponse(code=0, data=[], msg="No active waves found.")

    all_lines = batches.mapped("move_line_ids")
    items = _move_lines_to_items(all_lines)
    return SortingDataResponse(code=0, data=items, msg="OK")


# ──────────────────────────────────────────────────────────────────────────── #
# Endpoint 3: Real-time Acquisition – POST /realtime-data                      #
# ──────────────────────────────────────────────────────────────────────────── #

@router.post("/realtime-data", response_model=SortingDataResponse)
def realtime_data(
    body: RealtimeDataRequest,
    env: Environment = Depends(odoo_env),
):
    """
    Look up a single product by barcode and return its current sorting assignment.

    The equipment sends a barcode (``Sn``) and Odoo returns the matching
    move line data from any active batch.
    """
    product = env["product.product"].search(
        [("barcode", "=", body.Sn)], limit=1
    )
    if not product:
        return SortingDataResponse(
            code=1,
            data=[],
            msg=f"Product with barcode '{body.Sn}' not found.",
        )

    # Find active move lines for this product
    move_lines = env["stock.move.line"].search(
        [
            ("product_id", "=", product.id),
            ("state", "not in", ("done", "cancel")),
            ("picking_id.batch_id", "!=", False),
        ],
        limit=1,
    )
    if not move_lines:
        return SortingDataResponse(
            code=1,
            data=[],
            msg=f"No active sorting assignment for barcode '{body.Sn}'.",
        )

    items = _move_lines_to_items(move_lines)
    return SortingDataResponse(code=0, data=items, msg="OK")


# ──────────────────────────────────────────────────────────────────────────── #
# Endpoint 5: Sorting Status Push – POST /sorting-status-push                  #
# ──────────────────────────────────────────────────────────────────────────── #

@router.post("/sorting-status-push", response_model=AckResponse)
def sorting_status_push(
    body: SortingStatusPushRequest,
    env: Environment = Depends(odoo_env),
):
    """
    Equipment pushes a sorting result to Odoo.

    - ``status == "Sorting Completed"`` → validate the related move line.
    - Any other status (jams, errors) → log a warning in wms.sorter.log.
    """
    Log = env["wms.sorter.log"].sudo()

    # Validate product
    product = env["product.product"].search(
        [
            ("barcode", "=", body.sn),
        ],
        limit=1,
    )
    if not product:
        Log.log_event(
            sku=body.order,
            barcode=body.sn,
            quantity=body.num,
            chute=body.chute,
            status=body.status,
            level="error",
            note="Product not found during status push.",
        )
        return AckResponse(code=1, msg=f"Product '{body.order}' / '{body.sn}' not found.")

    if body.status == "Sorting Completed":
        # Find the matching move line in an active batch
        move_line = env["stock.move.line"].search(
            [
                ("product_id", "=", product.id),
                ("state", "not in", ("done", "cancel")),
                ("picking_id.batch_id", "!=", False),
                ("picking_id.sale_id.name", "=", body.order),
            ],
            limit=1,
        )
        if move_line:
            try:
                move_line.sudo().write({
                    "qty_done": body.num,
                })
                # Release Chute
                move_line.picking_id.sudo()._release_sorter_chute()

                Log.log_event(
                    sku=body.order,
                    barcode=body.sn,
                    quantity=body.num,
                    chute=body.chute,
                    status=body.status,
                    level="info",
                    note=f"Move line {move_line.id} updated and chute released.",
                    batch_id=move_line.picking_id.batch_id.id,
                )
            except Exception as exc:  # noqa: BLE001
                _logger.exception("Error updating move line for sorter push: %s", exc)
                return AckResponse(code=1, msg=f"Error updating move: {exc}")
        else:
            Log.log_event(
                sku=body.order,
                barcode=body.sn,
                quantity=body.num,
                chute=body.chute,
                status=body.status,
                level="warning",
                note="Sorting Completed received but no active move line found.",
            )
    else:
        # Equipment error / jam
        level = "warning" if "jammed" in body.status.lower() else "info"
        Log.log_event(
            sku=body.order,
            barcode=body.sn,
            quantity=body.num,
            chute=body.chute,
            status=body.status,
            level=level,
            note=f"Equipment status event: {body.status}",
        )
        _logger.warning(
            "Sorter equipment event for SKU %s (barcode %s) chute %s: %s",
            body.order, body.sn, body.chute, body.status,
        )

    return AckResponse(code=0, msg="Received")
