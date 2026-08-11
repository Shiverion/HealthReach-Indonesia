"""Build a routable NetworkX graph from the Kalsel road GeoJSON and snap health
facilities to their nearest graph node. Kept as a separate, cheap step so the
(memory-heavier) accessibility computation can be iterated on without re-parsing
roads every time.
"""
import json
import geopandas as gpd
import networkx as nx
import numpy as np
from pathlib import Path
from shapely.geometry import Point

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
DATA_PROC = Path(__file__).resolve().parent.parent / "data" / "processed"

ROADS = DATA_RAW / "population_roads" / "kalsel_roads.geojson"
FACILITIES = DATA_RAW / "facilities" / "kalsel_facilities.geojson"

# rough free-flow speed assumptions by road class (km/h) — standard AccessMod-style
# defaults for Indonesia-like road conditions; refine later if better local data surfaces
SPEED_KMH = {
    "motorway": 80, "motorway_link": 50,
    "trunk": 60, "trunk_link": 40,
    "primary": 50, "primary_link": 35,
    "secondary": 40, "secondary_link": 30,
    "tertiary": 30, "tertiary_link": 25,
    "unclassified": 20,
    "residential": 20,
}


def haversine_m(lon1, lat1, lon2, lat2):
    R = 6_371_000
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlambda / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def build_graph(roads: gpd.GeoDataFrame) -> nx.Graph:
    G = nx.Graph()
    for _, row in roads.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        coords = list(geom.coords)
        speed = SPEED_KMH.get(row["highway"], 20)
        for (lon1, lat1), (lon2, lat2) in zip(coords[:-1], coords[1:]):
            u, v = (lon1, lat1), (lon2, lat2)
            dist_m = haversine_m(lon1, lat1, lon2, lat2)
            if dist_m <= 0:
                continue
            time_min = (dist_m / 1000) / speed * 60
            if G.has_edge(u, v):
                if G[u][v]["time_min"] <= time_min:
                    continue
            G.add_edge(u, v, length_m=dist_m, time_min=time_min, highway=row["highway"])
    return G


def snap_to_nearest_node(G: nx.Graph, point: Point):
    nodes = np.array(G.nodes())
    d2 = (nodes[:, 0] - point.x) ** 2 + (nodes[:, 1] - point.y) ** 2
    idx = np.argmin(d2)
    return tuple(nodes[idx])


def main():
    roads = gpd.read_file(ROADS)
    print(f"[info] loaded {len(roads)} road segments")

    G = build_graph(roads)
    print(f"[info] graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    components = list(nx.connected_components(G))
    components.sort(key=len, reverse=True)
    largest = components[0]
    print(f"[info] {len(components)} connected components; largest has {len(largest)} nodes "
          f"({100*len(largest)/G.number_of_nodes():.1f}% of all nodes)")
    G_main = G.subgraph(largest).copy()

    facilities = gpd.read_file(FACILITIES)
    facilities["snapped_node"] = facilities.geometry.apply(lambda p: snap_to_nearest_node(G_main, p))
    facilities["snap_dist_m"] = facilities.apply(
        lambda r: haversine_m(r.geometry.x, r.geometry.y, r["snapped_node"][0], r["snapped_node"][1]), axis=1
    )
    print(f"[info] facility snap distance: median={facilities['snap_dist_m'].median():.0f}m, "
          f"max={facilities['snap_dist_m'].max():.0f}m, "
          f">2km: {(facilities['snap_dist_m'] > 2000).sum()} facilities (likely off-network / unmapped access road)")

    DATA_PROC.mkdir(parents=True, exist_ok=True)
    nx.write_gpickle = getattr(nx, "write_gpickle", None)
    import pickle
    with open(DATA_PROC / "kalsel_road_graph.pickle", "wb") as f:
        pickle.dump(G_main, f)
    facilities_out = facilities.drop(columns=["snapped_node"])
    facilities_out["snap_lon"] = facilities["snapped_node"].apply(lambda t: t[0])
    facilities_out["snap_lat"] = facilities["snapped_node"].apply(lambda t: t[1])
    facilities_out.to_file(DATA_PROC / "kalsel_facilities_snapped.geojson", driver="GeoJSON")
    print(f"[ok] graph -> data/processed/kalsel_road_graph.pickle")
    print(f"[ok] snapped facilities -> data/processed/kalsel_facilities_snapped.geojson")


if __name__ == "__main__":
    main()
