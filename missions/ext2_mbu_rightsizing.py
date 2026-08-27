"""Extension 2 — Right-sizing Inference Workloads by MBU & $/GB-VRAM.

Analysis:
1. Calculates $/GB-VRAM and $/TB-s memory bandwidth across the GPU catalog.
2. Identifies memory-bound workloads (low arithmetic intensity / low MFU, moderate MBU).
3. Recommends right-sized GPUs (e.g. A10G, L4, or MI300X/A100) instead of expensive H100s.
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num, catalog_by_type
from finops import metrics


def run(verbose: bool = True) -> dict:
    cat = catalog_by_type()
    tel = load_csv("gpu_telemetry.csv")

    # 1. Catalog Unit Economics per Memory / Compute metric
    catalog_metrics = []
    for gtype, c in cat.items():
        od = num(c["on_demand_hr"])
        hbm = num(c["hbm_gb"])
        bw = num(c["peak_bw_tbs"])
        fp16 = num(c["peak_tflops_fp16"])
        catalog_metrics.append({
            "gpu_type": gtype,
            "on_demand_hr": od,
            "hbm_gb": hbm,
            "peak_bw_tbs": bw,
            "cost_per_gb_vram": round(od / hbm, 4),
            "cost_per_tbs_bw": round(od / bw, 3),
            "cost_per_tflop_fp16": round(od / fp16, 5),
        })

    catalog_metrics.sort(key=lambda x: x["cost_per_tbs_bw"])

    # 2. Workload right-sizing suggestions for flagged GPUs
    from collections import defaultdict
    agg = defaultdict(lambda: {"util": [], "mfu": [], "mbu": [], "type": None, "bw_achieved": []})
    for r in tel:
        gtype = r["gpu_type"]
        peak_fp16 = num(cat[gtype]["peak_tflops_fp16"])
        peak_bw = num(cat[gtype]["peak_bw_tbs"])
        mfu = metrics.compute_mfu(num(r["achieved_tflops"]), peak_fp16)
        mbu = metrics.compute_mbu(num(r["achieved_bw_tbs"]), peak_bw)
        a = agg[r["gpu_id"]]
        a["type"] = gtype
        a["util"].append(num(r["gpu_util_pct"]))
        a["mfu"].append(mfu)
        a["mbu"].append(mbu)
        a["bw_achieved"].append(num(r["achieved_bw_tbs"]))

    recommendations = []
    for gid, a in agg.items():
        avg_mfu = sum(a["mfu"]) / len(a["mfu"])
        avg_mbu = sum(a["mbu"]) / len(a["mbu"])
        avg_bw = sum(a["bw_achieved"]) / len(a["bw_achieved"])
        gtype = a["type"]
        curr_od = num(cat[gtype]["on_demand_hr"])

        # Check if memory-bound (MFU is low, workload bounded by bandwidth)
        if avg_mfu < 0.25 and gtype in ("H100", "H200"):
            # Find cheaper alternative that can satisfy avg_bw requirement
            for alt in catalog_metrics:
                alt_type = alt["gpu_type"]
                if alt["on_demand_hr"] < curr_od and alt["peak_bw_tbs"] >= avg_bw * 1.2:
                    rec_savings_pct = (1.0 - alt["on_demand_hr"] / curr_od) * 100
                    recommendations.append({
                        "gpu_id": gid,
                        "current_gpu": gtype,
                        "current_od": curr_od,
                        "avg_mfu": round(avg_mfu, 3),
                        "avg_mbu": round(avg_mbu, 3),
                        "achieved_bw_tbs": round(avg_bw, 2),
                        "recommended_gpu": alt_type,
                        "rec_od": alt["on_demand_hr"],
                        "monthly_savings_usd": round((curr_od - alt["on_demand_hr"]) * 24 * 30),
                        "savings_pct": round(rec_savings_pct, 1),
                    })
                    break

    if verbose:
        print("== Extension 2: MBU & Memory-Bound Right-Sizing ==")
        print("\n--- GPU Catalog Bandwidth & VRAM Unit Economics ---")
        print(f"{'GPU':8}{'$/hr':>6}{'VRAM(GB)':>10}{'BW(TB/s)':>10}{'$/GB-VRAM':>12}{'$/(TB/s BW)':>14}")
        for cm in catalog_metrics:
            print(f"{cm['gpu_type']:8}${cm['on_demand_hr']:>5.2f}{cm['hbm_gb']:>10.0f}{cm['peak_bw_tbs']:>10.1f}${cm['cost_per_gb_vram']:>11.4f}${cm['cost_per_tbs_bw']:>13.3f}")

        print("\n--- Right-Sizing Recommendations for Memory-Bound Workloads ---")
        for r in recommendations:
            print(f"[{r['gpu_id']}] Current: {r['current_gpu']} (${r['current_od']}/hr, MFU={r['avg_mfu']:.2f}) "
                  f"-> Recommended: {r['recommended_gpu']} (${r['rec_od']}/hr) "
                  f"| Savings: ${r['monthly_savings_usd']:,}/mo ({r['savings_pct']}%)")

    return {
        "catalog_metrics": catalog_metrics,
        "recommendations": recommendations,
    }


if __name__ == "__main__":
    run()
