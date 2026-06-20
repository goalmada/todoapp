#!/usr/bin/env python3
"""
Lifetime health-insurance premium calculator (Mexican gastos medicos mayores).

Reconstructs historical premiums by discounting today's known premium backward,
then sums every year from start_age to current_age.

    premium(age k) = current_premium / (1 + annual_rate)^(current_age - k)

Default values reflect Diego's mother-in-law's policy.
"""

import argparse
import json
import sys


def calc_lifetime(current_premium: float, current_age: int, start_age: int,
                  annual_rate: float) -> dict:
    years = current_age - start_age
    if years <= 0:
        raise ValueError("current_age must be greater than start_age")

    breakdown = []
    total = 0.0
    for age in range(start_age, current_age + 1):
        years_back = current_age - age
        estimated_premium = current_premium / ((1 + annual_rate) ** years_back)
        total += estimated_premium
        breakdown.append({
            "age": age,
            "years_back": years_back,
            "estimated_premium": round(estimated_premium, 2),
            "cumulative": round(total, 2),
        })

    avg = total / (current_age - start_age + 1)

    return {
        "params": {
            "current_premium": current_premium,
            "current_age": current_age,
            "start_age": start_age,
            "annual_rate": annual_rate,
        },
        "lifetime_total": round(total, 2),
        "average_annual": round(avg, 2),
        "ratio_peak_to_avg": round(current_premium / avg, 2),
        "years_covered": current_age - start_age + 1,
        "breakdown": breakdown,
    }


def run_range(current_premium: float, current_age: int, start_age: int,
              rates: list[float]) -> list[dict]:
    results = []
    for r in rates:
        res = calc_lifetime(current_premium, current_age, start_age, r)
        results.append({
            "rate_pct": round(r * 100, 1),
            "lifetime_total": res["lifetime_total"],
            "average_annual": res["average_annual"],
            "ratio_peak_to_avg": res["ratio_peak_to_avg"],
        })
    return results


def fmt_mxn(val: float) -> str:
    return f"${val:,.0f}"


def main():
    parser = argparse.ArgumentParser(
        description="Lifetime health-insurance premium calculator")
    parser.add_argument("--premium", type=float, default=290_000,
                        help="Current annual premium in MXN (default: 290000)")
    parser.add_argument("--current-age", type=int, default=62,
                        help="Current age (default: 62)")
    parser.add_argument("--start-age", type=int, default=35,
                        help="Age when policy started (default: 35)")
    parser.add_argument("--rate", type=float, default=0.12,
                        help="Annual premium growth rate (default: 0.12)")
    parser.add_argument("--range", action="store_true",
                        help="Run sensitivity analysis at 8-15%% rates")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of formatted text")
    args = parser.parse_args()

    if args.range:
        rates = [r / 100 for r in range(8, 16)]
        results = run_range(args.premium, args.current_age, args.start_age, rates)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\nSensitivity analysis: {fmt_mxn(args.premium)}/yr premium, "
                  f"age {args.start_age}-{args.current_age}\n")
            print(f"{'Rate':>6}  {'Lifetime Total':>16}  {'Avg Annual':>12}  {'Peak/Avg':>8}")
            print("-" * 48)
            for r in results:
                print(f"{r['rate_pct']:>5.0f}%  {fmt_mxn(r['lifetime_total']):>16}  "
                      f"{fmt_mxn(r['average_annual']):>12}  {r['ratio_peak_to_avg']:>7.1f}x")
    else:
        res = calc_lifetime(args.premium, args.current_age, args.start_age, args.rate)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            p = res["params"]
            print(f"\nLifetime Premium Calculator")
            print(f"{'='*40}")
            print(f"Current premium:  {fmt_mxn(p['current_premium'])}/yr")
            print(f"Annual increase:  {p['annual_rate']*100:.0f}%")
            print(f"Policy period:    age {p['start_age']} to {p['current_age']} "
                  f"({res['years_covered']} years)")
            print(f"{'='*40}")
            print(f"LIFETIME TOTAL:   {fmt_mxn(res['lifetime_total'])}")
            print(f"Average annual:   {fmt_mxn(res['average_annual'])}")
            print(f"Peak / avg ratio: {res['ratio_peak_to_avg']:.1f}x")
            print(f"\nPer-year breakdown:")
            print(f"{'Age':>5}  {'Estimated Premium':>18}  {'Cumulative':>14}")
            print("-" * 42)
            for row in res["breakdown"]:
                print(f"{row['age']:>5}  {fmt_mxn(row['estimated_premium']):>18}  "
                      f"{fmt_mxn(row['cumulative']):>14}")


if __name__ == "__main__":
    main()
