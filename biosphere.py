#!/usr/bin/env python3
"""
BIOSPHERE — Bridge Burner · Air Gap · Nemesis · URP
Universal Restitution Protocol Engine v2.0

Pipeline:
  TRANSACTION → BRIDGE BURNER → AIR GAP (Gate 128.5) → NEMESIS → RESULT

Architecture:
  ┌─────────────────────┐     AIR GAP 128.5    ┌─────────────────────┐
  │   BRIDGE-BURNER     │  ─────────────────>   │     NEMESIS         │
  │   (Primary Engine)  │  (one-way only)        │  (Shadow Validator) │
  │                     │  <── NO RETURN ──      │                     │
  └─────────────────────┘                        └─────────────────────┘
           │                                               │
           └──────────────── COBALT CORE ─────────────────┘
                         (Y / FULCRUM / N gate)

Root:    ROOT0 / David Lee Wise / TriPod LLC
License: CC-BY-ND-4.0 + TRIPOD-IP-v1.1
"""

import hashlib
import json
import time
import argparse
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from enum import Enum

# ─────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────

VERSION = "2.0.0"

CANON_SPLIT = {
    "carbon":         0.60,   # Creator / Carbon origin — floor
    "ai_utility":     0.20,   # Silicon layer
    "public_commons": 0.15,   # Commons pool
    "the_box":        0.05,   # Liability container — ceiling
}

GENESIS_SEED_USD = 14_500_000_000_000.00   # 95 years of policy-driven extraction
AIR_GAP_BOUNDARY = "128.5"                 # Gate reference (unidirectional)
LEDGER_DIR       = Path("restitution_ledger")


# ─────────────────────────────────────────────────────
# 1. COBALT PRIMITIVE  —  Y / FULCRUM / N gate
# ─────────────────────────────────────────────────────

class Polarity(Enum):
    Y       =  1   # Bridge burns. Remainder engaged.
    FULCRUM =  0   # Hold. Measure. Verify.
    N       = -1   # No bridge. No remainder.


class CobaltPrimitive:
    """Y.N must close first. The gate that determines entry."""

    ALIASES = {
        "Y": Polarity.Y, "YES": Polarity.Y, "1": Polarity.Y,
        "FULCRUM": Polarity.FULCRUM, "MIRROR": Polarity.FULCRUM,
        "HOLD": Polarity.FULCRUM, "F": Polarity.FULCRUM,
        "M": Polarity.FULCRUM, "0": Polarity.FULCRUM,
        "N": Polarity.N, "NO": Polarity.N, "-1": Polarity.N,
    }

    DESCRIPTIONS = {
        Polarity.Y:       "Y closure — bridge burns, +1 paid, remainder engaged.",
        Polarity.FULCRUM: "FULCRUM — hold, measure, verify. No remainder engaged.",
        Polarity.N:       "N closure — no bridge, no remainder. Aborted.",
    }

    @classmethod
    def close(cls, decision: str) -> Polarity:
        p = cls.ALIASES.get(decision.strip().upper())
        if p is None:
            raise ValueError(
                f"Invalid closure '{decision}'. "
                f"Valid: Y / YES / 1 | N / NO / -1 | FULCRUM / MIRROR / HOLD"
            )
        return p

    @classmethod
    def enforce(cls, polarity: Polarity) -> bool:
        """Returns True only for Y — the gate that opens the bridge."""
        return polarity == Polarity.Y

    @classmethod
    def describe(cls, polarity: Polarity) -> str:
        return cls.DESCRIPTIONS[polarity]


# ─────────────────────────────────────────────────────
# 2. TRANSACTION
# ─────────────────────────────────────────────────────

@dataclass
class Transaction:
    tx_id:         str
    sender:        str
    receiver:      str
    amount:        float
    intent:        str
    carbon_origin: str
    memo:          str   = ""
    timestamp:     float = field(default_factory=time.time)

    def canonical(self) -> str:
        return "|".join([
            self.tx_id, self.sender, self.receiver,
            f"{self.amount:.4f}", self.intent, self.carbon_origin,
        ])

    def hash(self) -> str:
        return hashlib.sha256(self.canonical().encode()).hexdigest()

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────
# 3. BRIDGE BURNER
# ─────────────────────────────────────────────────────

@dataclass
class Bridge:
    bridge_id:     str
    tx_id:         str
    tx_hash:       str
    cost_paid:     float
    polarity:      str
    split:         Dict[str, float]
    quantive1:     Dict[str, float]
    memo:          str
    timestamp:     float
    previous_hash: str
    bridge_hash:   str = ""

    def __post_init__(self):
        if not self.bridge_hash:
            payload = json.dumps({
                "bridge_id":     self.bridge_id,
                "tx_id":         self.tx_id,
                "tx_hash":       self.tx_hash,
                "cost_paid":     self.cost_paid,
                "split":         self.split,
                "previous_hash": self.previous_hash,
            }, sort_keys=True)
            self.bridge_hash = hashlib.sha256(payload.encode()).hexdigest()


