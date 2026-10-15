import os
import shutil
import hashlib
import time
import uuid
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Callable
import requests

from backend.app.core.config import settings

logger = logging.getLogger("floodscope.downloads")


class InsufficientStorageError(Exception):
    """Raised when destination drive lacks sufficient space for download."""
    pass


class DownloadValidationError(Exception):
    """Raised when downloaded payload fails content-length or integrity checks."""
    pass


class AuthCredentialsMissingError(Exception):
    """Raised when attempting authenticated download without configured CDSE credentials."""
    pass


def redact_secrets(text: str) -> str:
    """Safely redact sensitive tokens or credentials from log messages."""
    if not text:
        return text
    creds = settings.get_cdse_credentials()
    clean = text
    for key in ["password", "client_secret"]:
        val = creds.get(key)
        if val and len(val) > 3:
            clean = clean.replace(val, "[REDACTED]")
    return clean


class CDSEAuthClient:
    """Manages authentication with Copernicus Data Space Ecosystem Keycloak OAuth2."""
    TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

    def __init__(self):
        self._token: Optional[str] = None
        self._expires_at: float = 0.0

    def get_access_token(self) -> str:
        """Obtain a valid bearer token from CDSE or raise AuthCredentialsMissingError."""
        now = time.time()
        if self._token and now < (self._expires_at - 60):
            return self._token

        creds = settings.get_cdse_credentials()
        username = creds.get("username")
        password = creds.get("password")
        client_id = creds.get("client_id")
        client_secret = creds.get("client_secret")

        if username and password:
            data = {
                "client_id": "cdse-public",
                "username": username,
                "password": password,
                "grant_type": "password",
            }
        elif client_id and client_secret:
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            }
        else:
            raise AuthCredentialsMissingError(
                "Copernicus Data Space Ecosystem (CDSE) download credentials not configured. "
                "Set CDSE_USERNAME and CDSE_PASSWORD (or CDSE_CLIENT_ID and CDSE_CLIENT_SECRET) in .env "
                "to authorize satellite scene downloads. Register for free at https://dataspace.copernicus.eu."
            )

        try:
            logger.info("Requesting OAuth2 access token from CDSE identity service...")
            resp = requests.post(self.TOKEN_URL, data=data, timeout=15)
            if resp.status_code == 401:
                raise requests.HTTPError(
                    "Invalid CDSE credentials. Please verify your CDSE_USERNAME/CDSE_PASSWORD in .env."
                )
            resp.raise_for_status()
            res_json = resp.json()
            self._token = res_json["access_token"]
            expires_in = res_json.get("expires_in", 600)
            self._expires_at = now + expires_in
            return self._token
        except requests.exceptions.RequestException as e:
            logger.error(redact_secrets(f"CDSE authentication failed: {e}"))
            raise


