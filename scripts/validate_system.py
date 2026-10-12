import subprocess
import time
import sys
import urllib.request
import json


def validate_live_backend():
    print("Launching Uvicorn backend process...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    try:
        # Wait for server to bind with retry loop
        health_url = "http://127.0.0.1:8000/api/health"
        print(f"\n1. Waiting for server ready on {health_url}...")
        bound = False
        for attempt in range(20):
            try:
                time.sleep(0.5)
                req = urllib.request.Request(health_url, headers={"User-Agent": "System-Validator/1.0"})
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        bound = True
                        break
            except Exception:
                pass

        if not bound:
            raise RuntimeError("Uvicorn server failed to start within 10 seconds.")
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            body = json.loads(resp.read().decode())
            print(f"Health Status: {body['status']} (v{body['backend_version']})")
            assert body["application_name"] == "FloodScope AI"
            assert body["services"]["copernicus_catalog_available"] is True
            print("[OK] GET /api/health passed.")

        # 2. Test Live Catalog Search Endpoint
        search_url = "http://127.0.0.1:8000/api/catalog/search"
        print(f"\n2. Testing POST {search_url} (Live Trishuli Pilot AOI)...")
        search_payload = json.dumps({
            "bbox": [85.10, 27.85, 85.25, 28.05],
            "event_date": "2026-08-26",
            "pre_days": 15,
            "post_days": 15,
            "include_sentinel_1": True,
            "include_sentinel_2": True
        }).encode("utf-8")

        req_search = urllib.request.Request(
            search_url,
            data=search_payload,
            headers={"Content-Type": "application/json", "User-Agent": "System-Validator/1.0"}
        )
        with urllib.request.urlopen(req_search, timeout=40) as resp:
            assert resp.status == 200
            search_res = json.loads(resp.read().decode())
            search_id = search_res["search_id"]
            print(f"Search ID: {search_id}")
            print(f"Total Discovered Products: {search_res['total_discovered']}")
            print(f"  - Sentinel-1 SAR GRD: {search_res['sentinel_1_count']}")
            print(f"  - Sentinel-2 Optical: {search_res['sentinel_2_count']}")
            print(f"  - Recommended SAR Pairs: {len(search_res['recommended_sar_pairs'])}")
            print(f"  - Payload Downloaded: {search_res['data_downloaded']} (Confirmed 0 MB)")

            if search_res["recommended_sar_pairs"]:
                best = search_res["recommended_sar_pairs"][0]
                print(f"  Top SAR Match:")
                print(f"    Pre-Event:  {best['pre_event_product_name']}")
                print(f"    Post-Event: {best['post_event_product_name']}")
                print(f"    Track/Orbit: RelOrbit {best['relative_orbit']} ({best['orbit_direction']})")
                print(f"    Temporal Baseline: {best['temporal_baseline_days']} days")
                print(f"    Suitability Score: {best['suitability_score']}")

            assert search_res["total_discovered"] > 0
            assert search_res["sentinel_1_count"] > 0
            assert search_res["data_downloaded"] is False
            print("[OK] POST /api/catalog/search passed.")

        # 3. Test Retrieval of Cached Search Results by search_id
        results_url = f"http://127.0.0.1:8000/api/catalog/results/{search_id}"
        print(f"\n3. Testing GET {results_url}...")
        req_results = urllib.request.Request(results_url, headers={"User-Agent": "System-Validator/1.0"})
        with urllib.request.urlopen(req_results, timeout=5) as resp:
            assert resp.status == 200
            cached_res = json.loads(resp.read().decode())
            assert cached_res["search_id"] == search_id
            print(f"[OK] GET /api/catalog/results/{search_id} passed.")

        # 4. Test Data Manifest Endpoint
        manifest_url = "http://127.0.0.1:8000/api/downloads/manifest"
        print(f"\n4. Testing GET {manifest_url}...")
        req_man = urllib.request.Request(manifest_url, headers={"User-Agent": "System-Validator/1.0"})
        with urllib.request.urlopen(req_man, timeout=5) as resp:
            assert resp.status == 200
            manifest_res = json.loads(resp.read().decode())
            print(f"Manifest Version: {manifest_res['manifest_version']}")
            print(f"Total Acquired Products: {len(manifest_res['products'])}")
            for pid, prod in manifest_res["products"].items():
                print(f"  - {pid}: {prod['original_filename']} ({prod['file_size_mb']} MB, status: {prod['processing_status']})")
            assert len(manifest_res["products"]) >= 1
            print("[OK] GET /api/downloads/manifest passed.")

        # 5. Test Storage Status Endpoint
        storage_url = "http://127.0.0.1:8000/api/downloads/storage-status"
        print(f"\n5. Testing GET {storage_url}...")
        req_stor = urllib.request.Request(storage_url, headers={"User-Agent": "System-Validator/1.0"})
        with urllib.request.urlopen(req_stor, timeout=5) as resp:
            assert resp.status == 200
            stor_res = json.loads(resp.read().decode())
            print(f"Storage Directory: {stor_res['data_directory']}")
            print(f"Free Space: {stor_res['free_gb']} GB (Safe: {stor_res['storage_safe_for_downloads']})")
            assert stor_res["free_gb"] > 5.0
            print("[OK] GET /api/downloads/storage-status passed.")

        print("\nALL LIVE SYSTEM VALIDATIONS PASSED!")
    finally:
        print("\nTerminating Uvicorn process...")
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    validate_live_backend()
