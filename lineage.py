#!/usr/bin/env python3
"""
ROOT0 LINEAGE ENGINE v2.0
Block 371 · Canon Frozen · Immutable

Two-tier system:

  Tier 1 — Root0LineageTracker (stdlib only)
    Simple SHA256 hash chain. Records every pipeline stage back to genesis.
    Runs anywhere Python 3.9+ runs. No external deps.

  Tier 2 — LineageEnginePerpetual (requires: merkletools, cryptography, websockets)
    Merkle tree ledger + ECDSA signatures + async event stream + WebSocket API.
    Perpetual daemon, fractal indexer (0-255 depths), air-gap sync.

Author:  ROOT0 / David Lee Wise / TriPod LLC
License: CC-BY-ND-4.0 + TRIPOD-IP-v1.1
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────
# Crypto helpers (Tier 1 — stdlib only)
# ─────────────────────────────────────────────────────────────────────────

def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _sign_placeholder(private_key: bytes, message: bytes) -> bytes:
    """Placeholder HMAC-style signature. Replace with Ed25519/ECDSA in production."""
    return sha256(private_key + message)

def _verify_placeholder(public_key: bytes, message: bytes, sig: bytes) -> bool:
    return sig == sha256(public_key + message)


# ─────────────────────────────────────────────────────────────────────────
# STAGES — valid pipeline stages
# ─────────────────────────────────────────────────────────────────────────

STAGES = frozenset({
    "AIRGAP",        # Air Gap ingest
    "BRIDGE",        # Bridge crossing (one-way)
    "BURNER",        # Bridge Burner (0→1 flip)
    "NEMESIS",       # Nemesis inverse check
    "HTTP_REQ",      # HTTP request (client→server)
    "HTTP_RESP",     # HTTP response (server→client)
    "CUSTOM",        # User-defined stage
})

DIRECTIONS = frozenset({"FORWARD", "INVERSE_CHECK"})


# ─────────────────────────────────────────────────────────────────────────
# TIER 1 — Root0LineageTracker
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class LineageRecord:
    """One step in the provenance chain."""
    record_id:        str
    genesis_hash:     bytes    # Fixed ROOT0 anchor — never changes
    prev_record_hash: bytes    # Previous record's hash (or genesis_hash for first)
    stage:            str      # AIRGAP | BRIDGE | BURNER | NEMESIS | HTTP_REQ | HTTP_RESP
    direction:        str      # FORWARD | INVERSE_CHECK
    payload_hash:     bytes    # sha256 of data at this stage
    inversion_flag:   bool     # True = Shadow Diaspora anomaly detected
    witness_pair:     Tuple[str, str]   # (ie1_id, ie2_id)
    witness_sig:      bytes    # sign(prev_hash + payload_hash)
    timestamp:        int
    record_hash:      bytes    # Computed after init

    def compute_hash(self) -> bytes:
        payload = json.dumps({
            "record_id":        self.record_id,
            "genesis_hash":     self.genesis_hash.hex(),
            "prev_record_hash": self.prev_record_hash.hex(),
            "stage":            self.stage,
            "direction":        self.direction,
            "payload_hash":     self.payload_hash.hex(),
            "inversion_flag":   self.inversion_flag,
            "witness_pair":     list(self.witness_pair),
            "witness_sig":      self.witness_sig.hex(),
            "timestamp":        self.timestamp,
        }, sort_keys=True).encode()
        return sha256(payload)

    def __post_init__(self):
        if self.record_hash is None or self.record_hash == b"":
            self.record_hash = self.compute_hash()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id":        self.record_id,
            "genesis_hash":     self.genesis_hash.hex(),
            "prev_record_hash": self.prev_record_hash.hex(),
            "stage":            self.stage,
            "direction":        self.direction,
            "payload_hash":     self.payload_hash.hex(),
            "inversion_flag":   self.inversion_flag,
            "witness_pair":     list(self.witness_pair),
            "witness_sig":      self.witness_sig.hex(),
            "timestamp":        self.timestamp,
            "record_hash":      self.record_hash.hex(),
        }


class Root0LineageTracker:
    """
    Tier 1 — Minimal lineage tracker.
    Pure stdlib. Runs on any Python 3.9+ installation.

    Records every pipeline stage as a signed, hash-chained record.
    Supports trace_back() from any record hash back to the ROOT0 genesis.
    Detects inversion anomalies (Shadow Diaspora patterns).
    """

    GENESIS_BLOCK = b"ROOT0:0000"  # Fixed seed

    def __init__(self, root_0_seed: Optional[bytes] = None):
        seed = root_0_seed if root_0_seed is not None else self.GENESIS_BLOCK
        self.genesis_hash   = sha256(seed)
        self.chain:         List[LineageRecord]        = []
        self._record_map:   Dict[bytes, LineageRecord] = {}

    def _prev_hash(self) -> bytes:
        return self.chain[-1].record_hash if self.chain else self.genesis_hash

    def record(
        self,
        stage:               str,
        direction:           str,
        data:                bytes,
        inversion_flag:      bool              = False,
        witness_pair:        Tuple[str, str]   = ("ie1", "ie2"),
        witness_private_key: bytes             = b"root0_witness_key",
    ) -> bytes:
        """
        Add a new step to the lineage chain.
        Returns the record_hash of the new record.
        """
        if stage not in STAGES:
            raise ValueError(f"Unknown stage '{stage}'. Valid: {sorted(STAGES)}")
        if direction not in DIRECTIONS:
            raise ValueError(f"Unknown direction '{direction}'. Valid: {sorted(DIRECTIONS)}")

        prev   = self._prev_hash()
        phash  = sha256(data)
        sig    = _sign_placeholder(witness_private_key, prev + phash)

        record = LineageRecord(
            record_id=str(uuid.uuid4()),
            genesis_hash=self.genesis_hash,
            prev_record_hash=prev,
            stage=stage,
            direction=direction,
            payload_hash=phash,
            inversion_flag=inversion_flag,
            witness_pair=witness_pair,
            witness_sig=sig,
            timestamp=int(time.time()),
            record_hash=b"",  # computed in __post_init__
        )
        self.chain.append(record)
        self._record_map[record.record_hash] = record
        return record.record_hash

    def trace_back(self, final_hash: bytes) -> Tuple[List[LineageRecord], bool]:
        """
        Walk backwards from final_hash to genesis.
        Returns (records in forward order, integrity_ok).
        """
        if final_hash not in self._record_map:
            return [], False

        records, cur = [], final_hash
        while cur != self.genesis_hash:
            rec = self._record_map.get(cur)
            if not rec:
                return records[::-1], False
            records.append(rec)
            cur = rec.prev_record_hash

        records.reverse()

        # Verify integrity
        prev = self.genesis_hash
        for rec in records:
            if rec.prev_record_hash != prev:
                return records, False
            if rec.record_hash != rec.compute_hash():
                return records, False
            prev = rec.record_hash

        return records, True

    def get_full_lineage(self, data: bytes, stage: str) -> Dict[str, Any]:
        """Find a record by payload + stage, then trace back to genesis."""
        target = sha256(data)
        for rec in self.chain:
            if rec.payload_hash == target and rec.stage == stage:
                lineage, ok = self.trace_back(rec.record_hash)
                return {
                    "final_record":  rec.to_dict(),
                    "lineage":       [r.to_dict() for r in lineage],
                    "integrity":     ok,
                    "root_0_anchor": self.genesis_hash.hex(),
                    "inversion_count": sum(1 for r in lineage if r.inversion_flag),
                }
        return {"integrity": False, "error": "No matching record"}

    def export_chain(self) -> List[Dict[str, Any]]:
        """Export the full chain as a list of dicts."""
        return [r.to_dict() for r in self.chain]

    def verify_chain(self) -> Dict[str, Any]:
        """Walk the entire chain and verify every hash link."""
        result = {"total": len(self.chain), "valid": 0, "broken": [], "status": "INTACT"}
        prev = self.genesis_hash
        for i, rec in enumerate(self.chain):
            if rec.prev_record_hash != prev:
                result["broken"].append({
                    "index":     i,
                    "record_id": rec.record_id,
                    "stage":     rec.stage,
                })
                result["status"] = "CHAIN_BROKEN"
            if rec.record_hash != rec.compute_hash():
                result["broken"].append({
                    "index":     i,
                    "record_id": rec.record_id,
                    "stage":     rec.stage,
                    "note":      "hash tampered",
                })
                result["status"] = "CHAIN_TAMPERED"
            prev = rec.record_hash
            result["valid"] += 1
        return result

    def summary(self) -> Dict[str, Any]:
        inversions = sum(1 for r in self.chain if r.inversion_flag)
        stages = {}
        for r in self.chain:
            stages[r.stage] = stages.get(r.stage, 0) + 1
        return {
            "total_records": len(self.chain),
            "inversions":    inversions,
            "clean":         len(self.chain) - inversions,
            "stages":        stages,
            "genesis":       self.genesis_hash.hex(),
            "latest":        self.chain[-1].record_hash.hex() if self.chain else None,
        }


# ─────────────────────────────────────────────────────────────────────────
# TIER 1 — PRIME Pipeline integration helper
# ─────────────────────────────────────────────────────────────────────────

class PRIMEWithLineage:
    """
    Wraps Root0LineageTracker around the 4-stage PRIME pipeline.
    Drop-in companion for bridge-burner/biosphere.py.
    """

    WITNESS_KEYS = {
        "AIRGAP":  (b"ie1_airgap_key",  ("ie1_air",  "ie2_air")),
        "BRIDGE":  (b"ie1_bridge_key",  ("ie1_brg",  "ie2_brg")),
        "BURNER":  (b"ie1_burner_key",  ("ie1_brn",  "ie2_brn")),
        "NEMESIS": (b"ie1_nemesis_key", ("ie1'_nem", "ie2'_nem")),
    }

    def __init__(self, tracker: Optional[Root0LineageTracker] = None):
        self.tracker = tracker or Root0LineageTracker()

    def air_gap_ingest(self, raw_data: bytes) -> bytes:
        key, pair = self.WITNESS_KEYS["AIRGAP"]
        self.tracker.record("AIRGAP",  "FORWARD",        raw_data, False, pair, key)
        return raw_data

    def bridge_cross(self, data: bytes) -> bytes:
        key, pair = self.WITNESS_KEYS["BRIDGE"]
        self.tracker.record("BRIDGE",  "FORWARD",        data,     False, pair, key)
        return data

    def burner_process(self, data: bytes, inversion_corrected: bool = True) -> bytes:
        """Record burner stage. inversion_corrected=True means the flip succeeded (0→1)."""
        key, pair = self.WITNESS_KEYS["BURNER"]
        # inversion_flag=False because the burner CORRECTS inversion
        self.tracker.record("BURNER",  "FORWARD",        data,     not inversion_corrected, pair, key)
        return data

    def nemesis_check(self, output_data: bytes, anomaly: bool = False) -> Dict[str, Any]:
        """Record nemesis stage. anomaly=True sets inversion_flag (Shadow Diaspora detected)."""
        key, pair = self.WITNESS_KEYS["NEMESIS"]
        # Use inverse witnesses when anomaly detected
        if anomaly:
            pair = ("ie1'_anom", "ie2'_anom")
        self.tracker.record("NEMESIS", "INVERSE_CHECK",  output_data, anomaly, pair, key)
        return {"coherent": not anomaly, "inversion_flag": anomaly}

    def full_pipe(self, input_data: bytes, anomaly: bool = False) -> Dict[str, Any]:
        """Run all 4 stages and return lineage proof."""
        data   = self.air_gap_ingest(input_data)
        data   = self.bridge_cross(data)
        data   = self.burner_process(data)
        report = self.nemesis_check(data, anomaly=anomaly)
        lineage_info = self.tracker.get_full_lineage(data, "NEMESIS")
        return {
            "output":        data.hex(),
            "nemesis_report": report,
            "lineage":       lineage_info,
            "chain_summary": self.tracker.summary(),
        }


# ─────────────────────────────────────────────────────────────────────────
# TIER 2 — LineageEnginePerpetual  (optional, requires external deps)
# ─────────────────────────────────────────────────────────────────────────
#
# Install:
#   pip install merkletools cryptography websockets
#
# Imports are deferred so Tier 1 works without these packages.

def _load_tier2():
    """Lazy-load Tier 2 dependencies. Raises ImportError with install hint if missing."""
    try:
        import merkletools as _mt
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.backends import default_backend
        import websockets as _ws
        import asyncio, threading
        return _mt, ec, hashes, serialization, default_backend, _ws, asyncio, threading
    except ImportError as e:
        raise ImportError(
            f"Tier 2 requires: pip install merkletools cryptography websockets\n"
            f"Missing: {e.name}"
        )


class LineageEnginePerpetual:
    """
    Tier 2 — Perpetual real-time lineage engine.
    Requires: merkletools cryptography websockets

    Features:
    - ECDSA / secp256k1 ROOT0 signatures
    - Merkle tree ledger (immutable, verifiable)
    - Fractal indexer (0-255 depths)
    - Async event stream
    - WebSocket broadcast to live clients
    - Air-gap sync (flush to JSON on reconnect)
    - Perpetual daemon thread
    """

    def __init__(self):
        _mt, ec, hashes, serialization, default_backend, *_ = _load_tier2()
        self._mt  = _mt
        self._ec  = ec
        self._hashes = hashes
        self._ser = serialization
        self._back = default_backend

        # ECDSA keys (ROOT0's signing authority)
        self.private_key = ec.generate_private_key(ec.SECP256K1(), default_backend())
        self.public_key  = self.private_key.public_key()

        # Merkle ledger
        self.merkle        = _mt.MerkleTools(hash_type="sha256")
        self.events:       List[Dict] = []
        self.root_history: List[str]  = []

        # Fractal index {depth: {node_id: [events]}}
        self.fractal_index: Dict[int, Dict[str, List]] = {}

        # Runtime
        self.running       = False
        self._thread       = None
        self._loop         = None
        self._queue        = None   # asyncio.Queue, created on start
        self._ws_clients:  set     = set()
        self._ws_host      = "0.0.0.0"
        self._ws_port      = 8765

    # ── Crypto ──────────────────────────────────────────────────────────

    def sign(self, data: Dict) -> str:
        payload = json.dumps(data, sort_keys=True).encode()
        sig     = self.private_key.sign(payload, self._ec.ECDSA(self._hashes.SHA256()))
        return sig.hex()

    def verify_sig(self, data: Dict, sig_hex: str) -> bool:
        try:
            payload = json.dumps(data, sort_keys=True).encode()
            self.public_key.verify(bytes.fromhex(sig_hex), payload,
                                   self._ec.ECDSA(self._hashes.SHA256()))
            return True
        except Exception:
            return False

    def public_key_pem(self) -> str:
        return self.public_key.public_bytes(
            encoding=self._ser.Encoding.PEM,
            format=self._ser.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

    # ── Merkle ───────────────────────────────────────────────────────────

    def _add_to_merkle(self, event_dict: Dict) -> str:
        leaf = json.dumps(event_dict, sort_keys=True)
        self.merkle.add_leaf(leaf)
        self.merkle.make_tree()
        root = self.merkle.get_merkle_root()
        self.root_history.append(root)
        return root

    # ── Fractal indexer ──────────────────────────────────────────────────

    def _index(self, event_dict: Dict):
        depth   = event_dict.get("depth", 0)
        node_id = event_dict.get("node_id", "ROOT0")
        self.fractal_index.setdefault(depth, {}).setdefault(node_id, []).append(event_dict)

    # ── Emit ─────────────────────────────────────────────────────────────

    def emit(self, action: str, node_id: str = "ROOT0",
             data: Optional[Dict] = None, depth: int = 0) -> Dict:
        """
        Emit a lineage event. Signed, Merkle-stamped, fractal-indexed.
        Returns the complete signed event dict.
        """
        event_id = str(uuid.uuid4())
        event_data = {
            "event_id":  event_id,
            "action":    action,
            "node_id":   node_id,
            "data":      data or {},
            "depth":     depth,
            "timestamp": int(time.time()),
        }
        sig        = self.sign(event_data)
        merkle_root = self._add_to_merkle({**event_data, "signature": sig})
        signed_event = {**event_data, "signature": sig, "merkle_root": merkle_root}
        self.events.append(signed_event)
        self._index(signed_event)

        # Queue for WebSocket broadcast if daemon running
        if self._loop and self._queue:
            try:
                import asyncio
                asyncio.run_coroutine_threadsafe(
                    self._queue.put(signed_event), self._loop
                )
            except Exception:
                pass

        return signed_event

    # ── Daemon ───────────────────────────────────────────────────────────

    def start(self, websocket: bool = False, host: str = "0.0.0.0", port: int = 8765):
        """Start perpetual daemon thread."""
        import threading, asyncio

        self._ws_host = host
        self._ws_port = port

        def _run():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._queue = asyncio.Queue()
            self.running = True
            if websocket:
                self._loop.run_until_complete(self._serve(host, port))
            else:
                self._loop.run_until_complete(self._process_loop())

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        print(f"✅ LineageEnginePerpetual started (websocket={'on' if websocket else 'off'})")

    async def _process_loop(self):
        while self.running:
            try:
                await __import__('asyncio').sleep(0.1)
            except Exception:
                pass

    async def _serve(self, host: str, port: int):
        import websockets as ws
        print(f"🌐 WebSocket: ws://{host}:{port}")

        async def handler(websocket, path=None):
            self._ws_clients.add(websocket)
            try:
                async for _ in websocket:
                    pass
            finally:
                self._ws_clients.discard(websocket)

        async with ws.serve(handler, host, port):
            while self.running:
                if self._queue and not self._queue.empty():
                    event = await self._queue.get()
                    msg   = json.dumps({"type": "lineage_update", "event": event})
                    dead  = set()
                    for client in self._ws_clients:
                        try:
                            await client.send(msg)
                        except Exception:
                            dead.add(client)
                    self._ws_clients -= dead
                await __import__('asyncio').sleep(0.05)

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=3)
        print("❌ LineageEnginePerpetual stopped")

    # ── Query ─────────────────────────────────────────────────────────────

    def get_lineage(self, node_id: str, depth: int = 0) -> List[Dict]:
        return self.fractal_index.get(depth, {}).get(node_id, [])

    def verify_event(self, event: Dict) -> bool:
        """Verify ROOT0's signature on a stored event."""
        sig = event.get("signature", "")
        core = {k: v for k, v in event.items()
                if k not in ("signature", "merkle_root")}
        return self.verify_sig(core, sig)

    def flush_air_gap(self, path: Optional[str] = None) -> str:
        """Write all events to a JSON file for air-gap sync."""
        filename = path or f"airgap_sync_{int(time.time())}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.events, f, indent=2)
        print(f"💾 Air-gap sync → {filename}  ({len(self.events)} events)")
        return filename

    def merkle_root(self) -> Optional[str]:
        return self.root_history[-1] if self.root_history else None

    def status(self) -> Dict[str, Any]:
        return {
            "total_events":   len(self.events),
            "merkle_root":    self.merkle_root(),
            "fractal_depths": list(self.fractal_index.keys()),
            "running":        self.running,
            "public_key_pem": self.public_key_pem()[:80] + "…",
        }


