"""
WMS Sorter API - Full sorting flow by wave
WMS 分拣 API - 按波次完整分拣流程

Steps / 步骤: wave-sorting → sorting-status-push (per item / 每个项目) → wave-end
"""

import requests
import json
import sys

BASE_URL = "https://test.jdchouse.com/api/sorter/v1"
API_KEY  = "2DL617oeMIRV79vjVhajDd5l7DuZdHpuvwcq6vytlhIiVl74fLRy6pesGgd6QTfH"

HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


# ─────────────────────────────────────────────
# STEP 1 – Retrieve items for the wave
# 第一步 – 获取波次中的待分拣项目
# ─────────────────────────────────────────────
def wave_sorting(wave_no: str) -> dict:
    """
    POST /wave-sorting
    Returns the list of orders/items to be sorted in the wave.
    返回波次中需要分拣的订单/项目列表。
    """
    url = f"{BASE_URL}/wave-sorting"
    payload = {"wave_No": wave_no}

    print(f"\n[STEP 1 / 第一步] wave-sorting  →  wave_No={wave_no}")
    resp = requests.post(url, headers=HEADERS, json=payload)
    resp.raise_for_status()

    data = resp.json()
    print(f"         HTTP Status / HTTP状态码: {resp.status_code}")
    print(f"         Response / 响应          : {json.dumps(data, indent=2)}")
    return data


# ─────────────────────────────────────────────
# STEP 2 – Push the sorting status for each item
# 第二步 – 推送每个项目的分拣状态
# ─────────────────────────────────────────────
def sorting_status_push(order: str, sn: str, num: int,
                         chute: str, status: str = "completed") -> dict:
    """
    POST /sorting-status-push
    Notifies the sorting result for a single item.
    通知单个项目的分拣结果。
    """
    url = f"{BASE_URL}/sorting-status-push"
    payload = {
        "order":  order,   # Order number / 订单号
        "sn":     sn,      # Serial number / 序列号
        "num":    num,     # Quantity / 数量
        "chute":  chute,   # Chute assigned / 分配的滑槽
        "status": status,  # Sorting status / 分拣状态
    }

    print(f"\n[STEP 2 / 第二步] sorting-status-push  →  order={order} | sn={sn} | chute={chute}")
    resp = requests.post(url, headers=HEADERS, json=payload)
    resp.raise_for_status()

    data = resp.json()
    print(f"         HTTP Status / HTTP状态码: {resp.status_code}")
    print(f"         Response / 响应          : {json.dumps(data, indent=2)}")
    return data


# ─────────────────────────────────────────────
# STEP 3 – Close / end the wave
# 第三步 – 关闭/结束波次
# ─────────────────────────────────────────────
def wave_end(wave_no: str) -> dict:
    """
    POST /wave-end
    Marks the wave as finished.
    将波次标记为已完成。
    """
    url = f"{BASE_URL}/wave-end"
    payload = {"wave_No": wave_no}

    print(f"\n[STEP 3 / 第三步] wave-end  →  wave_No={wave_no}")
    resp = requests.post(url, headers=HEADERS, json=payload)
    resp.raise_for_status()

    data = resp.json()
    print(f"         HTTP Status / HTTP状态码: {resp.status_code}")
    print(f"         Response / 响应          : {json.dumps(data, indent=2)}")
    return data


# ─────────────────────────────────────────────
# FULL FLOW / 完整流程
# ─────────────────────────────────────────────
def run_full_flow(wave_no: str):
    """
    Runs all 3 steps in sequence using the real data returned by the API.
    按顺序执行全部三个步骤，使用 API 返回的真实数据。

    Assumes wave-sorting returns a structure like:
    假设 wave-sorting 返回如下结构：
    {
      "items": [
        { "order": "S00020", "sn": "SN000000001", "num": 1, "chute": "16" },
        ...
      ]
    }
    Adjust field names below to match the actual API response.
    请根据实际 API 响应调整下方的字段名称。
    """

    # ── Step 1 / 第一步 ──────────────────────
    wave_data = wave_sorting(wave_no)

    # Extract items from the response.
    # 从响应中提取项目列表。
    # Adjust the key to match the real JSON structure.
    # 请根据实际 JSON 结构调整键名。
    items = (
        wave_data.get("items")
        or wave_data.get("data")
        or wave_data.get("orders")
        or []
    )

    if not items:
        # No items found – check the actual response structure
        # 未找到项目 – 请检查实际响应结构
        print("\n⚠️  No items found in wave-sorting response. / 在 wave-sorting 响应中未找到项目。")
        print("    Review the response structure and adjust the keys in run_full_flow().")
        print("    请检查响应结构并在 run_full_flow() 中调整键名。")
        return

    # ── Step 2 – one call per item / 第二步 – 每个项目调用一次 ──
    for item in items:
        order  = item.get("order")                # Order number / 订单号
        sn     = item.get("sn")                   # Serial number / 序列号
        num    = item.get("num")                  # Quantity / 数量
        chute  = item.get("chute")                # Chute / 滑槽
        status = item.get("status", "completed")  # Default: completed / 默认：已完成

        # Skip incomplete items / 跳过不完整的项目
        if not all([order, sn, chute]):
            print(f"\n⚠️  Incomplete item, skipping. / 项目不完整，已跳过: {item}")
            continue

        sorting_status_push(
            order=str(order),
            sn=str(sn),
            num=int(num),
            chute=str(chute),
            status=status,
        )

    # ── Step 3 / 第三步 ──────────────────────
    wave_end(wave_no)

    print("\n✅  Full flow completed successfully. / 完整流程已成功完成。")


# ─────────────────────────────────────────────
# ENTRY POINT / 程序入口
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Pass wave_No as a command-line argument, or change the default value below.
    # 可通过命令行参数传入 wave_No，或在下方修改默认值。
    # Usage / 用法: python sorter_flow.py WAVE/00014
    wave = sys.argv[1] if len(sys.argv) > 1 else "WAVE/00014"
    run_full_flow(wave)