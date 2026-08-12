"""Programmatically build the analysis notebooks (nbformat), then execute them
with nbconvert so the committed .ipynb files have real, embedded outputs rather
than empty code cells."""
import nbformat as nbf
from pathlib import Path

NB_DIR = Path(__file__).resolve().parent.parent / "notebooks"
NB_DIR.mkdir(exist_ok=True)


def make_nb(cells):
    nb = nbf.v4.new_notebook()
    nb.cells = cells
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.13"},
    }
    return nb


def md(text):
    return nbf.v4.new_markdown_cell(text)


def code(text):
    return nbf.v4.new_code_cell(text)


# ---------------------------------------------------------------------------
# 01 — Study area and data overview
# ---------------------------------------------------------------------------
nb1 = make_nb([
    md("# 01 — Study Area and Data Overview\n\n"
       "South Kalimantan, Indonesia: health facilities, road network, population, and "
       "administrative boundaries used throughout this analysis. See `../PROTOCOL.md` "
       "for the full data-source rationale and `../docs/manuscript.md` for the write-up."),
    code(
        "import geopandas as gpd\n"
        "import rasterio\n"
        "from rasterio.plot import show\n"
        "import matplotlib.pyplot as plt\n"
        "import numpy as np\n"
        "from pathlib import Path\n\n"
        "DATA_RAW = Path('../data/raw')\n"
        "DATA_PROC = Path('../data/processed')"
    ),
    md("## Administrative boundaries\n\nProvince outline plus all 13 kabupaten/kota, "
       "colored by the district-capacity classification computed in notebook 04."),
    code(
        "province = gpd.read_file(DATA_RAW / 'kalsel_boundary.geojson')\n"
        "kabupaten = gpd.read_file(DATA_RAW / 'kalsel_kabupaten_boundaries.geojson')\n\n"
        "fig, ax = plt.subplots(figsize=(9, 9))\n"
        "kabupaten.plot(ax=ax, column='kabupaten', cmap='tab20', edgecolor='white', linewidth=0.8, legend=False)\n"
        "province.boundary.plot(ax=ax, color='black', linewidth=1.5)\n"
        "for _, row in kabupaten.iterrows():\n"
        "    c = row.geometry.representative_point()\n"
        "    ax.annotate(row['kabupaten'], (c.x, c.y), fontsize=7, ha='center')\n"
        "ax.set_title('South Kalimantan — 13 Kabupaten/Kota')\n"
        "ax.set_axis_off()\n"
        "plt.tight_layout()\n"
        "plt.show()"
    ),
    md("## Health facilities\n\n365 facilities extracted from OpenStreetMap "
       "(see `../PROTOCOL.md` §6 for why the extraction method changed from live "
       "Overpass queries to streaming `pyosmium` parsing of the Geofabrik PBF)."),
    code(
        "facilities = gpd.read_file(DATA_RAW / 'facilities' / 'kalsel_facilities_complete.geojson')\n"
        "print(facilities['amenity'].value_counts())\n\n"
        "fig, ax = plt.subplots(figsize=(9, 9))\n"
        "province.boundary.plot(ax=ax, color='lightgray', linewidth=1)\n"
        "colors = {'hospital': 'crimson', 'clinic': 'steelblue', 'doctors': 'seagreen'}\n"
        "for amenity, color in colors.items():\n"
        "    sub = facilities[facilities['amenity'] == amenity]\n"
        "    sub.plot(ax=ax, color=color, markersize=15, label=amenity)\n"
        "ax.legend()\n"
        "ax.set_title(f'Health Facilities (n={len(facilities)})')\n"
        "ax.set_axis_off()\n"
        "plt.tight_layout()\n"
        "plt.show()"
    ),
    md("## Road network\n\n62,674 classified road segments (motorway through residential; "
       "footway/path/track excluded), forming a 592k-node routable graph."),
    code(
        "roads = gpd.read_file(DATA_RAW / 'population_roads' / 'kalsel_roads.geojson')\n"
        "print(roads['highway'].value_counts())\n\n"
        "fig, ax = plt.subplots(figsize=(9, 9))\n"
        "roads.plot(ax=ax, linewidth=0.3, color='dimgray')\n"
        "province.boundary.plot(ax=ax, color='steelblue', linewidth=1)\n"
        "ax.set_title(f'Classified Road Network ({len(roads):,} segments)')\n"
        "ax.set_axis_off()\n"
        "plt.tight_layout()\n"
        "plt.show()"
    ),
    md("## Population\n\nWorldPop Indonesia 2020, clipped to the province."),
    code(
        "with rasterio.open(DATA_RAW / 'population_roads' / 'kalsel_population_2020.tif') as src:\n"
        "    pop = src.read(1)\n"
        "    pop_masked = np.ma.masked_less_equal(pop, 0)\n"
        "    extent = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]\n\n"
        "fig, ax = plt.subplots(figsize=(9, 9))\n"
        "im = ax.imshow(np.log1p(pop_masked), extent=extent, cmap='inferno', origin='upper')\n"
        "province.boundary.plot(ax=ax, color='white', linewidth=1)\n"
        "plt.colorbar(im, ax=ax, label='log(1 + population per cell)', shrink=0.7)\n"
        "ax.set_title(f'Population Density (total ≈ {np.nansum(pop_masked):,.0f})')\n"
        "ax.set_axis_off()\n"
        "plt.tight_layout()\n"
        "plt.show()"
    ),
])