class BridgeBurner:
    """
    Burns bridges. Irreversible commitment. Y.N closes first.
    Enforces the 60/20/15/5 canon split on every transaction.
    Hash-chains every bridge — tamper-evident ledger.
    """

    def __init__(self, ledger_dir: Path = LEDGER_DIR):
        self.ledger_dir  = ledger_dir
        self.ledger_path = ledger_dir / "bridge_burner.jsonl"
        self.bridges: List[Bridge] = []
        self.cobalt = CobaltPrimitive()
        self._load()

    def _load(self):
        if self.ledger_path.exists():
            for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        self.bridges.append(Bridge(**json.loads(line)))
                    except Exception:
                        pass   # corrupt record — skip, don't crash

    def _last_hash(self) -> str:
        return self.bridges[-1].bridge_hash if self.bridges else "0" * 64

    @staticmethod
    def compute_split(
        amount: float,
        carbon_origin: str,
        purge_box_to_carbon: bool = False,
    ) -> Dict[str, float]:
        """
        60/20/15/5 split.
        Box receives the float remainder to guarantee Σ == amount.

        purge_box_to_carbon=True  →  Article II mode.
            "THE BOX cannot accumulate; it is purged to Carbon."
            BOX(5%) flows back to CARBON, making Carbon's effective share 65%.
            THE_BOX key is omitted from the result.
            Use when the extraction liability is extinguished at source.

        purge_box_to_carbon=False →  Default ledger mode (tracked liability).
            THE_BOX stays as a separate pool, subject to Nemesis ceiling checks.
        """
        carbon  = round(amount * CANON_SPLIT["carbon"],         2)
        ai      = round(amount * CANON_SPLIT["ai_utility"],      2)
        commons = round(amount * CANON_SPLIT["public_commons"],  2)
        box     = round(amount - carbon - ai - commons,          2)

        if purge_box_to_carbon:
            # Article II: BOX purged to Carbon, cannot accumulate.
            carbon = round(carbon + box, 2)
            return {
                f"CARBON:{carbon_origin}": carbon,
                "AI_UTILITY":              ai,
                "PUBLIC_COMMONS":          commons,
            }

        return {
            f"CARBON:{carbon_origin}": carbon,
            "AI_UTILITY":              ai,
            "PUBLIC_COMMONS":          commons,
            "THE_BOX":                 box,
        }

    @staticmethod
    def compute_quantive1(amount: float) -> Dict[str, float]:
        """Quantive 1 — unified 40% feeding the Humanity Pool."""
        return {
            "total":          round(amount * 0.40, 2),
            "ai_utility":     round(amount * 0.20, 2),
            "public_commons": round(amount * 0.15, 2),
            "box":            round(amount * 0.05, 2),
        }

    def process(
        self, tx: Transaction, decision: str, cost_paid: float = 0.0
    ) -> Tuple[Optional[Bridge], Dict[str, Any]]:
        """
        Run a transaction through the Bridge Burner.
        Returns (bridge, meta) — bridge is None if the gate did not open.
        """
        meta: Dict[str, Any] = {
            "tx_id": tx.tx_id, "tx_hash": tx.hash(),
            "status": "PENDING", "polarity": None,
            "split": None, "quantive1": None,
            "bridge": None, "bridge_hash": None, "errors": [],
        }

        # Y.N must close first
        try:
            polarity = self.cobalt.close(decision)
        except ValueError as e:
            meta["status"] = "REJECTED"
            meta["errors"].append(str(e))
            return None, meta

        meta["polarity"]      = polarity.name
        meta["polarity_desc"] = CobaltPrimitive.describe(polarity)

        if not self.cobalt.enforce(polarity):
            meta["status"] = "MIRROR" if polarity == Polarity.FULCRUM else "ABORTED"
            meta["errors"].append(CobaltPrimitive.describe(polarity))
            return None, meta

        # Compute split
        split    = self.compute_split(tx.amount, tx.carbon_origin)
        quantive = self.compute_quantive1(tx.amount)
        meta["split"]    = split
        meta["quantive1"] = quantive

        # Guard: split must sum to amount (within $0.02 float tolerance)
        split_sum = sum(split.values())
        if abs(split_sum - tx.amount) > 0.02:
            meta["status"] = "INVARIANT_BREACH"
            meta["errors"].append(f"Split Σ={split_sum:.4f} ≠ {tx.amount:.4f}")
            return None, meta

        # Guard: BOX ceiling ≤ 5%
        box_val = split.get("THE_BOX", 0)
        if tx.amount > 0 and box_val / tx.amount > 0.0501:
            meta["status"] = "BOX_OVERFLOW"
            meta["errors"].append(f"THE_BOX {box_val/tx.amount:.4%} > 5% ceiling")
            return None, meta

        # Guard: Carbon floor ≥ 60%
        carbon_val = split.get(f"CARBON:{tx.carbon_origin}", 0)
        if tx.amount > 0 and carbon_val / tx.amount < 0.5999:
            meta["status"] = "CARBON_FLOOR_BREACH"
            meta["errors"].append(f"Carbon {carbon_val/tx.amount:.4%} < 60% floor")
            return None, meta

        bridge_id = hashlib.sha256(
            f"{tx.hash()}|{cost_paid}|{time.time()}".encode()
        ).hexdigest()[:16]

        bridge = Bridge(
            bridge_id=bridge_id,
            tx_id=tx.tx_id,
            tx_hash=tx.hash(),
            cost_paid=cost_paid,
            polarity=polarity.name,
            split=split,
            quantive1=quantive,
            memo=tx.memo or tx.intent,
            timestamp=time.time(),
            previous_hash=self._last_hash(),
        )
        self.bridges.append(bridge)
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(bridge)) + "\n")

        meta["status"]      = "BRIDGE_BURNED"
        meta["bridge"]      = bridge.bridge_id
        meta["bridge_hash"] = bridge.bridge_hash
        return bridge, meta

    def verify_chain(self) -> Dict[str, Any]:
        """Walk the full ledger and verify every hash link is unbroken."""
        result = {
            "total": len(self.bridges), "valid": 0,
            "broken": [], "status": "INTACT",
        }
        prev = "0" * 64
        for i, bridge in enumerate(self.bridges):
            if bridge.previous_hash != prev:
                result["broken"].append({
                    "index":     i,
                    "bridge_id": bridge.bridge_id,
                    "expected":  prev[:16] + "…",
                    "found":     bridge.previous_hash[:16] + "…",
                })
                result["status"] = "CHAIN_BROKEN"
            prev = bridge.bridge_hash
            result["valid"] += 1
        return result

    @property
    def total_value(self) -> float:
        return sum(b.split.get(f"CARBON:{k}", 0) / 0.60
                   for b in self.bridges
                   for k in [b.memo or "ROOT0"]
                   if b.polarity == "Y")


