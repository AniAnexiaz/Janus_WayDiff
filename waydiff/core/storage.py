"""
Results storage and directory management for Janus Diff.

Handles:
- Timestamp-based result directory creation
- Snapshot index file generation (for human-readable references)
- Diff file storage (HTML and JSON)
- Metadata tracking and reproducibility
"""

import os
import json
import difflib
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from .config import TIMESTAMP_FORMAT, RESULTS_BASE_DIR

logger = logging.getLogger(__name__)


# ==========================================================
# RESULTS DIRECTORY MANAGER
# ==========================================================

class ResultsManager:
    """
    Manage timestamped result directories with increment system.
    
    Creates directory structure like:
    results/
    └── example.com/
        └── 20240109_153000_abc123/
            ├── snapshots/
            ├── diffs/
            ├── reports/
            ├── logs/
            ├── index.txt
            ├── index.json
            └── metadata.json
    """
    
    def __init__(self, domain: str, base_dir: str = RESULTS_BASE_DIR):
        """
        Initialize results manager.
        
        Args:
            domain: Target domain
            base_dir: Base results directory (default: results/)
        """
        self.domain = domain
        self.base_dir = base_dir
        self.domain_dir = None
        self.result_path = None
        self.run_id = None
        self.timestamp = None
        self._setup_directories()
    
    def _setup_directories(self):
        """Create timestamped result directory structure."""
        # Create timestamp and run ID
        self.timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        self.run_id = self._generate_run_id()
        
        # Create domain-specific directory
        domain_path = Path(self.base_dir) / self.domain
        domain_path.mkdir(parents=True, exist_ok=True)
        self.domain_dir = str(domain_path)
        
        # Create timestamped run directory
        run_dir_name = f"{self.timestamp}_{self.run_id}"
        result_path = domain_path / run_dir_name
        result_path.mkdir(parents=True, exist_ok=True)
        self.result_path = str(result_path)
        
        # Create subdirectories
        subdirs = ["snapshots", "diffs", "reports", "logs"]
        for subdir in subdirs:
            (result_path / subdir).mkdir(exist_ok=True)
        
        logger.info(f"✓ Results directory: {self.result_path}")
    
    @staticmethod
    def _generate_run_id() -> str:
        """Generate unique 6-character run ID."""
        import hashlib
        ts = datetime.now().isoformat()
        return hashlib.md5(ts.encode()).hexdigest()[:6]
    
    def get_path(self, category: str, filename: str) -> str:
        """
        Get full path for file in category.
        
        Args:
            category: Category (snapshots, diffs, reports, logs)
            filename: Filename
        
        Returns:
            Full file path
        """
        return str(Path(self.result_path) / category / filename)
    
    def __repr__(self) -> str:
        return f"ResultsManager(domain={self.domain}, path={self.result_path})"


# ==========================================================
# INDEX MANAGER - Snapshot Reference System
# ==========================================================

class IndexManager:
    """
    Manage snapshot index files for the reference system.
    
    Generates two index files:
    - index.txt: Human-readable list with dates
    - index.json: Machine-readable for programmatic access
    
    Format allows users to reference snapshots by number:
      python janus_diff.py diff example.com1 --pick 1 42 487
    """
    
    def __init__(self, result_path: str):
        """
        Initialize index manager.
        
        Args:
            result_path: Result directory path
        """
        self.result_path = result_path
        self.index_path = Path(result_path) / "index.txt"
        self.index_json_path = Path(result_path) / "index.json"
        self.snapshots = []
    
    def add_snapshots(self, snapshots: List[Tuple[str, str]]):
        """
        Add snapshots to index.
        
        Args:
            snapshots: List of (timestamp, original_url) tuples
        """
        self.snapshots = snapshots
    
    def save(self):
        """Save both text and JSON index files."""
        if not self.snapshots:
            logger.warning("No snapshots to index")
            return
        
        # Text index (human-readable)
        self._save_text_index()
        
        # JSON index (machine-readable)
        self._save_json_index()
    
    def _save_text_index(self):
        """Save human-readable text index."""
        with open(self.index_path, "w", encoding="utf-8") as f:
            f.write("# Snapshot Index for Attack Surface Analysis\n")
            f.write(f"# Total snapshots: {len(self.snapshots)}\n")
            f.write("# Format: NUM | DATE | TIMESTAMP | ORIGINAL_URL\n\n")
            
            for idx, (timestamp, original_url) in enumerate(self.snapshots, 1):
                date = self._format_timestamp(timestamp)
                f.write(f"{idx} | {date} | {timestamp} | {original_url}\n")
        
        logger.info(f"✓ Text index saved: {self.index_path}")
    
    def _save_json_index(self):
        """Save machine-readable JSON index."""
        index_data = {
            "total": len(self.snapshots),
            "date_range": {
                "start": self.snapshots[0][0] if self.snapshots else None,
                "end": self.snapshots[-1][0] if self.snapshots else None,
            },
            "snapshots": [
                {
                    "number": idx,
                    "timestamp": timestamp,
                    "date": self._format_timestamp(timestamp),
                    "original_url": original_url
                }
                for idx, (timestamp, original_url) in enumerate(self.snapshots, 1)
            ]
        }
        
        with open(self.index_json_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2)
        
        logger.info(f"✓ JSON index saved: {self.index_json_path}")
    
    def get_snapshot(self, number: int) -> Optional[Tuple[str, str]]:
        """
        Get snapshot by reference number.
        
        Args:
            number: Snapshot number (1-based)
        
        Returns:
            (timestamp, original_url) tuple or None
        """
        if 1 <= number <= len(self.snapshots):
            return self.snapshots[number - 1]
        return None
    
    @staticmethod
    def _format_timestamp(ts: str) -> str:
        """Convert timestamp to human-readable date."""
        try:
            dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return ts