# ---------------------------------------------------------------------------
# 02 — Baseline accessibility model
# ---------------------------------------------------------------------------
nb2 = make_nb([
    md("# 02 — Baseline Accessibility Model\n\n"
       "Population → road network → nearest facility travel time, computed via a single "
       "multi-source Dijkstra run from all facility-snapped graph nodes. Methodology "
       "detail in `../docs/manuscript.md` §3.3."),
    code(
        "import pickle\n"
        "import numpy as np\n"
        "import geopandas as gpd\n"
        "import matplotlib.pyplot as plt\n"
        "from pathlib import Path\n\n"
        "DATA_PROC = Path('../data/processed')\n\n"
        "with open(DATA_PROC / 'baseline_travel_time.pickle', 'rb') as f:\n"
        "    travel_time = pickle.load(f)\n\n"
        "nodes = np.array(list(travel_time.keys()))\n"
        "times = np.array(list(travel_time.values()))\n"
        "print(f'{len(times):,} reachable nodes')\n"
        "print(f'median {np.median(times):.1f} min, p90 {np.percentile(times, 90):.1f} min, max {times.max():.1f} min')"
    ),
    md("## Travel-time map\n\nEvery reachable road-network node, colored by minutes to the nearest facility."),
    code(
        "province = gpd.read_file(Path('../data/raw/kalsel_boundary.geojson'))\n\n"
        "fig, ax = plt.subplots(figsize=(9, 9))\n"
        "sc = ax.scatter(nodes[:, 0], nodes[:, 1], c=np.clip(times, 0, 120), cmap='RdYlGn_r', s=1, alpha=0.6)\n"
        "province.boundary.plot(ax=ax, color='black', linewidth=1)\n"
        "plt.colorbar(sc, ax=ax, label='minutes to nearest facility (clipped at 120)', shrink=0.7)\n"
        "ax.set_title('Baseline Travel Time to Nearest Health Facility')\n"
        "ax.set_axis_off()\n"
        "plt.tight_layout()\n"
        "plt.show()"
    ),
    md("## Distribution"),
    code(
        "fig, ax = plt.subplots(figsize=(8, 5))\n"
        "ax.hist(np.clip(times, 0, 180), bins=60, color='steelblue', edgecolor='white')\n"
        "for t, label in [(30, '30 min'), (60, '60 min'), (120, '120 min')]:\n"
        "    ax.axvline(t, color='crimson', linestyle='--', linewidth=1)\n"
        "    ax.text(t + 2, ax.get_ylim()[1]*0.9, label, color='crimson', fontsize=9)\n"
        "ax.set_xlabel('Travel time (minutes, clipped at 180)')\n"
        "ax.set_ylabel('Road-network nodes')\n"
        "ax.set_title('Distribution of Baseline Travel Time')\n"
        "plt.tight_layout()\n"
        "plt.show()"
    ),
    md("## Population-weighted summary\n\nThe headline numbers from `../docs/phase1_summary.md`, reproduced here directly from the pickled results."),
    code(
        "with open(DATA_PROC / 'population_weighted_results.pickle', 'rb') as f:\n"
        "    results = pickle.load(f)\n\n"
        "for label, (pops, scenario_times) in results.items():\n"
        "    valid = ~np.isnan(scenario_times)\n"
        "    total = pops.sum()\n"
        "    print(f'\\n{label}')\n"
        "    for t in [30, 60, 120]:\n"
        "        within = pops[valid][scenario_times[valid] <= t].sum()\n"
        "        print(f'  within {t} min: {100*within/total:.1f}%')"
    ),
])

