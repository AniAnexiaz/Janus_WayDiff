"""
Janus WayDiff - Attack Surface Intelligence Tool
Root entrypoint
"""

import sys
import logging
from pathlib import Path

# --- FIX 1: Ensure project root is in Python path ---
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point with error handling."""
    try:
        from waydiff.cli.main import cli_main
        cli_main()

    except ImportError as e:
        print("✗ Error: Failed to import WayDiff modules")
        print(f"  Details: {e}")
        print("\nMake sure WayDiff is properly installed:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠ Analysis interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.exception("Fatal error occurred")
        print(f"\n✗ Unexpected error: {e}")
        print("\nFor debugging run:")
        print("  python janus_diff.py -vv")
        sys.exit(1)


if __name__ == "__main__":
    main()