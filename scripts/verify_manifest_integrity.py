import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app.geospatial.validation import compute_sha256

for mpath in ["D:/FloodScope-Data/manifest.json", "data/manifest.json"]:
    with open(mpath, "r") as f:
        m = json.load(f)
    print("Checking", mpath, f"({len(m['products'])} products):")
    for pid, p in m["products"].items():
        fpath = Path(p["local_path"])
        assert fpath.exists(), f"File does not exist: {fpath}"
        actual_size = fpath.stat().st_size
        expected_size = p["file_size_bytes"]
        assert actual_size == expected_size, f"Size mismatch: {actual_size} vs {expected_size}"
        actual_sha = compute_sha256(fpath)
        expected_sha = p["sha256_checksum"]
        assert actual_sha == expected_sha, f"SHA mismatch: {actual_sha} vs {expected_sha}"
        print(f"  [OK] {pid}: size={actual_size} bytes, sha256 matches.")
print("\nAll manifest paths, sizes, and checksums verified against real files on disk!")
