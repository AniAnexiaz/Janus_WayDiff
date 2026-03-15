"""
Service orchestrator for Janus Diff.

Complete analysis pipeline orchestration:
- Wayback analysis: fetch → extract → diff → report
- Snapshot diff: load → diff → report
- Results management with timestamp-based directories
- Index file generation for snapshot reference system
- Metadata tracking for reproducibility and auditing

This module coordinates all core modules and generates the complete
analysis output with organized directory structure and comprehensive reports.
"""

import os
import sys
import asyncio
import logging
import shutil
import json
from pathlib import Path
from datetime import datetime

# Fix asyncio cleanup errors on Windows (Python 3.10+)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from typing import Optional, List, Tuple, Dict, Any
from urllib.parse import urlparse

from .validation import (
    sanitize_domain,
    validate_date_range,
    validate_snapshot_list,
    DomainValidationError,
    DateValidationError
)
from .fetcher import fetch_snapshot_list, fetch_selected_snapshots
from .extractor import extract_security_surface
from .diff_engine import compute_surface_diff
from .storage import (
    ResultsManager,
    IndexManager,
    MetadataManager,
    save_html_diff,
    save_structured_diff
)

logger = logging.getLogger(__name__)


# ==========================================================
# WAYBACK MACHINE ANALYSIS
# ==========================================================

