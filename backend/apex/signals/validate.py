"""Validation harness: detected SIGNALS vs the persona manifest (specs/data-generator.md).

    python -m apex.signals.detect      # populate SIGNALS first
    python -m apex.signals.validate    # then check against generated_manifest.json

Pass criteria:
  - RECALL: every persona's expected_signals are detected (the engineered intent fires).
  - NOISE:  noise-population customers trip nothing.
EXTRAS (a signal-persona firing beyond its expected set) are reported as warnings, not
failures — several signals (e.g. protection_gap) are legitimately broad.

`fiscal_year_end_window` is calendar-gated (Jan–Mar). Out of window it cannot fire, so it
is reported as CONDITIONAL: passing iff its data precondition (idle_balance detected for
that customer) holds — i.e. it *would* fire in-window.
"""
import json
from collections import defaultdict
from datetime import datetime

from ..config import BACKEND_DIR
from ..database.db import SessionLocal
from .detectors import DETECTORS
from .thresholds import FISCAL_YEAR_END_MONTHS

CALENDAR_GATED = {"fiscal_year_end_window": "idle_balance"}   # signal -> precondition signal


def _detected_by_customer(session):
    from ..database.models import Signal
    out = defaultdict(set)
    for s in session.query(Signal).all():
        out[str(s.customer_id)].add(s.signal_type)
    return out


def validate(now: datetime | None = None):
    now = now or datetime.now()
    in_fiscal_window = now.month in FISCAL_YEAR_END_MONTHS

    with open(BACKEND_DIR / "generated_manifest.json", encoding="utf-8") as fh:
        manifest = json.load(fh)
    with SessionLocal() as session:
        detected = _detected_by_customer(session)

    missing, noise_fires, extras = [], [], []
    conditional_pass, conditional_fail = [], []
    recall_hit = defaultdict(int)
    recall_total = defaultdict(int)

    for cid, entry in manifest.items():
        name = entry["name"]
        expected = set(entry.get("expected_signals", []))
        got = detected.get(cid, set())

        if entry["persona"] == "noise":
            if got:
                noise_fires.append((name, sorted(got)))
            continue

        for sig in expected:
            recall_total[sig] += 1
            if sig in CALENDAR_GATED and not in_fiscal_window:
                precond = CALENDAR_GATED[sig]
                if precond in got:
                    conditional_pass.append((name, sig, precond))
                    recall_hit[sig] += 1
                else:
                    conditional_fail.append((name, sig, precond))
                continue
            if sig in got:
                recall_hit[sig] += 1
            else:
                missing.append((name, sig))

        for sig in got - expected:
            extras.append((name, sig))

    # ---- report ---- #
    print(f"=== Signal validation (asof {now:%Y-%m-%d}, "
          f"fiscal window {'OPEN' if in_fiscal_window else 'closed'}) ===\n")

    print("Per-signal recall (expected personas detected):")
    for sig, _ in DETECTORS:
        tot = recall_total.get(sig, 0)
        if tot:
            print(f"  {sig:26} {recall_hit.get(sig, 0)}/{tot}")

    extras_by_signal = defaultdict(list)
    for name, sig in extras:
        extras_by_signal[sig].append(name)

    print("\nFAILURES")
    if not missing and not noise_fires and not conditional_fail:
        print("  none ✓")
    for name, sig in missing:
        print(f"  MISSING   {name}: expected '{sig}', not detected")
    for name, sig, precond in conditional_fail:
        print(f"  COND-FAIL {name}: '{sig}' out of window AND precondition '{precond}' absent")
    for name, got in noise_fires:
        print(f"  NOISE     {name} tripped {got} (should be silent)")

    if conditional_pass:
        print("\nCONDITIONAL (calendar-gated, precondition satisfied → would fire in-window)")
        for name, sig, precond in conditional_pass:
            print(f"  {name}: '{sig}' OK via '{precond}'")

    if extras_by_signal:
        print("\nEXTRAS (warnings — signal-persona fired beyond expected)")
        for sig in sorted(extras_by_signal):
            print(f"  {sig:26} {len(extras_by_signal[sig])}: {', '.join(extras_by_signal[sig])}")

    ok = not missing and not noise_fires and not conditional_fail
    print(f"\nRESULT: {'PASS ✓' if ok else 'FAIL ✗'}")
    return ok


if __name__ == "__main__":
    validate()
