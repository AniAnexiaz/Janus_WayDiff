"""
CLI banner and styling utilities for Janus Diff.

Display hierarchy:
  No args                  → display_banner() + display_short_usage()
  -h / --help              → display_banner() + display_usage()
  --no-banner (no command) → nothing
  Valid command            → display_run_header()  (compact single line)
  --no-banner + command    → nothing printed by the banner system
"""

VERSION = "1.0.0"

BANNER = r"""
     ██╗ █████╗ ███╗   ██╗██╗   ██╗███████╗    ██╗    ██╗ █████╗ ██╗   ██╗██████╗ ██╗███████╗███████╗
     ██║██╔══██╗████╗  ██║██║   ██║██╔════╝    ██║    ██║██╔══██╗╚██╗ ██╔╝██╔══██╗██║██╔════╝██╔════╝
     ██║███████║██╔██╗ ██║██║   ██║███████╗    ██║ █╗ ██║███████║ ╚████╔╝ ██║  ██║██║█████╗  █████╗  
██   ██║██╔══██║██║╚██╗██║██║   ██║╚════██║    ██║███╗██║██╔══██║  ╚██╔╝  ██║  ██║██║██╔══╝  ██╔══╝  
╚█████╔╝██║  ██║██║ ╚████║╚██████╔╝███████║    ╚███╔███╔╝██║  ██║   ██║   ██████╔╝██║██║     ██║     
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝     ╚══╝╚══╝ ╚═╝  ╚═╝   ╚═╝   ╚═════╝ ╚═╝╚═╝     ╚═╝     
"""

TAGLINE = f"  Attack Surface Intelligence Tool  v{VERSION}  |  By Kels1er"

_HEAVY = "━" * 100
_THIN  = "─" * 100


# ==========================================================
# FULL BANNER — used only for help screens
# ==========================================================

def display_banner():
    """Print full ASCII banner. Only called for no-args and -h/--help screens."""
    print(BANNER)
    print(TAGLINE)
    print()
    print(_HEAVY)


# ==========================================================
# RUN HEADER — compact single line for actual command runs
# ==========================================================

def display_run_header(command: str = ""):
    """
    Print a compact single-line header at the start of a command run.
    Keeps analysis output clean — no giant banner during real usage.

    Examples:
        ━━━ Janus WayDiff v1.0.0 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ━━━ Janus WayDiff v1.0.0 ━━━━━━━━━━━━━━━━━━━  wayback  ━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    prefix = f"━━━ Janus WayDiff v{VERSION} "
    if command:
        label = f"  {command}  "
        remaining = 100 - len(prefix) - len(label)
        half = remaining // 2
        line = prefix + "━" * half + label + "━" * (remaining - half)
    else:
        line = prefix + "━" * (100 - len(prefix))
    print(line)
    print()


# ==========================================================
# SHORT USAGE — shown after the banner when no args are given
# ==========================================================

def display_short_usage():
    """Compact usage reference printed when the tool is called with no arguments."""
    print(f"""
USAGE
  python janus_diff.py <command> [arguments] [options]

COMMANDS
  wayback <domain>            Diff Wayback Machine snapshots against the live site
  diff <results-folder>       Re-diff snapshots from a previous wayback run
  localsnap capture <url>     Capture a snapshot of any URL
  localsnap compare           Compare two previously captured local snapshots
  config llm                  Configure LLM backend
  config show                 Show current configuration

OPTIONS
  -h, --help                  Show full help and usage reference
  --version                   Show version and exit
  --no-banner                 Suppress banner and run header
  -v / -vv                    Verbose / debug output

  python janus_diff.py <command> --help    Per-command help
""")


# ==========================================================
# FULL USAGE — shown only with -h / --help
# ==========================================================

def display_usage():
    """Full usage reference. Only printed when -h or --help is passed."""
    print(f"""
USAGE
  python janus_diff.py <command> [arguments] [options]
  python janus_diff.py <command> --help          Per-command help

{_HEAVY}

