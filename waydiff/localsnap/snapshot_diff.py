"""
Local snapshot diff module for Janus Diff.

Compares two snapshots and generates:
- HTML visual diffs
- Structured security surface diffs
- Security reports (rule-based and LLM)
- Reproducibility tracking via metadata

Integrates with ResultsManager and MetadataManager for organized results.
"""

import os
import sys
import json
import shutil
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from ..core.extractor import extract_security_surface
from ..core.diff_engine import compute_surface_diff
from ..core.storage import ResultsManager, MetadataManager, save_html_diff, save_structured_diff
from ..intelligence.diff_security_report import generate_security_report

logger = logging.getLogger(__name__)


def compare_snapshots(
    snap_a_path: str,
    snap_b_path: str,
    output_dir: str = "results",
    llm_backend: str = "none",
    llm_model: Optional[str] = None,
    llm_timeout: int = 60,
    verbose: bool = False
) -> Optional[Dict[str, str]]:
    """
    Compare two local snapshots and generate reports.

    Compares security surfaces and generates:
    - HTML visual diff
    - Structured JSON diff
    - Security report (rule-based)
    - LLM report (if enabled)

    Args:
        snap_a_path: Path to first snapshot (e.g., results/domain/timestamp_id/snapshots/snap1)
        snap_b_path: Path to second snapshot (e.g., results/domain/timestamp_id/snapshots/snap2)
        output_dir: Output directory for diff results (default: results/)
        llm_backend: LLM backend (none, local, online, heuristic)
        llm_model: Specific LLM model
        llm_timeout: LLM request timeout in seconds
        verbose: Enable verbose logging

    Returns:
        Dict with paths to generated files:
        {
            "html_diff": "path/to/diff.html",
            "structured_diff": "path/to/diff.json",
            "security_report": "path/to/report.txt",
            "llm_report": "path/to/llm_report.txt"  (if LLM enabled)
        }
        Or None on failure

    Example:
        >>> compare_snapshots(
        ...     snap_a_path="results/domain/20240109_153000_abc123/snapshots/v1.0_20240109_153000",
        ...     snap_b_path="results/domain/20240109_153000_abc123/snapshots/v1.1_20240110_100000",
        ...     llm_backend="local",
        ...     verbose=True
        ... )
    """
    metadata_mgr = None
    results_mgr = None

    try:
        logger.info("=" * 70)
        logger.info("Starting Snapshot Comparison")
        logger.info("=" * 70)

        # ===== LOAD BOTH SNAPSHOTS =====
        logger.info("Loading snapshots...")

        snap_a_data = _load_snapshot_safe(snap_a_path)
        snap_b_data = _load_snapshot_safe(snap_b_path)

        if not snap_a_data or not snap_b_data:
            raise FileNotFoundError("Could not load one or both snapshots")

        if verbose:
            logger.info(f"✓ Loaded snapshot A: {snap_a_path}")
            logger.info(f"✓ Loaded snapshot B: {snap_b_path}")

        html_a = snap_a_data["html_lines"]
        surface_a = snap_a_data["surface"]
        headers_a = snap_a_data.get("headers", {})
        meta_a = snap_a_data["metadata"]

        html_b = snap_b_data["html_lines"]
        surface_b = snap_b_data["surface"]
        headers_b = snap_b_data.get("headers", {})
        meta_b = snap_b_data["metadata"]

        # Extract domain from metadata
        domain = meta_a.get("domain", "unknown")

        if verbose:
            logger.info(f"Domain: {domain}")
            logger.info(f"Snapshot A: {meta_a.get('snapshot_name', 'unknown')}")
            logger.info(f"Snapshot B: {meta_b.get('snapshot_name', 'unknown')}")

        # ===== CREATE RESULTS DIRECTORY =====
        results_mgr = ResultsManager(domain, output_dir)
        metadata_mgr = MetadataManager(results_mgr.result_path, domain, "localsnap_diff")

        snap_a_name = meta_a.get("snapshot_name", meta_a.get("snapshot_id", "A"))
        snap_b_name = meta_b.get("snapshot_name", meta_b.get("snapshot_id", "B"))

        metadata_mgr.set_arguments(
            snapshot_a=snap_a_name,
            snapshot_b=snap_b_name,
            snap_a_path=snap_a_path,
            snap_b_path=snap_b_path,
            llm_backend=llm_backend
        )

        if verbose:
            logger.info(f"Results directory: {results_mgr.result_path}")

        # ===== GENERATE HTML DIFF =====
        logger.info("Generating HTML diff...")

        html_diff_filename = f"localsnap_diff_{snap_a_name}_vs_{snap_b_name}.html"
        html_diff_path = results_mgr.get_path("diffs", html_diff_filename)

        save_html_diff(html_a, html_b, html_diff_path)

        if verbose:
            logger.info(f"✓ HTML diff: {html_diff_path}")

        # ===== GENERATE STRUCTURED DIFF =====
        logger.info("Generating structured diff...")

        # Extract surfaces if not already done
        if not surface_a:
            logger.info("Extracting surface A...")
            surface_a = extract_security_surface(html_a, headers=headers_a)

        if not surface_b:
            logger.info("Extracting surface B...")
            surface_b = extract_security_surface(html_b, headers=headers_b)

        diff = compute_surface_diff(surface_a, surface_b)

        structured_diff_filename = f"structured_diff_{snap_a_name}_vs_{snap_b_name}.json"
        structured_diff_path = results_mgr.get_path("diffs", structured_diff_filename)

        save_structured_diff(structured_diff_path, diff)

        if verbose:
            logger.info(f"✓ Structured diff: {structured_diff_path}")

        metadata_mgr.set_diffs_generated(1)

        # ===== GENERATE SECURITY REPORT =====
        logger.info("Generating security report...")

        report_path = _generate_security_report(
            results_mgr.get_path("reports", ""),
            verbose=verbose
        )

        # ===== GENERATE LLM REPORT =====
        llm_report_path = None

        if llm_backend != "none":
            llm_report_path = _generate_llm_report(
                results_mgr.get_path("reports", ""),
                llm_backend=llm_backend,
                llm_model=llm_model,
                llm_timeout=llm_timeout,
                verbose=verbose
            )

        # ===== FINALIZE =====
        metadata_mgr.set_success()
        metadata_mgr.save()

        logger.info("=" * 70)
        logger.info("✓ SNAPSHOT COMPARISON COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Results: {results_mgr.result_path}")

        return {
            "html_diff": html_diff_path,
            "structured_diff": structured_diff_path,
            "security_report": report_path,
            "llm_report": llm_report_path
        }

    except FileNotFoundError as e:
        logger.error(f"Snapshot not found: {e}")
        if metadata_mgr:
            metadata_mgr.set_error(str(e))
            metadata_mgr.save()
        return None

    except Exception as e:
        logger.exception("Unexpected error during snapshot comparison")
        if metadata_mgr:
            metadata_mgr.set_error(str(e))
            metadata_mgr.save()
        return None


