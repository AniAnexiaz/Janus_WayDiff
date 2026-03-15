# Janus WayDiff

**Attack Surface Intelligence Tool**

Janus WayDiff identifies attack surface drift by comparing historical Wayback Machine snapshots of a domain against its live state, and by comparing internal snapshots over time. It extracts security-relevant surface data — endpoints, forms, scripts, headers, inputs — and generates structured diffs, risk-scored findings reports, and optional LLM-powered analysis.

---

## Table of Contents

- [What It Does](#what-it-does)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands](#commands)
  - [wayback](#wayback)
  - [diff](#diff)
  - [localsnap capture](#localsnap-capture)
  - [localsnap compare](#localsnap-compare)
  - [config](#config)
- [Global Options](#global-options)
- [LLM Integration](#llm-integration)
- [Output Structure](#output-structure)
- [What Gets Extracted](#what-gets-extracted)
- [Security Report Format](#security-report-format)

---

## What It Does

| Capability | Description |
|---|---|
| **Wayback diff** | Fetches historical snapshots from the Wayback Machine CDX API and diffs their attack surface against the live site |
| **Snapshot re-diff** | Re-runs analysis on any subset of snapshots from a previous run without re-fetching |
| **Local snapshot capture** | Captures a full snapshot of any URL — including internal, staging, or VPN-only sites |
| **Local snapshot compare** | Diffs two local snapshots to detect changes over time |
| **Rule-based reports** | Generates risk-scored findings with pentest recommendations |
| **LLM analysis** | Optionally adds a second LLM-powered report on top of the rule-based report (local via Ollama or online via OpenAI) |

---

## Installation

**Requirements:** Python 3.10+

```bash
git clone https://github.com/youruser/janus-waydiff.git
cd janus-waydiff
pip install -r requirements.txt
```

Verify:

```bash
python janus_diff.py --version
```

---

## Quick Start

```bash
# Diff the last 2 years of Wayback snapshots for a domain
python janus_diff.py wayback example.com

# Same, with local Ollama LLM analysis
python janus_diff.py wayback example.com --llm local --url http://localhost:11434

# Capture an internal admin panel (not indexed by Wayback)
python janus_diff.py localsnap capture https://internal.company.com/admin --name baseline

# Compare two captures taken at different times
python janus_diff.py localsnap compare \
    --snap-a results/internal.company.com/run1/snapshots/baseline_20240109_120000 \
    --snap-b results/internal.company.com/run2/snapshots/baseline_20240115_120000
```

---

## CLI Output Behaviour

The tool adjusts what it prints depending on how it is invoked:

| Invocation | Output |
|---|---|
| `janus_diff.py` (no args) | Full ASCII banner + compact command summary |
| `janus_diff.py -h` | Full ASCII banner + full usage reference |
| `janus_diff.py --no-banner` | Nothing — silent exit |
| `janus_diff.py --no-banner -h` | Full usage reference only (no banner) |
| `janus_diff.py wayback …` | Compact one-line run header + analysis output |
| `janus_diff.py --no-banner wayback …` | Analysis output only — no header |

The full ASCII banner is only shown on help screens. During actual analysis runs a compact single-line header is printed instead, keeping output clean and easy to pipe or log.

---

## Commands

### wayback

Fetches historical snapshots from the Wayback Machine CDX API, selects the earliest and latest within the date range, and diffs each against the live site.

```
python janus_diff.py wayback <domain> [options]
```

**Arguments**

| Argument | Description |
|---|---|
| `domain` | Target domain (e.g., `example.com`). `http[s]://` is stripped automatically. |

**Options**

| Option | Default | Description |
|---|---|---|
| `--start DATE` | 2 years ago | Start of date range (`YYYY-MM-DD`) |
| `--end DATE` | Today | End of date range (`YYYY-MM-DD`) |
| `--llm [local\|online]` | — | Add LLM report on top of the always-generated rule-based report |
| `--url URL` | — | Ollama endpoint (required with `--llm local`) |
| `--api KEY` | — | OpenAI API key (required with `--llm online`) |
| `-o, --output DIR` | `results/` | Output directory |

**Examples**

```bash
# Default — last 2 years, no LLM
python janus_diff.py wayback example.com

# Custom date range
python janus_diff.py wayback example.com --start 2021-01-01 --end 2024-06-01

# With local Ollama
python janus_diff.py wayback example.com --llm local --url http://localhost:11434

# With OpenAI
python janus_diff.py wayback example.com --llm online --api sk-...

# Debug logging, custom output directory
python janus_diff.py wayback example.com -o /tmp/janus-results -vv
```

---

### diff

Re-runs diff analysis on snapshots from a previous `wayback` run. Use the numbers from `index.txt` to select which snapshots to analyse.

```
python janus_diff.py diff <results-folder> <selection> [options]
```

**Arguments**

| Argument | Description |
|---|---|
| `results-folder` | Path to a previous `wayback` results directory |

**Snapshot selection** — exactly one required

| Flag | Description |
|---|---|
| `--pick N [N ...]` | Compare specific snapshot numbers (from `index.txt`) |
| `--earliest` | Compare the earliest snapshot |
| `--latest` | Compare the latest snapshot |
| `--all` | Compare every snapshot in the index |
| `--interactive, -i` | Browse and select interactively |
| `--file PATH` | Load snapshot numbers from a custom list file |

**Options**

| Option | Default | Description |
|---|---|---|
| `--llm [local\|online]` | — | Add LLM report on top of the always-generated rule-based report |
| `--url URL` | — | Ollama endpoint (required with `--llm local`) |
| `--api KEY` | — | OpenAI API key (required with `--llm online`) |
| `-o, --output DIR` | `results/` | Output directory |

**Examples**

```bash
# Re-diff snapshot #1 only
python janus_diff.py diff results/example.com/20240109_153000_abc123 --pick 1

# Diff snapshots 1, 42, and 487
python janus_diff.py diff results/example.com/20240109_153000_abc123 --pick 1 42 487

# Diff the earliest snapshot with LLM
python janus_diff.py diff results/example.com/20240109_153000_abc123 --earliest \
    --llm local --url http://localhost:11434

# Diff all snapshots
python janus_diff.py diff results/example.com/20240109_153000_abc123 --all
```

**Tip:** Open `index.txt` in the results folder to browse available snapshot numbers and dates before choosing.

---

### localsnap capture

Captures a full snapshot of any URL — including internal sites, VPN-accessible hosts, and staging environments not indexed by the Wayback Machine.

```
python janus_diff.py localsnap capture <url> [options]
```

**Arguments**

| Argument | Description |
|---|---|
| `url` | Full URL to snapshot. Must include `http://` or `https://`. |

**Options**

| Option | Default | Description |
|---|---|---|
| `--name LABEL` | Timestamp | Snapshot label used in the directory name |
| `-o, --output DIR` | `results/` | Output directory |

**Examples**

```bash
# Basic capture
python janus_diff.py localsnap capture https://internal.company.com/admin

# Named capture for before/after comparison
python janus_diff.py localsnap capture https://staging.company.com --name pre-deploy-v2.1
```

**Output:**

```
results/<domain>/<timestamp>_<id>/snapshots/<name>_<timestamp>/
├── snapshot.html     Cleaned HTML content
├── surface.json      Extracted security surface
└── metadata.json     Capture details (URL, timestamp, counts)
```

---

### localsnap compare

Compares two snapshots previously created with `localsnap capture`.

```
python janus_diff.py localsnap compare --snap-a <path> --snap-b <path> [options]
```

**Required**

| Option | Description |
|---|---|
| `--snap-a PATH` | Path to the first snapshot directory |
| `--snap-b PATH` | Path to the second snapshot directory |

**Options**

| Option | Default | Description |
|---|---|---|
| `--llm [local\|online]` | — | Add LLM report on top of the always-generated rule-based report |
| `--url URL` | — | Ollama endpoint (required with `--llm local`) |
| `--api KEY` | — | OpenAI API key (required with `--llm online`) |
| `-o, --output DIR` | `results/` | Output directory |

**Examples**

```bash
# Basic comparison
python janus_diff.py localsnap compare \
    --snap-a results/internal.company.com/run1/snapshots/pre-deploy-v2.1_20240109_120000 \
    --snap-b results/internal.company.com/run2/snapshots/pre-deploy-v2.2_20240115_140000

# With LLM analysis
python janus_diff.py localsnap compare \
    --snap-a results/domain/run1/snapshots/snap1 \
    --snap-b results/domain/run2/snapshots/snap2 \
    --llm local --url http://localhost:11434
```

---

### config

Persists LLM settings to `~/.janus/config.json` so you don't need to pass `--llm`, `--url`, or `--api` on every run.

#### config llm

```
python janus_diff.py config llm --type [local|online] [options]
```

| Option | Description |
|---|---|
| `--type [local\|online]` | LLM backend type (required) |
| `--url URL` | Ollama endpoint (required when `--type local`) |
| `--api KEY` | OpenAI API key (required when `--type online`) |
| `--model NAME` | Model name (default: `mistral` for local, `gpt-4` for online) |

```bash
# Ollama with default model (mistral)
python janus_diff.py config llm --type local --url http://localhost:11434

# Ollama with a specific model
python janus_diff.py config llm --type local --url http://localhost:11434 --model llama3

# OpenAI GPT-4o
python janus_diff.py config llm --type online --api sk-... --model gpt-4o
```

#### config show

```bash
python janus_diff.py config show
```

Displays the current contents of `~/.janus/config.json`.

---

## Global Options

| Flag | Description |
|---|---|
| `-h, --help` | Show full usage reference (with banner) |
| `--version` | Show version and exit |
| `--no-banner` | Suppress the ASCII banner and the run header |
| `-v` | Verbose — INFO-level progress messages |
| `-vv` | Debug — full trace logging |

```bash
python janus_diff.py wayback example.com -v           # show progress
python janus_diff.py wayback example.com -vv          # full debug trace
python janus_diff.py wayback example.com --no-banner  # no header, clean output
```

---

## LLM Integration

A rule-based security report (`security_report.txt`) is **always generated automatically** with no external dependencies. `--llm` adds a second report (`llm_security_report.txt`) on top of it using an AI model for deeper analysis.

### Local — Ollama (recommended for sensitive targets)

Runs entirely offline. No data leaves your machine.

```bash
# 1. Install Ollama — https://ollama.com/download

# 2. Pull a model
ollama pull mistral        # recommended default
ollama pull llama3         # alternative

# 3. Configure Janus WayDiff
python janus_diff.py config llm --type local --url http://localhost:11434

# Or pass inline per run
python janus_diff.py wayback example.com --llm local --url http://localhost:11434
```

### Online — OpenAI

```bash
# Configure once
python janus_diff.py config llm --type online --api sk-... --model gpt-4o

# Or pass inline
python janus_diff.py wayback example.com --llm online --api sk-...
```

---

## Output Structure

### wayback / diff

```
results/
└── example.com/
    └── 20240109_153000_abc123/         ← timestamp + unique run ID
        ├── index.txt                   ← human-readable snapshot list (for `diff --pick`)
        ├── index.json                  ← machine-readable snapshot list
        ├── metadata.json               ← run metadata for reproducibility
        ├── diffs/
        │   ├── snapshot_20220115000000.html    ← visual side-by-side HTML diff
        │   └── snapshot_20220115000000.json    ← structured surface diff
        ├── reports/
        │   ├── security_report.txt             ← rule-based findings with risk scores
        │   └── llm_security_report.txt         ← LLM report (only if --llm is passed)
        ├── snapshots/
        └── logs/
```

**index.txt format:**

```
# Snapshot Index for Attack Surface Analysis
# Total snapshots: 847
# Format: NUM | DATE | TIMESTAMP | ORIGINAL_URL

1   | 2021-03-14 08:22:00 | 20210314082200 | http://example.com/
2   | 2021-05-07 14:10:00 | 20210507141000 | http://example.com/
...
847 | 2024-01-08 19:45:00 | 20240108194500 | http://example.com/
```

Pass `NUM` values to `--pick`: `--pick 1 42 487`

### localsnap

```
results/
└── internal.company.com/
    └── 20240109_153000_abc123/
        ├── metadata.json
        └── snapshots/
            └── pre-deploy-v2.1_20240109_153000/
                ├── snapshot.html       ← cleaned HTML content
                ├── surface.json        ← extracted security surface
                └── metadata.json       ← capture details
```

---

## What Gets Extracted

| Surface Element | Description |
|---|---|
| `authentication_routes` | Login, logout, OAuth, MFA, SSO, token, reset endpoints |
| `admin_routes` | Admin, dashboard, internal, debug paths |
| `api_routes` | Paths containing `/api` |
| `query_parameters` | URL query parameter names |
| `forms` | Form actions, methods, and input field names |
| `hidden_fields` | Hidden form inputs |
| `sensitive_inputs` | Password and credential inputs |
| `file_inputs` | File upload fields |
| `external_scripts` | Third-party JavaScript includes |
| `client_fetch_calls` | Fetch API calls found in inline JavaScript |
| `business_logic_indicators` | Fields named: price, amount, role, plan, discount, tier |
| `security_headers` | CSP, HSTS, X-Frame-Options, Referrer-Policy, Permissions-Policy, Server, Set-Cookie |

---

## Security Report Format

`security_report.txt` contains risk-scored findings grouped by snapshot, sorted by severity.

```
SECURITY DRIFT INTELLIGENCE REPORT
======================================================================

TOP TESTING PRIORITIES
--------------------------------------------------
HIGH (Risk 9/10): [security_headers] Removed: content-security-policy
  → Review header policy.

HIGH (Risk 8/10): [admin_routes] /admin/config/backup
  → Test access control and forced browsing.

HIGH (Risk 8/10): [file_inputs] file:document_upload
  → Test upload validation and RCE.
```

**Risk scoring:**

| Score | Severity | Examples |
|---|---|---|
| 8–10 | HIGH | Admin routes, auth routes, file uploads, removed security headers |
| 5–7 | MEDIUM | API routes, external scripts, security header changes |
| 1–4 | LOW | Query parameters, general form fields |

---

## Notes

- Wayback Machine availability varies by domain. Low-traffic sites may have few or no snapshots.
- The CDX API is rate-limited. Use `--start`/`--end` to keep date ranges focused.
- For sensitive internal targets use `localsnap` with a local LLM — no data leaves your machine.
- All results are stored locally. Nothing is sent externally unless `--llm online` is used.
