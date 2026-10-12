import urllib.request
import json
from shapely.geometry import shape, box

ids = [
    ("04db2c11-1319-4808-adaa-da7f7ccbbd4f", "Pre-event COG candidate"),
    ("844b9a32-9aa2-4611-83f6-ae6501c01955", "Pre-event standard SAFE product"),
    ("9e6c24a1-24ca-419f-bcec-db66791dcf19", "Post-event COG candidate"),
    ("9cb3c885-cfb8-40cc-a44a-8673e772c794", "Post-event standard SAFE product")
]

aoi_poly = box(85.10, 27.85, 85.25, 28.05)

for pid, desc in ids:
    url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({pid})?$expand=Attributes"
    req = urllib.request.Request(url, headers={"User-Agent": "FloodScope-Audit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            p = json.loads(resp.read().decode())
            attrs = {a["Name"]: a["Value"] for a in p.get("Attributes", [])}
            fp = p.get("GeoFootprint")
            fp_geom = shape(fp) if fp else None
            intersects = fp_geom.intersects(aoi_poly) if fp_geom else False
            cov_pct = (fp_geom.intersection(aoi_poly).area / aoi_poly.area * 100) if (fp_geom and intersects) else 0.0
            content_len = p.get("ContentLength") or 0
            size_mb = content_len / (1024 * 1024)

            print(f"=== {desc} ===")
            print(f"ID: {p['Id']}")
            print(f"Name: {p['Name']}")
            print(f"Start: {p.get('ContentDate', {}).get('Start')}")
            print(f"End:   {p.get('ContentDate', {}).get('End')}")
            print(f"Online: {p.get('Online')}")
            print(f"Size: {content_len} bytes ({size_mb:.2f} MB)")
            print(f"S3Path: {p.get('S3Path')}")
            print(f"OrbitDirection: {attrs.get('orbitDirection')}")
            print(f"RelativeOrbit: {attrs.get('relativeOrbitNumber')}")
            print(f"Mode: {attrs.get('operationalMode')}")
            print(f"Polarization: {attrs.get('polarisationChannels')}")
            print(f"ProductType: {attrs.get('productType')}")
            print(f"AOI Intersects: {intersects} (Coverage: {cov_pct:.1f}%)")
            print()
    except Exception as e:
        print(f"Error querying {pid}: {e}")
