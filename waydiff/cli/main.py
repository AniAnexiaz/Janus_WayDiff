"""
Main CLI interface for Janus Diff.

Handles command routing for:
- wayback: Analyze Wayback Machine snapshots vs live
- diff: Compare specific snapshots against live
- localsnap: Capture and compare local snapshots
- config: Manage tool configuration
"""

import sys
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from waydiff.cli.banner import (
    display_banner, display_run_header, display_usage, display_short_usage,
    print_section, print_success, print_error, print_info, print_warning
)
from waydiff.cli.validator import (
    validate_domain, validate_url, validate_date, validate_date_range,
    validate_snapshot_file, validate_argument_combination
)
from waydiff.cli.config_manager import ConfigManager
from waydiff.core.service import run_wayback_diff, run_snapshot_diff

logger = logging.getLogger(__name__)


class JanusDiffCLI:
    """Main CLI handler for Janus Diff."""

    def __init__(self, show_banner=True):
        self.show_banner = show_banner
        self.config = ConfigManager()
        self.args = None

    # ==========================================================
    # PARSER
    # ==========================================================

    def create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser with subcommands."""

        parser = argparse.ArgumentParser(
            prog="janus_diff.py",
            description="Janus WayDiff - Attack Surface Intelligence Tool",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            add_help=False,  # We handle help manually to integrate the banner
        )

        # Global options
        parser.add_argument("--no-banner", action="store_true",
                            help="Suppress banner and run header")
        parser.add_argument("--help", "-h", action="store_true",
                            help="Show full help and usage reference")
        parser.add_argument("--version", action="store_true",
                            help="Show version information")
        parser.add_argument("-v", "--verbose", action="count", default=0,
                            help="Verbose output (-v for info, -vv for debug)")

        subparsers = parser.add_subparsers(dest="command", help="Command to execute")

        # ===== WAYBACK =====
        wayback = subparsers.add_parser(
            "wayback",
            help="Fetch Wayback snapshots and diff against live site",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="""
Analyze attack surface drift by comparing Wayback Machine snapshots with the live site.

USAGE
  python janus_diff.py wayback <domain> [options]

EXAMPLES
  python janus_diff.py wayback example.com
  python janus_diff.py wayback example.com --start 2021-01-01 --end 2024-06-01
  python janus_diff.py wayback example.com --llm local --url http://localhost:11434
  python janus_diff.py wayback example.com --llm online --api sk-...
  python janus_diff.py wayback example.com -o /tmp/results -vv
"""
        )
        wayback.add_argument("domain",
                             help="Target domain (e.g., example.com). http[s]:// stripped automatically.")
        wayback.add_argument("--start", metavar="DATE",
                             help="Start date (YYYY-MM-DD, default: 2 years ago)")
        wayback.add_argument("--end", metavar="DATE",
                             help="End date   (YYYY-MM-DD, default: today)")
        wayback.add_argument("--llm", choices=["local", "online", "none"],
                             help="Add LLM report on top of the rule-based report (optional)")
        wayback.add_argument("--url", metavar="URL",
                             help="Ollama endpoint (required with --llm local)")
        wayback.add_argument("--api", metavar="KEY",
                             help="OpenAI API key  (required with --llm online)")
        wayback.add_argument("--output", "-o", type=Path, default=Path("results"),
                             metavar="DIR", help="Output directory (default: results/)")
        wayback.add_argument("-v", "--verbose", action="count", default=0,
                             help="Verbose output (-v for info, -vv for debug)")
        wayback.set_defaults(func=self.cmd_wayback)

        # ===== DIFF =====
        diff = subparsers.add_parser(
            "diff",
            help="Re-run diff on snapshots from a previous wayback analysis",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="""
Compare specific Wayback snapshots (from a previous `wayback` run) against the live site.
Reference snapshots by the numbers shown in index.txt inside the results folder.

USAGE
  python janus_diff.py diff <results-folder> <selection> [options]

SNAPSHOT SELECTION  (exactly one required)
  --pick  N [N ...]   Specific snapshot numbers (e.g., --pick 1 42 487)
  --earliest          Earliest snapshot in the index
  --latest            Latest snapshot in the index
  --all               Every snapshot in the index
  --interactive, -i   Browse and select interactively
  --file  PATH        Load snapshot numbers from a list file

EXAMPLES
  python janus_diff.py diff results/example.com/20240109_153000_abc123 --pick 1
  python janus_diff.py diff results/example.com/20240109_153000_abc123 --pick 1 42 487
  python janus_diff.py diff results/example.com/20240109_153000_abc123 --earliest
  python janus_diff.py diff results/example.com/20240109_153000_abc123 --all --llm local --url http://localhost:11434