def _load_snapshot_safe(snapshot_dir: str) -> Optional[Dict[str, Any]]:
    """
    Safely load a snapshot with proper error handling.

    Args:
        snapshot_dir: Path to snapshot directory

    Returns:
        Dict with html_lines, surface, metadata, headers; or None on failure
    """
    try:
        snapshot_path = Path(snapshot_dir)

        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot directory not found: {snapshot_dir}")

        # Load HTML
        html_path = snapshot_path / "snapshot.html"
        if not html_path.exists():
            raise FileNotFoundError(f"HTML file not found: {html_path}")

        with open(html_path, "r", encoding="utf-8") as f:
            html_lines = f.read().split("\n")

        # Load security surface
        surface = None
        surface_path = snapshot_path / "surface.json"
        if surface_path.exists():
            with open(surface_path, "r", encoding="utf-8") as f:
                surface = json.load(f)

        # Load metadata
        metadata = {}
        metadata_path = snapshot_path / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

        return {
            "html_lines": html_lines,
            "surface": surface,
            "metadata": metadata,
            "headers": metadata.get("headers", {})
        }

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        return None
    except Exception as e:
        logger.exception(f"Error loading snapshot: {e}")
        return None


def _generate_security_report(
    output_folder: str,
    verbose: bool = False
) -> Optional[str]:
    """
    Generate rule-based security report.

    Args:
        output_folder: Output folder (reports/)
        verbose: Verbose logging

    Returns:
        Path to report file, or None on failure
    """
    try:
        # structured_diff_*.json files live in the diffs/ subdirectory
        diffs_dir = str(Path(output_folder).parent / "diffs")
        report_path = generate_security_report(diffs_dir)

        # Move report from diffs/ to reports/
        if report_path and Path(report_path).exists():
            dest = Path(output_folder) / Path(report_path).name
            shutil.move(report_path, str(dest))
            report_path = str(dest)

        if report_path and verbose:
            logger.info(f"✓ Security report: {report_path}")

        return report_path

    except ImportError:
        logger.warning("Security report module not available")
        return None
    except Exception as e:
        logger.warning(f"Failed to generate security report: {e}")
        return None


