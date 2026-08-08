# Fresh-reread review preamble

Restart from disk. Ignore prior reasoning and reread the assigned documents in
their current state before answering.

Review mode only:

- Do not implement changes or propose commits.
- Do not accept, reject, or otherwise decide an ADR.
- Do not expand beyond the assigned product, architecture, specification, or ADR
  boundary.
- Follow references only when required to understand a delegated canonical
  contract or resolve a contradiction.

Report at most five high-value issues, ordered by severity. Report blockers first.
For each blocker include:

- `Severity: blocking`
- `Why it blocks the next decision or proof`
- `Documents involved`
- `Evidence needed`
- `Suggested decision or specification change`

Do not praise or summarize material that is already clear. If no blocking issues
remain, say so explicitly and add only worthwhile non-blocking items under
`Suggested follow-ups`.

End the review after identifying the remaining blockers or concluding that the
assigned material is ready for its next decision, experiment, or implementation
step. Do not reopen the design for wording preferences, speculative future scale,
or low-probability edge cases.
