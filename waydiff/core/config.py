"""
Configuration constants for Janus Diff core modules.
"""

# Wayback CDX API
CDX_API = "https://web.archive.org/cdx/search/cdx"

# Network and API limits
MAX_SNAPSHOTS = 10000
MAX_YEAR_RANGE = 10
REQUEST_TIMEOUT = 40
MAX_CONCURRENT_FETCH = 5

# Results directory management
RESULTS_BASE_DIR = "results"
TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
RUN_ID_LENGTH = 6  # Length of unique run ID hash

# Pagination for snapshot selection
PAGE_SIZE = 10

# Domain validation
MAX_DOMAIN_LENGTH = 253
MAX_LABEL_LENGTH = 63

# Report generation
MAX_ENDPOINTS_IN_SUMMARY = 15
MAX_SCRIPTS_IN_SUMMARY = 10
MAX_INPUTS_IN_SUMMARY = 10
MAX_FINDINGS_IN_PRIORITY = 5

# Logging levels
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Metadata fields
METADATA_VERSION = "1.0.0"
