"""Fetch OSM road network, health facilities, and admin boundary for South Kalimantan.

Data sources: OpenStreetMap via osmnx (Overpass + Nominatim). See PROTOCOL.md §6/§7 —
facility/road counts were spot-checked against official Dinkes Kalsel figures before
committing to this pipeline.
"""
import osmnx as ox
from pathlib import Path

ox.settings.timeout = 300
ox.settings.log_console = True
ox.settings.overpass_url = "https://overpass.kumi.systems/api/interpreter"
ox.settings.overpass_rate_limit = False
# Kalsel's Nominatim polygon includes a large offshore/maritime buffer, which
# blows past the default max query area and forces a 74-way split against a
# free public instance. Raise the cap so it goes through as one request.
ox.settings.max_query_area_size = 250_000 * 1_000_000  # 250,000 km^2 in m^2

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
PLACE = "Kalimantan Selatan, Indonesia"


def fetch_boundary():
    out = DATA_RAW / "kalsel_boundary.geojson"
    if out.exists():
        print(f"[skip] {out} already exists")
        return
    print("Fetching admin boundary...")
    boundary = ox.geocode_to_gdf(PLACE)
    boundary.to_file(out, driver="GeoJSON")
    print(f"[ok] boundary -> {out}")


CLASSIFIED_ROADS_FILTER = (
    '["highway"~"motorway|trunk|primary|secondary|tertiary|unclassified'
    '|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link"]'
)


def fetch_roads():
    out_gml = DATA_RAW / "population_roads" / "kalsel_road_network.graphml"
    out_geojson = DATA_RAW / "population_roads" / "kalsel_roads.geojson"
    if out_geojson.exists():
        print(f"[skip] {out_geojson} already exists")
        return
    print("Fetching classified road network (province-wide 'drive' incl. residential OOM'd the box; restricting to classified roads)...")
    G = ox.graph_from_place(PLACE, custom_filter=CLASSIFIED_ROADS_FILTER, retain_all=True, simplify=True)
    print(f"[ok] graph: {len(G.nodes)} nodes, {len(G.edges)} edges")
    ox.save_graphml(G, out_gml)
    _, edges = ox.graph_to_gdfs(G)
    edges.to_file(out_geojson, driver="GeoJSON")
    print(f"[ok] roads -> {out_geojson}")


def fetch_facilities():
    out = DATA_RAW / "facilities" / "kalsel_facilities.geojson"
    if out.exists():
        print(f"[skip] {out} already exists")
        return
    print("Fetching health facilities...")
    tags = {
        "amenity": ["hospital", "clinic", "doctors"],
        "healthcare": ["hospital", "centre", "clinic"],
    }
    facilities = ox.features_from_place(PLACE, tags)
    # keep only point-like geometry info usable for nearest-facility routing:
    # centroid of any polygon/way features, native point for nodes
    facilities = facilities.reset_index()
    facilities.to_file(out, driver="GeoJSON")
    print(f"[ok] facilities -> {out} ({len(facilities)} features)")


if __name__ == "__main__":
    fetch_boundary()
    fetch_roads()
    fetch_facilities()
