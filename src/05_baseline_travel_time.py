"""Compute travel time from every road-network node to the nearest health facility
(baseline / undisrupted conditions) via a single multi-source Dijkstra run.

Multi-source Dijkstra with all facility-snapped nodes as sources is far cheaper than
running one shortest-path query per population point: O((V+E) log V) once, instead of
once per population cell.
"""
import pickle
import geopandas as gpd
import networkx as nx
from pathlib import Path

DATA_PROC = Path(__file__).resolve().parent.parent / "data" / "processed"
GRAPH = DATA_PROC / "kalsel_road_graph.pickle"
FACILITIES = DATA_PROC / "kalsel_facilities_snapped.geojson"
OUT = DATA_PROC / "baseline_travel_time.pickle"


def main():
    with open(GRAPH, "rb") as f:
        G = pickle.load(f)
    facilities = gpd.read_file(FACILITIES)

    sources = set(zip(facilities["snap_lon"], facilities["snap_lat"]))
    sources = {s for s in sources if s in G}
    print(f"[info] {len(sources)}/{facilities.shape[0]} unique facility source nodes present in graph")

    print("Running multi-source Dijkstra...")
    travel_time = nx.multi_source_dijkstra_path_length(G, sources, weight="time_min")
    print(f"[info] reachable nodes: {len(travel_time)}/{G.number_of_nodes()}")

    times = list(travel_time.values())
    times.sort()
    import statistics
    print(f"[info] travel time (min) — median={statistics.median(times):.1f}, "
          f"p90={times[int(0.9*len(times))]:.1f}, max={max(times):.1f}")

    with open(OUT, "wb") as f:
        pickle.dump(travel_time, f)
    print(f"[ok] baseline travel time -> {OUT}")


if __name__ == "__main__":
    main()
