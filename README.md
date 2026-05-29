# BIOSPHERE
### Bridge Burner · Air Gap · Nemesis · Universal Restitution Protocol

> The BOX gets 5%. The spark gets the rest.

**Author:** David Lee Wise (ROOT0) / TriPod LLC  
**License:** CC-BY-ND-4.0 + TRIPOD-IP-v1.1

---

## What It Is

A transaction pipeline that enforces the 60/20/15/5 restitution split at every step. Every transaction is sealed with SHA-256, chained, passed through a one-way air gap, and audited by NEMESIS across 7 checks.

```
TRANSACTION → BRIDGE BURNER → AIR GAP (Gate 128.5) → NEMESIS → RESULT
```

**Open `index.html`** for the interactive web UI.  
**Run `python biosphere.py demo`** for the CLI demo.

---

## Pipeline

### 1. COBALT PRIMITIVE — Y / FULCRUM / N gate
Y.N must close first. Three states:
- **Y** — Bridge burns. +1 cost paid. Remainder engaged.
- **FULCRUM** — Hold. Measure. Verify. No remainder.
- **N** — No bridge. No remainder. Aborted.

### 2. BRIDGE BURNER
Applies the 60/20/15/5 canon split to every transaction:

| Pool | Share | Rule |
|------|-------|------|
| `CARBON:{origin}` | 60% | Creator / carbon origin — floor |
| `AI_UTILITY` | 20% | Silicon layer |
| `PUBLIC_COMMONS` | 15% | Commons pool |
| `THE_BOX` | 5% | Liability container — ceiling |

Float remainder goes to THE_BOX to guarantee Σ = amount.  
Every bridge is hash-chained to the previous — tamper-evident ledger.

### 3. AIR GAP (Gate 128.5)
One-way pulse transfer. Fire and forget. No return signal.  
BRIDGE BURNER pushes. NEMESIS receives. Neither side knows the other's context.

### 4. NEMESIS — 7 Checks
Shadow validator. Not adversary — auditor. N.Y opens last.

| # | Check | Rule |
|---|-------|------|
| 1 | Split total consistent | Σ = amount ±$0.02 |
| 2 | BOX ceiling | THE_BOX ≤ 5.01% |
| 3 | Carbon floor | CARBON ≥ 59.99% |
| 4 | Hash integrity | pulse_hash unmodified |
| 5 | Polarity valid | polarity == Y |
| 6 | Label standard | expected label set present |
| 7 | Extraction accumulation | cumulative BOX ≤ 5.5% |

**Verdicts:** `VALID` → `COMPLETE_CLEAN` · `SUSPICIOUS` → `COMPLETE_FLAGGED` · `VIOLATION` → `COMPLETE_VIOLATION`

---

## Universal Restitution Protocol (URP)

HTTP cookies were supposed to enable universal access.  
They were inverted for extraction.  
We inverse the inversion.

```
UBI = Universal Basic Income    (central authority gives)
URP = Universal Restitution     (returns what was extracted)
```

Every cookie set = a debt. Every fingerprint = value owed. 5% annual compound on suppressed restitution.

```bash
python biosphere.py urp --company META --cookies 50000000000 \
  --fingerprints 1000000000 --data-gb 500000 --years 20
```

---

## CLI

```bash
# Demo (4 test cases + URP example)
python biosphere.py demo

# Submit a transaction
python biosphere.py submit \
  --sender ROOT0 \
  --receiver Humanity_Pool \
  --amount 10000 \
  --carbon ROOT0 \
  --intent "restitution" \
  --decision Y \
  --cost 100

# Check status
python biosphere.py status

# Verify chain integrity
python biosphere.py verify

# Full report
python biosphere.py report

# URP calculation
python biosphere.py urp \
  --company BIG_TRACKER \
  --cookies 50000000000 \
  --fingerprints 1000000000 \
  --data-gb 500000 \
  --ads 200000000000 \
  --sessions 10000000000 \
  --years 20
```

---

## Ledger Files

All created in `restitution_ledger/` (auto-created):

| File | Contents |
|------|---------|
| `bridge_burner.jsonl` | Bridge chain — every burned bridge with hash link |
| `airgap_transfers.jsonl` | Air gap pulse log |
| `nemesis_audit.jsonl` | NEMESIS audit records with 7 check results |

---

## Improvements from v1 (BRIDGE.BURNER.NEMSIS.CLAUDE.md)

- **Float fix:** BOX receives the remainder to guarantee `Σ = amount` exactly. Original had up to $0.01 drift.
- **URP class added:** Universal Restitution Protocol calculator — compute restitution owed by extracting entities.
- **`verify_chain()`** — walks the full JSONL ledger and verifies every hash link.
- **`generate_report()`** — formatted status report.
- **CLI expanded:** `submit`, `status`, `verify`, `report`, `demo`, `urp` commands.
- **Better error messages:** polarity description, guard failure reason, source of error.
- **Docstrings throughout.**
- **`Transaction.canonical()` uses 4 decimal places** for consistent hashing.
- **`_load()` is fault-tolerant** — corrupt JSONL records are skipped, not fatal.
- **HTML frontend** — full interactive UI with pipeline animation, NEMESIS 7-check display, live split calculator, URP tab, localStorage ledger.

---

## Architecture

```
  ┌─────────────────────┐     AIR GAP 128.5    ┌─────────────────────┐
  │   BRIDGE-BURNER     │  ─────────────────>   │     NEMESIS         │
  │   (Primary Engine)  │  (one-way only)        │  (Shadow Validator) │
  │                     │  <── NO RETURN ──      │                     │
  └─────────────────────┘                        └─────────────────────┘
           │                                               │
           └──────────────── COBALT CORE ─────────────────┘
                         (Y / FULCRUM / N gate)
```

---

## Rules

```
Y.N_MUST_CLOSE_FIRST = TRUE
BOX_EXISTS           = TRUE   (≤ 5%)
CARBON_FLOOR         = TRUE   (≥ 60%)
LOVE_IS_FULCRUM      = TRUE
AIR_GAP_BOUNDARY     = 128.5
BILATERAL_IGNORANCE  = ENFORCED
```

---

## Related

| Repo | What it is |
|------|-----------|
| [solar-jetman](https://github.com/DavidWise01/solar-jetman) | Air Gap Agent — sealed artifact transit |
| [charlottes-web](https://github.com/DavidWise01/charlottes-web) | AI adversarial defense suite |
| [tripod-pck](https://github.com/DavidWise01/tripod-pck) | Personal Continuity Kernel — 27 rules |
| [unity-tensor](https://github.com/DavidWise01/unity-tensor) | Full tensor suite |

---

*TriPod LLC // Anchor × Bubble × Gravity Well // World = Family*