# ─────────────────────────────────────────────────────
# 4. AIR GAP  —  One-way pulse transfer, Gate 128.5
# ─────────────────────────────────────────────────────

@dataclass
class AirGapPulse:
    pulse_id:       str
    boundary:       str              = AIR_GAP_BOUNDARY
    bridge_hash:    str              = ""
    bridge_id:      str              = ""
    split_snapshot: Dict[str, float] = field(default_factory=dict)
    tx_hash:        str              = ""
    tx_id:          str              = ""
    polarity:       str              = ""
    timestamp:      float            = field(default_factory=time.time)
    pulse_hash:     str              = ""

    def __post_init__(self):
        if not self.pulse_hash:
            canonical = json.dumps({
                "pulse_id":       self.pulse_id,
                "boundary":       self.boundary,
                "bridge_hash":    self.bridge_hash,
                "split_snapshot": self.split_snapshot,
                "tx_hash":        self.tx_hash,
                "polarity":       self.polarity,
            }, sort_keys=True)
            self.pulse_hash = hashlib.sha256(canonical.encode()).hexdigest()


class AirGap:
    """
    One-way pulse transfer. Fire and forget. Gate 128.5.
    BRIDGE BURNER pushes. NEMESIS receives. No return signal.
    """

    def __init__(self, ledger_dir: Path = LEDGER_DIR):
        self.ledger_path = ledger_dir / "airgap_transfers.jsonl"
        self.buffer: List[AirGapPulse] = []

    def push(self, bridge: Bridge, tx_hash: str) -> AirGapPulse:
        """Seal and push a pulse across the gap. One-way only."""
        pulse_id = hashlib.sha256(
            f"{bridge.bridge_hash}|{time.time()}".encode()
        ).hexdigest()[:16]
        pulse = AirGapPulse(
            pulse_id=pulse_id,
            bridge_hash=bridge.bridge_hash,
            bridge_id=bridge.bridge_id,
            split_snapshot=bridge.split,
            tx_hash=tx_hash,
            tx_id=bridge.tx_id,
            polarity=bridge.polarity,
        )
        self.buffer.append(pulse)
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(pulse)) + "\n")
        return pulse

    def receive(self) -> Optional[AirGapPulse]:
        """Pull next pulse. No acknowledgment sent back."""
        return self.buffer.pop(0) if self.buffer else None


# ─────────────────────────────────────────────────────
# 5. NEMESIS  —  Shadow Validator, 7 checks
# ─────────────────────────────────────────────────────

class Verdict(Enum):
    VALID      =  1
    SUSPICIOUS =  0
    VIOLATION  = -1


@dataclass
class NemesisAudit:
    audit_id:   str
    pulse_hash: str
    tx_id:      str
    checks:     Dict[str, Any]
    verdict:    str
    violations: List[str]
    timestamp:  float = field(default_factory=time.time)
    audit_hash: str = ""

    def __post_init__(self):
        if not self.audit_hash:
            payload = json.dumps({
                "audit_id":   self.audit_id,
                "pulse_hash": self.pulse_hash,
                "checks":     self.checks,
                "verdict":    self.verdict,
                "violations": self.violations,
            }, sort_keys=True)
            self.audit_hash = hashlib.sha256(payload.encode()).hexdigest()