def run_wayback_diff(
    domain: str,
    start_date: str,
    end_date: str,
    output_dir: str = "results",
    interactive: bool = False,
    llm_backend: str = "none",
    llm_model: Optional[str] = None,
    llm_timeout: int = 60,
    verbose: bool = False,
    require_live: bool = False
) -> bool:
    """
    Run complete Wayback Machine diff analysis.

    Pipeline:
    1. Validate and sanitize inputs
    2. Fetch Wayback snapshots in date range
    3. Save snapshot index (for reference system)
    4. Select earliest and latest (default) or interactive
    5. Fetch snapshot and live site content
    6. Extract security surfaces
    7. Generate diffs (HTML and structured JSON)
    8. Generate security reports (rule-based and LLM)
    9. Save metadata for reproducibility

    Args:
        domain: Target domain (e.g., example.com)
        start_date: Start date (YYYY-MM-DD format)
        end_date: End date (YYYY-MM-DD format)
        output_dir: Output directory root (default: results/)
        interactive: Use interactive snapshot selection (not yet implemented)
        llm_backend: LLM backend (none, local, online, heuristic)
        llm_model: Specific LLM model name (optional)
        llm_timeout: LLM request timeout in seconds (default: 60)
        verbose: Enable verbose output logging
        require_live: Require live site, error if unavailable (default: False)

    Returns:
        True if analysis completed successfully, False otherwise

    Example:
        >>> run_wayback_diff(
        ...     domain="example.com",
        ...     start_date="2022-01-01",
        ...     end_date="2024-01-09",
        ...     llm_backend="local",
        ...     verbose=True
        ... )
        True

    Results Structure:
        results/example.com/
        └── 20240109_153000_abc123/
            ├── snapshots/
            ├── diffs/
            │   ├── snapshot_20220115000000.html
            │   └── snapshot_20220115000000.json
            ├── reports/
            │   ├── security_report.txt
            │   └── llm_security_report.txt (if LLM enabled)
            ├── logs/
            ├── index.txt (human-readable snapshot list)
            ├── index.json (machine-readable snapshot list)
            └── metadata.json (analysis tracking)
    """
    metadata = None
    results_mgr = None

    try:
        # ===== VALIDATION & SETUP =====
        logger.info("=" * 70)
        logger.info(f"Starting Wayback Machine Analysis")
        logger.info("=" * 70)

        # Validate and sanitize inputs
        domain = sanitize_domain(domain)
        start_yyyymmdd, end_yyyymmdd = validate_date_range(start_date, end_date)

        if verbose:
            logger.info(f"Domain: {domain}")
            logger.info(f"Date range: {start_yyyymmdd} to {end_yyyymmdd}")
            logger.info(f"LLM backend: {llm_backend}")

        # Create results directory with timestamp
        results_mgr = ResultsManager(domain, output_dir)

        # Initialize metadata tracking
        metadata = MetadataManager(results_mgr.result_path, domain, "wayback")
        metadata.set_arguments(
            domain=domain,
            start_date=start_date,
            end_date=end_date,
            interactive=interactive,
            llm_backend=llm_backend,
            require_live=require_live,
            verbose=verbose
        )

        logger.info(f"Results directory: {results_mgr.result_path}")

        # Attach file handler so all logs go to logs/analysis.log
        log_path = results_mgr.get_path("logs", "analysis.log")
        _file_handler = logging.FileHandler(log_path, encoding="utf-8")
        _file_handler.setLevel(logging.DEBUG)
        _file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logging.getLogger().addHandler(_file_handler)

        # ===== FETCH SNAPSHOTS =====
        logger.info("Fetching Wayback Machine snapshots...")

        snapshots = fetch_snapshot_list(domain, start_yyyymmdd, end_yyyymmdd)

        if not snapshots:
            raise ValueError(
                f"No Wayback snapshots found for {domain} "
                f"in date range {start_yyyymmdd} to {end_yyyymmdd}"
            )

        # Validate snapshot list
        snapshots = validate_snapshot_list(snapshots)
        metadata.set_snapshots_found(len(snapshots))

        logger.info(f"✓ Found {len(snapshots)} snapshots")

        # ===== SAVE INDEX FILES =====
        logger.info("Generating snapshot index files...")

        index_mgr = IndexManager(results_mgr.result_path)
        index_mgr.add_snapshots(snapshots)
        index_mgr.save()

        logger.info("✓ Index files saved (index.txt and index.json)")

        # ===== SELECT SNAPSHOTS FOR COMPARISON =====
        logger.info("Selecting snapshots for comparison...")

        if interactive:
            logger.warning("Interactive mode not yet implemented, using auto-selection")
            selected = _select_first_and_last(snapshots)
        else:
            # Default: first and last
            selected = _select_first_and_last(snapshots)

        if not selected:
            raise ValueError("Could not select snapshots for comparison")

        metadata.set_snapshots_analyzed(len(selected))
        snapshot_info = ", ".join([ts for ts, _ in selected])
        logger.info(f"Selected {len(selected)} snapshots: {snapshot_info}")

        # ===== FETCH SNAPSHOT AND LIVE CONTENT =====
        logger.info("Fetching snapshot and live site content...")

        snapshot_results, live_result = asyncio.run(
            fetch_selected_snapshots(domain, selected)
        )

        if not live_result:
            if require_live:
                raise ValueError("Live site unavailable and --require-live specified")
            logger.warning("⚠ Live site unavailable")
            live_result = None

        if live_result:
            logger.info("✓ Fetched live site")

        # ===== GENERATE DIFFS =====
        if live_result:
            logger.info("Generating diffs...")

            diffs_generated = _run_diffs(
                domain,
                results_mgr,
                selected,
                snapshot_results,
                live_result,
                verbose
            )

            metadata.set_diffs_generated(diffs_generated)
            logger.info(f"✓ Generated {diffs_generated} diff(s)")
        else:
            logger.warning("Skipping diffs - no live site available")
            metadata.set_diffs_generated(0)

        # ===== GENERATE REPORTS =====
        logger.info("Generating security reports...")

        # Security report (rule-based findings)
        _generate_security_report(
            results_mgr.get_path("reports", ""),
            verbose=verbose
        )

        # LLM report (if enabled)
        if llm_backend != "none":
            _generate_llm_report(
                results_mgr.get_path("reports", ""),
                llm_backend=llm_backend,
                llm_model=llm_model,
                llm_timeout=llm_timeout,
                verbose=verbose
            )

        # ===== FINALIZE =====
        metadata.set_success()
        metadata.save()

        logger.info("=" * 70)
        logger.info("✓ ANALYSIS COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Results saved to: {results_mgr.result_path}")

        return True

    except (DomainValidationError, DateValidationError, ValueError) as e:
        logger.error(f"Validation error: {e}")
        if metadata:
            metadata.set_error(str(e))
            metadata.save()
        return False

    except Exception as e:
        logger.exception("Unexpected error during wayback analysis")
        if metadata:
            metadata.set_error(str(e))
            metadata.save()
        return False


# ==========================================================
# SNAPSHOT DIFF ANALYSIS
# ==========================================================

