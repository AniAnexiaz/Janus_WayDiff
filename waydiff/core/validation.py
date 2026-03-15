"""
Validation and sanitization utilities for Janus Diff core.

Core-level validation focuses on:
- Defensive domain sanitization (expects potentially malformed input)
- Internal date handling (YYYYMMDD format for Wayback API)
- Snapshot data validation
- Security surface validation

Note: CLI-level validation (user input) is in waydiff/cli/validator.py
      This module handles core/internal validation only.
"""

import re
from datetime import datetime
from typing import Tuple

from .config import MAX_DOMAIN_LENGTH, MAX_LABEL_LENGTH, MAX_YEAR_RANGE


# ==========================================================
# DOMAIN VALIDATION & SANITIZATION
# ==========================================================

class DomainValidationError(ValueError):
    """Raised when domain validation fails."""
    pass


def sanitize_domain(domain: str) -> str:
    """
    Sanitize and validate domain for internal processing.
    
    Defensive approach: cleans up the input, fixes what it can,
    and validates the result.
    
    Args:
        domain: Domain string (may be malformed)
    
    Returns:
        Cleaned, validated domain
    
    Raises:
        DomainValidationError: If domain cannot be sanitized
    
    Examples:
        >>> sanitize_domain("example.com")
        'example.com'
        >>> sanitize_domain("EXAMPLE.COM")
        'example.com'
        >>> sanitize_domain("https://example.com/path")
        'example.com'
        >>> sanitize_domain("user@example.com:443")
        'example.com'
    """
    if not isinstance(domain, str):
        raise DomainValidationError("Domain must be a string")
    
    domain = domain.strip().lower()
    
    if not domain:
        raise DomainValidationError("Domain cannot be empty")
    
    # Reject control characters
    if any(ord(c) < 32 for c in domain):
        raise DomainValidationError("Domain contains invalid characters")
    
    # Reject multiple protocol declarations (indicates injection attempt)
    if domain.count("http://") + domain.count("https://") > 1:
        raise DomainValidationError("Domain contains multiple protocols")
    
    # Remove protocol if present
    domain = re.sub(r"^https?://", "", domain)
    
    # Reject newlines (injection attempt)
    if "\n" in domain or "\r" in domain:
        raise DomainValidationError("Domain contains newlines")
    
    # Remove userinfo (user@domain) - keep domain part only
    if "@" in domain:
        domain = domain.split("@")[-1]
    
    # Remove port number if present
    if ":" in domain:
        domain = domain.split(":")[0]
    
    # Remove path if present (keep domain only)
    if "/" in domain:
        domain = domain.split("/")[0]
    
    # Remove invalid characters, keep alphanumeric, dots, hyphens
    domain = re.sub(r"[^a-z0-9.-]", "", domain)
    
    # Collapse multiple dots, strip leading/trailing dots
    domain = re.sub(r"\.+", ".", domain).strip(".")
    
    # Validate minimum domain structure (must have at least one dot)
    if not domain or "." not in domain:
        raise DomainValidationError("Invalid domain (must contain at least one dot)")
    
    # Reject bare IP addresses
    if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", domain):
        raise DomainValidationError("IP addresses are not valid domains")
    
    # Validate total length
    if len(domain) > MAX_DOMAIN_LENGTH:
        raise DomainValidationError(f"Domain too long (max {MAX_DOMAIN_LENGTH} chars)")
    
    # Validate each label (part between dots)
    for label in domain.split("."):
        if not label:
            raise DomainValidationError("Domain contains empty labels")
        
        if len(label) > MAX_LABEL_LENGTH:
            raise DomainValidationError(f"Domain label too long (max {MAX_LABEL_LENGTH} chars)")
        
        # Labels cannot start or end with hyphens
        if label.startswith("-") or label.endswith("-"):
            raise DomainValidationError("Domain labels cannot start or end with hyphens")
    
    return domain


# ==========================================================
# DATE VALIDATION & PARSING
# ==========================================================

class DateValidationError(ValueError):
    """Raised when date validation fails."""
    pass


def parse_date(date_str: str) -> datetime:
    """
    Parse date string flexibly (internal helper).
    
    Accepts multiple formats and converts to datetime.
    Used internally for date processing.
    
    Args:
        date_str: Date string (various formats)
    
    Returns:
        Parsed datetime object
    
    Raises:
        DateValidationError: If date cannot be parsed
    
    Examples:
        >>> parse_date("2022-01-15")
        datetime.datetime(2022, 1, 15, 0, 0)
        >>> parse_date("20220115")
        datetime.datetime(2022, 1, 15, 0, 0)
        >>> parse_date("2022-01-15 14:30:00")
        datetime.datetime(2022, 1, 15, 14, 30)
    """
    if not isinstance(date_str, str):
        date_str = str(date_str)
    
    date_str = date_str.strip()
    
    if not date_str:
        raise DateValidationError("Date string cannot be empty")
    
    # Remove dashes to normalize
    normalized = date_str.replace("-", "")
    
    # Try to extract YYYYMMDD from normalized string
    match = re.search(r"(\d{8})", normalized)
    if not match:
        raise DateValidationError(
            f"Cannot extract date from: {date_str}\n"
            f"Expected format: YYYY-MM-DD or YYYYMMDD"
        )
    
    yyyymmdd = match.group(1)
    
    try:
        return datetime.strptime(yyyymmdd, "%Y%m%d")
    except ValueError as e:
        raise DateValidationError(f"Invalid date: {yyyymmdd}") from e