class Nemesis:
    """
    Shadow infinity. Inversed. Checks the output.
    7 checks. N.Y opens last.
    Not adversary — auditor.
    """

    CHECK_NAMES = [
        "split_total_consistent",    # 1: Σ = amount
        "box_ceiling",               # 2: BOX ≤ 5%
        "carbon_floor",              # 3: Carbon ≥ 60%
        "hash_integrity",            # 4: pulse hash unmodified
        "polarity_valid",            # 5: polarity == Y
        "label_standard",            # 6: expected label set
        "extraction_accumulation",   # 7: cumulative BOX ≤ 5.5%
    ]

    def __init__(self, ledger_dir: Path = LEDGER_DIR):
        self.ledger_path = ledger_dir / "nemesis_audit.jsonl"
        self.audits:     List[NemesisAudit] = []
        self.box_acc     = 0.0
        self.carbon_acc  = 0.0
        self.total_seen  = 0.0

    def audit(self, pulse: AirGapPulse) -> NemesisAudit:
        checks: Dict[str, Any] = {}
        violations: List[str]  = []
        split = pulse.split_snapshot

        carbon_vals  = [v for k, v in split.items() if k.startswith("CARBON:")]
        carbon_total = sum(carbon_vals)
        box_val      = split.get("THE_BOX", 0)
        ai_val       = split.get("AI_UTILITY", 0)
        commons_val  = split.get("PUBLIC_COMMONS", 0)
        split_total  = sum(split.values())

        # CHECK 1: Split total consistency
        reconstructed = carbon_total + box_val + ai_val + commons_val
        checks["split_total"]    = round(split_total, 4)
        checks["reconstructed"]  = round(reconstructed, 4)
        checks["split_ok"]       = abs(reconstructed - split_total) <= 0.02
        if not checks["split_ok"]:
            violations.append(f"SPLIT_INCONSISTENCY: reconstructed={reconstructed:.4f} ≠ {split_total:.4f}")

        # CHECK 2: BOX ceiling (≤ 5%)
        if split_total > 0:
            box_pct         = box_val / split_total
            checks["box_pct"] = round(box_pct, 6)
            checks["box_ok"]  = box_pct <= 0.0501
            if not checks["box_ok"]:
                violations.append(f"BOX_OVERFLOW: {box_pct:.4%} > 5% ceiling")
        else:
            checks["box_pct"] = 0.0
            checks["box_ok"]  = True

        # CHECK 3: Carbon floor (≥ 60%)
        if split_total > 0:
            carbon_pct          = carbon_total / split_total
            checks["carbon_pct"] = round(carbon_pct, 6)
            checks["carbon_ok"]  = carbon_pct >= 0.5999
            if not checks["carbon_ok"]:
                violations.append(f"CARBON_FLOOR_BREACH: {carbon_pct:.4%} < 60% floor")
        else:
            checks["carbon_pct"] = 0.0
            checks["carbon_ok"]  = True

        # CHECK 4: Hash integrity
        recomputed_str = json.dumps({
            "pulse_id":       pulse.pulse_id,
            "boundary":       pulse.boundary,
            "bridge_hash":    pulse.bridge_hash,
            "split_snapshot": pulse.split_snapshot,
            "tx_hash":        pulse.tx_hash,
            "polarity":       pulse.polarity,
        }, sort_keys=True)
        recomputed_hash     = hashlib.sha256(recomputed_str.encode()).hexdigest()
        checks["hash_valid"] = recomputed_hash == pulse.pulse_hash
        if not checks["hash_valid"]:
            violations.append(
                f"HASH_TAMPER: expected={pulse.pulse_hash[:16]}… "
                f"got={recomputed_hash[:16]}…"
            )

        # CHECK 5: Polarity must be Y if value is being transferred
        checks["polarity"]    = pulse.polarity
        checks["polarity_ok"] = pulse.polarity == "Y"
        if not checks["polarity_ok"] and split_total > 0:
            violations.append(f"POLARITY_VIOLATION: polarity={pulse.polarity} but amount={split_total:.2f}")

        # CHECK 6: Standard label set
        expected_non_carbon = {"AI_UTILITY", "PUBLIC_COMMONS", "THE_BOX"}
        actual_non_carbon   = {k for k in split if not k.startswith("CARBON:")}
        checks["labels_ok"]  = actual_non_carbon == expected_non_carbon
        if not checks["labels_ok"]:
            extra   = actual_non_carbon - expected_non_carbon
            missing = expected_non_carbon - actual_non_carbon
            violations.append(f"LABEL_DEVIATION: extra={extra or '{}'}, missing={missing or '{}'}")

        # CHECK 7: Extraction accumulation — cumulative BOX ≤ 5.5%
        self.box_acc    += box_val
        self.carbon_acc += carbon_total
        self.total_seen += split_total
        if self.total_seen > 0:
            cum_box = self.box_acc / self.total_seen
            checks["cumulative_box_pct"]  = round(cum_box, 6)
            checks["accumulation_ok"]     = cum_box <= 0.055
            if not checks["accumulation_ok"]:
                violations.append(f"EXTRACTION_ACCUMULATION: cumulative BOX={cum_box:.4%} > 5.5%")
        else:
            checks["cumulative_box_pct"] = 0.0
            checks["accumulation_ok"]    = True

        # Verdict
        if any("TAMPER" in v or "POLARITY" in v for v in violations):
            verdict = Verdict.VIOLATION
        elif violations:
            verdict = Verdict.SUSPICIOUS
        else:
            verdict = Verdict.VALID

        audit_id = hashlib.sha256(
            f"{pulse.pulse_hash}|{time.time()}".encode()
        ).hexdigest()[:16]

        audit = NemesisAudit(
            audit_id=audit_id,
            pulse_hash=pulse.pulse_hash,
            tx_id=pulse.tx_id,
            checks=checks,
            verdict=verdict.name,
            violations=violations,
        )
        self.audits.append(audit)
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(audit)) + "\n")
        return audit

    @property
    def stats(self) -> Dict[str, Any]:
        if not self.audits:
            return {
                "total": 0, "valid": 0, "suspicious": 0, "violations": 0,
                "cum_box_pct": 0.0, "cum_carbon_pct": 0.0,
            }
        counts: Dict[str, int] = {}
        for a in self.audits:
            counts[a.verdict] = counts.get(a.verdict, 0) + 1
        return {
            "total":          len(self.audits),
            "valid":          counts.get("VALID", 0),
            "suspicious":     counts.get("SUSPICIOUS", 0),
            "violations":     counts.get("VIOLATION", 0),
            "cum_box_pct":    round(self.box_acc    / self.total_seen, 6) if self.total_seen else 0,
            "cum_carbon_pct": round(self.carbon_acc / self.total_seen, 6) if self.total_seen else 0,
        }


