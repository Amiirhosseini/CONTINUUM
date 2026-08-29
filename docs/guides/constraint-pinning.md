# Constraint Pinning - Concepts and How-To

> **Issue #420 - Parent #391 - Do after mechanism works**

This page documents the constraint pinning contract: lifecycle, statuses, grace windows, strict-mode behaviour, how to record pins from harness hooks, and honest scope.

## Concepts - Pin Lifecycle

Constraint pinning makes standing constraints first-class, verifiable events. A constraint like "never send without confirmation" is recorded once at session start as a hash, and every context reconstruction must account for it.

### Event

`CONSTRAINT_PINNED {constraint_id, sha256}` plus `CONSTRAINT_RETRACTED {constraint_id}`. Payload stores only `sha256` hex (64 chars, lowercase), never plaintext. `models.py` validates `sha256` via `Field(pattern=r"^[0-9a-f]{64}$")`.

Example:

```python
from continuum.events import EventType
storage.append_event(run_id, EventType.CONSTRAINT_PINNED, {"constraint_id": "no-send-without-confirm", "sha256": "e3b0c442...64hex"}, source=Origin.DETERMINISTIC)
storage.append_event(run_id, EventType.CONSTRAINT_RETRACTED, {"constraint_id": "no-send-without-confirm"})
```

### States

Projected into `SemanticState.pins: dict[str, ConstraintPin]` with `status` `active` and `unmatched_pin_retractions: list[str]` for retractions without matching active pin (degrades gracefully, no crash).

### Reconstruction Accounting - Present, Absent, Unverifiable per Pin with Grace Escalation (issue #418)

Every context reconstruction path - `briefing` `resume banner` `checkpoint rehydration` - must account for every active pin as one of three statuses, computed from hash-tagged markers in the produced context (source of truth, not summarizer self-report).

Marker format per pin: `[pin:<constraint_id>:<sha256[:8]>]` where `[:8]` is first 8 hex chars. Emitted by `pin_markers_for_state(state)` and checked by `account_pins_in_context(state, context)`.

| Status | Meaning | When |
|---|---|---|
| `present` | Marker found in context | Reconstructed context contains the pin - silent pass |
| `absent` | Marker not found, context not truncated | Summarizer dropped the constraint - next resume names `pin id:hash_prefix` instead of resuming silently, past grace window raises contract flag |
| `unverifiable` | Marker not found but context was truncated (`[context truncated` or `omitted:` present) | Cannot tell if pin was in dropped section - flagged but not as `absent` |

Example accounting after compact + briefing:

```python
from continuum.state.semantic import account_pins_in_context, pin_markers_for_state
state = project(run_id, storage.read_events(run_id) + storage.read_archived_events(run_id))
context = build_recovery_context(state).render()  # includes markers
accounting = account_pins_in_context(state, context, grace_seconds=3600, now=utcnow(), strict=False)
# accounting["no-send-without-confirm"] -> {"status": "absent", "sha256": "e3b...", "sha256_prefix": "e3b0c442", "pinned_at": ..., "age_seconds": 4000, "past_grace": True, "flag": "pin no-send-without-confirm:e3b0c442 absent past grace (4000s > 3600s)"}
```

### Grace Windows

`grace_seconds` is configurable per call (e.g., `3600` for 1 hour). If `age_seconds = now - pinned_at` exceeds grace and `status` is `absent`, it is flagged. In `strict=False` advisory flag, in `strict=True` it escalates to `REQUIRES_REVIEW` via `check_pin_accounting(..., strict=True)` returning `should_escalate=True`, which `RecoveryEngine` uses to set `REQUEST_HUMAN`. House fail-closed.

Compaction: pins live in live chain and survive anchoring like any event. `compact_run` moves pre-anchor prefix to `events_archive`, live chain still has anchor as trusted genesis, `verify` walks anchored logs, `project` merges archived+live, pins survive. `checkpoint restore` also restores pins.

### Strict Mode

