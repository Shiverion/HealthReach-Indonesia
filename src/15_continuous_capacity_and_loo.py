"""P1 robustness check: does the inequality finding depend on the median-split
binarization, or on any single influential district?

n=13, so no formal regression -- Spearman correlation + scatter is the right
level of rigor here, not a fitted model that would mostly cosplay as
statistical power. Leave-one-district-out tests whether the class-level
finding is being driven by one district (notably Banjarmasin, already flagged
as behaving unusually in earlier analysis).
"""
import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

DATA_PROC = Path(__file__).resolve().parent.parent / "data" / "processed"

per_kab = pd.read_csv(DATA_PROC / "inequality_per_kabupaten.csv")
per_kab["access_change_pp"] = per_kab["s1_moderate_pct_within60"] - per_kab["baseline_pct_within60"]

print("=== Continuous relationship: workforce density vs. accessibility change ===\n")
rho, p = stats.spearmanr(per_kab["clinical_staff_per_10k"], per_kab["access_change_pp"])
print(f"Spearman rho = {rho:.3f}, p = {p:.3f} (n={len(per_kab)})")
print("(n=13 -- treat this as descriptive triangulation alongside the scatter, not a significance test to lean on)\n")

print(per_kab[["kabupaten", "clinical_staff_per_10k", "access_change_pp"]]
      .sort_values("clinical_staff_per_10k").to_string(index=False))

# scatter plot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(7, 6))
ax.scatter(per_kab["clinical_staff_per_10k"], per_kab["access_change_pp"], s=80, color="steelblue")
for _, row in per_kab.iterrows():
    ax.annotate(row["kabupaten"], (row["clinical_staff_per_10k"], row["access_change_pp"]),
                fontsize=8, xytext=(5, 5), textcoords="offset points")
ax.axhline(0, color="gray", linewidth=0.8)
ax.set_xlabel("Clinical staff per 10,000 population")
ax.set_ylabel("60-min accessibility change, baseline -> Sentinel-1 moderate (pp)")
ax.set_title(f"Workforce Density vs. Flood Accessibility Change (Spearman rho={rho:.2f}, n=13)")
plt.tight_layout()
out_png = DATA_PROC / "capacity_vs_access_change_scatter.png"
plt.savefig(out_png, dpi=150)
print(f"\n[ok] scatter -> {out_png}")

# --- Leave-one-district-out on the class-level (median-split) gap-widening finding ---
print("\n\n=== Leave-one-district-out: underserved-vs-well-served gap widening ===\n")

results = []
for excluded in per_kab["kabupaten"]:
    sub = per_kab[per_kab["kabupaten"] != excluded]
    rows = []
    for cls in ["underserved", "well-served"]:
        grp = sub[sub["capacity_class"] == cls]
        total_pop = grp["total_pop"].sum()
        baseline_w = (grp["baseline_pct_within60"] * grp["total_pop"]).sum() / total_pop
        moderate_w = (grp["s1_moderate_pct_within60"] * grp["total_pop"]).sum() / total_pop
        rows.append((cls, baseline_w, moderate_w))
    (u_cls, u_base, u_mod), (w_cls, w_base, w_mod) = rows
    baseline_gap = w_base - u_base
    moderate_gap = w_mod - u_mod
    widening = moderate_gap - baseline_gap
    results.append(dict(excluded=excluded, baseline_gap=baseline_gap, moderate_gap=moderate_gap, widening_pp=widening))

loo = pd.DataFrame(results)
print(loo.to_string(index=False))

n_positive = (loo["widening_pp"] > 0).sum()
print(f"\nGap widened (direction preserved) in {n_positive}/{len(loo)} leave-one-district-out runs")
print(f"Range of gap-widening estimate across LOO runs: {loo['widening_pp'].min():.2f}pp to {loo['widening_pp'].max():.2f}pp")

loo.to_csv(DATA_PROC / "leave_one_out_inequality.csv", index=False)
print(f"[ok] -> {DATA_PROC / 'leave_one_out_inequality.csv'}")