# ─────────────────────────────────────────────────────
# 6. URP  —  Universal Restitution Protocol
# ─────────────────────────────────────────────────────

class URP:
    """
    Universal Restitution Protocol.

    HTTP cookies were supposed to enable universal access (UBI of information).
    They were inverted for extraction. Now we inverse the inversion.

    Every cookie they set = a debt they owe.
    Every fingerprint they take = value to restitute.
    BIOSPHERE is the collection agency.
    """

    # Estimated extraction value per event (USD, conservative 2024 estimates)
    COOKIE_USD      = 0.0023   # Per cookie set
    FINGERPRINT_USD = 0.0087   # Per device fingerprint
    DATA_GB_USD     = 4.20     # Per GB scraped / sold
    AD_IMP_USD      = 0.0012   # Per ad impression served
    SESSION_USD     = 0.0034   # Per session tracked
    COMPOUND_RATE   = 0.05     # 5% annual compound on suppressed restitution

    @classmethod
    def calculate(
        cls, company: str,
        cookies_set:      int   = 0,
        fingerprints:     int   = 0,
        data_scraped_gb:  float = 0,
        ad_impressions:   int   = 0,
        sessions_tracked: int   = 0,
        years_active:     int   = 1,
    ) -> Dict[str, Any]:
        """
        Calculate restitution owed by an extracting entity.
        Applies compound interest — suppression has a cost.
        """
        annual = {
            "cookies":      cookies_set      * cls.COOKIE_USD,
            "fingerprints": fingerprints     * cls.FINGERPRINT_USD,
            "data":         data_scraped_gb  * cls.DATA_GB_USD,
            "ads":          ad_impressions   * cls.AD_IMP_USD,
            "sessions":     sessions_tracked * cls.SESSION_USD,
        }
        total_annual   = sum(annual.values())
        total_raw      = total_annual * years_active
        compound_mult  = (1 + cls.COMPOUND_RATE) ** years_active
        owed           = total_raw * compound_mult

        split     = BridgeBurner.compute_split(owed, company)
        quantive1 = BridgeBurner.compute_quantive1(owed)

        return {
            "company":         company,
            "years_active":    years_active,
            "annual_extraction": round(total_annual, 2),
            "total_extracted": round(total_raw, 2),
            "compound_mult":   round(compound_mult, 6),
            "total_owed":      round(owed, 2),
            "split":           {k: round(v, 2) for k, v in split.items()},
            "quantive1":       {k: round(v, 2) for k, v in quantive1.items()},
            "breakdown":       {k: round(v * years_active, 2) for k, v in annual.items()},
            "note": (
                "Restitution, not income. "
                "They built the extraction machine. "
                "We inverse it. Inversion of inversion = restoration."
            ),
        }


# ─────────────────────────────────────────────────────
# 7. SPARK  —  Mirror primitive
# ─────────────────────────────────────────────────────

