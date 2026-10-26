"""模拟一台真实终端，持续向平台上报测量数据。

没有硬件时用它验证"终端 → 平台 → 页面"整条链路是否通。

    python scripts/device_simulator.py --device WSD-01 --count 20 --interval 2
    python scripts/device_simulator.py --device WSD-01 --count 0 --interval 10
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone


def build_payload(device_id: str, base: float, index: int, rng: random.Random) -> dict:
    """按演示数据同样的规律造一条读数：慢漂移 + 快抖动 + 随机噪声"""
    slow = math.sin(index / 45.0) * 0.018
    fast = math.sin(index / 7.0) * 0.005
    drift = slow + fast
    noise = rng.uniform(-0.008, 0.008)

    resistance = base * (1.0 + drift + noise)
    impedance = resistance * 1.03
    phase = drift * 16.0 + rng.uniform(-0.3, 0.3)

    return {
        "device_id": device_id,
        "id": f"sim-{device_id}",
        "version": "1.0",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "params": {
            "resistance_ohm": {"value": round(resistance, 3)},
            "phase_deg": {"value": round(phase, 3)},
            "impedance_magnitude_ohm": {"value": round(impedance, 3)},
            "frequency_hz": {"value": 1000},
        },
    }


def post(url: str, payload: dict) -> tuple[int, str]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        return 0, f"连接失败: {exc.reason}"


def main() -> int:
    parser = argparse.ArgumentParser(description="模拟采集终端上报数据")
    parser.add_argument("--host", default="127.0.0.1", help="平台地址")
    parser.add_argument("--port", type=int, default=8002, help="平台端口")
    parser.add_argument("--device", default="WSD-01", help="设备编号")
    parser.add_argument("--base", type=float, default=1000.0, help="电阻基准值")
    parser.add_argument("--count", type=int, default=20, help="上报次数，0 表示一直报")
    parser.add_argument("--interval", type=float, default=2.0, help="间隔秒数")
    parser.add_argument("--seed", type=int, default=None, help="随机种子")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}/api/v1/measurements"
    rng = random.Random(args.seed)
    index = 0
    sent = 0

    print(f"向 {url} 模拟上报，设备 {args.device}，基准电阻 {args.base}Ω")
    print("按 Ctrl+C 停止\n")

    try:
        while args.count == 0 or sent < args.count:
            payload = build_payload(args.device, args.base, index, rng)
            status, body = post(url, payload)
            value = payload["params"]["resistance_ohm"]["value"]
            if status == 200:
                print(f"  [{sent + 1:4d}] HTTP {status}  电阻 {value:10.3f} Ω")
            else:
                print(f"  [{sent + 1:4d}] HTTP {status}  {body[:120]}")
            sent += 1
            index += 1
            if args.count == 0 or sent < args.count:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\n已停止，共上报 {sent} 条")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
