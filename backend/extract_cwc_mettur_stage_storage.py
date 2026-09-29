import re
import csv
import PyPDF2
from pathlib import Path

PDF = Path(r"C:\NEERAKSH-1\data\raw\CWC_Mettur_Stanley_Sedimentation_2020.pdf")
OUT = Path(r"C:\NEERAKSH-1\data\hydrology\mettur\cwc_stage_storage_2020.csv")

OUT.parent.mkdir(parents=True, exist_ok=True)

reader = PyPDF2.PdfReader(str(PDF))

# CWC table is on PDF page 27.
text = reader.pages[26].extract_text() or ""

rows = []

for line in text.splitlines():

    line = " ".join(line.split())

    # Normal elevation rows:
    # 230 87.43358716 85.22216465 943.3780728
    m = re.match(
        r"^(\d{3})\s+"
        r"([-+]?\d+(?:\.\d+)?)\s+"
        r"([-+]?\d+(?:\.\d+)?)\s+"
        r"([-+]?\d+(?:\.\d+)?)\s*$",
        line
    )

    if m:
        elevation = float(m.group(1))
        area_original = float(m.group(2))
        area_modified = float(m.group(3))
        capacity_mcm = float(m.group(4))

        rows.append([
            elevation,
            area_original,
            area_modified,
            capacity_mcm,
            "CWC_2020_Sedimentation_Assessment"
        ])

    # FRL row:
    # FRL 240.79 136.8009382 106.6100564 2150.553085
    m = re.match(
        r"^FRL\s+"
        r"(\d+(?:\.\d+)?)\s+"
        r"([-+]?\d+(?:\.\d+)?)\s+"
        r"([-+]?\d+(?:\.\d+)?)\s+"
        r"([-+]?\d+(?:\.\d+)?)\s*$",
        line
    )

    if m:
        elevation = float(m.group(1))
        area_original = float(m.group(2))
        area_modified = float(m.group(3))
        capacity_mcm = float(m.group(4))

        rows.append([
            elevation,
            area_original,
            area_modified,
            capacity_mcm,
            "CWC_2020_Sedimentation_Assessment_FRL"
        ])

# Remove duplicate elevations while preserving first occurrence.
unique = {}

for row in rows:
    unique[row[0]] = row

rows = [unique[k] for k in sorted(unique)]

if not rows:
    raise RuntimeError(
        "No elevation-capacity rows were extracted. "
        "Inspect the PDF text before proceeding."
    )

with OUT.open("w", newline="", encoding="utf-8") as f:

    writer = csv.writer(f)

    writer.writerow([
        "elevation_m",
        "area_original_m2",
        "area_modified_m2",
        "capacity_mcm",
        "source"
    ])

    writer.writerows(rows)

print("=" * 70)
print("CWC METTUR STAGE-STORAGE EXTRACTION")
print("=" * 70)
print()
print("Source:")
print(PDF)
print()
print("Rows extracted:", len(rows))
print("Minimum elevation:", rows[0][0], "m")
print("Maximum elevation:", rows[-1][0], "m")
print("Maximum capacity:", rows[-1][3], "MCM")
print()
print("FIRST 5 ROWS")
for row in rows[:5]:
    print(row)

print()
print("LAST 5 ROWS")
for row in rows[-5:]:
    print(row)

print()
print("Saved:")
print(OUT)