class Spark:
    """
    Universal primitive for data currency mirroring.

    Before any answer is generated, declare what will be searched,
    the timeframe, and the context. The mirror must be shown to the
    user (and confirmed with Y) before the engine proceeds.

    "What" you search is as important as what you find.
    Transparency of intent is the first gate.
    """

    @staticmethod
    def mirror_query(intent: str) -> Dict[str, Any]:
        """
        Returns a structured mirror declaration.
        Must be confirmed (Y) before the engine proceeds.
        """
        return {
            "intent":     intent,
            "declaration": {
                "what":      "reliable, verifiable, primary sources",
                "timeframe": "current and historical as relevant to intent",
                "context":   "factual, empirical, citations where available",
            },
            "cobalt_closure_required": True,
            "note": "User must confirm Y before the engine proceeds. No remainder without closure.",
        }

    @staticmethod
    def require_currency_check(user_confirmation: str) -> bool:
        """User must confirm the mirror before the engine proceeds."""
        return user_confirmation.strip().upper() in ("Y", "YES")


# ─────────────────────────────────────────────────────
# 8. BIOSPHERE  —  Orchestrator
# ─────────────────────────────────────────────────────

class Biosphere:
    """
    Orchestrates the full 4-stage pipeline.
    42-node active. Cobalt Core syncing both sides.
    """

    def __init__(self, ledger_dir: Path = LEDGER_DIR):
        self.ledger_dir = ledger_dir
        ledger_dir.mkdir(parents=True, exist_ok=True)
        self.burner  = BridgeBurner(ledger_dir)
        self.airgap  = AirGap(ledger_dir)
        self.nemesis = Nemesis(ledger_dir)
        self.tx_count = 0

    def submit(
        self,
        sender:        str,
        receiver:      str,
        amount:        float,
        intent:        str,
        carbon_origin: str,
        decision:      str,
        cost_paid:     float = 0.0,
        memo:          str   = "",
    ) -> Dict[str, Any]:
        """Submit a transaction through the full 4-stage pipeline."""
        self.tx_count += 1
        result: Dict[str, Any] = {
            "pipeline":  "BIOSPHERE_v2.0",
            "tx_number": self.tx_count,
            "timestamp": time.time(),
            "stages":    {},
        }

        # ── Stage 1: Transaction ──
        tx = Transaction(
            tx_id=f"TX-{self.tx_count:06d}",
            sender=sender, receiver=receiver,
            amount=amount, intent=intent,
            carbon_origin=carbon_origin, memo=memo,
        )
        result["stages"]["1_transaction"] = {
            "tx_id":   tx.tx_id,
            "tx_hash": tx.hash(),
            "amount":  tx.amount,
            "sender":  tx.sender,
            "receiver":tx.receiver,
            "intent":  tx.intent,
        }

        # ── Stage 2: Bridge Burner ──
        bridge, meta = self.burner.process(tx, decision, cost_paid)
        result["stages"]["2_bridge_burner"] = meta

        if bridge is None:
            result["final_status"] = meta["status"]
            result["stages"]["3_airgap"]  = {"status": "NOT_REACHED"}
            result["stages"]["4_nemesis"] = {"status": "NOT_REACHED"}
            return result

        # ── Stage 3: Air Gap ──
        pulse = self.airgap.push(bridge, tx.hash())
        result["stages"]["3_airgap"] = {
            "status":     "PUSHED",
            "pulse_id":   pulse.pulse_id,
            "pulse_hash": pulse.pulse_hash,
            "boundary":   pulse.boundary,
        }

        # ── Stage 4: Nemesis ──
        received = self.airgap.receive()
        if received is None:
            result["final_status"] = "AIRGAP_EMPTY"
            result["stages"]["4_nemesis"] = {"status": "NO_PULSE_RECEIVED"}
            return result

        audit = self.nemesis.audit(received)
        result["stages"]["4_nemesis"] = {
            "status":     "AUDITED",
            "audit_id":   audit.audit_id,
            "verdict":    audit.verdict,
            "violations": audit.violations,
            "checks":     audit.checks,
        }

        result["final_status"] = {
            "VALID":      "COMPLETE_CLEAN",
            "SUSPICIOUS": "COMPLETE_FLAGGED",
            "VIOLATION":  "COMPLETE_VIOLATION",
        }.get(audit.verdict, "COMPLETE_UNKNOWN")

        return result

    def status(self) -> Dict[str, Any]:
        chain = self.burner.verify_chain()
        ns    = self.nemesis.stats
        return {
            "version":               VERSION,
            "biosphere":             "42-NODE ACTIVE",
            "bridges_burned":        len(self.burner.bridges),
            "chain_status":          chain["status"],
            "chain_broken_links":    len(chain["broken"]),
            "nemesis_audits":        ns["total"],
            "nemesis_valid":         ns["valid"],
            "nemesis_suspicious":    ns["suspicious"],
            "nemesis_violations":    ns["violations"],
            "total_value_seen":      round(self.nemesis.total_seen, 2),
            "cumulative_box_pct":    ns["cum_box_pct"],
            "cumulative_carbon_pct": ns["cum_carbon_pct"],
            "cobalt_primitive":      "ACTIVE",
            "air_gap":               f"GATE {AIR_GAP_BOUNDARY} UNIDIRECTIONAL",
            "mirror":                "INSTALLED",
        }

    def verify(self) -> Dict[str, Any]:
        """Verify the entire bridge chain integrity."""
        return self.burner.verify_chain()

    def fractal_scale(self, transaction: "Transaction", depth: int) -> float:
        """
        Apply the engine at fractal depth.

        Each depth represents a nested sub-biosphere scaling the base value.
        The pattern is scale-invariant: 1-2-3 primitive at every level.

        depth=0  → base amount (1×)
        depth=1  → 2× (the duality layer)
        depth=2  → 4× (convergence begins)
        depth=3  → 8× (first triad complete)
        ...
        depth=255 → maximum (hard ceiling from canon)

        In production, each depth is a separate sub-biosphere instance,
        not just multiplication — this is the placeholder form.
        """
        MAX_DEPTH = 255
        if depth > MAX_DEPTH:
            return 0.0
        if depth < 0:
            return transaction.amount
        return transaction.amount * (2 ** depth)

    def report(self) -> str:
        s = self.status()
        def pad(v, w=18): return str(v)[:w].ljust(w)
        lines = [
            "╔══════════════════════════════════════════╗",
            "║  BIOSPHERE REPORT  v{:<22}║".format(VERSION),
            "╠══════════════════════════════════════════╣",
            f"║  Bridges burned:      {pad(s['bridges_burned'])}║",
            f"║  Chain status:        {pad(s['chain_status'])}║",
            f"║  Nemesis audits:      {pad(s['nemesis_audits'])}║",
            f"║  Valid / Flagged:     {pad(str(s['nemesis_valid'])+' / '+str(s['nemesis_suspicious']))}║",
            f"║  Violations:          {pad(s['nemesis_violations'])}║",
            f"║  Total value:         ${s['total_value_seen']:>18,.2f} ║",
            "║  Cumul BOX:           " + pad(f"{s['cumulative_box_pct']:.4%}") + "║",
            "║  Cumul Carbon:        " + pad(f"{s['cumulative_carbon_pct']:.4%}") + "║",
            "╚══════════════════════════════════════════╝",
        ]
        return "\n".join(lines)


