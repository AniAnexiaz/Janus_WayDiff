"""
Local snapshot capture module for Janus Diff.

Captures snapshots of URLs (internal or external domains) with:
- HTML content
- Security surface extraction
- Metadata tracking
- Reproducibility logging

Integrates with ResultsManager and MetadataManager for organized results.
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from ..core.fetcher import fetch_single_snapshot
from ..core.extractor import extract_security_surface
from ..cli.validator import validate_url, ValidationError
from ..core.storage import ResultsManager, MetadataManager

logger = logging.getLogger(__name__)


async def take_snapshot(
    url: str,
    output_dir: str = "results",
    name: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    verbose: bool = False
) -> Optional[str]:
    """
    Capture a snapshot of a URL (internal or external domain).

    Creates organized result directory with:
    - snapshot.html (raw HTML content)
    - surface.json (extracted security surface)
    - metadata.json (capture details and reproducibility)

    Args:
        url: URL to snapshot (e.g., https://internal.local/admin)
        output_dir: Output directory root (default: results/)
        name: Optional snapshot name (default: timestamp)
        headers: Optional HTTP headers for request
        verbose: Enable verbose logging

    Returns:
        Path to snapshot directory, None on failure

    Example:
        >>> import asyncio
        >>> asyncio.run(take_snapshot(
        ...     url="https://internal.local/admin",
        ...     name="v1.0",
        ...     verbose=True
        ... ))
        "./results/internal.local/20240109_153000_abc123/snapshots/v1.0_20240109_153000"

    Directory Structure:
        results/domain/timestamp_id/
        ├── snapshots/
        │   └── snapshot_name_timestamp/
        │       ├── snapshot.html
        │       ├── surface.json
        │       └── metadata.json
        ├── diffs/
        ├── reports/
        └── logs/
    """
    metadata_mgr = None
    results_mgr = None

    try:
        logger.info("=" * 70)
        logger.info("Starting Snapshot Capture")
        logger.info("=" * 70)

        # Validate and clean URL
        try:
            url = validate_url(url)
        except (ValidationError) as e:
            raise ValueError(f"Invalid URL: {e}")

        # Extract domain from URL
        domain = urlparse(url).netloc

        if verbose:
            logger.info(f"URL: {url}")
            logger.info(f"Domain: {domain}")

        # Create results directory structure
        results_mgr = ResultsManager(domain, output_dir)

        # Initialize metadata tracking
        metadata_mgr = MetadataManager(results_mgr.result_path, domain, "localsnap")
        metadata_mgr.set_arguments(
            url=url,
            snapshot_name=name,
            verbose=verbose
        )

        if verbose:
            logger.info(f"Results directory: {results_mgr.result_path}")

        # ===== FETCH SNAPSHOT CONTENT =====
        logger.info("Fetching snapshot content...")

        result = await fetch_single_snapshot(url, headers=headers)

        if not result:
            raise ValueError(f"Failed to fetch URL: {url}")

        html_lines = result.get("html", [])
        response_headers = result.get("headers", {})

        if verbose:
            logger.info(f"✓ Fetched {len(html_lines)} HTML lines")

        # ===== GENERATE SNAPSHOT DIRECTORY =====
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_name = name or timestamp
        snapshot_subdir = f"{snapshot_name}_{timestamp}"
        
        snapshot_dir = results_mgr.get_path("snapshots", snapshot_subdir)
        os.makedirs(snapshot_dir, exist_ok=True)

        if verbose:
            logger.info(f"Snapshot directory: {snapshot_dir}")

        # ===== SAVE HTML CONTENT =====
        html_path = os.path.join(snapshot_dir, "snapshot.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write("\n".join(html_lines))

        if verbose:
            logger.info(f"✓ Saved HTML: {html_path}")

        # ===== EXTRACT SECURITY SURFACE =====
        logger.info("Extracting security surface...")

        surface = extract_security_surface(html_lines, headers=response_headers)

        surface_path = os.path.join(snapshot_dir, "surface.json")
        with open(surface_path, "w", encoding="utf-8") as f:
            json.dump(surface, f, indent=2)

        if verbose:
            endpoints_count = len(surface.get("api_routes", []))
            inputs_count = len(surface.get("forms", []))
            scripts_count = len(surface.get("external_scripts", []))
            logger.info(f"✓ Extracted security surface:")
            logger.info(f"  - Endpoints: {endpoints_count}")
            logger.info(f"  - Inputs: {inputs_count}")
            logger.info(f"  - Scripts: {scripts_count}")

        # ===== SAVE SNAPSHOT METADATA =====
        snapshot_metadata = {
            "snapshot_name": snapshot_name,
            "snapshot_id": snapshot_subdir,
            "timestamp": timestamp,
            "datetime": datetime.now().isoformat(),
            "url": url,
            "domain": domain,
            "html_lines": len(html_lines),
            "html_bytes": sum(len(line.encode("utf-8")) for line in html_lines),
            "headers_captured": bool(response_headers),
            "endpoints_found": len(surface.get("api_routes", [])),
            "inputs_found": len(surface.get("forms", [])),
            "scripts_found": len(surface.get("external_scripts", [])),
            "authentication_routes": len(surface.get("authentication_routes", [])),
            "admin_routes": len(surface.get("admin_routes", []))
        }

        metadata_path = os.path.join(snapshot_dir, "metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(snapshot_metadata, f, indent=2)

        if verbose:
            logger.info(f"✓ Saved metadata: {metadata_path}")

        # ===== FINALIZE TRACKING =====
        metadata_mgr.set_success()
        metadata_mgr.save()

        logger.info("=" * 70)
        logger.info("✓ SNAPSHOT CAPTURED")
        logger.info("=" * 70)
        logger.info(f"Location: {snapshot_dir}")

        return snapshot_dir

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        if metadata_mgr:
            metadata_mgr.set_error(str(e))
            metadata_mgr.save()
        return None

    except Exception as e:
        logger.exception("Unexpected error during snapshot capture")
        if metadata_mgr:
            metadata_mgr.set_error(str(e))
            metadata_mgr.save()
        return None


def load_snapshot(snapshot_dir: str) -> Optional[Dict[str, Any]]:
    """
    Load a saved snapshot from disk.

    Args:
        snapshot_dir: Path to snapshot directory (e.g., results/domain/timestamp_id/snapshots/snap_name_time)

    Returns:
        Dict with keys:
        - html_lines: List of HTML lines
        - surface: Extracted security surface dict
        - metadata: Snapshot metadata dict
        Or None on failure

    Raises:
        FileNotFoundError: If snapshot files not found
    """
    try:
        snapshot_path = Path(snapshot_dir)

        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot not found: {snapshot_dir}")

        # Load HTML
        html_path = snapshot_path / "snapshot.html"
        if not html_path.exists():
            raise FileNotFoundError(f"HTML file not found: {html_path}")

        with open(html_path, "r", encoding="utf-8") as f:
            html_lines = f.read().split("\n")

        # Load security surface
        surface_path = snapshot_path / "surface.json"
        if surface_path.exists():
            with open(surface_path, "r", encoding="utf-8") as f:
                surface = json.load(f)
        else:
            surface = None

        # Load metadata
        metadata_path = snapshot_path / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        else:
            metadata = {}

        logger.info(f"✓ Loaded snapshot: {snapshot_dir}")

        return {
            "html_lines": html_lines,
            "surface": surface,
            "metadata": metadata
        }

    except FileNotFoundError as e:
        logger.error(f"Snapshot not found: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in snapshot: {e}")
        return None
    except Exception as e:
        logger.exception(f"Error loading snapshot: {e}")
        return None


def list_snapshots(
    domain: str,
    output_dir: str = "results"
) -> list:
    """
    List all snapshots for a domain.

    Args:
        domain: Domain name
        output_dir: Root output directory

    Returns:
        List of snapshot directories (most recent first)
    """
    try:
        # Find all timestamp-based directories for this domain
        domain_path = Path(output_dir) / domain

        if not domain_path.exists():
            return []

        snapshots = []

        # Iterate through timestamp directories (20240109_153000_abc123)
        for timestamp_dir in sorted(domain_path.iterdir(), reverse=True):
            if not timestamp_dir.is_dir():
                continue

            snapshots_path = timestamp_dir / "snapshots"
            if not snapshots_path.exists():
                continue

            # Collect all snapshot subdirectories
            for snap_dir in sorted(snapshots_path.iterdir(), reverse=True):
                if snap_dir.is_dir():
                    snapshots.append(str(snap_dir))

        return snapshots

    except Exception as e:
        logger.exception(f"Error listing snapshots: {e}")
        return []
