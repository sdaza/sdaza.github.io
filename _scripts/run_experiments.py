"""Run and check every counterfactual in the marketplace SD model.

The scenarios themselves live in scenarios.py, which is also what
make_anylogic_sd.py turns into AnyLogic experiments, so the runs here and the
runs in AnyLogic are the same list by construction.

Three things happen.

1. Each scenario is run through the equations stored in the .alp file, and
   checked against the notebook's independent Python implementation. If the two
   ever disagree the check fails loudly, which is the only way the claim that
   they are the same model stays true.

2. The promotion multiplier baked into the .alp is recomputed from the model and
   checked, so the calibration cannot go stale.

3. AnyLogic writes its own runs to assets/files/experiments/. Any that are
   present are compared against the same scenarios.

Usage:
    .venv/bin/python _scripts/run_experiments.py              # run and verify
    .venv/bin/python _scripts/run_experiments.py --settings   # AnyLogic recipe
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from alp_model import AlpModel  # noqa: E402
from scenarios import (CALL_ARGS, DT, MATCH_SHIFT, PROMOTION_MULTIPLIER,  # noqa: E402
                       SCENARIOS, TRACKED, VARIABLE_COST_RATE, WEEKS,
                       Scenario, take_rate_of)

ROOT = Path(__file__).resolve().parent.parent
ALP = ROOT / "assets/files/marketplace_sd.alp"
NOTEBOOK = ROOT / "_jupyter/system-dynamics-marketplace.ipynb"
OUT_DIR = ROOT / "data/experiments"
# Where the AnyLogic experiments write their results: next to the .alp, because
# that is AnyLogic's working directory during a run.
ANYLOGIC_DIR = ALP.parent / "experiments"


def load_notebook_model():
    """Pull Params/simulate out of the executed notebook.

    The notebook is the published artifact, so it is the reference
    implementation; importing from it means the check cannot pass by comparing
    the .alp against a stale copy of itself.
    """
    nb = json.loads(NOTEBOOK.read_text())
    cells = [
        "".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"
    ]
    source = next(c for c in cells if "class Params" in c)
    ns: dict[str, object] = {}
    exec("import numpy as np\nimport pandas as pd\n"
         "from dataclasses import dataclass, replace\n", ns)
    exec(source, ns)
    return ns["Params"], ns["simulate"]


def measured_lift(Params, simulate) -> float:
    """The conversion lift the A/B test reads off the matching change.

    Both policies are entered into the model with this same measured effect,
    which is the comparison the post is built on.
    """
    p = Params()
    base = simulate(p, weeks=WEEKS, dt=DT)
    at_start = base[np.isclose(base.week, 52.0)].iloc[0]
    demand = at_start.buyers * p.sessionsPerBuyer
    capacity = at_start.sellers * p.sellerCapacity

    def match_of(alpha):
        return 1 - np.exp(-alpha * capacity / demand)

    def conv_of(m):
        return min(0.9, max(0.01, p.baseConversion
                            * (1 + p.conversionSensitivity * (m - p.matchReference))))

    return conv_of(match_of(p.matchEfficiencyBase + MATCH_SHIFT)) / conv_of(
        match_of(p.matchEfficiencyBase)) - 1


def run_alp(model: AlpModel, sc: Scenario) -> pd.DataFrame:
    return model.run(weeks=WEEKS, dt=DT, overrides=sc.overrides)


def run_notebook(Params, simulate, sc: Scenario) -> pd.DataFrame:
    field_overrides = {k: v for k, v in sc.overrides.items() if k not in CALL_ARGS}
    call_overrides = {k: v for k, v in sc.overrides.items() if k in CALL_ARGS}
    return simulate(replace(Params(), **field_overrides), weeks=WEEKS, dt=DT,
                    **call_overrides)


def max_relative_error(a: pd.DataFrame, b: pd.DataFrame, columns) -> dict[str, float]:
    merged = a.merge(b, on="week", suffixes=("_a", "_b"))
    return {
        c: float(np.max(np.abs(merged[f"{c}_a"] - merged[f"{c}_b"])
                        / np.maximum(np.abs(merged[f"{c}_a"]), 1e-9)))
        for c in columns
        if f"{c}_a" in merged and f"{c}_b" in merged
    }


def cumulative_gmv(df: pd.DataFrame, since: float = 0.0) -> float:
    d = df[df.week >= since]
    return float(np.trapezoid(d.weeklyGMV, d.week))


def ensure_gm(df: pd.DataFrame, take_rate: float) -> pd.DataFrame:
    """Add weeklyGM when an older AnyLogic export only has GMV."""
    if "weeklyGM" in df.columns:
        return df
    out = df.copy()
    out["weeklyGM"] = out["weeklyGMV"] * (take_rate - VARIABLE_COST_RATE)
    return out


def cumulative_gm(df: pd.DataFrame, since: float = 0.0, take_rate: float = 0.30) -> float:
    d = ensure_gm(df, take_rate)
    d = d[d.week >= since]
    return float(np.trapezoid(d.weeklyGM, d.week))


def anylogic_settings_table(scenarios: list[Scenario]) -> str:
    """What each experiment in the .alp is already set to.

    Nothing here has to be typed in: every scenario exists in the model as its
    own experiment, carrying these values. The table is a reference for reading
    the results, and for spotting a scenario whose values look wrong.
    """
    lines = [
        "AnyLogic experiments",
        "====================",
        "",
        f"Open {ALP.relative_to(ROOT)}. Each scenario below is its own experiment",
        "in the project tree, already carrying the parameter values shown.",
        "Run one and it writes its weekly series to",
        f"{ANYLOGIC_DIR.relative_to(ROOT)}/<scenario>.csv, then re-run this script",
        "to compare those results against the model's equations.",
        "",
    ]
    width = max(len(s.name) for s in scenarios) + 2
    for sc in scenarios:
        settings = ", ".join(f"{k} = {v:g}" for k, v in sc.overrides.items()) or "defaults"
        lines.append(f"{sc.name:<{width}} {settings}")
        lines.append(f"{'':<{width}} {sc.description}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", action="store_true",
                        help="print the AnyLogic parameter recipe and exit")
    parser.add_argument("--tolerance", type=float, default=1e-9,
                        help="maximum allowed relative difference .alp vs notebook")
    args = parser.parse_args()

    Params, simulate = load_notebook_model()
    model = AlpModel.from_file(ALP)
    scenarios = SCENARIOS

    if args.settings:
        print(anylogic_settings_table(scenarios))
        return 0

    # The multiplier is a literal in scenarios.py because it is written into the
    # .alp, so it has to be checked against the model rather than trusted.
    lift = measured_lift(Params, simulate)
    expected = round(1 + lift, 6)
    if abs(expected - PROMOTION_MULTIPLIER) > 5e-7:
        print(f"PROMOTION_MULTIPLIER is stale: scenarios.py says "
              f"{PROMOTION_MULTIPLIER}, the model implies {expected}. "
              f"Update it and regenerate the .alp.")
        return 1

    print(f"measured A/B conversion lift both policies produce: {100 * lift:+.2f}%")
    print(f"running {len(scenarios)} scenarios to week {WEEKS:.0f}\n")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    worst = 0.0
    failures = []

    for sc in scenarios:
        alp = run_alp(model, sc)
        nb = run_notebook(Params, simulate, sc)

        errors = max_relative_error(alp, nb, TRACKED)
        scenario_worst = max(errors.values()) if errors else 0.0
        worst = max(worst, scenario_worst)
        if scenario_worst > args.tolerance:
            failures.append((sc.name, errors))

        alp.to_csv(OUT_DIR / f"{sc.name}.csv", index=False)

        end = alp.iloc[-1]
        rows.append({
            "scenario": sc.name,
            "buyers": end.buyers,
            "sellers": end.sellers,
            "matchRate": end.matchRate,
            "fillRate": end.fillRate,
            "sellerEarnings": end.sellerEarnings,
            "cumulativeGMV_M": cumulative_gmv(alp) / 1e6,
            "cumulativeGM_M": cumulative_gm(alp, take_rate=take_rate_of(sc)) / 1e6,
            "alp_vs_notebook": scenario_worst,
        })

    summary = pd.DataFrame(rows)
    baseline = summary[summary.scenario == "baseline"].iloc[0]
    summary["buyers_vs_baseline_%"] = 100 * (summary.buyers / baseline.buyers - 1)
    summary["gmv_vs_baseline_%"] = 100 * (
        summary.cumulativeGMV_M / baseline.cumulativeGMV_M - 1)
    summary["gm_vs_baseline_%"] = 100 * (
        summary.cumulativeGM_M / baseline.cumulativeGM_M - 1)

    summary_path = OUT_DIR / "summary.csv"
    summary.to_csv(summary_path, index=False)

    display = summary[["scenario", "buyers", "sellers", "matchRate",
                       "buyers_vs_baseline_%", "gmv_vs_baseline_%",
                       "gm_vs_baseline_%"]]
    print(display.to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print(f"\nworst .alp vs notebook relative difference: {worst:.2e}")
    if failures:
        print("MISMATCH between the AnyLogic equations and the notebook:")
        for name, errors in failures:
            detail = ", ".join(f"{k} {v:.2e}" for k, v in errors.items())
            print(f"  {name}: {detail}")
        return 1
    print("the .alp equations and the notebook agree to machine precision")

    compare_anylogic(scenarios, model)
    print(f"\nwrote {summary_path.relative_to(ROOT)} "
          f"and {len(scenarios)} per-scenario CSVs in {OUT_DIR.relative_to(ROOT)}")
    return 0


def compare_anylogic(scenarios: list[Scenario], model: AlpModel) -> None:
    """Compare real AnyLogic exports against the same scenarios, when present."""
    exports = sorted(ANYLOGIC_DIR.glob("*.csv")) if ANYLOGIC_DIR.exists() else []
    if not exports:
        print(f"\nno AnyLogic runs in {ANYLOGIC_DIR.relative_to(ROOT)} yet; "
              f"open the .alp and run an experiment, it writes its own CSV there")
        return

    by_name = {sc.name: sc for sc in scenarios}
    print(f"\ncomparing {len(exports)} AnyLogic export(s):")
    for path in exports:
        sc = by_name.get(path.stem)
        if sc is None:
            print(f"  {path.name}: no scenario named {path.stem}, skipped")
            continue
        actual = pd.read_csv(path)
        actual.columns = [c.strip() for c in actual.columns]
        if "week" not in actual.columns:
            print(f"  {path.name}: no 'week' column, skipped")
            continue
        expected = run_alp(model, sc)
        errors = max_relative_error(expected, actual, TRACKED)
        if not errors:
            print(f"  {path.name}: no comparable columns")
            continue
        detail = ", ".join(f"{k} {v:.1e}" for k, v in errors.items())
        verdict = "ok" if max(errors.values()) < 1e-6 else "DIFFERS"
        print(f"  {path.name}: {verdict} ({detail})")


if __name__ == "__main__":
    raise SystemExit(main())
