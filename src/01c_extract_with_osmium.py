"""Stream-extract roads and health facilities from the local Kalimantan PBF using
pyosmium, then clip to the Kalsel boundary with geopandas.

Switched to this after both live Overpass (OOM on full 'drive' network) and GDAL's
built-in OSM driver (node-cache parse errors on this file) proved unreliable.
osmium processes the file in a single streaming pass with bounded memory.
"""
import osmium
import shapely.wkb as wkblib
import geopandas as gpd
import pandas as pd
from pathlib import Path

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
PBF = str(DATA_RAW / "population_roads" / "kalimantan-latest.osm.pbf")
BOUNDARY = DATA_RAW / "kalsel_boundary.geojson"
OUT_ROADS = DATA_RAW / "population_roads" / "kalsel_roads.geojson"
OUT_FACILITIES = DATA_RAW / "facilities" / "kalsel_facilities.geojson"

CLASSIFIED = {
    "motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential",
    "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link",
}
FACILITY_AMENITY = {"hospital", "clinic", "doctors"}
FACILITY_HEALTHCARE = {"hospital", "centre", "clinic"}


class Extractor(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.wkbfab = osmium.geom.WKBFactory()
        self.roads = []
        self.facility_nodes = []
        self.facility_ways = []

    def node(self, n):
        amenity = n.tags.get("amenity")
        healthcare = n.tags.get("healthcare")
        if amenity in FACILITY_AMENITY or healthcare in FACILITY_HEALTHCARE:
            try:
                wkb = self.wkbfab.create_point(n)
            except Exception:
                return
            self.facility_nodes.append(
                dict(osm_id=n.id, name=n.tags.get("name"), amenity=amenity, healthcare=healthcare, wkb=wkb)
            )

    def way(self, w):
        highway = w.tags.get("highway")
        if highway in CLASSIFIED:
            try:
                wkb = self.wkbfab.create_linestring(w)
                self.roads.append(dict(osm_id=w.id, name=w.tags.get("name"), highway=highway, wkb=wkb))
            except Exception:
                pass
            return

        amenity = w.tags.get("amenity")
        healthcare = w.tags.get("healthcare")
        if amenity in FACILITY_AMENITY or healthcare in FACILITY_HEALTHCARE:
            try:
                wkb = self.wkbfab.create_multipolygon(w) if w.is_closed() else None
            except Exception:
                wkb = None
            if wkb is not None:
                self.facility_ways.append(
                    dict(osm_id=w.id, name=w.tags.get("name"), amenity=amenity, healthcare=healthcare, wkb=wkb)
                )


def to_gdf(records, crs="EPSG:4326"):
    if not records:
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs=crs)
    df = pd.DataFrame(records)
    geom = df.pop("wkb").apply(lambda x: wkblib.loads(bytes.fromhex(x) if isinstance(x, str) else x))
    return gpd.GeoDataFrame(df, geometry=geom, crs=crs)


def main():
    if OUT_ROADS.exists() and OUT_FACILITIES.exists():
        print("[skip] both outputs already exist")
        return

    print("Streaming Kalimantan PBF (roads + facility nodes/ways in one pass)...")
    h = Extractor()
    h.apply_file(PBF, locations=True, idx="flex_mem")
    print(f"[info] raw counts: roads={len(h.roads)}, facility_nodes={len(h.facility_nodes)}, facility_ways={len(h.facility_ways)}")

    boundary = gpd.read_file(BOUNDARY)
    poly = boundary.union_all()

    if not OUT_ROADS.exists():
        roads = to_gdf(h.roads)
        roads = roads[roads.intersects(poly)]
        roads.to_file(OUT_ROADS, driver="GeoJSON")
        print(f"[ok] roads -> {OUT_ROADS} ({len(roads)} segments)")
        print(roads["highway"].value_counts())

    if not OUT_FACILITIES.exists():
        nodes = to_gdf(h.facility_nodes)
        nodes["source_layer"] = "node"
        ways = to_gdf(h.facility_ways)
        if len(ways):
            ways["geometry"] = ways.geometry.centroid
        ways["source_layer"] = "way_centroid"

        combined = pd.concat([nodes, ways], ignore_index=True)
        combined = gpd.GeoDataFrame(combined, geometry="geometry", crs="EPSG:4326")
        combined = combined[combined.intersects(poly)]
        combined.to_file(OUT_FACILITIES, driver="GeoJSON")
        print(f"[ok] facilities -> {OUT_FACILITIES} ({len(combined)} features)")


if __name__ == "__main__":
    main()
