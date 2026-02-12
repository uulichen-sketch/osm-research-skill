#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    s = re.sub(r"\s+", "-", value.strip())
    s = re.sub(r"[^\w\-\u4e00-\u9fff]", "", s)
    return s or "region"


def http_get_json(url: str, headers: Dict[str, str]) -> Any:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_get_bytes(url: str, headers: Dict[str, str]) -> bytes:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def bbox_from_geometry(geometry: Dict[str, Any]) -> Tuple[float, float, float, float]:
    coords: List[Tuple[float, float]] = []

    def walk(g: Any) -> None:
        if isinstance(g, list):
            if len(g) == 2 and all(isinstance(v, (int, float)) for v in g):
                coords.append((float(g[0]), float(g[1])))
            else:
                for x in g:
                    walk(x)

    walk(geometry.get("coordinates", []))
    if not coords:
        raise ValueError("geometry coordinates empty")

    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return min(lons), min(lats), max(lons), max(lats)


def bbox_area(b: Tuple[float, float, float, float]) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def choose_candidate(candidates: List[Dict[str, Any]], region_query: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    scored = []
    q = region_query.lower()
    for c in candidates:
        cls = c.get("class") == "boundary"
        typ = c.get("type") == "administrative"
        name = (c.get("display_name") or "").lower()
        rank = (10 if cls else 0) + (10 if typ else 0) + (3 if q in name else 0)
        scored.append((rank, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    ranked = [c for _, c in scored]
    if not ranked:
        raise ValueError("no region candidate selected")
    return ranked[0], ranked[:5]


def ensure_layout(base: Path) -> Dict[str, Path]:
    paths = {
        "meta": base / "meta",
        "raw": base / "raw",
        "changeset_download": base / "raw" / "changeset_download",
        "stats": base / "stats",
        "figures": base / "figures",
        "logs": base / "logs",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def encode_geojson_overlay(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
    ring = [[min_lon, min_lat], [max_lon, min_lat], [max_lon, max_lat], [min_lon, max_lat], [min_lon, min_lat]]
    feature = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [ring]},
        "properties": {"stroke": "#ff2d55", "stroke-width": 3, "stroke-opacity": 1, "fill-opacity": 0},
    }
    return urllib.parse.quote(json.dumps(feature, separators=(",", ":"), ensure_ascii=False), safe="")


def write_monthly_stub(path: Path, year: int) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["month", "CS", "CHG", "U", "AU_10cs", "AU_500chg", "ERL_raw_m", "ERL_unique_m"])
        for m in range(1, 13):
            writer.writerow([f"{year}-{m:02d}", 0, 0, 0, 0, 0, 0.0, 0.0])


def parse_bbox(s: str) -> Tuple[float, float, float, float]:
    parts = [float(x.strip()) for x in s.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox format should be minLon,minLat,maxLon,maxLat")
    return parts[0], parts[1], parts[2], parts[3]


def main() -> int:
    parser = argparse.ArgumentParser(description="OSM annual region update pipeline (metadata + map + stubs)")
    parser.add_argument("--region-query", required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--timezone", default="UTC")
    parser.add_argument("--osm-api-base", default="https://api.openstreetmap.org")
    parser.add_argument("--nominatim-base", default="https://nominatim.openstreetmap.org")
    parser.add_argument("--overpass-base", default="https://overpass-api.de/api/interpreter")
    parser.add_argument("--mapbox-token-env", default="MAPBOX_ACCESS_TOKEN")
    parser.add_argument("--mapbox-style", default="mapbox/streets-v12")
    parser.add_argument("--image-size", default="1000x700")
    parser.add_argument("--granularity", default="month", choices=["year_total", "month", "week"])
    parser.add_argument("--road-key-rule", default="way:highway=*")
    parser.add_argument("--output-root", default="outputs")
    parser.add_argument("--user-agent", default="osm-annual-region-update-skill/1.0")
    parser.add_argument("--bbox", help="Optional override: minLon,minLat,maxLon,maxLat (offline/bootstrap mode)")
    args = parser.parse_args()

    if args.year < 2004 or args.year > 2100:
        raise SystemExit("year out of reasonable range")

    width, height = [int(x) for x in args.image_size.split("x")]
    region_slug = slugify(args.region_query)
    root = Path(args.output_root) / region_slug / str(args.year)
    dirs = ensure_layout(root)

    log_path = dirs["logs"] / "run.log"
    log_path.write_text(f"[{now_iso()}] start\n", encoding="utf-8")
    headers = {"User-Agent": args.user_agent}

    region_json: Dict[str, Any]

    if args.bbox:
        min_lon, min_lat, max_lon, max_lat = parse_bbox(args.bbox)
        geometry = {
            "type": "Polygon",
            "coordinates": [[[min_lon, min_lat], [max_lon, min_lat], [max_lon, max_lat], [min_lon, max_lat], [min_lon, min_lat]]],
        }
        region_json = {
            "region_query": args.region_query,
            "timezone": args.timezone,
            "chosen_osm_object": None,
            "candidate_topn": [],
            "boundary_source": "bbox_override",
            "bbox": {"minLon": min_lon, "minLat": min_lat, "maxLon": max_lon, "maxLat": max_lat},
            "bbox_validation": {"selection": "bbox_override"},
            "polygon_geojson": geometry,
            "polygon_hash": hashlib.sha256(json.dumps(geometry, sort_keys=True).encode("utf-8")).hexdigest(),
            "generated_at": now_iso(),
        }
    else:
        try:
            search_url = (
                f"{args.nominatim_base}/search?"
                f"q={urllib.parse.quote(args.region_query)}&format=jsonv2&addressdetails=1&limit=5"
            )
            candidates = http_get_json(search_url, headers=headers)
            if not candidates:
                raise RuntimeError("nominatim search returned no candidates")

            chosen, topn = choose_candidate(candidates, args.region_query)
            osm_type = (chosen.get("osm_type") or "").upper()
            osm_id = chosen.get("osm_id")
            if not osm_type or osm_id is None:
                raise RuntimeError("chosen candidate missing osm_type/osm_id")

            lookup_url = f"{args.nominatim_base}/lookup?osm_ids={osm_type}{osm_id}&format=geojson&polygon_geojson=1"
            geo = http_get_json(lookup_url, headers=headers)
            features = geo.get("features") or []
            if not features:
                raise RuntimeError("nominatim lookup returned empty feature")

            feat = features[0]
            geometry = feat.get("geometry")
            if not geometry:
                raise RuntimeError("lookup feature missing geometry")

            geom_bbox = bbox_from_geometry(geometry)
            nm_bbox_list = feat.get("bbox")
            nm_bbox = tuple(nm_bbox_list) if isinstance(nm_bbox_list, list) and len(nm_bbox_list) == 4 else None

            final_bbox = geom_bbox
            correction_note = "use_geometry_bbox"
            if nm_bbox:
                lon_diff = max(abs(nm_bbox[0] - geom_bbox[0]), abs(nm_bbox[2] - geom_bbox[2]))
                lat_diff = max(abs(nm_bbox[1] - geom_bbox[1]), abs(nm_bbox[3] - geom_bbox[3]))
                area_g = bbox_area(geom_bbox)
                area_n = bbox_area(nm_bbox)
                area_ratio = abs(area_n - area_g) / area_g if area_g > 0 else 0.0
                if lon_diff <= 0.01 and lat_diff <= 0.01 and area_ratio <= 0.05:
                    final_bbox = nm_bbox
                    correction_note = "use_nominatim_bbox"

            min_lon, min_lat, max_lon, max_lat = final_bbox
            geom_hash = hashlib.sha256(json.dumps(geometry, sort_keys=True).encode("utf-8")).hexdigest()
            region_json = {
                "region_query": args.region_query,
                "timezone": args.timezone,
                "chosen_osm_object": {
                    "osm_type": osm_type,
                    "osm_id": osm_id,
                    "display_name": chosen.get("display_name"),
                    "class": chosen.get("class"),
                    "type": chosen.get("type"),
                },
                "candidate_topn": topn,
                "boundary_source": "nominatim_lookup_geojson",
                "bbox": {"minLon": min_lon, "minLat": min_lat, "maxLon": max_lon, "maxLat": max_lat},
                "bbox_validation": {
                    "nominatim_bbox": nm_bbox,
                    "geometry_bbox": geom_bbox,
                    "selection": correction_note,
                    "threshold": {"deg": 0.01, "area_ratio": 0.05},
                },
                "polygon_geojson": geometry,
                "polygon_hash": geom_hash,
                "generated_at": now_iso(),
            }
        except Exception as e:
            raise SystemExit(f"failed to resolve region via Nominatim: {e}. Use --bbox for bootstrap/offline mode.")

    (dirs["meta"] / "region.json").write_text(json.dumps(region_json, ensure_ascii=False, indent=2), encoding="utf-8")
    min_lon = region_json["bbox"]["minLon"]
    min_lat = region_json["bbox"]["minLat"]
    max_lon = region_json["bbox"]["maxLon"]
    max_lat = region_json["bbox"]["maxLat"]

    cap_path = dirs["meta"] / "capabilities.xml"
    try:
        cap = http_get_bytes(f"{args.osm_api_base}/api/capabilities", headers=headers)
        cap_path.write_bytes(cap)
    except Exception as e:
        cap_path.write_text(f"capabilities fetch failed: {e}\n", encoding="utf-8")

    fig_path = dirs["figures"] / "bbox_map.png"
    token = os.getenv(args.mapbox_token_env, "")
    map_status = {"ok": False, "reason": "missing token"}
    if token:
        overlay = f"geojson({encode_geojson_overlay(min_lon, min_lat, max_lon, max_lat)})"
        static_url = (
            f"https://api.mapbox.com/styles/v1/{args.mapbox_style}/static/"
            f"{overlay}/[{min_lon},{min_lat},{max_lon},{max_lat}]/{width}x{height}"
            f"?access_token={urllib.parse.quote(token)}"
        )
        try:
            img = http_get_bytes(static_url, headers=headers)
            fig_path.write_bytes(img)
            map_status = {"ok": True, "path": str(fig_path)}
        except Exception as e:
            map_status = {"ok": False, "reason": str(e)}

    (dirs["raw"] / "changesets.csv").write_text(
        "id,created_at,closed_at,uid,user,changes_count,min_lon,min_lat,max_lon,max_lat,tags_json\n", encoding="utf-8"
    )
    write_monthly_stub(dirs["stats"] / "monthly.csv", args.year)

    summary = {
        "meta": {
            "region_query": args.region_query,
            "chosen_osm_object": region_json.get("chosen_osm_object"),
            "boundary_source": region_json["boundary_source"],
            "bbox": region_json["bbox"],
            "polygon_hash": region_json["polygon_hash"],
            "year": args.year,
            "t_start": f"{args.year}-01-01T00:00:00Z",
            "t_end": f"{args.year + 1}-01-01T00:00:00Z",
            "granularity": args.granularity,
        },
        "changesets": {"CS_total": 0, "CHG_total": 0, "monthly": [], "created_by_topk": [], "discussion_stats": None,
                       "note": "collection layer not executed in this bootstrap script"},
        "contributors": {"U_total": 0, "AU_10cs": 0, "AU_500chg": 0, "topk_users_by_chg": []},
        "features": {"FEAT_EDIT_total": {}, "FEAT_EDIT_BY_TAG_total": {}, "UNIQUE_FEAT_total": None},
        "roads": {"ERL_raw_total": 0, "ERL_unique_total": 0, "monthly": [], "missing_nodes_rate": None,
                  "affected_ways_count": None,
                  "method_note": "road length requires changeset download + node fetch pipeline"},
        "quality": {
            "truncation_windows": [],
            "bbox_cross_border_risk_note": "changeset bbox hit does not guarantee all edits are inside boundary",
            "api_errors": [],
            "retries": [],
            "partial_failures": [map_status] if not map_status.get("ok") else [],
        },
    }
    (dirs["stats"] / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"[{now_iso()}] done region={args.region_query} year={args.year} map={map_status}\n")

    print(f"Generated outputs at: {root}")
    print(json.dumps({"region": region_slug, "year": args.year, "map": map_status}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
