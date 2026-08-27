"""Run all 5 'Your Turn' Extensions and print comprehensive analysis results."""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from missions import (
    ext1_tier_policy,
    ext2_mbu_rightsizing,
    ext3_cache_economics,
    ext4_reasoning_budget,
    ext5_carbon_scheduling,
)


def main():
    print("=" * 70)
    print("      LAB 25 - ADVANCED 'YOUR TURN' EXTENSIONS SUITE")
    print("=" * 70 + "\n")

    print(">>> RUNNING EXTENSION 1: Advanced Tier Policy...")
    r1 = ext1_tier_policy.run(verbose=True)
    print("\n" + "-" * 70 + "\n")

    print(">>> RUNNING EXTENSION 2: MBU & Memory Right-Sizing...")
    r2 = ext2_mbu_rightsizing.run(verbose=True)
    print("\n" + "-" * 70 + "\n")

    print(">>> RUNNING EXTENSION 3: Prompt Caching Economics...")
    r3 = ext3_cache_economics.run(verbose=True)
    print("\n" + "-" * 70 + "\n")

    print(">>> RUNNING EXTENSION 4: Reasoning Budget & Energy Governance...")
    r4 = ext4_reasoning_budget.run(verbose=True)
    print("\n" + "-" * 70 + "\n")

    print(">>> RUNNING EXTENSION 5: Carbon-Aware Scheduling...")
    r5 = ext5_carbon_scheduling.run(verbose=True)
    print("\n" + "=" * 70)
    print("      ALL 5 EXTENSIONS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
