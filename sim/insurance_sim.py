#!/usr/bin/env python3
"""
Community-Owned Mutual vs Fee-for-Service Insurance: 30-Year Cost Simulation

Compares cumulative costs for one enrollee over 30 years:
  A) Status-quo fee-for-service with annual premium compounding
  B) Salaried community-owned mutual with low admin and no profit extraction

Also computes the lifetime-tier lump sum (one-time payment invested to cover
decades of mutual premiums).

All key assumptions are parameterized with sensible defaults.
Run with --help to see all options, or import and call run_simulation().
"""

import argparse
import sys


def run_simulation(
    years: int = 30,
    starting_premium_annual: float = 8_000.0,
    ffs_compound_rate: float = 0.15,
    ffs_admin_pct: float = 0.18,
    ffs_profit_pct: float = 0.05,
    ffs_waste_pct: float = 0.25,
    mutual_admin_pct: float = 0.02,
    mutual_profit_pct: float = 0.0,
    mutual_waste_pct: float = 0.02,
    mutual_medical_inflation: float = 0.04,
    lifetime_investment_return: float = 0.05,
    lifetime_horizon: int = 40,
) -> dict:
    """
    Run the simulation and return a results dict.

    Parameters
    ----------
    years : int
        Simulation horizon in years (default 30).
    starting_premium_annual : float
        Year-1 annual premium under fee-for-service (default $8,000).
    ffs_compound_rate : float
        Annual premium increase rate for fee-for-service (default 0.15 = 15%).
    ffs_admin_pct : float
        Admin overhead as fraction of premium, fee-for-service (default 0.18).
    ffs_profit_pct : float
        Profit margin as fraction of premium, fee-for-service (default 0.05).
    ffs_waste_pct : float
        Waste/fraud as fraction of claims paid, fee-for-service (default 0.25).
    mutual_admin_pct : float
        Admin overhead as fraction of premium, mutual (default 0.02).
    mutual_profit_pct : float
        Profit extraction, mutual (default 0.0, member-owned).
    mutual_waste_pct : float
        Residual waste in salaried model (default 0.02).
    mutual_medical_inflation : float
        Annual cost growth for the mutual (medical inflation only, default 0.04).
    lifetime_investment_return : float
        Annual return on the lifetime lump-sum corpus (default 0.05 = 5%).
    lifetime_horizon : int
        Years the lifetime lump sum must cover (default 40).

    Returns
    -------
    dict with keys: yearly_detail, summary
    """

    # Derive the mutual's year-1 premium.
    # The mutual eliminates the waste, excess admin, and profit baked into FFS.
    # FFS premium = actual_care / (1 - waste_pct) / (1 - admin_pct - profit_pct)
    # So actual_care = FFS_premium * (1 - admin_pct - profit_pct) * (1 - waste_pct)
    # Mutual premium = actual_care / (1 - mutual_admin_pct - mutual_waste_pct)
    ffs_care_fraction = (1 - ffs_admin_pct - ffs_profit_pct) * (1 - ffs_waste_pct)
    actual_care_cost = starting_premium_annual * ffs_care_fraction
    mutual_starting = actual_care_cost / (1 - mutual_admin_pct - mutual_waste_pct)

    yearly = []
    cum_ffs = 0.0
    cum_mutual = 0.0
    breakeven_year = None

    for y in range(1, years + 1):
        ffs_premium = starting_premium_annual * ((1 + ffs_compound_rate) ** (y - 1))
        mutual_premium = mutual_starting * ((1 + mutual_medical_inflation) ** (y - 1))

        cum_ffs += ffs_premium
        cum_mutual += mutual_premium

        savings = cum_ffs - cum_mutual
        yearly.append({
            "year": y,
            "ffs_premium": round(ffs_premium, 2),
            "mutual_premium": round(mutual_premium, 2),
            "ffs_cumulative": round(cum_ffs, 2),
            "mutual_cumulative": round(cum_mutual, 2),
            "cumulative_savings": round(savings, 2),
        })

        if breakeven_year is None and savings > 0:
            breakeven_year = y

    # Lifetime-tier corpus calculation.
    # The lump sum L, invested at r% annual return, must fund mutual premiums
    # for `lifetime_horizon` years. Each year i the mutual premium is
    # mutual_starting * (1 + mutual_medical_inflation)^(i-1).
    # Present value of all future premiums at the investment rate:
    pv_premiums = 0.0
    for i in range(1, lifetime_horizon + 1):
        future_premium = mutual_starting * ((1 + mutual_medical_inflation) ** (i - 1))
        pv_premiums += future_premium / ((1 + lifetime_investment_return) ** i)

    lifetime_corpus = round(pv_premiums, 2)

    # Compare to 30-year FFS cumulative
    ffs_30yr = cum_ffs
    mutual_30yr = cum_mutual

    summary = {
        "simulation_years": years,
        "starting_premium_annual": starting_premium_annual,
        "ffs_year1_premium": round(starting_premium_annual, 2),
        "mutual_year1_premium": round(mutual_starting, 2),
        "mutual_discount_vs_ffs_year1": f"{((1 - mutual_starting / starting_premium_annual) * 100):.1f}%",
        "ffs_cumulative_30yr": round(ffs_30yr, 2),
        "mutual_cumulative_30yr": round(mutual_30yr, 2),
        "total_savings_30yr": round(ffs_30yr - mutual_30yr, 2),
        "savings_pct": f"{((ffs_30yr - mutual_30yr) / ffs_30yr * 100):.1f}%",
        "breakeven_year": breakeven_year if breakeven_year else "N/A (mutual always cheaper)",
        "lifetime_corpus_needed": lifetime_corpus,
        "lifetime_horizon_years": lifetime_horizon,
        "lifetime_investment_return": f"{lifetime_investment_return * 100:.1f}%",
        "lifetime_vs_ffs_30yr": f"{((1 - lifetime_corpus / ffs_30yr) * 100):.1f}%",
    }

    return {"yearly_detail": yearly, "summary": summary}


