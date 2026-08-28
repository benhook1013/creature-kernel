# AI observations

Status: Operational inbox; 1 open observation

Record only unexpected, evidenced operational friction that is recurring or
likely to save future retries or work rounds. The main thread is the default
writer; a delegated thread writes only with exclusive inbox ownership and
otherwise returns a concise observation candidate. Resolve or promote entries
during a purposeful tooling/instruction improvement round, then remove them;
Git preserves the history.

Copyable entry:

- `YYYY-MM-DD HH:MM TZ`: short title
  - Observation: what happened and where
  - Expected pattern: what should happen instead

- `2026-08-28 18:30 NZST`: Bare Python was too old for ad-hoc TOML parsing
  - Observation: System Python 3.10 failed with `No module named 'tomllib'` before it could parse `.codex/config.toml`.
  - Expected pattern: Use the actual configuration consumer or a confirmed managed interpreter; do not try an unverified system interpreter first.
