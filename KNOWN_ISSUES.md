# Known Issues & Pending Tests

## Not Yet Implemented

- `diff --interactive` flag is a placeholder — prints "not yet implemented" and exits cleanly.
  Full interactive snapshot browser is scoped for a future release.

## Untested

- **OpenAI API backend** (`--llm online --api sk-...`) — not tested due to budget constraints.
  Code is implemented and follows the OpenAI chat completions API spec, but has not been
  run end-to-end. Use at your own risk until verified.

- **Ollama LLM backend** (`--llm local`) — implemented and tested locally with Mistral.

## Known Limitations

- **Wayback CDX API cap** — the CDX API returns a maximum of 10,000 snapshots per query.
  For high-traffic domains (e.g. amazon.com, google.com), the default earliest/latest
  selection may not pick the true latest snapshot in the date range — it picks the last
  of the first 10,000 results instead.
  
  **Workaround:** Use `--start` and `--end` to narrow the date range, or use
  `diff --pick` to manually select specific snapshot numbers from `index.txt`.
  
  **Planned fix:** Reverse CDX query in `fetcher.py` to always fetch the true latest
  snapshot independently. Scoped but not yet implemented.

## Notes for Contributors

- If you have an OpenAI API key, please test `--llm online` and report results.
- LLM heuristic fallback (`--llm none` or when no LLM is available) is fully tested.
