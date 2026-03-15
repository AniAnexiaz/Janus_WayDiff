"""
Core module for Janus Diff.

Provides attack surface analysis, security extraction, diff computation,
and results management.

Core components:
  - service: Analysis orchestration (wayback, snapshot diff)
  - validation: Input validation and sanitization
  - fetcher: Async HTTP fetching
  - extractor: Security surface extraction
  - diff_engine: Surface difference computation
  - storage: Results management with ResultsManager, IndexManager, MetadataManager
  - cleaner: HTML cleaning utilities
  - config: Configuration constants
"""

# Service orchestration
from .service import (
    run_wayback_diff,
    run_snapshot_diff,
)

# Validation
from .validation import (
    sanitize_domain,
    validate_date_range,
    validate_snapshot_list,
    DomainValidationError,
    DateValidationError,
)

# Storage and results management
from .storage import (
    ResultsManager,
    IndexManager,
    MetadataManager,
    save_html_diff,
    save_structured_diff,
)

# Analysis utilities
from .fetcher import (
    fetch_snapshot_list,
    fetch_selected_snapshots,
)

from .extractor import extract_security_surface
from .diff_engine import compute_surface_diff
from .cleaner import clean_html

# Configuration
from .config import (
    MAX_DOMAIN_LENGTH,
    MAX_LABEL_LENGTH,
    MAX_YEAR_RANGE,
    RESULTS_BASE_DIR,
    TIMESTAMP_FORMAT,
)

__all__ = [
    # Service
    "run_wayback_diff",
    "run_snapshot_diff",
    # Validation
    "sanitize_domain",
    "validate_date_range",
    "validate_snapshot_list",
    "DomainValidationError",
    "DateValidationError",
    # Storage
    "ResultsManager",
    "IndexManager",
    "MetadataManager",
    "save_html_diff",
    "save_structured_diff",
    # Analysis
    "fetch_snapshot_list",
    "fetch_selected_snapshots",
    "extract_security_surface",
    "compute_surface_diff",
    "clean_html",
    # Config
    "MAX_DOMAIN_LENGTH",
    "MAX_LABEL_LENGTH",
    "MAX_YEAR_RANGE",
    "RESULTS_BASE_DIR",
    "TIMESTAMP_FORMAT",
]
