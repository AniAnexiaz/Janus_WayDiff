"""
Janus Diff - Attack Surface Security Analysis Tool.

A comprehensive security tool that:
1. Analyzes Wayback Machine snapshots to detect attack surface drift
2. Compares internal domain snapshots over time
3. Identifies security risks: new endpoints, inputs, scripts, headers
4. Provides rule-based and AI-powered security recommendations

Quick Start:
    # Analyze Wayback snapshots
    $ python janus_diff.py wayback example.com --start 2022-01-01 --end 2024-01-09
    
    # Compare specific snapshots by number
    $ python janus_diff.py diff results/example.com/* --pick 1 42 487
    
    # Capture internal domain snapshot
    $ python janus_diff.py localsnap capture https://internal.local/admin --name "v1.0"
    
    # Compare two snapshots
    $ python janus_diff.py localsnap compare --snap-a snap1_path --snap-b snap2_path
    
    # Configure LLM backend
    $ python janus_diff.py config llm --type local --url http://localhost:11434

Modules:
    - cli: Command-line interface with subcommands
    - core: Security analysis engine (validation, fetching, extraction, diffing)
    - intelligence: AI-powered and rule-based security reporting
    - localsnap: Local/internal domain snapshot capture and comparison

Documentation:
    For detailed usage, run: python janus_diff.py --help
"""

__version__ = "0.1.0"
__author__ = "Kels1er"
__license__ = "MIT"

# Import main CLI entry point
from .cli import cli_main, JanusDiffCLI

# Import core functionality
from .core import (
    run_wayback_diff,
    run_snapshot_diff,
    sanitize_domain,
    validate_date_range,
    validate_snapshot_list,
    ResultsManager,
    IndexManager,
    MetadataManager,
)

# Import intelligence
from .intelligence import (
    generate_security_report,
    generate_llm_report,
)

# Import local snapshots
from .localsnap import (
    take_snapshot,
    load_snapshot,
    list_snapshots,
    compare_snapshots,
    find_latest_snapshots,
)

__all__ = [
    # Version
    "__version__",
    "__author__",
    "__license__",
    
    # CLI
    "cli_main",
    "JanusDiffCLI",
    
    # Core analysis
    "run_wayback_diff",
    "run_snapshot_diff",
    
    # Validation
    "sanitize_domain",
    "validate_date_range",
    "validate_snapshot_list",
    
    # Storage & Management
    "ResultsManager",
    "IndexManager",
    "MetadataManager",
    
    # Intelligence
    "generate_security_report",
    "generate_llm_report",
    
    # Local Snapshots
    "take_snapshot",
    "load_snapshot",
    "list_snapshots",
    "compare_snapshots",
    "find_latest_snapshots",
]