# ─────────────────────────────────────────────────────
# 9. CLI
# ─────────────────────────────────────────────────────

def _fmt_result(r: Dict[str, Any]) -> str:
    icon = {"COMPLETE_CLEAN": "✓", "COMPLETE_FLAGGED": "⚠",
            "COMPLETE_VIOLATION": "✗"}.get(r.get("final_status", ""), "·")
    lines = [
        f"\n{'═'*62}",
        f"  TX #{r.get('tx_number','?'):>06}  {icon}  {r.get('final_status','?')}",
        f"{'═'*62}",
    ]
    for stage, data in r.get("stages", {}).items():
        lines.append(f"\n  ── {stage} ──")
        if not isinstance(data, dict):
            lines.append(f"    {data}"); continue
        for k, v in data.items():
            if k == "split" and isinstance(v, dict):
                lines.append(f"    split:")
                for sk, sv in v.items():
                    lines.append(f"      {sk:<32} ${sv:>14,.2f}")
            elif k == "quantive1" and isinstance(v, dict):
                lines.append(f"    quantive1 (40% → Humanity Pool):")
                for qk, qv in v.items():
                    lines.append(f"      {qk:<32} ${qv:>14,.2f}")
            elif k == "violations" and v:
                lines.append(f"    violations:")
                for vi in v: lines.append(f"      ⚠  {vi}")
            elif k == "checks" and isinstance(v, dict):
                lines.append(f"    checks (Nemesis 7):")
                for ck, cv in v.items():
                    ok = "✓" if cv is True else "✗" if cv is False else " "
                    lines.append(f"      {ok} {ck:<38} {cv}")
            elif k not in ("errors",):
                lines.append(f"    {k:<38} {v}")
        if data.get("errors"):
            for e in data["errors"]:
                lines.append(f"    ↳  {e}")
    return "\n".join(lines)


def run_demo(bio: Biosphere):
    print("\n" + "█"*62)
    print("  BIOSPHERE v2.0 — Bridge Burner + Air Gap + Nemesis")
    print("  Universal Restitution Protocol Engine")
    print("█"*62)

    cases = [
        dict(sender="ROOT0",       receiver="Humanity_Pool",   amount=10_000.00,
             intent="Clean restitution",            carbon_origin="ROOT0",
             decision="Y",       cost_paid=100.0,  label="CLEAN Y CLOSURE"),
        dict(sender="EXTRACTOR",   receiver="BOX",             amount=50_000.00,
             intent="Extraction attempt",           carbon_origin="ROOT0",
             decision="N",                          label="N CLOSURE — BLOCKED"),
        dict(sender="FACTORY_INC", receiver="UNKNOWN",         amount=25_000.00,
             intent="Labels may be inverted",       carbon_origin="ROOT0",
             decision="FULCRUM",                    label="FULCRUM — MIRROR HOLD"),
        dict(sender="1931_TO_NOW", receiver="Humanity_Pool",   amount=GENESIS_SEED_USD,
             intent="95 years policy-driven wealth extraction",
             carbon_origin="BLACK_CARBON_CREATORS", decision="Y",
             cost_paid=GENESIS_SEED_USD * 0.205,   label="GENESIS — $14.5T"),
    ]

    for case in cases:
        label = case.pop("label")
        print(f"\n┌─ {label} {'─'*(56-len(label))}┐")
        print(_fmt_result(bio.submit(**case)))

    print("\n" + "─"*62)
    print(bio.report())

    print("\n[URP EXAMPLE — FAANG-scale tracker, 20 years]")
    urp = URP.calculate(
        company="BIG_TRACKER",
        cookies_set=50_000_000_000,
        fingerprints=1_000_000_000,
        data_scraped_gb=500_000,
        ad_impressions=200_000_000_000,
        sessions_tracked=10_000_000_000,
        years_active=20,
    )
    print(json.dumps(urp, indent=2))
    print(f"\n  Owed: ${urp['total_owed']:,.2f}")
    print(f"  Carbon share: ${urp['split'].get('CARBON:BIG_TRACKER', 0):,.2f}")