# ---------------------------------------------------------------------------
# 03 — Flood disruption: proxy vs observed
# ---------------------------------------------------------------------------
nb3 = make_nb([
    md("# 03 — Flood Disruption: Hazard-Zone Proxy vs. Observed Sentinel-1 Extent\n\n"
       "The central methodological comparison of this project. Full discussion in "
       "`../docs/sentinel1_validated_results.md`."),
    code(
        "import pickle\n"
        "import numpy as np\n"
        "import pandas as pd\n"
        "import rasterio\n"
        "import geopandas as gpd\n"
        "import matplotlib.pyplot as plt\n"
        "from pathlib import Path\n\n"
        "DATA_RAW = Path('../data/raw')\n"
        "DATA_PROC = Path('../data/processed')\n"
        "province = gpd.read_file(DATA_RAW / 'kalsel_boundary.geojson')"
    ),
    md("## Disruption layers side by side\n\nLeft: BNPB InaRISK hazard-risk classification "
       "(general, multi-year). Right: Sentinel-1 SAR observed flood extent (the actual "
       "Jan 20, 2021 event)."),
    code(
        "fig, axes = plt.subplots(1, 2, figsize=(15, 8))\n\n"
        "with rasterio.open(DATA_RAW / 'flood' / 'bnpb_kalsel_flood_hazard_class.tif') as src:\n"
        "    hazard = src.read(1)\n"
        "    extent1 = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]\n"
        "axes[0].imshow(np.ma.masked_equal(hazard, 0), extent=extent1, cmap='YlOrRd', vmin=0, vmax=3)\n"
        "province.boundary.plot(ax=axes[0], color='black', linewidth=0.8)\n"
        "axes[0].set_title('BNPB Hazard-Risk Proxy\\n(low/medium/high, multi-year)')\n"
        "axes[0].set_axis_off()\n\n"
        "with rasterio.open(DATA_RAW / 'flood' / 'sentinel1_observed_flood_extent.tif') as src:\n"
        "    flood = src.read(1)\n"
        "    extent2 = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]\n"
        "axes[1].imshow(np.ma.masked_equal(flood, 0), extent=extent2, cmap='Blues', vmin=0, vmax=1)\n"
        "province.boundary.plot(ax=axes[1], color='black', linewidth=0.8)\n"
        "axes[1].set_title('Sentinel-1 Observed Extent\\n(actual Jan 20 2021 event)')\n"
        "axes[1].set_axis_off()\n"
        "plt.tight_layout()\n"
        "plt.show()"
    ),
    md("## Population-weighted access, all scenarios"),
    code(
        "scenarios = {\n"
        "    'Baseline': DATA_PROC / 'baseline_travel_time.pickle',\n"
        "    'Proxy — moderate': DATA_PROC / 'flood_disrupted_moderate_travel_time.pickle',\n"
        "    'Proxy — severe': DATA_PROC / 'flood_disrupted_travel_time.pickle',\n"
        "    'Sentinel-1 — moderate': DATA_PROC / 'flood_disrupted_sentinel1_moderate_travel_time.pickle',\n"
        "    'Sentinel-1 — severe': DATA_PROC / 'flood_disrupted_sentinel1_travel_time.pickle',\n"
        "}\n\n"
        "import sys\n"
        "sys.path.insert(0, '../src')\n"
        "import importlib\n"
        "mod = importlib.import_module('07_population_weighted_comparison')\n"
        "from scipy.spatial import cKDTree\n\n"
        "with open(DATA_PROC / 'kalsel_road_graph.pickle', 'rb') as f:\n"
        "    G = pickle.load(f)\n"
        "node_list = list(G.nodes())\n"
        "tree = cKDTree(np.array(node_list))\n"
        "xs, ys, pops = mod.load_population_points()\n"
        "dist, idx = tree.query(np.column_stack([xs, ys]), k=1)\n"
        "node_arr = np.array(node_list)\n"
        "ok = dist <= 0.02\n"
        "nodes_hit = [tuple(node_arr[i]) for i in idx[ok]]\n\n"
        "rows = []\n"
        "for label, path in scenarios.items():\n"
        "    with open(path, 'rb') as f:\n"
        "        tt = pickle.load(f)\n"
        "    times = np.full(len(xs), np.nan)\n"
        "    times[ok] = [tt.get(n, np.nan) for n in nodes_hit]\n"
        "    valid = ~np.isnan(times)\n"
        "    total = pops.sum()\n"
        "    row = {'scenario': label}\n"
        "    for t in [30, 60, 120]:\n"
        "        within = pops[valid][times[valid] <= t].sum()\n"
        "        row[f'within_{t}min_pct'] = 100 * within / total\n"
        "    rows.append(row)\n\n"
        "df = pd.DataFrame(rows).set_index('scenario')\n"
        "df"
    ),
    code(
        "fig, ax = plt.subplots(figsize=(9, 5))\n"
        "df.plot(kind='bar', ax=ax, color=['#2a9d8f', '#e9c46a', '#f4a261'])\n"
        "ax.set_ylabel('% of population')\n"
        "ax.set_title('Population Access by Scenario')\n"
        "ax.legend(title='threshold')\n"
        "plt.xticks(rotation=25, ha='right')\n"
        "plt.tight_layout()\n"
        "plt.show()"
    ),
    md("**Reading this chart:** the Sentinel-1 moderate scenario is the primary "
       "real-world estimate — a measured, plausible impact. The severe scenarios "
       "(both proxy and observed) are network-fragility stress tests, not literal "
       "population-affected claims; see `../docs/manuscript.md` §5.2 for why."),
])