COMMANDS

  wayback <domain>            Fetch Wayback Machine snapshots and diff against live site
  diff <results-folder>       Re-run diff on a previous wayback analysis using snapshot numbers
  localsnap capture <url>     Capture a snapshot of an internal or external URL
  localsnap compare           Compare two previously captured local snapshots
  config llm                  Persist LLM settings to ~/.janus/config.json
  config show                 Display current saved configuration

{_HEAVY}

GLOBAL OPTIONS

  -h, --help                  Show this full help reference
  --version                   Show version and exit
  --no-banner                 Suppress the ASCII banner and run header
  -v                          Verbose output (INFO-level progress messages)
  -vv                         Debug output (full trace logging)

{_HEAVY}

COMMAND: wayback

  Fetches historical snapshots from the Wayback Machine CDX API for the given domain
  and diffs each selected snapshot against the live site to detect attack surface drift.

  SYNOPSIS
    python janus_diff.py wayback <domain> [options]

  ARGUMENTS
    domain                    Target domain (e.g., example.com). http[s]:// stripped automatically.

  OPTIONS
    --start DATE              Start of date range  (YYYY-MM-DD, default: 2 years ago)
    --end   DATE              End   of date range  (YYYY-MM-DD, default: today)
    --llm   [local|online]    Add LLM analysis on top of the rule-based report
    --url   URL               Ollama endpoint      (required with --llm local)
    --api   KEY               OpenAI API key       (required with --llm online)
    -o, --output DIR          Output directory     (default: results/)

  EXAMPLES
    python janus_diff.py wayback example.com
    python janus_diff.py wayback example.com --start 2021-01-01 --end 2024-06-01
    python janus_diff.py wayback example.com --llm local --url http://localhost:11434
    python janus_diff.py wayback example.com --llm online --api sk-...
    python janus_diff.py wayback example.com -o /tmp/janus-results -vv

  OUTPUT
    results/example.com/<timestamp>_<id>/
    ├── index.txt          Human-readable snapshot list  (use numbers with `diff --pick`)
    ├── index.json         Machine-readable snapshot list
    ├── diffs/
    │   ├── snapshot_<timestamp>.html   Visual side-by-side HTML diff
    │   └── snapshot_<timestamp>.json   Structured surface diff
    ├── reports/
    │   ├── security_report.txt         Rule-based report — always generated
    │   └── llm_security_report.txt     LLM report — only if --llm is passed
    ├── snapshots/
    ├── logs/
    └── metadata.json      Run metadata for reproducibility

{_HEAVY}

COMMAND: diff

  Re-runs diff analysis against the live site using snapshots from a previous
  `wayback` run. Reference snapshots by the numbers shown in index.txt.

  SYNOPSIS
    python janus_diff.py diff <results-folder> <selection> [options]

  ARGUMENTS
    results-folder            Path to a previous wayback results directory
                              (e.g., results/example.com/20240109_153000_abc123)

  SNAPSHOT SELECTION  (exactly one required)
    --pick  N [N ...]         Specific snapshot numbers  (e.g., --pick 1 42 487)
    --earliest                Earliest snapshot in the index
    --latest                  Latest snapshot in the index
    --all                     Every snapshot in the index
    --interactive, -i         Browse and select interactively
    --file  PATH              Load snapshot numbers from a list file

  OPTIONS
    --llm   [local|online]    Add LLM analysis on top of the rule-based report
    --url   URL               Ollama endpoint  (required with --llm local)
    --api   KEY               OpenAI API key   (required with --llm online)
    -o, --output DIR          Output directory (default: results/)

  EXAMPLES
    python janus_diff.py diff results/example.com/20240109_153000_abc123 --pick 1
    python janus_diff.py diff results/example.com/20240109_153000_abc123 --pick 1 42 487
    python janus_diff.py diff results/example.com/20240109_153000_abc123 --earliest
    python janus_diff.py diff results/example.com/20240109_153000_abc123 --all --llm local --url http://localhost:11434

{_HEAVY}

