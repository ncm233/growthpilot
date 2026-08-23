"""Generates a synthetic dataset shaped like Kaggle's "Digital Marketing
Performance Dataset" (platform/date/spend/impressions/clicks/conversions/revenue).
Used as demo/eval fixture data — no real Kaggle download dependency, no real
company data. Run: python generate_synthetic_data.py
"""
import csv
import os
import random
from datetime import date, timedelta

OUT_DIR = os.path.join(os.path.dirname(__file__), "datasets")
PLATFORMS = ["Meta", "Google Search", "TikTok", "LinkedIn"]
DAYS = 90


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = random.Random(42)
    start = date.today() - timedelta(days=DAYS)

    rows = []
    for platform in PLATFORMS:
        base_spend = {"Meta": 1800, "Google Search": 2400, "TikTok": 1200, "LinkedIn": 900}[platform]
        base_ctr = {"Meta": 0.018, "Google Search": 0.032, "TikTok": 0.014, "LinkedIn": 0.009}[platform]
        base_cvr = {"Meta": 0.041, "Google Search": 0.058, "TikTok": 0.025, "LinkedIn": 0.071}[platform]
        for d in range(DAYS):
            day = start + timedelta(days=d)
            spend = round(base_spend * rng.uniform(0.8, 1.2), 2)
            impressions = int(spend / rng.uniform(0.008, 0.015))
            clicks = int(impressions * base_ctr * rng.uniform(0.85, 1.15))
            conversions = int(clicks * base_cvr * rng.uniform(0.8, 1.2))
            revenue = round(conversions * rng.uniform(180, 320), 2)
            rows.append({
                "date": day.isoformat(),
                "platform": platform,
                "spend": spend,
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "revenue": revenue,
                "ctr": round(clicks / impressions, 4) if impressions else 0,
                "cvr": round(conversions / clicks, 4) if clicks else 0,
                "cpa": round(spend / conversions, 2) if conversions else None,
                "roas": round(revenue / spend, 2) if spend else None,
            })

    out_path = os.path.join(OUT_DIR, "digital_marketing_performance.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows -> {out_path}")


if __name__ == "__main__":
    main()