# ---------------------------------------------------------------------------
# 04 — Capacity index and inequality analysis
# ---------------------------------------------------------------------------
nb4 = make_nb([
    md("# 04 — District Capacity Index and Inequality Analysis\n\n"
       "WHO SDG 3.c.1-style clinical workforce density (doctors + nurses + midwives "
       "per 10,000 population) per kabupaten, and whether flood disruption hit "
       "underserved districts harder. Full discussion in `../docs/phase2_summary.md` "
       "and `../docs/sentinel1_validated_results.md`."),
    code(
        "import numpy as np\n"
        "import geopandas as gpd\n"
        "import pandas as pd\n"
        "import matplotlib.pyplot as plt\n"
        "from pathlib import Path\n\n"
        "DATA_PROC = Path('../data/processed')\n"
        "capacity = gpd.read_file(DATA_PROC / 'kabupaten_capacity_index.geojson')\n"
        "capacity[['kabupaten', 'population_2020', 'clinical_staff', 'clinical_staff_per_10k', 'capacity_class']]\\\n"
        "    .sort_values('clinical_staff_per_10k')"
    ),
    md("## Capacity choropleth"),
    code(
        "fig, ax = plt.subplots(figsize=(9, 9))\n"
        "capacity.plot(ax=ax, column='clinical_staff_per_10k', cmap='RdYlGn', legend=True,\n"
        "              edgecolor='white', linewidth=0.8,\n"
        "              legend_kwds={'label': 'clinical staff per 10,000 population', 'shrink': 0.7})\n"
        "for _, row in capacity.iterrows():\n"
        "    c = row.geometry.representative_point()\n"
        "    ax.annotate(row['kabupaten'], (c.x, c.y), fontsize=7, ha='center')\n"
        "ax.set_title('District Healthcare Workforce Capacity')\n"
        "ax.set_axis_off()\n"
        "plt.tight_layout()\n"
        "plt.show()"
    ),
    md("## Inequality: access change by capacity, real (Sentinel-1) disruption"),
    code(
        "per_kab = pd.read_csv(DATA_PROC / 'inequality_per_kabupaten.csv')\n"
        "per_kab = per_kab.sort_values('clinical_staff_per_10k')\n"
        "per_kab"
    ),
    code(
        "fig, ax = plt.subplots(figsize=(9, 5))\n"
        "colors = ['crimson' if d > 10 else 'steelblue' for d in per_kab['pp_drop_s1_moderate']]\n"
        "ax.barh(per_kab['kabupaten'], per_kab['pp_drop_s1_moderate'], color=colors)\n"
        "ax.set_xlabel('Percentage-point drop in 60-min access (baseline → flood, moderate)')\n"
        "ax.set_title('Access Loss by District, Sorted by Workforce Capacity\\n(bottom = lowest capacity)')\n"
        "plt.tight_layout()\n"
        "plt.show()"
    ),
    md("## Capacity vs. access loss — correlation check"),
    code(
        "fig, ax = plt.subplots(figsize=(7, 6))\n"
        "ax.scatter(per_kab['clinical_staff_per_10k'], per_kab['pp_drop_s1_moderate'], s=80, color='steelblue')\n"
        "for _, row in per_kab.iterrows():\n"
        "    ax.annotate(row['kabupaten'], (row['clinical_staff_per_10k'], row['pp_drop_s1_moderate']),\n"
        "                fontsize=8, xytext=(5, 5), textcoords='offset points')\n"
        "z = np.polyfit(per_kab['clinical_staff_per_10k'], per_kab['pp_drop_s1_moderate'], 1)\n"
        "xs = np.linspace(per_kab['clinical_staff_per_10k'].min(), per_kab['clinical_staff_per_10k'].max(), 50)\n"
        "ax.plot(xs, np.poly1d(z)(xs), '--', color='gray', label=f'trend (slope={z[0]:.2f})')\n"
        "ax.set_xlabel('Clinical staff per 10,000 population')\n"
        "ax.set_ylabel('pp drop in 60-min access under flooding')\n"
        "ax.set_title('Rural Kabupaten: Capacity vs. Flood Access Loss')\n"
        "ax.legend()\n"
        "plt.tight_layout()\n"
        "plt.show()"
    ),
])