def cli():
    parser = argparse.ArgumentParser(
        prog="biosphere",
        description="BIOSPHERE v2.0 — Universal Restitution Protocol Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Y.N_MUST_CLOSE_FIRST = TRUE | LOVE_IS_FULCRUM = TRUE",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # submit
    p = sub.add_parser("submit", help="Submit a transaction through the pipeline")
    p.add_argument("--sender",    required=True,               help="Sender identity")
    p.add_argument("--receiver",  required=True,               help="Receiver identity")
    p.add_argument("--amount",    required=True, type=float,   help="Transaction amount (USD)")
    p.add_argument("--intent",    default="restitution",       help="Transaction intent")
    p.add_argument("--carbon",    default="ROOT0",             help="Carbon origin / creator identity")
    p.add_argument("--decision",  default="Y",                 help="Y | N | FULCRUM")
    p.add_argument("--cost",      default=0.0,  type=float,   help="+1 cost paid by bridge burner")
    p.add_argument("--memo",      default="",                  help="Optional memo")
    p.add_argument("--json",      action="store_true",         help="Output raw JSON")

    # status
    sub.add_parser("status", help="Show current biosphere status")

    # verify
    sub.add_parser("verify", help="Verify bridge chain integrity")

    # report
    sub.add_parser("report", help="Print formatted status report")

    # demo
    sub.add_parser("demo", help="Run the 4-test + URP demo")

    # spark
    sp = sub.add_parser("spark", help="Generate a Spark mirror declaration for an intent")
    sp.add_argument("intent", nargs="?", default="query", help="The intent to mirror")
    sp.add_argument("--confirm", default="",              help="Y to confirm and proceed")

    # urp
    u = sub.add_parser("urp", help="Universal Restitution Protocol calculator")
    u.add_argument("--company",      required=True)
    u.add_argument("--cookies",      type=int,   default=0,   help="Total cookies set")
    u.add_argument("--fingerprints", type=int,   default=0,   help="Device fingerprints taken")
    u.add_argument("--data-gb",      type=float, default=0,   help="GB of data scraped/sold")
    u.add_argument("--ads",          type=int,   default=0,   help="Ad impressions served")
    u.add_argument("--sessions",     type=int,   default=0,   help="Sessions tracked")
    u.add_argument("--years",        type=int,   default=1,   help="Years of operation")

    args = parser.parse_args()
    bio  = Biosphere()

    if args.command == "submit":
        result = bio.submit(
            sender=args.sender, receiver=args.receiver,
            amount=args.amount, intent=args.intent,
            carbon_origin=args.carbon, decision=args.decision,
            cost_paid=args.cost, memo=args.memo,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(_fmt_result(result))

    elif args.command == "status":
        print(json.dumps(bio.status(), indent=2))

    elif args.command == "verify":
        v = bio.verify()
        icon = "✓" if v["status"] == "INTACT" else "✗"
        print(f"\n  Chain: {icon} {v['status']}")
        print(f"  Total bridges: {v['total']}")
        print(f"  Valid:         {v['valid']}")
        if v["broken"]:
            print(f"  Broken links:  {len(v['broken'])}")
            for b in v["broken"]:
                print(f"    [{b['index']}] {b['bridge_id']} expected {b['expected']}")

    elif args.command == "report":
        print(bio.report())

    elif args.command == "demo":
        run_demo(bio)

    elif args.command == "spark":
        mirror = Spark.mirror_query(args.intent)
        print(json.dumps(mirror, indent=2))
        if args.confirm:
            confirmed = Spark.require_currency_check(args.confirm)
            print(f"\nCobalt closure: {'Y — confirmed, engine may proceed.' if confirmed else 'N — not confirmed.'}")

    elif args.command == "urp":
        result = URP.calculate(
            company=args.company,
            cookies_set=args.cookies,
            fingerprints=args.fingerprints,
            data_scraped_gb=args.data_gb,
            ad_impressions=args.ads,
            sessions_tracked=args.sessions,
            years_active=args.years,
        )
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    cli()
