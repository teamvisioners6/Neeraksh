import sqlite3
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from pathlib import Path
import re
import json

# ============================================================
# NEERAKSH - REAL GOVERNMENT DATA INGESTION
# Mettur Reservoir
# Source: Tamil Nadu Government Reservoir Portal
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_DIR = BASE_DIR / "data" / "database"
RAW_DIR = BASE_DIR / "data" / "raw"
DB_PATH = DB_DIR / "neeraksh.db"

DB_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_URL = "https://tnagriculture.in/ARS/home/reservoir/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0 Safari/537.36"
    )
}


# ============================================================
# DATABASE
# ============================================================

def create_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            organization TEXT NOT NULL,
            url TEXT NOT NULL,
            data_type TEXT,
            description TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservoir_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            reservoir_name TEXT NOT NULL,

            observation_date TEXT,
            fetched_at TEXT NOT NULL,

            full_depth_ft REAL,
            full_capacity_mcft REAL,

            current_level_ft REAL,
            current_storage_mcft REAL,

            inflow_cusecs REAL,
            outflow_cusecs REAL,

            last_year_level_ft REAL,
            last_year_storage_mcft REAL,

            source_url TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            dam_name TEXT UNIQUE NOT NULL,
            river_name TEXT,

            latitude REAL,
            longitude REAL,

            source TEXT,
            source_url TEXT,

            created_at TEXT NOT NULL
        )
    """)

    conn.commit()

    # Official source registration
    cursor.execute("""
        INSERT OR IGNORE INTO data_sources
        (
            name,
            organization,
            url,
            data_type,
            description,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        "Major Reservoir Storage and Flow Data",
        "Government of Tamil Nadu - Agriculture Department",
        SOURCE_URL,
        "REAL_TIME_RESERVOIR_OBSERVATION",
        "Official reservoir level, storage, inflow and outflow observations.",
        datetime.now(timezone.utc).isoformat()
    ))

    # Mettur dam record.
    # Coordinates will NOT be fabricated here.
    # They will be populated later from an authoritative geospatial source.
    cursor.execute("""
        INSERT OR IGNORE INTO dams
        (
            dam_name,
            river_name,
            source,
            source_url,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        "Mettur",
        "Cauvery",
        "Government source",
        SOURCE_URL,
        datetime.now(timezone.utc).isoformat()
    ))

    conn.commit()
    conn.close()


# ============================================================
# HELPERS
# ============================================================

def clean_number(value):
    if value is None:
        return None

    value = str(value).strip()

    if value in ("", "-", "--", "N/A", "NA", "None"):
        return None

    value = value.replace(",", "")

    match = re.search(r"-?\d+(?:\.\d+)?", value)

    if not match:
        return None

    try:
        return float(match.group())
    except ValueError:
        return None


def normalize_text(text):
    return " ".join(str(text).split()).strip()


# ============================================================
# FETCH OFFICIAL GOVERNMENT PAGE
# ============================================================

def fetch_page():

    print("\n==============================================")
    print("NEERAKSH REAL DATA INGESTION")
    print("==============================================")

    print(f"Source:")
    print(SOURCE_URL)

    response = requests.get(
        SOURCE_URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    print(f"\nHTTP STATUS: {response.status_code}")

    html = response.text

    # Save the actual government response.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    raw_file = RAW_DIR / f"tn_reservoir_{timestamp}.html"

    raw_file.write_text(
        html,
        encoding="utf-8"
    )

    print(f"Raw government response saved:")
    print(raw_file)

    return html


# ============================================================
# PARSE METTUR
# ============================================================

def parse_mettur(html):

    soup = BeautifulSoup(html, "html.parser")

    tables = soup.find_all("table")

    if not tables:
        raise RuntimeError(
            "No table found on the official government page."
        )

    print(f"\nTables detected: {len(tables)}")

    for table in tables:

        rows = table.find_all("tr")

        for row in rows:

            cells = row.find_all(["td", "th"])

            values = [
                normalize_text(cell.get_text(" ", strip=True))
                for cell in cells
            ]

            if not values:
                continue

            # Find Mettur row
            if values[0].upper().startswith("METTUR"):

                print("\nMettur row found:")
                print(values)

                if len(values) < 9:
                    raise RuntimeError(
                        f"Mettur row does not contain expected fields: {values}"
                    )

                result = {
                    "reservoir_name": "Mettur",

                    "full_depth_ft": clean_number(values[1]),
                    "full_capacity_mcft": clean_number(values[2]),

                    "current_level_ft": clean_number(values[3]),
                    "current_storage_mcft": clean_number(values[4]),

                    "inflow_cusecs": clean_number(values[5]),
                    "outflow_cusecs": clean_number(values[6]),

                    "last_year_level_ft": clean_number(values[7]),
                    "last_year_storage_mcft": clean_number(values[8])
                }

                return result

    raise RuntimeError(
        "Mettur reservoir row was not found on the official page."
    )


# ============================================================
# STORE OBSERVATION
# ============================================================

def save_observation(data):

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    fetched_at = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
        INSERT INTO reservoir_observations
        (
            reservoir_name,
            observation_date,
            fetched_at,

            full_depth_ft,
            full_capacity_mcft,

            current_level_ft,
            current_storage_mcft,

            inflow_cusecs,
            outflow_cusecs,

            last_year_level_ft,
            last_year_storage_mcft,

            source_url
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["reservoir_name"],

        datetime.now().strftime("%Y-%m-%d"),

        fetched_at,

        data["full_depth_ft"],
        data["full_capacity_mcft"],

        data["current_level_ft"],
        data["current_storage_mcft"],

        data["inflow_cusecs"],
        data["outflow_cusecs"],

        data["last_year_level_ft"],
        data["last_year_storage_mcft"],

        SOURCE_URL
    ))

    conn.commit()

    row_id = cursor.lastrowid

    conn.close()

    return row_id


# ============================================================
# EXPORT LATEST JSON
# ============================================================

def export_latest_json():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM reservoir_observations
        WHERE reservoir_name = 'Mettur'
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cursor.fetchone()

    conn.close()

    if row is None:
        return

    output = dict(row)

    output["source"] = {
        "organization": "Government of Tamil Nadu",
        "url": SOURCE_URL,
        "type": "official_government_observation"
    }

    output_dir = BASE_DIR / "data" / "mettur"

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = output_dir / "latest_official_observation.json"

    output_file.write_text(
        json.dumps(
            output,
            indent=4
        ),
        encoding="utf-8"
    )

    print("\nLatest observation exported:")
    print(output_file)


# ============================================================
# MAIN
# ============================================================

def main():

    create_database()

    html = fetch_page()

    data = parse_mettur(html)

    print("\n==============================================")
    print("REAL GOVERNMENT DATA")
    print("==============================================")

    print(f"Reservoir       : {data['reservoir_name']}")
    print(f"Full depth      : {data['full_depth_ft']} ft")
    print(f"Full capacity   : {data['full_capacity_mcft']} M.Cft")
    print(f"Current level   : {data['current_level_ft']} ft")
    print(f"Current storage : {data['current_storage_mcft']} M.Cft")
    print(f"Inflow          : {data['inflow_cusecs']} cusecs")
    print(f"Outflow         : {data['outflow_cusecs']} cusecs")

    row_id = save_observation(data)

    print(f"\nDatabase row inserted: {row_id}")

    export_latest_json()

    print("\n==============================================")
    print("INGESTION COMPLETE")
    print("==============================================")


if __name__ == "__main__":
    main()