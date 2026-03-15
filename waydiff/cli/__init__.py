"""
CLI layer for Janus Diff.

Provides command-line interface with:
- Argument parsing (argparse subcommands)
- Banner and styling
- Input validation
- Configuration management
"""

from .main import cli_main, JanusDiffCLI
from .banner import display_banner, print_section, print_success, print_error, print_info
from .validator import (
    validate_domain, validate_url, validate_date, validate_date_range,
    validate_snapshot_file, wayback_to_user
)
from .config_manager import ConfigManager

__all__ = [
    "cli_main",
    "JanusDiffCLI",
    "display_banner",
    "print_section",
    "print_success",
    "print_error",
    "print_info",
    "validate_domain",
    "validate_url",
    "validate_date",
    "validate_date_range",
    "validate_snapshot_file",
    "wayback_to_user",
    "ConfigManager",
]