COMMAND: localsnap capture

  Captures a full snapshot of any URL — including internal sites, staging environments,
  and admin panels not indexed by the Wayback Machine.

  SYNOPSIS
    python janus_diff.py localsnap capture <url> [options]

  ARGUMENTS
    url                       Full URL to snapshot (must include http:// or https://)

  OPTIONS
    --name  LABEL             Snapshot label for easy reference (default: timestamp)
    -o, --output DIR          Output directory (default: results/)

  EXAMPLES
    python janus_diff.py localsnap capture https://internal.company.com/admin
    python janus_diff.py localsnap capture https://staging.company.com --name pre-release-v2

  OUTPUT
    results/<domain>/<timestamp>_<id>/snapshots/<name>_<timestamp>/
    ├── snapshot.html     Cleaned HTML content
    ├── surface.json      Extracted security surface
    └── metadata.json     Capture details

{_HEAVY}

COMMAND: localsnap compare

  Compares two snapshots previously created with `localsnap capture`.

  SYNOPSIS
    python janus_diff.py localsnap compare --snap-a <path> --snap-b <path> [options]

  REQUIRED
    --snap-a PATH             Path to first  snapshot directory
    --snap-b PATH             Path to second snapshot directory

  OPTIONS
    --llm   [local|online]    Add LLM analysis on top of the rule-based report
    --url   URL               Ollama endpoint  (required with --llm local)
    --api   KEY               OpenAI API key   (required with --llm online)
    -o, --output DIR          Output directory (default: results/)

  EXAMPLES
    python janus_diff.py localsnap compare \\
        --snap-a results/domain/run1/snapshots/snap1 \\
        --snap-b results/domain/run2/snapshots/snap2

    python janus_diff.py localsnap compare \\
        --snap-a results/domain/run1/snapshots/snap1 \\
        --snap-b results/domain/run2/snapshots/snap2 \\
        --llm local --url http://localhost:11434

{_HEAVY}

COMMAND: config

  Persist LLM settings to ~/.janus/config.json so --llm, --url, and --api
  don't need to be passed on every run.

  SUBCOMMANDS
    config llm                Configure the LLM backend
    config show               Display current saved configuration

  config llm OPTIONS
    --type  [local|online]    LLM backend type (required)
    --url   URL               Ollama endpoint  (required when --type local)
    --api   KEY               OpenAI API key   (required when --type online)
    --model NAME              Model name       (default: mistral / gpt-4)

  EXAMPLES
    python janus_diff.py config llm --type local --url http://localhost:11434
    python janus_diff.py config llm --type local --url http://localhost:11434 --model llama3
    python janus_diff.py config llm --type online --api sk-... --model gpt-4o
    python janus_diff.py config show

{_HEAVY}

LLM INTEGRATION

  A rule-based security report (security_report.txt) is always generated automatically
  with no external dependencies. --llm adds a second LLM-powered report on top of it.

  LOCAL  (Ollama — recommended for sensitive targets, fully offline)
    1. Install Ollama:  https://ollama.com/download
    2. Pull a model:   ollama pull mistral
    3. Configure:      python janus_diff.py config llm --type local --url http://localhost:11434

  ONLINE  (OpenAI)
    1. Configure:      python janus_diff.py config llm --type online --api sk-...
       Or pass inline: --llm online --api sk-...

{_HEAVY}

  Per-command help:   python janus_diff.py <command> --help
""")


# ==========================================================
# PRINT UTILITIES
# ==========================================================

def print_section(title: str):
    """Print a named section divider."""
    print(f"\n{title}")
    print(_THIN)


def print_success(msg: str):
    print(f"✓ {msg}")


def print_error(msg: str):
    print(f"✗ {msg}")


def print_info(msg: str, end: str = "\n"):
    print(f"ℹ {msg}", end=end)


def print_warning(msg: str):
    print(f"⚠ {msg}")


def print_tip(msg: str):
    print(f"💡 {msg}")


def print_progress(current: int, total: int, label: str = ""):
    """Print inline progress bar."""
    if total > 0:
        percent = (current / total) * 100
        filled = int(percent / 5)
        bar = "█" * filled + "░" * (20 - filled)
        status = f"{label} " if label else ""
        print(f"⠙ {status}[{bar}] {percent:.1f}% ({current}/{total})", end="\r")
    else:
        print(f"⠙ {label}...", end="\r")