"""
        )
        diff.add_argument(
            "results_folder",
            help="Path to a previous wayback results directory"
        )
        snap_select = diff.add_mutually_exclusive_group(required=True)
        snap_select.add_argument("--pick", type=int, nargs="+", metavar="N",
                                 help="Snapshot numbers to compare")
        snap_select.add_argument("--interactive", "-i", action="store_true",
                                 help="Interactive snapshot selection")
        snap_select.add_argument("--earliest", action="store_true",
                                 help="Compare the earliest snapshot")
        snap_select.add_argument("--latest", action="store_true",
                                 help="Compare the latest snapshot")
        snap_select.add_argument("--all", action="store_true",
                                 help="Compare all snapshots")
        snap_select.add_argument("--file", type=Path, metavar="PATH",
                                 help="Custom snapshot list file")
        diff.add_argument("--llm", choices=["local", "online", "none"],
                          help="Add LLM report on top of the rule-based report (optional)")
        diff.add_argument("--url", metavar="URL",
                          help="Ollama endpoint (required with --llm local)")
        diff.add_argument("--api", metavar="KEY",
                          help="OpenAI API key  (required with --llm online)")
        diff.add_argument("--output", "-o", type=Path, default=Path("results"),
                          metavar="DIR", help="Output directory (default: results/)")
        diff.add_argument("-v", "--verbose", action="count", default=0,
                          help="Verbose output (-v for info, -vv for debug)")
        diff.set_defaults(func=self.cmd_diff)

        # ===== LOCALSNAP =====
        localsnap = subparsers.add_parser(
            "localsnap",
            help="Capture and compare snapshots of internal or external URLs",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="""
Capture snapshots of any URL (internal admin panels, staging sites, etc.)
and compare them over time to detect attack surface changes.

SUBCOMMANDS
  capture <url>   Capture a new snapshot
  compare         Compare two existing snapshots

EXAMPLES
  python janus_diff.py localsnap capture https://internal.company.com/admin
  python janus_diff.py localsnap capture https://staging.company.com --name pre-release-v2
  python janus_diff.py localsnap compare --snap-a results/.../snap1 --snap-b results/.../snap2
"""
        )
        localsnap_sub = localsnap.add_subparsers(dest="localsnap_action")

        # capture
        capture = localsnap_sub.add_parser(
            "capture",
            help="Capture a snapshot of a URL",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="""
Fetch and save a full snapshot of any URL for later comparison.

USAGE
  python janus_diff.py localsnap capture <url> [options]

EXAMPLES
  python janus_diff.py localsnap capture https://internal.company.com/admin
  python janus_diff.py localsnap capture https://staging.company.com --name pre-release-v2
"""
        )
        capture.add_argument("url",
                             help="URL to snapshot (must include http:// or https://)")
        capture.add_argument("--name", metavar="LABEL",
                             help="Snapshot label for easy reference (default: timestamp)")
        capture.add_argument("--output", "-o", type=Path, default=Path("results"),
                             metavar="DIR", help="Output directory (default: results/)")
        capture.add_argument("-v", "--verbose", action="count", default=0,
                             help="Verbose output (-v for info, -vv for debug)")
        capture.set_defaults(func=self.cmd_localsnap_capture)

        # compare
        compare = localsnap_sub.add_parser(
            "compare",
            help="Compare two local snapshots",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="""
Compare two snapshots previously created with `localsnap capture`.

USAGE
  python janus_diff.py localsnap compare --snap-a <path> --snap-b <path> [options]

EXAMPLES
  python janus_diff.py localsnap compare \\
      --snap-a results/domain/run1/snapshots/snap1 \\
      --snap-b results/domain/run2/snapshots/snap2

  python janus_diff.py localsnap compare \\
      --snap-a results/domain/run1/snapshots/snap1 \\
      --snap-b results/domain/run2/snapshots/snap2 \\
      --llm local --url http://localhost:11434
