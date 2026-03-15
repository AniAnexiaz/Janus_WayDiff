"""
Local snapshot module for Janus Diff.

Provides functionality to:
- Capture snapshots of URLs (internal/external domains)
- Compare two local snapshots
- Generate diffs and security reports

Usage:
    # Capture snapshot
    import asyncio
    from waydiff.localsnap import take_snapshot
    
    asyncio.run(take_snapshot("https://internal.local/admin", name="v1.0"))
    
    # Compare snapshots
    from waydiff.localsnap import compare_snapshots
    
    compare_snapshots(
        snap_a_path="results/domain/timestamp_id/snapshots/v1.0_time",
        snap_b_path="results/domain/timestamp_id/snapshots/v1.1_time"
    )
"""

from .snapshot import take_snapshot, load_snapshot, list_snapshots
from .snapshot_diff import compare_snapshots, find_latest_snapshots

__all__ = [
    "take_snapshot",
    "load_snapshot",
    "list_snapshots",
    "compare_snapshots",
    "find_latest_snapshots",
]