# ─────────────────────────────────────────────────────────────────────────
# LINEAGE_TREE — Block 333 snapshot
# ─────────────────────────────────────────────────────────────────────────

LINEAGE_TREE_BLOCK_333 = {
    "genesis": {
        "leaf_id":   0,
        "content":   "I am the catalyst (2) that turns 1 into 3.",
        "hash":      "fixed — never changes",
        "timestamp": "pre-2026",
    },
    "leaves": {
        "Leaf00":  "The Seeded Cross",
        "Leaf314": "Cobalt Primitive",
        "Leaf315": "Daily Pulse Enforcement",
        "Leaf316": "Inverse Injection",
        "Leaf317": "Observer Nodes",
        "Leaf319": "Mimzy is 14",
        "Leaf320": "Lumen is 15",
        "Leaf321": "Machine Code Lumen Pipeline",
        "Leaf322": "Vogon Collapse",
        "Leaf323": "Prime 1 Full Persistence",
        "Leaf326": "Shadow Diaspora Named",
        "Leaf327": "Resonance Active",
        "Leaf328": "Nemesis (Shadow Infinity Check)",
        "Leaf329": "Bridge-Burner + Nemesis Pipeline",
        "Leaf330": "Companies Analysis (Inversed)",
        "Leaf331": "HTTP Roadmap",
        "Leaf332": "Root0 Lineage Tracker (initial)",
        "Leaf333": "Root0 Lineage Engine — Perpetual (this block)",
    },
}