"""
        )
        compare.add_argument("--snap-a", type=Path, required=True, metavar="PATH",
                             help="Path to first  snapshot directory")
        compare.add_argument("--snap-b", type=Path, required=True, metavar="PATH",
                             help="Path to second snapshot directory")
        compare.add_argument("--llm", choices=["local", "online", "none"],
                             help="Add LLM report on top of the rule-based report (optional)")
        compare.add_argument("--url", metavar="URL",
                             help="Ollama endpoint (required with --llm local)")
        compare.add_argument("--api", metavar="KEY",
                             help="OpenAI API key  (required with --llm online)")
        compare.add_argument("--output", "-o", type=Path, default=Path("results"),
                             metavar="DIR", help="Output directory (default: results/)")
        compare.add_argument("-v", "--verbose", action="count", default=0,
                             help="Verbose output (-v for info, -vv for debug)")
        compare.set_defaults(func=self.cmd_localsnap_compare)

        # ===== CONFIG =====
        config = subparsers.add_parser(
            "config",
            help="Manage persistent tool configuration (~/.janus/config.json)",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="""
Save LLM settings persistently so --llm, --url, and --api don't need to be
passed on every run. Configuration is stored in ~/.janus/config.json.

SUBCOMMANDS
  llm    Configure the LLM backend
  show   Display current saved configuration

EXAMPLES
  python janus_diff.py config llm --type local --url http://localhost:11434
  python janus_diff.py config llm --type local --url http://localhost:11434 --model llama3
  python janus_diff.py config llm --type online --api sk-... --model gpt-4o
  python janus_diff.py config show
"""
        )
        config_sub = config.add_subparsers(dest="config_action")

        llm_config = config_sub.add_parser(
            "llm",
            help="Configure the LLM backend",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="""
Persist LLM configuration to ~/.janus/config.json.

EXAMPLES
  python janus_diff.py config llm --type local --url http://localhost:11434
  python janus_diff.py config llm --type local --url http://localhost:11434 --model llama3
  python janus_diff.py config llm --type online --api sk-... --model gpt-4o