class SafeDownloadManager:
    """Robust, atomic, streaming downloader with disk space safeguards and SHA-256 verification."""

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        auth_client: Optional[CDSEAuthClient] = None,
        chunk_size: int = 1024 * 1024  # 1 MB chunk
    ):
        self.base_dir = base_dir or (settings.data_dir / "raw")
        self.auth_client = auth_client or CDSEAuthClient()
        self.chunk_size = chunk_size

    def check_disk_space(self, target_dir: Path, required_bytes: int):
        """Verify that target drive has sufficient free space (with 1.5x safety multiplier)."""
        target_dir.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(str(target_dir))
        needed_with_margin = int(required_bytes * 1.5)
        if usage.free < needed_with_margin:
            free_mb = usage.free / (1024 * 1024)
            req_mb = needed_with_margin / (1024 * 1024)
            raise InsufficientStorageError(
                f"Insufficient disk space on destination volume. "
                f"Free: {free_mb:.1f} MB, Required (with 1.5x margin): {req_mb:.1f} MB. "
                f"Configured path: '{target_dir}'. Set FLOODSCOPE_DATA_DIR to an alternate drive with more space."
            )

    def download_file(
        self,
        url: str,
        destination_filename: str,
        expected_size_bytes: Optional[int] = None,
        authenticated: bool = True,
        max_retries: int = 3,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """Download file atomically with retries, checksum calculation, and cleanup on failure.
        
        Returns:
            Dict containing local_path, file_size_bytes, sha256_checksum, and download_duration_seconds.
        """
        self.base_dir.mkdir(parents=True, exist_ok=True)
        final_path = self.base_dir / destination_filename
        temp_path = self.base_dir / f"{destination_filename}.tmp.{uuid.uuid4().hex[:8]}"

        # Pre-flight disk space check if expected size is known
        if expected_size_bytes:
            self.check_disk_space(self.base_dir, expected_size_bytes)

        headers = {
            "User-Agent": "FloodScope-AI-Downloader/1.0",
        }
        if authenticated:
            token = self.auth_client.get_access_token()
            headers["Authorization"] = f"Bearer {token}"

        start_time = time.time()

        for attempt in range(1, max_retries + 1):
            sha256 = hashlib.sha256()
            total_downloaded = 0
            temp_path = self.base_dir / f"{destination_filename}.tmp.{uuid.uuid4().hex[:8]}"
            try:
                logger.info(f"Downloading {destination_filename} (Attempt {attempt}/{max_retries})...")
                with requests.get(url, headers=headers, stream=True, timeout=(20, 120)) as resp:
                    if resp.status_code == 401 and authenticated:
                        logger.error("Download unauthorized (401). Access token rejected or expired.")
                        resp.raise_for_status()
                    resp.raise_for_status()

                    # Recheck content length from server header
                    content_length = resp.headers.get("Content-Length")
                    if content_length:
                        reported_bytes = int(content_length)
                        self.check_disk_space(self.base_dir, reported_bytes)

                    with open(temp_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=self.chunk_size):
                            if chunk:
                                f.write(chunk)
                                sha256.update(chunk)
                                total_downloaded += len(chunk)
                                if progress_callback and content_length:
                                    progress_callback(total_downloaded, int(content_length))

                # Verify downloaded byte count
                if expected_size_bytes and expected_size_bytes > 0:
                    if total_downloaded != expected_size_bytes:
                        raise DownloadValidationError(
                            f"Downloaded file size ({total_downloaded} bytes) differs from "
                            f"expected size ({expected_size_bytes} bytes)."
                        )

                # Atomic rename
                if temp_path.exists():
                    os.replace(temp_path, final_path)
                    duration = time.time() - start_time
                    checksum = sha256.hexdigest()
                    logger.info(
                        f"Download complete: {destination_filename} "
                        f"({total_downloaded / (1024*1024):.2f} MB, {duration:.1f}s, SHA-256: {checksum[:8]}...)"
                    )
                    return {
                        "local_path": str(final_path),
                        "file_size_bytes": total_downloaded,
                        "file_size_mb": round(total_downloaded / (1024 * 1024), 2),
                        "sha256_checksum": checksum,
                        "download_duration_seconds": round(duration, 2),
                    }

            except (requests.exceptions.RequestException, DownloadValidationError) as e:
                logger.warning(redact_secrets(f"Download attempt {attempt} failed: {e}"))
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass
                if attempt == max_retries:
                    raise
                time.sleep(1.5 * attempt)
            finally:
                # Guarantee temporary file is cleaned up if rename didn't happen
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass

        raise RuntimeError(f"Unexpected termination of download for {destination_filename}.")

    def download_cdse_product(
        self,
        product_id: str,
        product_name: str,
        estimated_size_mb: Optional[float] = None
    ) -> Dict[str, Any]:
        """Download product from CDSE OData $value endpoint."""
        url = f"https://download.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
        dest_filename = f"{product_name}.zip" if not product_name.endswith((".zip", ".tif")) else product_name
        expected_bytes = int(estimated_size_mb * 1024 * 1024) if estimated_size_mb else None
        return self.download_file(
            url=url,
            destination_filename=dest_filename,
            expected_size_bytes=expected_bytes,
            authenticated=True
        )
