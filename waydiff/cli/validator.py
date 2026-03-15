"""
Argument and input validation for Janus Diff.
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional


# Constants
DOMAIN_REGEX = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
URL_REGEX = r'^https?://[^\s/$.?#].[^\s]*$'


class ValidationError(Exception):
    """Custom validation error."""
    pass


def validate_domain(domain: str) -> str:
    """
    Validate domain format.
    
    Args:
        domain: Domain name (e.g., example.com)
    
    Returns:
        Validated domain
    
    Raises:
        ValidationError: If domain format is invalid
    """
    domain = domain.strip().lower()
    
    if not domain:
        raise ValidationError("Domain cannot be empty")
    
    # Remove http[s]:// if present
    if domain.startswith("http://"):
        domain = domain[7:]
    elif domain.startswith("https://"):
        domain = domain[8:]
    
    # Remove path if present
    if "/" in domain:
        domain = domain.split("/")[0]
    
    # Validate format
    if not re.match(DOMAIN_REGEX, domain):
        raise ValidationError(f"Invalid domain format: {domain}")
    
    return domain


def validate_url(url: str) -> str:
    """
    Validate URL format.
    
    Args:
        url: Full URL (e.g., https://example.com/path)
    
    Returns:
        Validated URL
    
    Raises:
        ValidationError: If URL format is invalid
    """
    url = url.strip()
    
    if not url:
        raise ValidationError("URL cannot be empty")
    
    if not re.match(URL_REGEX, url):
        raise ValidationError(f"Invalid URL format: {url}")
    
    # Must start with http:// or https://
    if not url.startswith(("http://", "https://")):
        raise ValidationError("URL must start with http:// or https://")
    
    return url


def validate_date(date_str: str, label: str = "date") -> str:
    """
    Validate date format (YYYY-MM-DD).
    
    Args:
        date_str: Date string
        label: Label for error messages
    
    Returns:
        Validated date string
    
    Raises:
        ValidationError: If date format is invalid
    """
    try:
        # Parse to validate
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise ValidationError(
            f"Invalid {label} format: {date_str}\n"
            f"Expected format: YYYY-MM-DD (e.g., 2024-01-09)"
        )


def validate_date_range(start_str: str, end_str: str) -> Tuple[str, str]:
    """
    Validate date range.
    
    Args:
        start_str: Start date (YYYY-MM-DD)
        end_str: End date (YYYY-MM-DD)
    
    Returns:
        Tuple of (start_date, end_date)
    
    Raises:
        ValidationError: If dates are invalid or range is invalid
    """
    # Validate formats
    start_date = validate_date(start_str, "--start")
    end_date = validate_date(end_str, "--end")
    
    # Parse for comparison
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Validate range logic
    if start > end:
        raise ValidationError(
            f"Invalid date range: --start ({start_date}) is after --end ({end_date})"
        )
    
    # Warn if range is very small
    diff = (end - start).days
    if diff == 0:
        raise ValidationError("Start and end dates cannot be the same")
    
    return start_date, end_date


def validate_snapshot_file(filepath: Path) -> Path:
    """
    Validate snapshot list file exists and is readable.
    
    Args:
        filepath: Path to snapshot list file
    
    Returns:
        Validated filepath
    
    Raises:
        ValidationError: If file doesn't exist or can't be read
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise ValidationError(f"Snapshot list file not found: {filepath}")
    
    if not filepath.is_file():
        raise ValidationError(f"Not a file: {filepath}")
    
    if not filepath.readable():
        raise ValidationError(f"Cannot read file: {filepath}")
    
    return filepath


def validate_snapshot_count(snapshots: list, max_count: int = 100) -> None:
    """
    Validate snapshot list doesn't exceed maximum.
    
    Args:
        snapshots: List of snapshots
        max_count: Maximum allowed snapshots (default: 100)
    
    Raises:
        ValidationError: If count exceeds maximum
    """
    if len(snapshots) > max_count:
        raise ValidationError(
            f"Snapshot list exceeds maximum of {max_count} entries "
            f"(found {len(snapshots)})"
        )


def validate_snapshot_numbers(numbers: list, max_snapshots: int) -> list:
    """
    Validate snapshot numbers are valid.
    
    Args:
        numbers: List of snapshot numbers
        max_snapshots: Total available snapshots
    
    Returns:
        Validated numbers (deduplicated, sorted)
    
    Raises:
        ValidationError: If any numbers are invalid
    """
    if not numbers:
        raise ValidationError("No snapshots selected")
    
    # Check range
    for num in numbers:
        if num < 1 or num > max_snapshots:
            raise ValidationError(
                f"Snapshot number {num} out of range (1-{max_snapshots})"
            )
    
    # Deduplicate and sort
    return sorted(list(set(numbers)))


def validate_results_folder(folder_path: str) -> Path:
    """
    Validate results folder from previous analysis.
    
    Args:
        folder_path: Path to results folder
    
    Returns:
        Validated folder path
    
    Raises:
        ValidationError: If folder doesn't exist or is invalid
    """
    folder = Path(folder_path)
    
    if not folder.exists():
        raise ValidationError(f"Results folder not found: {folder}")
    
    if not folder.is_dir():
        raise ValidationError(f"Not a directory: {folder}")
    
    # Check for index file
    index = folder / "index.txt"
    if not index.exists():
        raise ValidationError(
            f"No snapshot index found in {folder}/\n"
            f"Missing: {index}"
        )
    
    return folder


def validate_argument_combination(args) -> None:
    """
    Validate that argument combination is valid.
    
    Args:
        args: Parsed arguments namespace
    
    Raises:
        ValidationError: If combination is invalid
    """
    # Validate LLM arguments
    if args.llm == "local" and not args.url:
        raise ValidationError(
            "--llm local requires --url argument\n"
            "Example: --llm local --url http://localhost:11434"
        )
    
    if args.llm == "online" and not args.api:
        raise ValidationError(
            "--llm online requires --api argument\n"
            "Example: --llm online --api sk-..."
        )


def wayback_to_user(timestamp: str) -> str:
    """
    Convert Wayback timestamp to human-readable date.
    
    Args:
        timestamp: Wayback timestamp (YYYYMMDDHHMMSS)
    
    Returns:
        Human-readable date string
    """
    try:
        dt = datetime.strptime(timestamp, "%Y%m%d%H%M%S")
        return dt.strftime("%B %d, %Y %H:%M")
    except (ValueError, TypeError):
        return timestamp
