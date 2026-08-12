"""Flood-disrupted travel-time scenarios using the BNPB InaRISK hazard-zone proxy.

Interim methodology note (see PROTOCOL.md): this uses the BNPB *hazard* layer
(a general multi-year risk classification) as a proxy for disruption, not
Sentinel-1 *observed* flood extent for the actual Jan 2021 event -- see
src/11_flood_disruption_sentinel1.py for the validated real-event scenario.
This proxy-based scenario is kept for methodological comparison (see
docs/manuscript.md §5.1 -- the proxy-vs-observed comparison is itself a
result, not just a discarded first attempt).

Two brackets, defined identically in *operation* to the Sentinel-1 scenarios
in 11_flood_disruption_sentinel1.py so the two are genuinely comparable:
  - severe:   medium+high hazard edges REMOVED (treated as impassable)
  - moderate: medium+high hazard edges PENALIZED 2.5x travel time, nothing
              removed -- connectivity is unchanged from baseline by
              construction, only travel time increases

(Earlier version of this script's "moderate" bracket removed high-hazard
edges AND penalized medium -- a mixed operation that was inconsistently
described elsewhere as "penalized, not removed", which does not hold for a
scenario that still deletes edges. Fixed here so proxy-moderate and
Sentinel-1-moderate mean the same operation, making the proxy-vs-observed
comparison apples-to-apples.)
"""
import pickle
import statistics
import numpy as np
import rasterio
import geopandas as gpd
import networkx as nx
from pathlib import Path
from shapely.geometry import LineString

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
DATA_PROC = Path(__file__).resolve().parent.parent / "data" / "processed"

GRAPH = DATA_PROC / "kalsel_road_graph.pickle"
HAZARD_CLASS = DATA_RAW / "flood" / "bnpb_kalsel_flood_hazard_class.tif"
FACILITIES = DATA_PROC / "kalsel_facilities_snapped.geojson"

DISRUPT_CLASSES = {2, 3}  # medium + high hazard
MODERATE_PENALTY = 2.5


def sample_hazard_at_midpoints(G, hazard_path):
    with rasterio.open(hazard_path) as src:
        band = src.read(1)
        transform = src.transform
        edges = list(G.edges(data=True))
        mid_lons = np.array([(u[0] + v[0]) / 2 for u, v, _ in edges])
        mid_lats = np.array([(u[1] + v[1]) / 2 for u, v, _ in edges])
        rows, cols = rasterio.transform.rowcol(transform, mid_lons, mid_lats)
        rows = np.clip(rows, 0, band.shape[0] - 1)
        cols = np.clip(cols, 0, band.shape[1] - 1)
        classes = band[rows, cols]
    return edges, classes


def run_scenario(G, facilities, edges, disrupted_mask, mode, out_time, out_edges=None):
    """mode='severe' removes disrupted edges; mode='moderate' only penalizes them."""
    G_scenario = G.copy()
    affected_rows = []
    for (u, v, data), is_disrupted in zip(edges, disrupted_mask):
        if not is_disrupted:
            continue
        affected_rows.append({"highway": data.get("highway"), "geometry": LineString([u, v])})
        if mode == "severe":
            G_scenario.remove_edge(u, v)
        elif mode == "moderate":
            G_scenario[u][v]["time_min"] *= MODERATE_PENALTY
        else:
            raise ValueError(mode)

    if out_edges is not None:
        gpd.GeoDataFrame(affected_rows, crs="EPSG:4326").to_file(out_edges, driver="GeoJSON")
        print(f"  [ok] flood-affected edges -> {out_edges}")

    components = sorted(nx.connected_components(G_scenario), key=len, reverse=True)
    G_main = G_scenario.subgraph(components[0]).copy()
    print(f"  [info] largest component: {len(components[0])} nodes "
          f"({100*len(components[0])/G.number_of_nodes():.1f}% of original graph)")

    sources = set(zip(facilities["snap_lon"], facilities["snap_lat"]))
    sources = {s for s in sources if s in G_main}
    print(f"  [info] {len(sources)} facility source nodes reachable")

    travel_time = nx.multi_source_dijkstra_path_length(G_main, sources, weight="time_min")
    times = sorted(travel_time.values())
    print(f"  [info] travel time (min) — median={statistics.median(times):.1f}, "
          f"p90={times[int(0.9*len(times))]:.1f}, max={max(times):.1f}")
    print(f"  [info] nodes stranded from all facilities: {G.number_of_nodes() - len(travel_time)}")

    with open(out_time, "wb") as f:
        pickle.dump(travel_time, f)
    print(f"  [ok] travel time -> {out_time}")


def main():
    with open(GRAPH, "rb") as f:
        G = pickle.load(f)
    facilities = gpd.read_file(FACILITIES)

    edges, classes = sample_hazard_at_midpoints(G, HAZARD_CLASS)
    disrupted_mask = np.isin(classes, list(DISRUPT_CLASSES))
    print(f"[info] {disrupted_mask.sum()}/{len(edges)} edges ({100*disrupted_mask.sum()/len(edges):.1f}%) "
          f"fall in medium/high BNPB flood-hazard zones\n")

    print("=== SEVERE (remove) ===")
    run_scenario(G, facilities, edges, disrupted_mask, "severe",
                 DATA_PROC / "flood_disrupted_travel_time.pickle",
                 DATA_PROC / "flood_affected_edges.geojson")

    print("\n=== MODERATE (penalize 2.5x, no removal) ===")
    run_scenario(G, facilities, edges, disrupted_mask, "moderate",
                 DATA_PROC / "flood_disrupted_moderate_travel_time.pickle")


if __name__ == "__main__":
    main()