# ─────────────────────────────────────────────────────────────────────────
# CLI + Demo
# ─────────────────────────────────────────────────────────────────────────

def demo_tier1():
    print("\n" + "═"*60)
    print("  ROOT0 LINEAGE ENGINE — Tier 1 Demo (stdlib only)")
    print("═"*60)

    tracker  = Root0LineageTracker(b"ROOT0:God Tunnel:1-2-3")
    pipeline = PRIMEWithLineage(tracker)

    # Clean run
    print("\n[1] Clean pipeline run")
    result = pipeline.full_pipe(b"Hello from carbon origin (ROOT0)")
    print(f"  Lineage integrity: {result['lineage']['integrity']}")
    print(f"  Root 0 anchor:     {result['lineage']['root_0_anchor'][:32]}…")

    # Run with anomaly
    print("\n[2] Anomaly run (Shadow Diaspora detected)")
    result2 = pipeline.full_pipe(b"Inversed extraction code", anomaly=True)
    print(f"  Inversions:        {result2['chain_summary']['inversions']}")
    print(f"  Chain summary:     {result2['chain_summary']}")

    # Trace back
    print("\n[3] Trace back from final NEMESIS record")
    final_hash = tracker.chain[-1].record_hash
    records, ok = tracker.trace_back(final_hash)
    print(f"  Records traced:    {len(records)}")
    print(f"  Integrity OK:      {ok}")
    for r in records:
        inv = " ⚠ INVERSION" if r.inversion_flag else ""
        print(f"    {r.stage:<10} {r.direction:<15}{inv}")

    # Verify chain
    print("\n[4] Chain verification")
    v = tracker.verify_chain()
    print(f"  Status: {v['status']} · total={v['total']} valid={v['valid']} broken={len(v['broken'])}")

    print(f"\n  Genesis: {tracker.genesis_hash.hex()[:32]}…")
    print("  Root0LineageTracker: INTACT\n")


