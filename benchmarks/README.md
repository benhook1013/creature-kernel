# Benchmarks

Status: Active policy; no benchmark implemented

Benchmarks provide reproducible performance evidence. They do not define product
requirements unless a canonical product document adopts their thresholds.

Every benchmark must identify:

- stable ID and scenario;
- input fixture and compiler/runtime revision;
- warm-up and measurement method;
- frame, generation, memory, transfer, or quality metrics;
- sample count and variance where relevant;
- CPU, GPU, memory, operating system, driver, and power mode;
- quality settings, resolution, character count, and active regions;
- exact reproduction command;
- raw result location;
- known sources of noise and limitations.

Avoid publishing a single best-case number without distribution or environment.
Separate offline compilation benchmarks from real-time runtime benchmarks.
