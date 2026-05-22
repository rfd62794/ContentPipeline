# ADR-RS-003: Enter-to-stop as primary stop mechanism

## Status
Accepted

## Context
Two candidates: `input()` blocking the main thread, or `signal.SIGINT` (Ctrl+C) as primary. `input()` is semantically cleaner — the user is in control of when recording ends, not fighting the terminal. `KeyboardInterrupt` is still caught as a fallback path and executes the same shutdown sequence.

## Decision
`input("Recording... Press Enter to stop.\n")` as primary. `KeyboardInterrupt` caught in `except` block, runs same cleanup. Both paths hit the same finally block.

## Consequences
Requires main thread to not block on anything else before `input()`. VLC and recording both run on subthread/subprocess. Honored by this design.
