"""Complete health facility extraction: nodes + simple ways + multipolygon
relations, via osmium's two-pass area assembly.

Supersedes src/01c_extract_with_osmium.py's facility extraction, which only
captured point-mapped facilities (90 total) -- an independent live-Overpass
count found 76 hospital-tagged + 275 clinic/health-centre-tagged features
province-wide (nodes+ways combined), meaning building/relation-mapped hospital
campuses were being missed entirely. This fixes that by properly assembling
multipolygon relations (osmium.area.AreaManager) instead of only handling
simple closed ways, which is what silently produced zero results before.
"""
import osmium
import shapely.wkb as wkblib
import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
PBF = str(DATA_RAW / "population_roads" / "kalimantan-latest.osm.pbf")
BOUNDARY = DATA_RAW / "kalsel_boundary.geojson"
OUT = DATA_RAW / "facilities" / "kalsel_facilities_complete.geojson"

# Care-providing facility types only -- matches the official Kemenkes/BNPB
# scope used throughout this project (RS/Puskesmas/Klinik; the Profil
# Kesehatan document explicitly excludes standalone Apotek/pharmacy from its
# facility counts, e.g. "Klinik Umum Swasta dan Rumah Bersalin tidak
# dikategorikan sebagai rumah sakit"). Excludes standalone pharmacy/
# laboratory/alternative-medicine tags, which a broader healthcare=* filter
# would otherwise pull in.
FACILITY_AMENITY = {"hospital", "clinic", "doctors", "dentist"}
FACILITY_HEALTHCARE = {"hospital", "clinic", "centre", "doctor", "dentist", "midwife"}


def is_facility(tags):
    amenity = tags.get("amenity")
    healthcare = tags.get("healthcare") or ""
    return (amenity in FACILITY_AMENITY) or any(h in healthcare for h in FACILITY_HEALTHCARE)


class NodeHandler(osmium.SimpleHandler):
    """Separate handler for point facilities. AreaManager's second_pass_handler
    wrapper does NOT forward node() events to the wrapped handler (confirmed
    empirically -- area-only records came back with zero node-type matches),
    so nodes need their own pass-through handler in the same osmium.apply() call."""

    def __init__(self):
        super().__init__()
        self.wkbfab = osmium.geom.WKBFactory()
        self.records = []

    def node(self, n):
        if is_facility(n.tags):
            try:
                wkb = self.wkbfab.create_point(n)
            except Exception:
                return
            self.records.append(dict(
                osm_id=n.id, osm_type="node",
                name=n.tags.get("name"), amenity=n.tags.get("amenity"),
                healthcare=n.tags.get("healthcare"), wkb=wkb,
            ))


class AreaHandler:
    """Areas (from AreaManager, covering both simple closed ways and
    assembled multipolygon relations) via area()."""

    def __init__(self):
        self.wkbfab = osmium.geom.WKBFactory()
        self.records = []

    def area(self, a):
        if not is_facility(a.tags):
            return
        try:
            wkb = self.wkbfab.create_multipolygon(a)
        except Exception:
            return
        # a.orig_id() is the source way/relation id; a.from_way()/is_multipolygon() distinguish origin
        self.records.append(dict(
            osm_id=a.orig_id(), osm_type="relation" if a.from_way() is False else "way",
            name=a.tags.get("name"), amenity=a.tags.get("amenity"),
            healthcare=a.tags.get("healthcare"), wkb=wkb,
        ))


def dedupe(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Nodes, ways, and relations can all represent the *same* real-world
    facility (e.g. a point marker plus a building outline plus a campus
    relation for one hospital). Collapse points within ~150m of each other
    that share a name (or are both unnamed) into one record, preferring the
    area-derived (way/relation) geometry over a bare node when available."""
    gdf = gdf.to_crs("EPSG:32750")  # UTM 50S, meters
    gdf["x"] = gdf.geometry.centroid.x
    gdf["y"] = gdf.geometry.centroid.y
    gdf["name_key"] = gdf["name"].fillna("").str.strip().str.lower()

    kept = []
    used = np.zeros(len(gdf), dtype=bool)
    coords = gdf[["x", "y"]].to_numpy()
    priority = gdf["osm_type"].map({"relation": 0, "way": 1, "node": 2}).to_numpy()
    order = np.argsort(priority)  # process relations/ways first so they "absorb" nearby duplicate nodes

    for i in order:
        if used[i]:
            continue
        dist = np.sqrt(((coords - coords[i]) ** 2).sum(axis=1))
        same_name = (gdf["name_key"].to_numpy() == gdf["name_key"].iloc[i]) | (gdf["name_key"].iloc[i] == "")
        dupes = (dist < 150) & same_name & ~used
        used[dupes] = True
        kept.append(gdf.index[i])

    result = gdf.loc[kept].drop(columns=["x", "y", "name_key"]).to_crs("EPSG:4326")
    return result


def main():
    print("Pass 1: identifying relation members...")
    area_mgr = osmium.area.AreaManager()
    reader1 = osmium.io.Reader(PBF, osmium.osm.osm_entity_bits.RELATION)
    osmium.apply(reader1, area_mgr.first_pass_handler())
    reader1.close()

    print("Pass 2: assembling areas + collecting nodes...")
    node_handler = NodeHandler()
    area_handler = AreaHandler()
    reader2 = osmium.io.Reader(PBF)
    idx = osmium.index.create_map("flex_mem")
    lh = osmium.NodeLocationsForWays(idx)
    osmium.apply(reader2, lh, node_handler, area_mgr.second_pass_handler(area_handler))
    reader2.close()

    all_records = node_handler.records + area_handler.records
    print(f"[info] raw matches: {len(all_records)}")
    by_type = pd.Series([r["osm_type"] for r in all_records]).value_counts()
    print(f"[info] by osm_type:\n{by_type}")

    def to_bytes(wkb):
        return bytes.fromhex(wkb) if isinstance(wkb, str) else bytes(wkb)

    geoms = [wkblib.loads(to_bytes(r.pop("wkb"))) for r in all_records]
    gdf = gpd.GeoDataFrame(all_records, geometry=geoms, crs="EPSG:4326")

    boundary = gpd.read_file(BOUNDARY)
    poly = boundary.union_all()
    gdf = gdf[gdf.intersects(poly)]
    print(f"[info] within Kalsel boundary: {len(gdf)}")

    deduped = dedupe(gdf)
    print(f"[info] after dedup (150m + name matching): {len(deduped)}")
    print(deduped["amenity"].value_counts(dropna=False))
    print(deduped["healthcare"].value_counts(dropna=False))

    # normalize to point geometry (centroid) for downstream nearest-facility routing
    deduped = deduped.copy()
    deduped["geometry"] = deduped.to_crs("EPSG:32750").geometry.centroid.to_crs("EPSG:4326")
    deduped.to_file(OUT, driver="GeoJSON")
    print(f"[ok] complete facilities -> {OUT}")


if __name__ == "__main__":
    main()