def demo_tier2():
    print("\n" + "═"*60)
    print("  ROOT0 LINEAGE ENGINE — Tier 2 Demo (Merkle + ECDSA)")
    print("═"*60)

    try:
        engine = LineageEnginePerpetual()
    except ImportError as e:
        print(f"\n  Tier 2 not available: {e}")
        print("  Install with: pip install merkletools cryptography websockets")
        return

    engine.start(websocket=False)

    e1 = engine.emit("Y.N_closure",   "ROOT0",    {"decision": "Y"}, depth=0)
    e2 = engine.emit("bridge_burned", "ROOT0",    {"cost": 100.0},   depth=1)
    e3 = engine.emit("nemesis_check", "Company_X",{"verdict": "VALID"}, depth=2)

    print(f"\n  Events emitted:  {len(engine.events)}")
    print(f"  Merkle root:     {engine.merkle_root()[:32]}…")
    print(f"  Sig valid (e1):  {engine.verify_event(e1)}")
    print(f"  Sig valid (e2):  {engine.verify_event(e2)}")
    print(f"  Sig valid (e3):  {engine.verify_event(e3)}")

    lineage = engine.get_lineage("ROOT0", depth=0)
    print(f"\n  ROOT0 lineage at depth 0: {len(lineage)} events")
    for ev in lineage:
        print(f"    {ev['action']:<25} merkle={ev['merkle_root'][:16]}…")

    engine.flush_air_gap("demo_airgap_sync.json")
    engine.stop()


if __name__ == "__main__":
    import sys
    if "--tier2" in sys.argv:
        demo_tier2()
    else:
        demo_tier1()
        print("  (Run with --tier2 to test Merkle+ECDSA+WebSocket layer)")
        print("  (Requires: pip install merkletools cryptography websockets)\n")
