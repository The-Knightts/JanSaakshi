from flask import Blueprint, jsonify, request
import json
import os
import sqlite3
import re

ward_bp = Blueprint("wards", __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GEOJSON_PATH = os.path.join(BASE_DIR, "data", "wards.geojson")

# Use the real JanSaakshi database (same one the rest of the app uses)
DB_PATH = os.path.join(BASE_DIR, "jansaakshi.db")


def _to_int_ward(raw) -> int:
    """Coerce any ward_no representation to an integer, e.g. '001' -> 1, '5A' -> 5."""
    if raw is None:
        return 0
    m = re.search(r'\d+', str(raw))
    return int(m.group()) if m else 0


def _resolve_city_id(conn):
    """Resolve city_id from ?city= query param (same logic as app.py)."""
    city_name = request.args.get("city", "").strip().lower()
    if not city_name:
        return None
    row = conn.execute(
        "SELECT city_id FROM city WHERE LOWER(city_name)=?", (city_name,)
    ).fetchone()
    return row[0] if row else None


@ward_bp.route("/geojson")
def get_geojson():
    """Serve ward GeoJSON with wardNumber normalised to integer."""
    if not os.path.exists(GEOJSON_PATH):
        return jsonify({"type": "FeatureCollection", "features": []})

    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    features = []
    for feature in raw.get("features", []):
        try:
            wn = int(feature["properties"].get("note", 0))
        except (ValueError, TypeError):
            wn = 0
        features.append({
            "type": "Feature",
            "properties": {
                "wardNumber": wn,
                "wardName": f"Ward {wn}",
            },
            "geometry": feature["geometry"],
        })

    return jsonify({"type": "FeatureCollection", "features": features})


@ward_bp.route("/stats")
def ward_stats():
    """Per-ward stats from the real jansaakshi.db projects table."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row

    cid = _resolve_city_id(conn)
    params = []
    city_filter = ""
    if cid:
        city_filter = " AND city_id=?"
        params.append(cid)

    rows = conn.execute(f"""
        SELECT
            ward_no,
            MAX(ward_name)        AS ward_name,
            MAX(corporator_name)  AS corporator_name,
            COUNT(*)              AS total,
            SUM(CASE WHEN LOWER(status) IN ('in progress','ongoing') THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN LOWER(status) = 'completed'  THEN 1 ELSE 0 END) AS completed,
            SUM(CASE WHEN LOWER(status) = 'delayed'    THEN 1 ELSE 0 END) AS delayed,
            SUM(CASE WHEN LOWER(status) = 'stalled'    THEN 1 ELSE 0 END) AS stalled,
            COALESCE(SUM(budget), 0) AS total_budget,
            COALESCE(AVG(CASE WHEN delay_days > 0 THEN delay_days END), 0) AS avg_delay_days
        FROM projects
        WHERE ward_no IS NOT NULL AND ward_no != ''
        {city_filter}
        GROUP BY ward_no
    """, params).fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        wn = _to_int_ward(d["ward_no"])
        if wn == 0:
            continue  # skip rows with no parseable ward number
        result.append({
            "wardNumber":    wn,                              # integer – matches GeoJSON
            "wardName":      d["ward_name"] or f"Ward {wn}",
            "corporatorName": d["corporator_name"] or "",
            "total":         d["total"],
            "active":        d["active"],
            "completed":     d["completed"],
            "delayed":       d["delayed"],
            "stalled":       d["stalled"],
            "total_budget":  d["total_budget"],
            "avg_delay_days": round(float(d["avg_delay_days"] or 0), 1),
        })

    return jsonify(result)


@ward_bp.route("/<int:ward_no>")
def single_ward(ward_no):
    """Stats for a single ward."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row

    cid = _resolve_city_id(conn)
    params: list = []
    city_filter = ""
    if cid:
        city_filter = " AND city_id=?"
        params.append(cid)

    # Match both numeric string and zero-padded versions
    rows = conn.execute(f"""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN LOWER(status) IN ('in progress','ongoing') THEN 1 ELSE 0 END) as active,
            SUM(CASE WHEN LOWER(status) = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN LOWER(status) = 'delayed'   THEN 1 ELSE 0 END) as delayed,
            SUM(CASE WHEN LOWER(status) = 'stalled'   THEN 1 ELSE 0 END) as stalled,
            COALESCE(SUM(budget), 0) as total_budget,
            MAX(ward_name) as ward_name,
            MAX(corporator_name) as corporator_name
        FROM projects
        WHERE CAST(ward_no AS INTEGER) = ?
        {city_filter}
    """, [ward_no] + params).fetchone()
    conn.close()

    return jsonify({
        "wardNumber":    ward_no,
        "wardName":      rows["ward_name"] or f"Ward {ward_no}",
        "corporatorName": rows["corporator_name"] or "",
        "total":         rows["total"] or 0,
        "active":        rows["active"] or 0,
        "completed":     rows["completed"] or 0,
        "delayed":       rows["delayed"] or 0,
        "stalled":       rows["stalled"] or 0,
        "total_budget":  rows["total_budget"] or 0,
    })