def _generate_llm_report(
    output_folder: str,
    llm_backend: str = "none",
    llm_model: Optional[str] = None,
    llm_timeout: int = 60,
    verbose: bool = False
) -> Optional[str]:
    """
    Generate LLM-powered security report.

    Args:
        output_folder: Output folder (reports/)
        llm_backend: LLM backend (none, local, online, heuristic)
        llm_model: Specific model
        llm_timeout: Request timeout
        verbose: Verbose logging

    Returns:
        Path to LLM report, or None on failure
    """
    try:
        from ..intelligence.diff_llm_report import generate_llm_report

        if verbose:
            logger.info(f"Running LLM analysis (backend: {llm_backend})...")

        diffs_dir = str(Path(output_folder).parent / "diffs")
        report_path = generate_llm_report(
            diffs_dir,
            backend=llm_backend,
            model=llm_model,
            timeout=llm_timeout
        )

        # Move report from diffs/ to reports/
        if report_path and Path(report_path).exists():
            dest = Path(output_folder) / Path(report_path).name
            shutil.move(report_path, str(dest))
            report_path = str(dest)

        if report_path and verbose:
            logger.info(f"✓ LLM report: {report_path}")

        return report_path

    except ImportError:
        logger.warning("LLM report module not available")
        return None
    except Exception as e:
        logger.warning(f"Failed to generate LLM report: {e}")
        return None


def find_latest_snapshots(
    domain: str,
    output_dir: str = "results",
    count: int = 2
) -> List[str]:
    """
    Find latest N snapshots for a domain.

    Args:
        domain: Domain name
        output_dir: Root output directory
        count: Number of snapshots to return (default: 2)

    Returns:
        List of snapshot directories (newest first)

    Example:
        >>> snaps = find_latest_snapshots("example.com")
        >>> if len(snaps) >= 2:
        ...     compare_snapshots(snaps[0], snaps[1])
    """
    try:
        domain_path = Path(output_dir) / domain

        if not domain_path.exists():
            logger.warning(f"No snapshots found for {domain}")
            return []

        snapshots = []

        # Iterate through timestamp directories (newest first)
        for timestamp_dir in sorted(domain_path.iterdir(), reverse=True):
            if not timestamp_dir.is_dir():
                continue

            snapshots_path = timestamp_dir / "snapshots"
            if not snapshots_path.exists():
                continue

            # Collect all snapshot subdirectories (newest first)
            for snap_dir in sorted(snapshots_path.iterdir(), reverse=True):
                if snap_dir.is_dir():
                    snapshots.append(str(snap_dir))
                    if len(snapshots) >= count:
                        return snapshots

        return snapshots

    except Exception as e:
        logger.exception(f"Error finding latest snapshots: {e}")
        return []