# ==========================================================
# METADATA MANAGER
# ==========================================================

class MetadataManager:
    """
    Track analysis metadata for reproducibility and auditing.
    
    Records:
    - Command and arguments
    - Analysis timing
    - Results summary
    - Status and errors
    """
    
    def __init__(self, result_path: str, domain: str, command: str):
        """
        Initialize metadata manager.
        
        Args:
            result_path: Result directory path
            domain: Target domain
            command: Command executed (wayback, diff, localsnap, etc.)
        """
        self.result_path = result_path
        self.metadata = {
            "analysis_id": ResultsManager._generate_run_id(),
            "timestamp": datetime.now().isoformat(),
            "domain": domain,
            "command": command,
            "arguments": {},
            "results": {
                "snapshots_found": 0,
                "snapshots_analyzed": 0,
                "diffs_generated": 0,
                "findings": 0,
            },
            "timing": {
                "total_seconds": 0,
                "fetch_seconds": 0,
                "analysis_seconds": 0,
            },
            "status": "running",
            "error": None
        }
        self.start_time = datetime.now()
    
    def set_arguments(self, **kwargs):
        """Record command arguments."""
        self.metadata["arguments"] = kwargs
    
    def set_snapshots_found(self, count: int):
        """Record total snapshots found."""
        self.metadata["results"]["snapshots_found"] = count
    
    def set_snapshots_analyzed(self, count: int):
        """Record snapshots analyzed."""
        self.metadata["results"]["snapshots_analyzed"] = count
    
    def set_diffs_generated(self, count: int):
        """Record diffs generated."""
        self.metadata["results"]["diffs_generated"] = count
    
    def set_findings(self, count: int):
        """Record total findings count."""
        self.metadata["results"]["findings"] = count
    
    def set_success(self):
        """Mark analysis as successful."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.metadata["timing"]["total_seconds"] = elapsed
        self.metadata["status"] = "success"
    
    def set_error(self, error: str):
        """Mark analysis as failed."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.metadata["timing"]["total_seconds"] = elapsed
        self.metadata["status"] = "error"
        self.metadata["error"] = error
    
    def save(self):
        """Save metadata to JSON file."""
        metadata_path = Path(self.result_path) / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)
        logger.info(f"✓ Metadata saved: {metadata_path}")


# ==========================================================
# DIFF STORAGE
# ==========================================================

def save_html_diff(snapshot_html: List[str], live_html: List[str], output_path: str):
    """
    Generate and save HTML visual diff.
    
    Args:
        snapshot_html: HTML lines from snapshot
        live_html: HTML lines from live site
        output_path: Path to save HTML diff
    """
    diff = difflib.HtmlDiff().make_file(
        snapshot_html,
        live_html,
        fromdesc="Snapshot",
        todesc="Live",
        context=False,
        numlines=1
    )
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(diff)
    
    logger.debug(f"✓ HTML diff saved: {output_path}")


def save_structured_diff(output_path: str, structured_diff: Dict[str, Any]):
    """
    Save structured JSON diff for programmatic analysis.
    
    Args:
        output_path: Path to save JSON diff
        structured_diff: Structured diff dictionary
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(structured_diff, f, indent=2)
    
    logger.debug(f"✓ JSON diff saved: {output_path}")


def save_snapshot_index(snapshot_file: str, snapshots: List[Tuple[str, str]]):
    """
    Save snapshot index file (legacy compatibility).
    
    Args:
        snapshot_file: Path to index file
        snapshots: List of (timestamp, url) tuples
    """
    with open(snapshot_file, "w", encoding="utf-8") as f:
        for idx, (timestamp, original) in enumerate(snapshots, 1):
            f.write(f"{idx}|{timestamp}|{original}\n")
    
    logger.debug(f"✓ Snapshot index saved: {snapshot_file}")
