"""Extension 3 — Prompt Caching Economics & Break-Even Analysis.

Analysis:
1. Simulates cache write costs vs read discounts across varying read frequencies.
2. Identifies empirical cache read frequency in token_usage.csv.
3. Quantifies net ROI (financial return on caching) per team and across the organization.
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num
from finops import pricing


def run(verbose: bool = True) -> dict:
    tokens = load_csv("token_usage.csv")

    # 1. Empirical cache stats from token_usage.csv
    total_input = sum(num(r["input_tokens"]) for r in tokens)
    total_cached = sum(num(r["cached_input_tokens"]) for r in tokens)
    cache_hit_rate = total_cached / total_input if total_input else 0.0

    # 2. Break-even analysis under various provider pricing models:
    # Model A: Gemini/OpenAI style (Write cost ~ 1.25x base read, Cached read ~ 0.1x / 90% off)
    scenarios = [
        {"provider": "Provider A (Standard)", "write_cost": 3.75, "base_price": 3.00, "read_discount": 0.10},
        {"provider": "Provider B (Aggressive)", "write_cost": 5.00, "base_price": 3.00, "read_discount": 0.20},
        {"provider": "Provider C (Low-write)",  "write_cost": 2.00, "base_price": 3.00, "read_discount": 0.10},
    ]

    scenario_results = []
    for sc in scenarios:
        eval_res = pricing.cache_is_worth_it(
            avg_cache_reads=4.0, # assume average 4 reads per cached system prompt
            write_cost_per_m=sc["write_cost"],
            base_read_price_per_m=sc["base_price"],
            read_discount=sc["read_discount"],
        )
        scenario_results.append({
            **sc,
            "break_even_reads": eval_res["break_even_reads"],
            "net_savings_4_reads": eval_res["net_savings_per_m"],
            "savings_ratio": eval_res["savings_ratio"],
        })

    # 3. Team-by-team cache ROI
    from collections import defaultdict
    team_cache = defaultdict(lambda: {"input": 0, "cached": 0, "requests": 0})
    for r in tokens:
        t = r.get("team", "unallocated")
        team_cache[t]["input"] += int(num(r["input_tokens"]))
        team_cache[t]["cached"] += int(num(r["cached_input_tokens"]))
        team_cache[t]["requests"] += 1

    team_summary = []
    for t, val in team_cache.items():
        hit_pct = val["cached"] / val["input"] * 100 if val["input"] else 0.0
        # Assuming write cost $3.75/1M, standard read $3.00/1M, discount 90%
        gross_savings = (val["cached"] / 1e6) * (3.00 * 0.90)
        # Assuming 1 write per 5 cached requests
        write_cost = (val["cached"] / 1e6 / 5.0) * 3.75
        net_savings = gross_savings - write_cost
        team_summary.append({
            "team": t,
            "requests": val["requests"],
            "input_tokens": val["input"],
            "cached_tokens": val["cached"],
            "cache_hit_pct": round(hit_pct, 1),
            "gross_savings_usd": round(gross_savings, 2),
            "write_cost_usd": round(write_cost, 2),
            "net_savings_usd": round(net_savings, 2),
        })

    if verbose:
        print("== Extension 3: Prompt Caching Economics & Break-Even Analysis ==")
        print(f"Overall Cache Hit Rate: {cache_hit_rate:.1%} ({total_cached:,} / {total_input:,} tokens)")
        print("\n--- Provider Pricing Model Break-Even Sensitivity ---")
        print(f"{'Provider':24}{'Write $/1M':>12}{'Base $/1M':>12}{'Break-Even Reads':>18}{'ROI (4 reads)':>15}")
        for s in scenario_results:
            print(f"{s['provider']:24}${s['write_cost']:>11.2f}${s['base_price']:>11.2f}{s['break_even_reads']:>18.2f}{s['savings_ratio']:>14.2f}x")

        print("\n--- Team-Level Caching Financial Performance ---")
        print(f"{'Team':16}{'Hit %':>8}{'Gross Saved':>14}{'Write Cost':>13}{'Net Profit':>13}")
        for ts in sorted(team_summary, key=lambda x: x["net_savings_usd"], reverse=True):
            print(f"{ts['team']:16}{ts['cache_hit_pct']:>7.1f}%${ts['gross_savings_usd']:>13.2f}${ts['write_cost_usd']:>12.2f}${ts['net_savings_usd']:>12.2f}")

    return {
        "cache_hit_rate": round(cache_hit_rate, 3),
        "scenario_results": scenario_results,
        "team_summary": team_summary,
    }


if __name__ == "__main__":
    run()