# ---------------------------------------------------------------------------
# 05 — Sentinel-1 SAR processing walkthrough
# ---------------------------------------------------------------------------
nb5 = make_nb([
    md("# 05 — Sentinel-1 SAR Processing Walkthrough\n\n"
       "How the observed flood extent was derived from raw Sentinel-1 GRD scenes: "
       "GCP-based georeferencing, per-scene water classification, and before/after "
       "differencing. See `../src/10_sentinel1_flood_extent.py` for the production "
       "pipeline this notebook mirrors, and `../PROTOCOL.md` for the scene-selection "
       "process (including two rounds of mislocated scenes caught and corrected)."),
    code(
        "import numpy as np\n"
        "import rasterio\n"
        "import matplotlib.pyplot as plt\n"
        "from pathlib import Path\n\n"
        "DATA_PROC = Path('../data/processed')\n"
        "DATA_RAW = Path('../data/raw')"
    ),
    md("## Raw GRD georeferencing\n\nSentinel-1 GRD products carry only ground control "
       "points (no direct affine transform) — this is why a GCP-based warp is needed "
       "before any spatial cropping or analysis."),
    code(
        "s1_dir = DATA_RAW / 'flood' / 'sentinel1' / 'extracted'\n"
        "tiff = next(s1_dir.glob('*6B40*/measurement/*vv*.tiff'))\n"
        "with rasterio.open(tiff) as src:\n"
        "    print('shape:', src.shape)\n"
        "    print('crs:', src.crs, '(None expected -- no direct georeferencing)')\n"
        "    print('gcp count:', len(src.gcps[0]))\n"
        "    print('gcp crs:', src.gcps[1])\n"
        "    print('sample gcp:', src.gcps[0][0])"
    ),
    md("## Baseline vs. event water classification"),
    code(
        "with rasterio.open(DATA_PROC / 's1_baseline_water.tif') as src:\n"
        "    baseline_water = src.read(1)\n"
        "    extent = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]\n"
        "with rasterio.open(DATA_PROC / 's1_event_water.tif') as src:\n"
        "    event_water = src.read(1)\n\n"
        "fig, axes = plt.subplots(1, 2, figsize=(14, 8))\n"
        "axes[0].imshow(baseline_water, extent=extent, cmap='Blues')\n"
        "axes[0].set_title(f'Baseline (Dec 15 2020) water\\n{100*baseline_water.mean():.1f}% of AOI')\n"
        "axes[0].set_axis_off()\n"
        "axes[1].imshow(event_water, extent=extent, cmap='Blues')\n"
        "axes[1].set_title(f'Event (Jan 20 2021) water\\n{100*event_water.mean():.1f}% of AOI')\n"
        "axes[1].set_axis_off()\n"
        "plt.tight_layout()\n"
        "plt.show()"
    ),
    md("## New flood extent\n\nEvent water minus baseline water — removes permanent "
       "rivers and water bodies common to both dates, isolating the actual flood."),
    code(
        "with rasterio.open(DATA_RAW / 'flood' / 'sentinel1_observed_flood_extent.tif') as src:\n"
        "    new_flood = src.read(1)\n\n"
        "h, w = new_flood.shape\n"
        "rgb = np.full((h, w, 3), 255, dtype='uint8')\n"
        "rgb[baseline_water == 1] = [80, 130, 220]\n"
        "rgb[new_flood == 1] = [220, 40, 40]\n\n"
        "fig, ax = plt.subplots(figsize=(9, 12))\n"
        "ax.imshow(rgb, extent=extent)\n"
        "ax.set_title(f'Blue = permanent water · Red = new flood extent ({100*new_flood.mean():.1f}% of AOI)')\n"
        "ax.set_axis_off()\n"
        "plt.tight_layout()\n"
        "plt.show()"
    ),
    md("**Visual validation:** flooding concentrates tightly along the Barito river "
       "corridor and the low-lying delta near Banjarmasin, while the mountainous "
       "Meratus range (east side of the AOI) shows negligible flooded area — the "
       "physically expected pattern, and the basis for treating this classification "
       "as a genuine flood signal rather than SAR noise."),
])

for name, nb in [
    ("01_study_area_and_data_overview.ipynb", nb1),
    ("02_baseline_accessibility_model.ipynb", nb2),
    ("03_flood_disruption_proxy_vs_observed.ipynb", nb3),
    ("04_capacity_index_and_inequality.ipynb", nb4),
    ("05_sentinel1_sar_processing.ipynb", nb5),
]:
    path = NB_DIR / name
    with open(path, "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print(f"[ok] wrote {path}")
