"""P1 robustness check: Null A (uniform random edge removal), testing whether
the observed Sentinel-1 flood damage is unusual relative to removing the same
NUMBER of edges chosen uniformly at random from the whole network.

This is deliberately the simplest null model (see docs/robustness_checks.md
for why Null B/C -- road-class-matched, spatially-constrained -- would be
needed to isolate the topology mechanism more precisely; this project stops
at Null A and states that limitation explicitly rather than overclaiming).

Damage metric: size of the largest connected component after edge removal
(cheap -- no Dijkstra needed per trial, unlike the full accessibility
scenarios -- which is what makes a few hundred trials tractable here).

Reports a genuine empirical randomization p-value: p = (b+1)/(B+1), where b
is the number of random trials at least as damaging as the observed removal.
"""
import pickle
import random
import time
import numpy as np
import rasterio
import networkx as nx
import pandas as pd
from pathlib import Path

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
DATA_PROC = Path(__file__).resolve().parent.parent / "data" / "processed"
N_TRIALS = 200  # scoped from actual per-trial runtime (~4s/trial), not chosen for a round number
SEED = 42


def get_observed_flooded_edges(G):
    with rasterio.open(DATA_RAW / "flood" / "sentinel1_observed_flood_extent.tif") as src:
        band = src.read(1)
        transform = src.transform
        bounds = src.bounds
        edges = list(G.edges())
        mid_lons = np.array([(u[0] + v[0]) / 2 for u, v in edges])
        mid_lats = np.array([(u[1] + v[1]) / 2 for u, v in edges])
        in_bounds = (mid_lons >= bounds.left) & (mid_lons <= bounds.right) & \
                    (mid_lats >= bounds.bottom) & (mid_lats <= bounds.top)
        rows, cols = rasterio.transform.rowcol(transform, mid_lons, mid_lats)
        rows = np.clip(rows, 0, band.shape[0] - 1)
        cols = np.clip(cols, 0, band.shape[1] - 1)
        flooded = (band[rows, cols] == 1) & in_bounds
    return [e for e, f in zip(edges, flooded) if f]


def largest_component_pct(G, removed_edges, total_nodes):
    G2 = G.copy()
    G2.remove_edges_from(removed_edges)
    components = sorted(nx.connected_components(G2), key=len, reverse=True)
    return 100 * len(components[0]) / total_nodes


def main():
    with open(DATA_PROC / "kalsel_road_graph.pickle", "rb") as f:
        G = pickle.load(f)
    total_nodes = G.number_of_nodes()
    all_edges = list(G.edges())

    observed_flooded = get_observed_flooded_edges(G)
    n_flooded = len(observed_flooded)
    observed_largest_pct = largest_component_pct(G, observed_flooded, total_nodes)
    print(f"[info] observed: {n_flooded:,} flooded edges -> largest component {observed_largest_pct:.2f}% of graph")
    print(f"[info] running {N_TRIALS} random-edge-removal trials (same edge count, uniform sample)...\n")

    random.seed(SEED)
    trial_results = []
    t0 = time.time()
    for i in range(N_TRIALS):
        sample = random.sample(all_edges, n_flooded)
        pct = largest_component_pct(G, sample, total_nodes)
        trial_results.append(pct)
        if (i + 1) % 25 == 0:
            elapsed = time.time() - t0
            print(f"  trial {i+1}/{N_TRIALS} ({elapsed:.0f}s elapsed, ~{elapsed/(i+1)*N_TRIALS:.0f}s total est.)")

    trial_results = np.array(trial_results)
    # "at least as damaging" = random trial's largest component <= observed largest component
    b = int((trial_results <= observed_largest_pct).sum())
    p_value = (b + 1) / (N_TRIALS + 1)

    print(f"\n[info] random-trial largest-component %: mean={trial_results.mean():.2f}, "
          f"median={np.median(trial_results):.2f}, min={trial_results.min():.2f}, max={trial_results.max():.2f}")
    print(f"[info] observed ({observed_largest_pct:.2f}%) vs random null distribution:")
    print(f"       {b}/{N_TRIALS} random trials were AT LEAST AS damaging as the observed flood")
    print(f"       empirical randomization p = (b+1)/(B+1) = {p_value:.4f}")

    pd.DataFrame({"trial": range(N_TRIALS), "largest_component_pct": trial_results}).to_csv(
        DATA_PROC / "null_model_random_edges.csv", index=False)
    print(f"\n[ok] -> {DATA_PROC / 'null_model_random_edges.csv'}")

    with open(DATA_PROC / "null_model_summary.pickle", "wb") as f:
        pickle.dump(dict(n_flooded=n_flooded, observed_largest_pct=observed_largest_pct,
                          n_trials=N_TRIALS, b=b, p_value=p_value,
                          trial_mean=trial_results.mean(), trial_min=trial_results.min(),
                          trial_max=trial_results.max()), f)


if __name__ == "__main__":
    main()
