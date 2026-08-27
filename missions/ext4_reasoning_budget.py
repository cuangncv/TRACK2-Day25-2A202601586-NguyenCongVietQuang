"""Extension 4 — Reasoning Budget & Energy/Cost Governance.

Analysis:
1. Segregates standard inference vs reasoning inference (is_reasoning=1).
2. Computes financial cost ($) and energy footprint (Wh) comparing the two modes.
3. Proposes an SLA / Confidence-based routing rule to govern reasoning spend.
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num
from finops import pricing, sustainability


def run(verbose: bool = True) -> dict:
    tokens = load_csv("token_usage.csv")

    PRICES = {
        "small": {"in": 0.20, "out": 0.40},
        "large": {"in": 3.00, "out": 15.00},
    }

    reasoning_stats = {"count": 0, "tokens": 0, "cost_baseline": 0.0, "cost_opt": 0.0, "energy_wh": 0.0}
    standard_stats = {"count": 0, "tokens": 0, "cost_baseline": 0.0, "cost_opt": 0.0, "energy_wh": 0.0}

    for r in tokens:
        in_tok = int(num(r["input_tokens"]))
        out_tok = int(num(r["output_tokens"]))
        cached_tok = int(num(r["cached_input_tokens"]))
        is_batch = bool(int(num(r["is_batch"])))
        is_rs = bool(int(num(r.get("is_reasoning", 0))))
        route = r.get("route_tier", "large")
        tot = in_tok + out_tok

        # Baseline (all on large, no cache, no batch)
        cost_base = pricing.request_cost(in_tok, out_tok, PRICES["large"]["in"], PRICES["large"]["out"])

        # Optimized
        p = PRICES[route]
        cost_opt = pricing.request_cost(
            in_tok, out_tok, p["in"], p["out"],
            cached_in=cached_tok, batch=is_batch,
        )

        # Energy consumption (Wh)
        wh = sustainability.wh_per_query(tot, is_reasoning=is_rs)

        bucket = reasoning_stats if is_rs else standard_stats
        bucket["count"] += 1
        bucket["tokens"] += tot
        bucket["cost_baseline"] += cost_base
        bucket["cost_opt"] += cost_opt
        bucket["energy_wh"] += wh

    total_requests = len(tokens)
    total_tokens = standard_stats["tokens"] + reasoning_stats["tokens"]
    total_energy_wh = standard_stats["energy_wh"] + reasoning_stats["energy_wh"]

    reasoning_token_share = reasoning_stats["tokens"] / total_tokens if total_tokens else 0.0
    reasoning_energy_share = reasoning_stats["energy_wh"] / total_energy_wh if total_energy_wh else 0.0

    # Policy Recommendation: Gated Reasoning Routing
    # If 50% of reasoning queries can be routed to standard via classifier confidence score:
    routed_saving_energy_wh = (reasoning_stats["energy_wh"] * 0.50) * (1.0 - 1.0 / sustainability.REASONING_ENERGY_MULTIPLIER)
    carbon_saved_g = sustainability.carbon_g(routed_saving_energy_wh, region="us-east-1")

    if verbose:
        print("== Extension 4: Reasoning Traffic Budget & Energy Governance ==")
        print(f"Total Requests: {total_requests:,} | Reasoning: {reasoning_stats['count']} ({reasoning_stats['count']/total_requests:.1%}) | Standard: {standard_stats['count']}")
        print("\n--- Comparative Metrics: Standard vs Reasoning ---")
        print(f"{'Category':18}{'Tokens':>12}{'Tokens %':>10}{'Cost (Opt)':>13}{'Energy (Wh)':>14}{'Energy %':>10}")
        print(f"{'Standard (rs=0)':18}{standard_stats['tokens']:>12,}{1-reasoning_token_share:>9.1%}${standard_stats['cost_opt']:>12.2f}{standard_stats['energy_wh']:>14.1f}{1-reasoning_energy_share:>9.1%}")
        print(f"{'Reasoning (rs=1)':18}{reasoning_stats['tokens']:>12,}{reasoning_token_share:>9.1%}${reasoning_stats['cost_opt']:>12.2f}{reasoning_stats['energy_wh']:>14.1f}{reasoning_energy_share:>9.1%}")

        print("\n--- Governance Insight & Proposed Policy ---")
        print(f"  * Energy Disparity: Reasoning accounts for {reasoning_token_share:.1%} of tokens but consumes {reasoning_energy_share:.1%} of total inference energy.")
        print(f"  * Proposed Gated Routing: Enforce reasoning only when difficulty/confidence score >= 0.85.")
        print(f"  * Estimated Impact: Diverting 50% of reasoning saves {routed_saving_energy_wh:,.1f} Wh/day ({carbon_saved_g:,.1f} gCO2e/day in us-east-1).")

    return {
        "reasoning_stats": reasoning_stats,
        "standard_stats": standard_stats,
        "reasoning_token_share": round(reasoning_token_share, 3),
        "reasoning_energy_share": round(reasoning_energy_share, 3),
        "routed_saving_energy_wh": round(routed_saving_energy_wh, 2),
        "carbon_saved_g": round(carbon_saved_g, 2),
    }


if __name__ == "__main__":
    run()