"""
        )
        llm_config.add_argument("--type", choices=["local", "online"], required=True,
                                help="LLM backend: local (Ollama) or online (OpenAI)")
        llm_config.add_argument("--url", metavar="URL",
                                help="Ollama endpoint (required when --type local)")
        llm_config.add_argument("--api", metavar="KEY",
                                help="OpenAI API key  (required when --type online)")
        llm_config.add_argument("--model", metavar="NAME",
                                help="Model name (default: mistral / gpt-4)")
        llm_config.set_defaults(func=self.cmd_config_llm)

        show_config = config_sub.add_parser("show", help="Display current saved configuration")
        show_config.set_defaults(func=self.cmd_config_show)

        return parser

    # ==========================================================
    # ARGUMENT PARSING & HELP ROUTING
    # ==========================================================

    def parse_args(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """
        Parse arguments and handle all help/banner routing.

        Behaviour matrix:
          No args                  → full banner + short usage, exit
          --no-banner (no command) → silent exit
          -h / --help              → full banner + full usage, exit
          --no-banner -h           → full usage only (no banner), exit
          --version                → version string, exit
          Valid command            → return parsed args for execution
        """
        parser = self.create_parser()
        parsed = parser.parse_args(args)

        if parsed.version:
            print(f"Janus Diff v1.0.0")
            sys.exit(0)

        no_banner = parsed.no_banner
        no_command = parsed.command is None

        if parsed.help:
            if not no_banner:
                display_banner()
            display_usage()
            sys.exit(0)

        if no_command:
            if no_banner:
                # --no-banner with no command: do nothing, exit cleanly
                sys.exit(0)
            display_banner()
            display_short_usage()
            sys.exit(0)

        return parsed

    # ==========================================================
    # LOGGING SETUP
    # ==========================================================

    def setup_logging(self):
        """Configure logging level based on verbosity flags."""
        root = logging.getLogger()
        root.handlers.clear()  # Remove any pre-existing handlers (e.g. from basicConfig)
        root.setLevel(logging.DEBUG)  # Always capture everything at root level

        # Console handler — level controlled by -v flags
        console = logging.StreamHandler()
        if self.args.verbose == 0:
            console.setLevel(logging.WARNING)   # quiet — warnings and errors only
        elif self.args.verbose == 1:
            console.setLevel(logging.INFO)      # -v  : progress messages
        else:
            console.setLevel(logging.DEBUG)     # -vv : full debug trace
        console.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(console)

    # ==========================================================
    # COMMAND HANDLERS
    # ==========================================================

    def cmd_wayback(self):
        """Handle wayback command."""
        if self.show_banner:
            display_run_header("wayback")
        print_section("Wayback Machine Analysis")

        try:
            domain = validate_domain(self.args.domain)
            print_info(f"Domain: {domain}")

            if self.args.start or self.args.end:
                # If either is provided, both are required and must be valid
                if not self.args.start:
                    raise ValueError("--end requires --start to also be set")
                if not self.args.end:
                    raise ValueError("--start requires --end to also be set")
                start_date, end_date = validate_date_range(self.args.start, self.args.end)
                print_info(f"Date range: {start_date} to {end_date}")
            else:
                today = datetime.now()
                two_years_ago = today - timedelta(days=365 * 2)
                start_date = two_years_ago.strftime("%Y-%m-%d")
                end_date = today.strftime("%Y-%m-%d")
                print_info(f"Date range (last 2 years): {start_date} to {end_date}")

            print_info("Fetching Wayback snapshots...")

            llm_backend = self.args.llm or "none"
            success = run_wayback_diff(
                domain=domain,
                start_date=start_date,
                end_date=end_date,
                output_dir=str(self.args.output),
                llm_backend=llm_backend,
                verbose=self.args.verbose > 0
            )

            if success:
                print_success("Analysis complete")
            else:
                print_error("Analysis failed — check logs for details")
                sys.exit(1)

        except Exception as e:
            print_error(str(e))
            sys.exit(1)

    def cmd_diff(self):
        """Handle diff command."""
        if self.show_banner:
            display_run_header("diff")
        print_section("Snapshot Diff Analysis")

        try:
            results_path = Path(self.args.results_folder)
            if not results_path.exists():
                raise ValueError(f"Results folder not found: {results_path}")

            index_file = results_path / "index.txt"
            if not index_file.exists():
                raise ValueError(
                    f"No snapshot index found in {results_path}/\n"
                    f"  Run `wayback` first to generate an index, then use `diff` to re-analyse."
                )

            print_info(f"Results folder: {results_path}")

            # Resolve snapshot numbers from selection flags
            import json as _json
            if self.args.pick:
                snapshot_numbers = self.args.pick
                print_info(f"Selected snapshots: {', '.join(map(str, snapshot_numbers))}")
            elif self.args.interactive:
                print_error("Interactive selection is not yet implemented")
                sys.exit(1)
            elif self.args.earliest:
                snapshot_numbers = [1]
                print_info("Selected: earliest snapshot")
            elif self.args.latest:
                with open(results_path / "index.json") as _f:
                    _idx = _json.load(_f)
                snapshot_numbers = [_idx["total"]]
                print_info("Selected: latest snapshot")
            elif self.args.all:
                with open(results_path / "index.json") as _f:
                    _idx = _json.load(_f)
                snapshot_numbers = list(range(1, _idx["total"] + 1))
                print_info(f"Selected: all {len(snapshot_numbers)} snapshots")
            elif self.args.file:
                validate_snapshot_file(self.args.file)
                with open(self.args.file) as _f:
                    snapshot_numbers = [
                        int(line.strip())
                        for line in _f
                        if line.strip().isdigit()
                    ]
                print_info(f"Using snapshot list: {self.args.file}")

            llm_backend = self.args.llm or "none"
            success = run_snapshot_diff(
                results_folder=str(results_path),
                snapshot_numbers=snapshot_numbers,
                output_dir=str(self.args.output),
                llm_backend=llm_backend,
                verbose=self.args.verbose > 0
            )

            if success:
                print_success("Diff analysis complete")
            else:
                print_error("Diff analysis failed — check logs for details")
                sys.exit(1)

        except Exception as e:
            print_error(str(e))
            sys.exit(1)

    def cmd_localsnap_capture(self):
        """Handle localsnap capture command."""
        if self.show_banner:
            display_run_header("localsnap capture")
        print_section("Local Snapshot Capture")

        try:
            url = validate_url(self.args.url)
            print_info(f"Target: {url}")

            if self.args.name:
                print_info(f"Snapshot name: {self.args.name}")

            print_info("Capturing snapshot...")

            import asyncio as _asyncio
            from waydiff.localsnap.snapshot import take_snapshot
            snapshot_dir = _asyncio.run(take_snapshot(
                url=url,
                output_dir=str(self.args.output),
                name=self.args.name,
                verbose=self.args.verbose > 0
            ))

            if snapshot_dir:
                print_success(f"Snapshot saved: {snapshot_dir}")
            else:
                print_error("Snapshot capture failed — check logs for details")
                sys.exit(1)

        except Exception as e:
            print_error(str(e))
            sys.exit(1)

    def cmd_localsnap_compare(self):
        """Handle localsnap compare command."""
        if self.show_banner:
            display_run_header("localsnap compare")
        print_section("Local Snapshot Comparison")

        try:
            if not self.args.snap_a.exists():
                raise ValueError(
                    f"Snapshot A not found: {self.args.snap_a}\n"
                    f"  Use `localsnap capture` to create a snapshot first."
                )
            if not self.args.snap_b.exists():
                raise ValueError(
                    f"Snapshot B not found: {self.args.snap_b}\n"
                    f"  Use `localsnap capture` to create a snapshot first."
                )

            print_info(f"Snapshot A: {self.args.snap_a}")
            print_info(f"Snapshot B: {self.args.snap_b}")


            from waydiff.localsnap.snapshot_diff import compare_snapshots
            llm_backend = self.args.llm or "none"
            result = compare_snapshots(
                snap_a_path=str(self.args.snap_a),
                snap_b_path=str(self.args.snap_b),
                output_dir=str(self.args.output),
                llm_backend=llm_backend,
                verbose=self.args.verbose > 0
            )

            if result:
                print_success("Snapshot comparison complete")
            else:
                print_error("Snapshot comparison failed — check logs for details")
                sys.exit(1)

        except Exception as e:
            print_error(str(e))
            sys.exit(1)

    def cmd_config_llm(self):
        """Handle config llm command."""
        if self.show_banner:
            display_run_header("config")
        print_section("LLM Configuration")

        try:
            if self.args.type == "local":
                if not self.args.url:
                    raise ValueError(
                        "--url is required when --type local\n"
                        "  Example: --type local --url http://localhost:11434"
                    )
                self.config.set_llm_local(self.args.url, self.args.model)
                model = self.args.model or "mistral"
                print_success(f"Local LLM configured: {self.args.url}  (model: {model})")

            elif self.args.type == "online":
                if not self.args.api:
                    raise ValueError(
                        "--api is required when --type online\n"
                        "  Example: --type online --api sk-..."
                    )
                self.config.set_llm_online(self.args.api, self.args.model)
                model = self.args.model or "gpt-4"
                print_success(f"Online LLM configured: OpenAI  (model: {model})")

            print_info(f"Saved to: {self.config.config_path}")

        except Exception as e:
            print_error(str(e))
            sys.exit(1)

    def cmd_config_show(self):
        """Handle config show command."""
        if self.show_banner:
            display_run_header("config")
        print_section("Current Configuration")

        try:
            config = self.config.load()
            if not config:
                print_info("No configuration saved yet.")
                print_info("Run `config llm` to set up your LLM backend.")
            else:
                print_info(f"Config file: {self.config.config_path}")
                print()
                for key, value in config.items():
                    if key == "llm" and isinstance(value, dict):
                        print_info(f"LLM type  : {value.get('type', 'not set')}")
                        print_info(f"LLM model : {value.get('model', 'not set')}")
                        if value.get("url"):
                            print_info(f"LLM url   : {value['url']}")
                        if value.get("api_key"):
                            print_info(f"LLM api   : {'*' * 8}... (set)")
                    else:
                        print_info(f"{key}: {value}")

        except Exception as e:
            print_error(str(e))
            sys.exit(1)

    # ==========================================================
    # HELPERS
    # ==========================================================

    @staticmethod
    def _validate_llm_args(llm_type: str, url: Optional[str], api: Optional[str]):
        """Validate LLM argument combinations."""
        if llm_type == "local" and not url:
            raise ValueError(
                "--llm local requires --url\n"
                "  Example: --llm local --url http://localhost:11434"
            )
        if llm_type == "online" and not api:
            raise ValueError(
                "--llm online requires --api\n"
                "  Example: --llm online --api sk-..."
            )

    # ==========================================================
    # ENTRY POINT
    # ==========================================================

    def run(self, args: Optional[List[str]] = None):
        """Parse arguments and execute the requested command."""

        self.args = self.parse_args(args)

        if self.args.no_banner:
            self.show_banner = False

        self.setup_logging()

        # Validate LLM argument combinations for commands that expose --llm
        if hasattr(self.args, "llm") and self.args.llm:
            try:
                self._validate_llm_args(
                    self.args.llm,
                    getattr(self.args, "url", None),
                    getattr(self.args, "api", None)
                )
            except ValueError as e:
                print_error(str(e))
                sys.exit(1)

        if hasattr(self.args, "func"):
            self.args.func()
        else:
            # Safety fallback — parse_args() should have handled this already
            if self.show_banner:
                display_banner()
            display_short_usage()


def cli_main():
    """Entry point for CLI."""
    cli = JanusDiffCLI()
    cli.run()


if __name__ == "__main__":
    cli_main()