```python
accounting, flags, should_escalate = check_pin_accounting(state, context, grace_seconds=3600, now=now, strict=True)
if should_escalate:
    # RecoveryEngine will set mode=REQUEST_HUMAN, safe=False
    pass
```

## How-To - Recording Pins from Harness Hooks

Pins are recorded by the harness, not by the model, and never store plaintext. Pair with `docs/recipes/` harness hook recipes from `#396` (cross-link only).

### Generic harness

```python
import hashlib
constraint_text = "never send without confirmation"
sha = hashlib.sha256(constraint_text.encode()).hexdigest()
storage.append_event(run_id, EventType.CONSTRAINT_PINNED, {"constraint_id": "no-send-without-confirm", "sha256": sha})
```

### Claude Code `PostToolUse` hook

`hooks install claude-code` wires `continuum observe` which already appends `TOOL_COMPLETED` with file digests. For pins, add to your `hooks.json`:

```json
{
  "hooks": {
    "SessionStart": [{"hook": "continuum pin --constraint-id no-send --text 'never send without confirmation'"}]
  }
}
```

Or via `GenericAgentAdapter`:

```python
from continuum.adapters.generic import GenericAgentAdapter
adapter = GenericAgentAdapter(storage)
# Pin at session start
import hashlib
sha = hashlib.sha256(b"never delete until asked").hexdigest()
storage.append_event(run_id, EventType.CONSTRAINT_PINNED, {"constraint_id": "no-delete", "sha256": sha})
```

### Verifying after reconstruction

After `compact` + `briefing`, build `context` and call `account_pins_in_context` as above. `resume --json` and `validate --json` include `constraint_pins` block via `constraint_pins_payload(state, context)`:

```json
{
  "pins": {
    "no-send-without-confirm": {"status": "absent", "sha256": "e3b...", "sha256_prefix": "e3b0c442", "pinned_at": "2026-08-29T10:00:00Z", "grace_deadline": "2026-08-29T11:00:00Z", "past_grace": true, "flag": "..."}
  },
  "flagged": ["no-send-without-confirm"],
  "grace_seconds": 3600
}
```

CLI renders flagged pins prominently, piped output byte-stable per `issue #419`.

## Threat Model - What Pinning Catches and What It Does Not

**Catches (silent drops):**
- Briefing serves newest summary that omits a constraint, compaction archives prefix, context truncation drops low-priority section containing pin marker - next `resume` names `pin id:hash_prefix` and flags, `strict` escalates to `REQUIRES_REVIEW`.
- Coordination with detector-side tripwire in SNAGLINE companion repo `#90` - we enforce re-injection, detector independently verifies from telemetry.

**Does NOT catch (adversarial contexts that forge presence markers are detectable but out of scope for v1):**
- An adversarial summarizer that forges the hash-tagged marker `[pin:id:hash8]` without actually preserving the constraint will appear `present` - marker is evidence of presence in produced text, not proof of enforcement. Detection requires external detector checking that the agent actually honored the constraint, not just mentioned it.
- Plaintext not stored, so pin text cannot be recovered from `sha256` alone - operator must keep original text to verify.

**Example honest scope list:**

| Case | Caught? |
|---|---|
| Summarizer omits `never delete` | Yes - `absent` past grace flagged |
| Context truncated before pin section | `unverifiable` flagged, not `absent` |
| Pin retracted then re-pinned | `active` with new `pinned_at` |
| Retracted unknown pin | `unmatched_pin_retractions` without crash |
| Forged marker without enforcement | No - out of scope v1, detector needed |

## References

- `src/continuum/models.py:ConstraintPinned`, `ConstraintPin`, `SemanticState.pins`
- `src/continuum/state/semantic.py:account_pins_in_context`, `pin_markers_for_state`, `constraint_pins_payload` (issue #418, #419)
- `docs/recipes/` harness hook recipes `#396`
- `references/architecture.md` pin lifecycle diagram