def run_snapshot_diff(
    results_folder: str,
    snapshot_numbers: List[int],
    output_dir: str = "results",
    llm_backend: str = "none",
    verbose: bool = False
) -> bool:
    """
    Run diff analysis on selected snapshots from previous wayback analysis.

    Uses snapshot index from previous analysis to identify snapshots by number.
    Generates new diffs and reports in a separate results directory.

    Args:
        results_folder: Path to previous wayback analysis results
                       (e.g., results/example.com/20240109_153000_abc123)
        snapshot_numbers: List of snapshot numbers to compare (1-based indexing)
                         (e.g., [1, 42, 487] for earliest, middle, latest)
        output_dir: Output directory for new results (default: results/)
        llm_backend: LLM backend to use (none, local, online, heuristic)
        verbose: Enable verbose output logging

    Returns:
        True if diff completed successfully, False otherwise

    Example:
        >>> run_snapshot_diff(
        ...     results_folder="results/example.com/20240109_153000_abc123",
        ...     snapshot_numbers=[1, 42, 487],
        ...     llm_backend="local",
        ...     verbose=True
        ... )
        True

    Error Handling:
        - ValueError: If results folder not found or invalid
        - FileNotFoundError: If index file missing
        - ValueError: If snapshot numbers out of range
    """
    metadata = None

    try:
        logger.info("=" * 70)
        logger.info(f"Starting Snapshot Diff Analysis")
        logger.info("=" * 70)

        # Verify results folder
        results_path = Path(results_folder)

        if not results_path.exists():
            raise FileNotFoundError(f"Results folder not found: {results_folder}")

        logger.info(f"Loading results from: {results_folder}")

        # Load index from previous analysis
        index_json = results_path / "index.json"

        if not index_json.exists():
            raise FileNotFoundError(f"No index found in {results_folder}")

        with open(index_json, "r") as f:
            index_data = json.load(f)

        # Extract snapshots from index
        snapshots = [
            (snap["timestamp"], snap["original_url"])
            for snap in index_data["snapshots"]
        ]

        logger.info(f"Loaded {len(snapshots)} snapshots from index")

        # Validate snapshot numbers
        for num in snapshot_numbers:
            if num < 1 or num > len(snapshots):
                raise ValueError(
                    f"Snapshot {num} out of range (1-{len(snapshots)})"
                )

        # Select requested snapshots
        selected = [snapshots[num - 1] for num in snapshot_numbers]
        domain = urlparse(snapshots[0][1]).netloc  # Extract domain from URL

        logger.info(f"Selected {len(selected)} snapshots for comparison")

        # Create new results directory for this diff run
        results_mgr = ResultsManager(domain, output_dir)
        metadata = MetadataManager(results_mgr.result_path, domain, "diff")

        metadata.set_arguments(
            results_folder=str(results_folder),
            snapshot_numbers=snapshot_numbers,
            llm_backend=llm_backend
        )

        logger.info(f"Results directory: {results_mgr.result_path}")

        # ===== FETCH AND COMPARE =====
        logger.info("Fetching snapshot and live site content...")

        snapshot_results, live_result = asyncio.run(
            fetch_selected_snapshots(domain, selected)
        )

        if not live_result:
            raise ValueError("Failed to fetch live site")

        logger.info("✓ Fetched live site")

        # ===== GENERATE DIFFS =====
        logger.info("Generating diffs...")

        diffs_generated = _run_diffs(
            domain,
            results_mgr,
            selected,
            snapshot_results,
            live_result,
            verbose
        )

        metadata.set_diffs_generated(diffs_generated)
        logger.info(f"✓ Generated {diffs_generated} diff(s)")

        # ===== GENERATE REPORTS =====
        logger.info("Generating security reports...")

        _generate_security_report(
            results_mgr.get_path("reports", ""),
            verbose=verbose
        )

        if llm_backend != "none":
            _generate_llm_report(
                results_mgr.get_path("reports", ""),
                llm_backend=llm_backend,
                verbose=verbose
            )

        # ===== FINALIZE =====
        metadata.set_success()
        metadata.save()

        logger.info("=" * 70)
        logger.info("✓ SNAPSHOT DIFF COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Results saved to: {results_mgr.result_path}")

        return True

    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Error: {e}")
        if metadata:
            metadata.set_error(str(e))
            metadata.save()
        return False

    except Exception as e:
        logger.exception("Unexpected error during snapshot diff")
        if metadata:
            metadata.set_error(str(e))
            metadata.save()
        return False


# ==========================================================
# DIFF GENERATION
# ==========================================================

