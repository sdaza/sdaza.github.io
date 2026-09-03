"""The counterfactuals discussed in the marketplace post, defined once.

Every scenario is a set of parameter values, never a code change. That is what
lets the same list drive two things without either drifting from the other:
`make_anylogic_sd.py` turns each entry into a ready-to-run AnyLogic experiment,
and `run_experiments.py` runs the same entry through the model's equations to
check the numbers.

PROMOTION_MULTIPLIER has to be a literal because it is written into the .alp,
which is a static file. `run_experiments.py` recomputes it from the model and
fails if the value below no longer matches, so it cannot go stale silently.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Conversion lift the A/B test measures for the matching change, applied to the
# promotion so both policies enter the model with the same measured effect.
# Recomputed and checked by run_experiments.py.
PROMOTION_MULTIPLIER = 1.074451

# The matching-efficiency gain the ranking change delivers.
MATCH_SHIFT = 0.15

# When a policy switches on, and the horizon every experiment runs to.
POLICY_START = 52.0
WEEKS = 500.0
DT = 0.125

# Passed to the notebook's simulate() as call arguments; everything else is a
# field of Params.
CALL_ARGS = {"matchEfficiencyShift", "conversionMultiplier", "paidVisitorMultiplier",
             "policyStart", "policyStop"}

# Reported for every scenario, and compared across implementations.
TRACKED = ["buyers", "sellers", "matchRate", "fillRate", "sellerEarnings",
           "weeklyGMV", "weeklyGM", "cumulativeGM"]

DEFAULT_TAKE_RATE = 0.30
# Lumped payment fees, refunds and breakage as a share of GMV. Synthetic.
VARIABLE_COST_RATE = 0.04


def take_rate_of(sc: Scenario) -> float:
    return float(sc.overrides.get("takeRate", DEFAULT_TAKE_RATE))


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    overrides: dict[str, float] = field(default_factory=dict)


SCENARIOS: list[Scenario] = [
    Scenario("baseline", "No intervention, the reference run"),

    # Structural counterfactuals: cut one feedback loop at a time.
    Scenario("no_R1_liquidity", "Cut R1: match rate no longer moves buyers",
             {"swLiquidity": 0.0}),
    Scenario("no_R2_word_of_mouth", "Cut R2: no referred visitors",
             {"swWordOfMouth": 0.0}),
    Scenario("no_B2_crowding", "Cut B2: sellers ignore earnings",
             {"swCrowding": 0.0}),
    Scenario("no_saturation", "Cut the finite-pool brake",
             {"swSaturation": 0.0}),

    # Policy counterfactuals, calibrated to the same measured A/B lift.
    Scenario("promotion", "Discount lifting conversion from week 52",
             {"conversionMultiplier": PROMOTION_MULTIPLIER,
              "policyStart": POLICY_START}),
    Scenario("better_matching", "Ranking change raising matching efficiency",
             {"matchEfficiencyShift": MATCH_SHIFT, "policyStart": POLICY_START}),

    # The same two policies, switched off again after 26 weeks.
    Scenario("promotion_26w", "Promotion that runs for 26 weeks only",
             {"conversionMultiplier": PROMOTION_MULTIPLIER,
              "policyStart": POLICY_START, "policyStop": POLICY_START + 26}),
    Scenario("better_matching_26w", "Matching change reverted after 26 weeks",
             {"matchEfficiencyShift": MATCH_SHIFT,
              "policyStart": POLICY_START, "policyStop": POLICY_START + 26}),

    # Timing: the identical change shipped later.
    *[
        Scenario(f"matching_start_{start}",
                 f"Matching change shipped at week {start}",
                 {"matchEfficiencyShift": MATCH_SHIFT, "policyStart": float(start)})
        for start in (104, 208, 312)
    ],

    # Levers that relax the binding B2 ceiling.
    Scenario("take_rate_20", "Take rate cut from 30% to 20%", {"takeRate": 0.20}),
    Scenario("price_24", "Price raised from 20 to 24", {"price": 24.0}),
    Scenario("earnings_reference_100", "Sellers with lower outside options",
             {"earningsReference": 100.0}),

    # The operating-point trap: below the reference, R1 flips sign.
    Scenario("reference_085", "Buyers judge the market against 0.85",
             {"matchReference": 0.85}),
    Scenario("reference_085_no_R1", "Same, with R1 cut",
             {"matchReference": 0.85, "swLiquidity": 0.0}),

    # Marketing counterfactual, for contrast with the two policies above.
    Scenario("paid_visitors_x2", "Double paid acquisition from week 52",
             {"paidVisitorMultiplier": 2.0, "policyStart": POLICY_START}),
]

BY_NAME = {sc.name: sc for sc in SCENARIOS}
