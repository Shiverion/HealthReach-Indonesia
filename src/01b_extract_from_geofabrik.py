"""Extract roads and health facilities for South Kalimantan from the Geofabrik
Kalimantan regional PBF, instead of live Overpass queries.

Switched to this after the live-Overpass province-wide road query hung/timed out
repeatedly on public mirrors (see PROTOCOL.md fetch log). The 139MB Kalimantan
extract is self-contained and far more reliable than a large live query against a
free, rate-limited service.
"""
import re
import geopandas as gpd
from pathlib import Path

DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
PBF = DATA_RAW / "population_roads" / "kalimantan-latest.osm.pbf"
BOUNDARY = DATA_RAW / "kalsel_boundary.geojson"
OUT_ROADS = DATA_RAW / "population_roads" / "kalsel_roads.geojson"
OUT_FACILITIES = DATA_RAW / "facilities" / "kalsel_facilities.geojson"

# drivable road classes (excludes footway/path/steps/track/etc.)
DRIVABLE = {
    "motorway", "trunk", "primary", "secondary", "tertiary",
    "unclassified", "residential",
    "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link",
}

TAG_RE = re.compile(r'"([^"]+)"=>"([^"]*)"')


def parse_other_tags(s):
    if not s:
        return {}
    return dict(TAG_RE.findall(s))


def main():
    boundary = gpd.read_file(BOUNDARY)
    bounds = tuple(boundary.total_bounds)
    poly = boundary.union_all()

    # --- roads ---
    if OUT_ROADS.exists():
        print(f"[skip] {OUT_ROADS} already exists")
    else:
        print("Reading 'lines' layer...")
        lines = gpd.read_file(PBF, layer="lines", bbox=bounds)
        roads = lines[lines["highway"].isin(DRIVABLE)].copy()
        roads = roads[roads.intersects(poly)]
        roads = roads[["osm_id", "name", "highway", "geometry"]]
        roads.to_file(OUT_ROADS, driver="GeoJSON")
        print(f"[ok] roads -> {OUT_ROADS} ({len(roads)} segments, classes: {roads['highway'].value_counts().to_dict()})")

    # --- facilities: points ---
    if OUT_FACILITIES.exists():
        print(f"[skip] {OUT_FACILITIES} already exists")
        return

    print("Reading 'points' layer...")
    pts = gpd.read_file(PBF, layer="points", bbox=bounds)
    pts_tags = pts["other_tags"].apply(parse_other_tags)
    pts["amenity"] = pts_tags.apply(lambda d: d.get("amenity"))
    pts["healthcare"] = pts_tags.apply(lambda d: d.get("healthcare"))
    health_pts = pts[
        pts["amenity"].isin(["hospital", "clinic", "doctors"])
        | pts["healthcare"].isin(["hospital", "centre", "clinic"])
    ].copy()
    health_pts = health_pts[health_pts.intersects(poly)]
    health_pts["source_layer"] = "points"
    print(f"[info] health points: {len(health_pts)}")

    # --- facilities: multipolygons (building-mapped, use centroid) ---
    print("Reading 'multipolygons' layer...")
    polys = gpd.read_file(PBF, layer="multipolygons", bbox=bounds)
    polys_tags = polys["other_tags"].apply(parse_other_tags)
    amenity_col = polys["amenity"] if "amenity" in polys.columns else polys_tags.apply(lambda d: d.get("amenity"))
    healthcare_col = polys_tags.apply(lambda d: d.get("healthcare"))
    health_polys = polys[
        amenity_col.isin(["hospital", "clinic", "doctors"]) | healthcare_col.isin(["hospital", "centre", "clinic"])
    ].copy()
    health_polys = health_polys[health_polys.intersects(poly)]
    health_polys["amenity"] = amenity_col[health_polys.index]
    health_polys["healthcare"] = healthcare_col[health_polys.index]
    health_polys = health_polys.copy()
    health_polys["geometry"] = health_polys.geometry.centroid
    health_polys["source_layer"] = "multipolygons_centroid"
    print(f"[info] health facility polygons (centroid): {len(health_polys)}")

    cols = ["osm_id", "name", "amenity", "healthcare", "source_layer", "geometry"]
    combined = gpd.GeoDataFrame(
        pd.concat([health_pts[cols], health_polys[cols]], ignore_index=True),
        crs=pts.crs,
    )
    combined.to_file(OUT_FACILITIES, driver="GeoJSON")
    print(f"[ok] facilities -> {OUT_FACILITIES} ({len(combined)} features)")


if __name__ == "__main__":
    import pandas as pd
    main()
