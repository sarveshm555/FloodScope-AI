import pytest
import os
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import requests

from backend.app.geospatial.downloads import (
    SafeDownloadManager,
    CDSEAuthClient,
    InsufficientStorageError,
    DownloadValidationError,
    AuthCredentialsMissingError,
    redact_secrets,
)
from backend.app.geospatial.manifest import (
    load_manifest,
    save_manifest,
    register_acquired_product,
)
from backend.app.schemas.downloads import (
    DataManifest,
    AcquiredProductManifestEntry,
    RasterValidationReport,
)


def test_redact_secrets():
    """Verify that credentials are not leaked in log messages."""
    text = "Error connecting with password: my_super_secret_pw123 and token abc"
    with patch("backend.app.core.config.AppSettings.get_cdse_credentials", return_value={"password": "my_super_secret_pw123"}):
        cleaned = redact_secrets(text)
        assert "my_super_secret_pw123" not in cleaned
        assert "[REDACTED]" in cleaned


def test_missing_credentials_raises_error():
    """Verify that calling get_access_token without env credentials raises AuthCredentialsMissingError."""
    client = CDSEAuthClient()
    with patch("backend.app.core.config.AppSettings.get_cdse_credentials", return_value={}):
        with pytest.raises(AuthCredentialsMissingError) as exc:
            client.get_access_token()
        assert "Copernicus Data Space Ecosystem (CDSE) download credentials not configured" in str(exc.value)


def test_disk_space_safeguard(tmp_path):
    """Verify that download fails before starting if disk space is insufficient."""
    mgr = SafeDownloadManager(base_dir=tmp_path)
    # Mock shutil.disk_usage returning only 1 MB free
    fake_usage = shutil._ntuple_diskusage(10 * 1024 * 1024, 9 * 1024 * 1024, 1 * 1024 * 1024)
    with patch("shutil.disk_usage", return_value=fake_usage):
        # Attempting download requiring 10 MB should raise InsufficientStorageError
        with pytest.raises(InsufficientStorageError) as exc:
            mgr.check_disk_space(tmp_path, required_bytes=10 * 1024 * 1024)
        assert "Insufficient disk space" in str(exc.value)


@patch("requests.get")
def test_chunked_download_and_atomic_rename(mock_get, tmp_path):
    """Verify streaming chunked download, atomic rename, and hash computation."""
    content = b"TEST_CHUNK_SATELLITE_DATA_PAYLOAD_12345" * 100
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Length": str(len(content))}
    mock_resp.iter_content.return_value = [content[:500], content[500:]]
    mock_get.return_value.__enter__.return_value = mock_resp

    mgr = SafeDownloadManager(base_dir=tmp_path, chunk_size=500)
    result = mgr.download_file(
        url="https://example.com/mock-product",
        destination_filename="sample_sar.tif",
        expected_size_bytes=len(content),
        authenticated=False
    )

    dest_file = tmp_path / "sample_sar.tif"
    assert dest_file.exists()
    assert dest_file.read_bytes() == content
    assert result["file_size_bytes"] == len(content)
    assert len(result["sha256_checksum"]) == 64
    # Ensure no leftover .tmp files
    assert len(list(tmp_path.glob("*.tmp.*"))) == 0


@patch("requests.get")
def test_interrupted_download_cleans_up_temp_file(mock_get, tmp_path):
    """Verify that interrupted downloads delete incomplete temporary files."""
    def fail_chunks(chunk_size):
        yield b"PARTIAL_DATA"
        raise requests.exceptions.ConnectionError("Connection abruptly terminated")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Length": "1000"}
    mock_resp.iter_content.side_effect = fail_chunks
    mock_get.return_value.__enter__.return_value = mock_resp

    mgr = SafeDownloadManager(base_dir=tmp_path)
    with pytest.raises(requests.exceptions.ConnectionError):
        mgr.download_file(
            url="https://example.com/fail-test",
            destination_filename="corrupt.tif",
            authenticated=False,
            max_retries=1
        )

    # Ensure no partial files remain on disk
    assert not (tmp_path / "corrupt.tif").exists()
    assert len(list(tmp_path.glob("*.tmp.*"))) == 0


@patch("requests.get")
def test_content_length_mismatch_raises_error(mock_get, tmp_path):
    """Verify that size mismatch between reported Content-Length and received payload triggers error."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Length": "5000"}
    mock_resp.iter_content.return_value = [b"ONLY_100_BYTES"]
    mock_get.return_value.__enter__.return_value = mock_resp

    mgr = SafeDownloadManager(base_dir=tmp_path)
    with pytest.raises(DownloadValidationError):
        mgr.download_file(
            url="https://example.com/size-mismatch",
            destination_filename="mismatch.tif",
            expected_size_bytes=5000,
            authenticated=False,
            max_retries=1
        )


def test_manifest_recording_and_loading(tmp_path):
    """Verify that data manifest can record, serialize, and load acquired products."""
    with patch("backend.app.geospatial.manifest.get_manifest_path", return_value=tmp_path / "manifest.json"):
        initial = load_manifest()
        assert len(initial.products) == 0

        entry = AcquiredProductManifestEntry(
            product_id="test-prod-1",
            source_catalog="Copernicus Data Space Ecosystem",
            acquisition_time="2026-08-16T12:21:41Z",
            original_filename="S1D_TEST.SAFE",
            local_path=str(tmp_path / "S1D_TEST.SAFE"),
            file_size_bytes=1024,
            file_size_mb=0.001,
            sha256_checksum="abc12345",
            download_timestamp="2026-10-12T19:00:00Z",
            processing_status="validated",
            known_limitations=["Pilot test fixture"]
        )

        register_acquired_product(entry)

        loaded = load_manifest()
        assert len(loaded.products) == 1
        assert "test-prod-1" in loaded.products
        assert loaded.products["test-prod-1"].original_filename == "S1D_TEST.SAFE"
