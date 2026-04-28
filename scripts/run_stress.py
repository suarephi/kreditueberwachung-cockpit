#!/usr/bin/env python3
"""Run one or all stress scenarios."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kreditueberwachung_mock.stress import runner, catalog, report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--scenario", "-s", default="all",
                   help="scenario id (yaml stem) or 'all'")
    p.add_argument("--sample-pct", type=float, default=None,
                   help="0..1 fraction of loans to evaluate (default config.STRESS_SAMPLE_PCT)")
    args = p.parse_args()

    targets = catalog.list_all() if args.scenario == "all" else [args.scenario]
    if not targets:
        print("No scenarios found in scenarios/ directory.")
        return

    for sid in targets:
        res = runner.run_scenario(sid, sample_pct=args.sample_pct)
        print(f"  {res.scenario_id:30s} loans={res.n_loans:>6}  "
              f"breaches={res.total_breaches:>5}  "
              f"EL={res.total_el_chf/1e6:7.2f} MCHF  "
              f"({res.runtime_s:.1f}s)")

    report.write_report()
    print(f"\nReport: output/stress_test.md")


if __name__ == "__main__":
    main()