def _run_diffs(
    domain: str,
    results_mgr: ResultsManager,
    selected: List[Tuple[str, str]],
    snapshot_results: list,
    live_result: Dict[str, Any],
    verbose: bool
) -> int:
    """
    Generate diffs for all selected snapshots.

    For each snapshot, generates:
    - HTML visual diff
    - Structured JSON diff with security surface extraction

    Args:
        domain: Target domain
        results_mgr: ResultsManager instance
        selected: List of (timestamp, url) tuples
        snapshot_results: List of snapshot fetch results
        live_result: Live site fetch result
        verbose: Verbose logging

    Returns:
        Number of diffs successfully generated
    """
    if not live_result:
        logger.warning("No live site available - skipping diffs")
        return 0

    # Extract security surface from live site once
    live_surface = extract_security_surface(
        live_result.get("html", []),
        headers=live_result.get("headers", {})
    )

    diffs_generated = 0

    for (timestamp, original_url), snapshot in zip(selected, snapshot_results):

        if not snapshot:
            if verbose:
                logger.warning(f"Snapshot {timestamp} not available, skipping")
            continue

        try:
            snapshot_html = snapshot.get("html", [])
            snapshot_headers = snapshot.get("headers", {})

            # Extract security surface from snapshot
            snapshot_surface = extract_security_surface(
                snapshot_html,
                headers=snapshot_headers
            )

            # Compute diff
            diff = compute_surface_diff(snapshot_surface, live_surface)

            # ===== SAVE HTML DIFF =====
            html_filename = f"snapshot_{timestamp}.html"
            html_path = results_mgr.get_path("diffs", html_filename)
            save_html_diff(
                snapshot_html,
                live_result.get("html", []),
                html_path
            )

            # ===== SAVE STRUCTURED DIFF =====
            json_filename = f"structured_diff_{timestamp}.json"
            json_path = results_mgr.get_path("diffs", json_filename)
            save_structured_diff(json_path, diff)

            diffs_generated += 1

            if verbose:
                logger.info(f"✓ Diff generated: {timestamp}")

        except Exception as e:
            logger.warning(f"Error generating diff for {timestamp}: {e}")
            continue

    return diffs_generated


# ==========================================================
# REPORT GENERATION
# ==========================================================

def _generate_security_report(output_folder: str, verbose: bool = False):
    """
    Generate rule-based security findings report.

    Uses heuristic analysis to identify security risks based on
    endpoints, inputs, scripts, and headers found in diffs.

    Args:
        output_folder: Output folder path
        verbose: Verbose logging
    """
    try:
        from ..intelligence.diff_security_report import generate_security_report

        # structured_diff_*.json files live in the diffs/ subdirectory
        diffs_dir = str(Path(output_folder).parent / "diffs")
        report_path = generate_security_report(diffs_dir)

        # Move report from diffs/ to reports/
        if report_path and Path(report_path).exists():
            dest = Path(output_folder) / Path(report_path).name
            shutil.move(report_path, str(dest))
            report_path = str(dest)

        if report_path:
            if verbose:
                logger.info(f"✓ Security report generated")
        else:
            if verbose:
                logger.warning("No findings to report")

    except ImportError:
        logger.warning("Security report module not available")
    except Exception as e:
        logger.warning(f"Failed to generate security report: {e}")


def _generate_llm_report(
    output_folder: str,
    llm_backend: str = "none",
    llm_model: Optional[str] = None,
    llm_timeout: int = 60,
    verbose: bool = False
):
    """
    Generate LLM-powered security intelligence report.

    Uses AI model to provide expert-level security analysis
    of the discovered attack surface drift.

    Args:
        output_folder: Output folder path
        llm_backend: LLM backend (none, local, online, heuristic)
        llm_model: Specific LLM model name
        llm_timeout: Request timeout in seconds
        verbose: Verbose logging
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

        if report_path:
            if verbose:
                logger.info(f"✓ LLM report generated")
        else:
            if verbose:
                logger.warning("LLM analysis skipped or failed")

    except ImportError:
        logger.warning("LLM report module not available")
    except Exception as e:
        logger.warning(f"Failed to generate LLM report: {e}")


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def _select_first_and_last(snapshots: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    Select first and last snapshots from list.

    Default selection strategy: Compare earliest with latest
    to identify maximum drift over time.

    Args:
        snapshots: List of (timestamp, url) tuples

    Returns:
        List of selected (timestamp, url) tuples (1-2 items)
    """
    if not snapshots:
        return []

    selected = [snapshots[0]]

    # Add last if different from first
    if len(snapshots) > 1 and snapshots[0] != snapshots[-1]:
        selected.append(snapshots[-1])

    return selected
