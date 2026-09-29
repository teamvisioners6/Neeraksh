import geopandas as gpd
from pathlib import Path

base = Path(r"C:\NEERAKSH-1\data\government\dam_nwdp\shp")

files = list(base.rglob("*.shp"))

print("Shapefiles:")
for f in files:
    print(f)

for shp in files:

    print("\n" + "=" * 70)
    print("READING:", shp)
    print("=" * 70)

    g = gpd.read_file(shp)

    print("CRS:", g.crs)
    print("Records:", len(g))
    print("Columns:")
    print(list(g.columns))

    text_columns = []

    for col in g.columns:

        if g[col].dtype == object:
            text_columns.append(col)

    mask = None

    for col in text_columns:

        current = (
            g[col]
            .fillna("")
            .astype(str)
            .str.contains(
                "METTUR|STANLEY",
                case=False,
                regex=True
            )
        )

        if mask is None:
            mask = current
        else:
            mask = mask | current

    if mask is not None:

        result = g[mask].copy()

        print("\nMettur/Stanley matches:", len(result))

        if len(result):

            print(
                result.to_string()
            )

            out = Path(
                r"C:\NEERAKSH-1\gis\raw\dam"
            )

            out.mkdir(
                parents=True,
                exist_ok=True
            )

            output = (
                out /
                "mettur_nwdp_dam.shp"
            )

            result.to_file(
                output,
                driver="ESRI Shapefile"
            )

            print(
                "\nSaved:",
                output
            )
