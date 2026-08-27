import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from finops import pricing, metrics, sustainability
from missions import (
    ext1_tier_policy,
    ext2_mbu_rightsizing,
    ext3_cache_economics,
    ext4_reasoning_budget,
    ext5_carbon_scheduling,
)


def test_cache_is_worth_it():
    # Break-even = 3.75 / (3.00 * 0.90) = 3.75 / 2.70 = 1.3888 reads
    res_under = pricing.cache_is_worth_it(avg_cache_reads=1.0, write_cost_per_m=3.75, base_read_price_per_m=3.00)
    assert res_under["is_worth_it"] is False
    assert res_under["break_even_reads"] == 1.39

    res_over = pricing.cache_is_worth_it(avg_cache_reads=2.0, write_cost_per_m=3.75, base_read_price_per_m=3.00)
    assert res_over["is_worth_it"] is True
    assert res_over["net_savings_per_m"] > 0


def test_ext1_runs():
    res = ext1_tier_policy.run(verbose=False)
    assert res["adv_savings_pct"] > 0
    assert res["total_advanced"] < res["total_od"]


def test_ext2_runs():
    res = ext2_mbu_rightsizing.run(verbose=False)
    assert len(res["catalog_metrics"]) > 0
    assert len(res["recommendations"]) > 0


def test_ext3_runs():
    res = ext3_cache_economics.run(verbose=False)
    assert res["cache_hit_rate"] > 0
    assert len(res["scenario_results"]) == 3


def test_ext4_runs():
    res = ext4_reasoning_budget.run(verbose=False)
    assert res["reasoning_stats"]["count"] > 0
    assert res["standard_stats"]["count"] > 0
    assert res["reasoning_energy_share"] > res["reasoning_token_share"]


def test_ext5_runs():
    res = ext5_carbon_scheduling.run(verbose=False)
    assert res["total_reduction_pct"] > 90.0
    assert res["total_reduction_kg"] > 0