def validate_date_range(start_str: str, end_str: str) -> Tuple[str, str]:
    """
    Validate and normalize date range for internal processing.
    
    Returns dates in YYYYMMDD format (Wayback Machine API format).
    
    Args:
        start_str: Start date (flexible format)
        end_str: End date (flexible format)
    
    Returns:
        Tuple of (start_yyyymmdd, end_yyyymmdd)
    
    Raises:
        DateValidationError: If dates are invalid or range is invalid
    
    Examples:
        >>> validate_date_range("2022-01-01", "2024-01-09")
        ('20220101', '20240109')
        >>> validate_date_range("2022-01-01", "2021-01-01")
        DateValidationError: Start date is after end date
    """
    # Parse dates
    try:
        start = parse_date(start_str)
        end = parse_date(end_str)
    except DateValidationError as e:
        raise DateValidationError(f"Date parsing error: {e}") from e
    
    # Validate range logic
    if start > end:
        raise DateValidationError(
            f"Invalid date range: start ({start.date()}) is after end ({end.date()})"
        )
    
    # Validate range span
    year_diff = end.year - start.year
    if year_diff > MAX_YEAR_RANGE:
        raise DateValidationError(
            f"Date range exceeds maximum ({MAX_YEAR_RANGE} years)\n"
            f"Requested: {year_diff} years ({start.date()} to {end.date()})"
        )
    
    # Return in Wayback API format (YYYYMMDD)
    start_yyyymmdd = start.strftime("%Y%m%d")
    end_yyyymmdd = end.strftime("%Y%m%d")
    
    return start_yyyymmdd, end_yyyymmdd


# ==========================================================
# SNAPSHOT DATA VALIDATION
# ==========================================================

def validate_snapshot_list(snapshots: list) -> list:
    """
    Validate snapshot list from Wayback CDX API.
    
    Args:
        snapshots: List of (timestamp, original_url) tuples
    
    Returns:
        Validated list
    
    Raises:
        ValueError: If snapshots list is invalid
    """
    if not isinstance(snapshots, list):
        raise ValueError("Snapshots must be a list")
    
    if len(snapshots) == 0:
        raise ValueError("Snapshots list is empty")
    
    if len(snapshots) > 10000:
        raise ValueError(f"Too many snapshots ({len(snapshots)}) - max is 10000")
    
    # Validate each snapshot
    for idx, snapshot in enumerate(snapshots):
        if not isinstance(snapshot, (tuple, list)) or len(snapshot) < 2:
            raise ValueError(f"Snapshot {idx} has invalid format")
        
        timestamp, original_url = snapshot[0], snapshot[1]
        
        # Validate timestamp format
        if not isinstance(timestamp, str) or not re.match(r"^\d{14}$", timestamp):
            raise ValueError(f"Snapshot {idx}: invalid timestamp {timestamp}")
        
        # Validate URL
        if not isinstance(original_url, str) or not original_url:
            raise ValueError(f"Snapshot {idx}: invalid URL")
    
    return snapshots


def validate_html_data(html_lines: list) -> list:
    """
    Validate HTML data fetched from snapshot or live site.
    
    Args:
        html_lines: List of HTML lines
    
    Returns:
        Validated list
    
    Raises:
        ValueError: If HTML data is invalid
    """
    if not isinstance(html_lines, list):
        raise ValueError("HTML data must be a list of lines")
    
    if len(html_lines) == 0:
        raise ValueError("HTML data is empty")
    
    if len(html_lines) > 1000000:
        raise ValueError("HTML data is too large (max 1M lines)")
    
    # Validate lines are strings
    for idx, line in enumerate(html_lines):
        if not isinstance(line, str):
            raise ValueError(f"HTML line {idx} is not a string")
    
    return html_lines


def validate_extracted_surface(surface: dict) -> dict:
    """
    Validate extracted security surface data.
    
    Args:
        surface: Extracted security surface dictionary
    
    Returns:
        Validated surface
    
    Raises:
        ValueError: If surface data is invalid
    """
    if not isinstance(surface, dict):
        raise ValueError("Surface must be a dictionary")
    
    required_keys = [
        "authentication_routes",
        "admin_routes",
        "api_routes",
        "query_parameters",
        "forms",
        "hidden_fields",
        "sensitive_inputs",
        "file_inputs",
        "external_scripts",
        "client_fetch_calls",
        "business_logic_indicators",
        "security_headers"
    ]
    
    for key in required_keys:
        if key not in surface:
            raise ValueError(f"Missing required key: {key}")
    
    return surface


# ==========================================================
# LEGACY COMPATIBILITY
# ==========================================================

# Note: wayback_to_user() has been moved to waydiff/cli/
# To use it in core, import from CLI:
# from waydiff.cli.validator import wayback_to_user
# OR
# from waydiff.cli.banner import wayback_to_user (if moved there)

# For now, keep a simple version for internal use only:
def _format_timestamp_iso(timestamp: str) -> str:
    """
    Internal helper: Convert Wayback timestamp to ISO date format.
    
    For display purposes only. User-facing formatting is in CLI.
    
    Args:
        timestamp: Wayback timestamp (YYYYMMDDHHMMSS)
    
    Returns:
        ISO format date string (YYYY-MM-DD HH:MM:SS)
    """
    try:
        dt = datetime.strptime(timestamp, "%Y%m%d%H%M%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return timestamp
