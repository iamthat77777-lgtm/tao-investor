#!/usr/bin/env python3
"""
Regenerate tao_data.js for dashboard.html from log files.
Run after monitor/guardian have collected new data points.
"""

import json
import glob
from pathlib import Path

ROOT = Path(__file__).parent
LOGS = ROOT / "logs"
OUT = ROOT / "tao_data.js"


def main():
    prices = []
    seen = set()
    for f in sorted(glob.glob(str(LOGS / "guardian_202*.json"))):
        if "state" in f:
            continue
        try:
            with open(f) as fp:
                for e in json.load(fp):
                    if "price" in e and "timestamp" in e:
                        key = e["timestamp"][:13]
                        if key not in seen:
                            seen.add(key)
                            prices.append({"x": e["timestamp"][:16], "y": e["price"]})
        except Exception as exc:
            print(f"  skip {f}: {exc}")

    balances = []
    for f in sorted(glob.glob(str(LOGS / "monitor_202*.json"))):
        try:
            with open(f) as fp:
                for e in json.load(fp):
                    if "total_tao" in e and e["total_tao"] > 0:
                        balances.append({"x": e["timestamp"][:16], "y": round(e["total_tao"], 6)})
        except Exception as exc:
            print(f"  skip {f}: {exc}")

    daily = {}
    for p in prices:
        day = p["x"][:10]
        daily.setdefault(day, []).append(p["y"])
    daily_avg = [{"x": d, "y": round(sum(v) / len(v), 2)} for d, v in sorted(daily.items())]

    with open(OUT, "w") as f:
        f.write(f"const TAO_PRICES = {json.dumps(prices)};\n")
        f.write(f"const TAO_DAILY = {json.dumps(daily_avg)};\n")
        f.write(f"const TAO_BALANCES = {json.dumps(balances)};\n")

    print(f"✓ Wrote {OUT}")
    print(f"  {len(prices)} hourly price points, {len(daily_avg)} daily, {len(balances)} balance points")


if __name__ == "__main__":
    main()