def print_results(results: dict) -> None:
    s = results["summary"]
    yearly = results["yearly_detail"]

    print("=" * 78)
    print("  COMMUNITY-OWNED MUTUAL vs FEE-FOR-SERVICE: 30-YEAR COMPARISON")
    print("=" * 78)
    print()

    # Year-by-year table (show every 5 years + year 1 and final year)
    show_years = {1, 5, 10, 15, 20, 25, 30}
    show_years = show_years.intersection(range(1, s["simulation_years"] + 1))
    show_years.add(s["simulation_years"])
    show_years.add(1)

    header = f"{'Year':>4}  {'FFS Premium':>12}  {'Mutual Premium':>14}  {'FFS Cumul.':>12}  {'Mutual Cumul.':>13}  {'Savings':>12}"
    print(header)
    print("-" * len(header))

    for row in yearly:
        if row["year"] in show_years:
            print(
                f"{row['year']:>4}  "
                f"${row['ffs_premium']:>11,.2f}  "
                f"${row['mutual_premium']:>13,.2f}  "
                f"${row['ffs_cumulative']:>11,.2f}  "
                f"${row['mutual_cumulative']:>12,.2f}  "
                f"${row['cumulative_savings']:>11,.2f}"
            )

    print()
    print("-" * 78)
    print("SUMMARY")
    print("-" * 78)
    print(f"  FFS year-1 premium:          ${s['ffs_year1_premium']:>12,.2f}")
    print(f"  Mutual year-1 premium:       ${s['mutual_year1_premium']:>12,.2f}  ({s['mutual_discount_vs_ffs_year1']} cheaper)")
    print(f"  FFS cumulative ({s['simulation_years']}yr):      ${s['ffs_cumulative_30yr']:>12,.2f}")
    print(f"  Mutual cumulative ({s['simulation_years']}yr):   ${s['mutual_cumulative_30yr']:>12,.2f}")
    print(f"  Total savings ({s['simulation_years']}yr):       ${s['total_savings_30yr']:>12,.2f}  ({s['savings_pct']})")
    print(f"  Break-even year:              {s['breakeven_year']}")
    print()
    print("-" * 78)
    print("LIFETIME TIER (one-time lump sum)")
    print("-" * 78)
    print(f"  Lump sum needed:             ${s['lifetime_corpus_needed']:>12,.2f}")
    print(f"  Covers:                       {s['lifetime_horizon_years']} years of mutual premiums")
    print(f"  Assumed investment return:     {s['lifetime_investment_return']} annually")
    print(f"  vs FFS {s['simulation_years']}yr cumulative:     {s['lifetime_vs_ffs_30yr']} less")
    print()


def main():
    p = argparse.ArgumentParser(
        description="Compare fee-for-service vs community-owned mutual insurance costs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--years", type=int, default=30, help="Simulation horizon")
    p.add_argument("--starting-premium", type=float, default=8000, help="Year-1 annual FFS premium ($)")
    p.add_argument("--ffs-compound", type=float, default=0.15, help="FFS annual premium increase rate")
    p.add_argument("--ffs-admin", type=float, default=0.18, help="FFS admin overhead fraction")
    p.add_argument("--ffs-profit", type=float, default=0.05, help="FFS profit margin fraction")
    p.add_argument("--ffs-waste", type=float, default=0.25, help="FFS waste/fraud fraction of claims")
    p.add_argument("--mutual-admin", type=float, default=0.02, help="Mutual admin overhead fraction")
    p.add_argument("--mutual-waste", type=float, default=0.02, help="Mutual residual waste fraction")
    p.add_argument("--mutual-inflation", type=float, default=0.04, help="Mutual annual medical cost inflation")
    p.add_argument("--investment-return", type=float, default=0.05, help="Annual return on lifetime corpus")
    p.add_argument("--lifetime-horizon", type=int, default=40, help="Years the lifetime lump sum must cover")
    p.add_argument("--json", action="store_true", help="Output raw JSON instead of formatted table")

    args = p.parse_args()

    results = run_simulation(
        years=args.years,
        starting_premium_annual=args.starting_premium,
        ffs_compound_rate=args.ffs_compound,
        ffs_admin_pct=args.ffs_admin,
        ffs_profit_pct=args.ffs_profit,
        ffs_waste_pct=args.ffs_waste,
        mutual_admin_pct=args.mutual_admin,
        mutual_waste_pct=args.mutual_waste,
        mutual_medical_inflation=args.mutual_inflation,
        lifetime_investment_return=args.investment_return,
        lifetime_horizon=args.lifetime_horizon,
    )

    if args.json:
        import json
        print(json.dumps(results, indent=2))
    else:
        print_results(results)


if __name__ == "__main__":
    main()
