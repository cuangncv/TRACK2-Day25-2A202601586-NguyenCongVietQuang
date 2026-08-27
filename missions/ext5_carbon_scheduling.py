"""Extension 5 — Carbon-Aware Scheduling for Interruptible Training Workloads.

Analysis:
1. Filters batch and training workloads from workloads.csv that are interruptible.
2. Models energy consumption based on GPU watts rating and total runtime hours.
3. Compares running in dirty baseline regions (e.g. us-east-1, europe-central2) vs
   greenest region (europe-north1 Norway Hydro or us-east-wa).
4. Quantifies carbon reduction (gCO2e & %) and electricity cost differences.
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num, catalog_by_type
from finops import sustainability


def run(verbose: bool = True) -> dict:
    jobs = load_csv("workloads.csv")
    cat = catalog_by_type()

    BASE_REGION = "us-east-1"
    GREEN_REGION = "europe-north1"
    DIRTY_REGION = "europe-central2"

    scheduled_jobs = []
    total_energy_kwh = 0.0
    total_base_carbon_kg = 0.0
    total_green_carbon_kg = 0.0
    total_base_elec_usd = 0.0
    total_green_elec_usd = 0.0

    for j in jobs:
        interruptible = bool(int(num(j["interruptible"])))
        if not interruptible:
            continue

        gtype = j["gpu_type"]
        ngpu = int(num(j["num_gpus"]))
        hpd = num(j["hours_per_day"])
        days = int(num(j["days"]))
        watts = num(cat[gtype]["watts"])

        total_gpu_hours = hpd * days * ngpu
        energy_wh = total_gpu_hours * watts
        energy_kwh = energy_wh / 1000.0

        # Carbon & Electricity calculations
        base_carbon_g = sustainability.carbon_g(energy_wh, region=BASE_REGION)
        green_carbon_g = sustainability.carbon_g(energy_wh, region=GREEN_REGION)
        dirty_carbon_g = sustainability.carbon_g(energy_wh, region=DIRTY_REGION)

        base_cost = sustainability.energy_cost_usd(energy_wh, region=BASE_REGION)
        green_cost = sustainability.energy_cost_usd(energy_wh, region=GREEN_REGION)

        total_energy_kwh += energy_kwh
        total_base_carbon_kg += (base_carbon_g / 1000.0)
        total_green_carbon_kg += (green_carbon_g / 1000.0)
        total_base_elec_usd += base_cost
        total_green_elec_usd += green_cost

        scheduled_jobs.append({
            "job_id": j["job_id"],
            "team": j["team"],
            "gpu_type": gtype,
            "ngpu": ngpu,
            "energy_kwh": round(energy_kwh, 1),
            "base_carbon_kg": round(base_carbon_g / 1000.0, 2),
            "green_carbon_kg": round(green_carbon_g / 1000.0, 2),
            "carbon_reduction_pct": round((1.0 - green_carbon_g / base_carbon_g) * 100, 1),
            "base_elec_usd": round(base_cost, 2),
            "green_elec_usd": round(green_cost, 2),
        })

    total_reduction_kg = total_base_carbon_kg - total_green_carbon_kg
    total_reduction_pct = (total_reduction_kg / total_base_carbon_kg) * 100 if total_base_carbon_kg else 0.0

    if verbose:
        print("== Extension 5: Carbon-Aware Workload Scheduling ==")
        print(f"Base Region: {BASE_REGION} ({sustainability.REGION_CARBON[BASE_REGION]} gCO2/kWh) -> Green: {GREEN_REGION} ({sustainability.REGION_CARBON[GREEN_REGION]} gCO2/kWh)")
        print(f"\n{'Job':18}{'Team':10}{'GPU':6}{'kWh':>10}{'US-East kgCO2':>15}{'Europe-North kgCO2':>20}{'CO2 Saved %':>13}")
        for sj in scheduled_jobs:
            print(f"{sj['job_id']:18}{sj['team']:10}{sj['gpu_type']:6}{sj['energy_kwh']:>10,}{sj['base_carbon_kg']:>15.2f}{sj['green_carbon_kg']:>20.2f}{sj['carbon_reduction_pct']:>12.1f}%")

        print("\n--- Carbon Optimization Totals (Interruptible Workloads) ---")
        print(f"  * Total Energy Consumption: {total_energy_kwh:,.1f} kWh")
        print(f"  * Carbon Footprint in {BASE_REGION}:  {total_base_carbon_kg:,.2f} kgCO2e")
        print(f"  * Carbon Footprint in {GREEN_REGION}: {total_green_carbon_kg:,.2f} kgCO2e")
        print(f"  * Net Carbon Avoided:        {total_reduction_kg:,.2f} kgCO2e ({total_reduction_pct:.1f}% reduction)")
        print(f"  * Electricity Cost Shift:    ${total_base_elec_usd:,.2f} -> ${total_green_elec_usd:,.2f}")

    return {
        "scheduled_jobs": scheduled_jobs,
        "total_energy_kwh": round(total_energy_kwh, 1),
        "total_base_carbon_kg": round(total_base_carbon_kg, 2),
        "total_green_carbon_kg": round(total_green_carbon_kg, 2),
        "total_reduction_kg": round(total_reduction_kg, 2),
        "total_reduction_pct": round(total_reduction_pct, 1),
    }


if __name__ == "__main__":
    run()
