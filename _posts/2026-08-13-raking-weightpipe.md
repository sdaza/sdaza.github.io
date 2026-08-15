---
layout: post
author: Sebastian Daza
title: "Raking weights with Python and weightpipe"
date: 2026-08-13
giscus_comments: true
tags: python, survey, data science
---

This is an update to my [2012 post on raking weights in
R](/blog/2012/raking/). It uses the same Chilean CEP survey example, but this
time in Python with
[weightpipe](https://github.com/sdaza/weightpipe), a package I wrote for
declarative survey weighting recipes.

The conceptual background—what raking is, when to use it, truncation, and
design-effect checks—has not changed. See the original post for that
discussion. Here I focus on the Python workflow: define population margins,
build a `Recipe`, calibrate, trim, and compare estimates.

Install from GitHub (not on PyPI yet):

```bash
pip install "git+https://github.com/sdaza/weightpipe.git"
# or
uv add "git+https://github.com/sdaza/weightpipe.git"
```

## Data

Again, I use the Opinion Public Survey CEP, July–August 2012, to estimate
presidential approval
([data](https://raw.githubusercontent.com/sdaza/sdaza.github.io/main/_R/data/cep.csv)).
Five variables enter the raking: `sex`, `agecat`, `ses`, `region`, and `area`.

{% highlight python %}
import numpy as np
import pandas as pd

pd.set_option("display.notebook_repr_html", False)
pd.set_option("display.float_format", lambda x: f"{x:.3f}")

from weightpipe import (
    Recipe,
    boot_proportion,
    bootstrap_weights,
    collect_weights,
    design_effect,
    estimate,
    weight_factors,
)

# data used in the 2012 post
dat = pd.read_csv(
    "https://raw.githubusercontent.com/sdaza/sdaza.github.io/main/_R/data/cep.csv"
)
dat["base"] = 1.0

# binary indicators for estimate(..., estimand="proportion")
for code, name in [
    (1, "approve"),
    (2, "disapprove"),
    (3, "unsure"),
    (9, "dk"),
]:
    dat[name] = (dat["approval"] == code).astype(int)

dat.head()
{% endhighlight %}

The unweighted sample margins are:

{% highlight python %}
for var in ["sex", "agecat", "ses", "region", "area"]:
    print(f"\n{var}")
    print(dat[var].value_counts(normalize=True).sort_index().round(3).to_string())
{% endhighlight %}

```
sex
1   0.407
2   0.593

agecat
1   0.124
2   0.159
3   0.177
4   0.194
5   0.346

ses
1   0.039
2   0.108
3   0.365
4   0.448
5   0.040

region
1    0.013
2    0.042
3    0.014
4    0.042
5    0.099
6    0.055
7    0.062
8    0.131
9    0.063
10   0.049
11   0.004
12   0.011
13   0.376
14   0.026
15   0.013

area
1   0.837
2   0.163
```

## Population targets

The population shares come from the Chilean Census 2002 (`sex`, `agecat`,
`region`, and `area`) and the Bicentenario Survey 2009 (`ses`). These are the
same targets used in the original post. Rounded census vectors may not sum
exactly to one; `weightpipe` renormalizes them by default (`force1=True`), as in
`anesrake`.

{% highlight python %}
# Chilean Census 2002
sex = {1: 0.49, 2: 0.51}  # 1 male, 2 female
agecat = {
    1: 0.163,  # 18–24
    2: 0.203,  # 25–34
    3: 0.195,  # 35–44
    4: 0.187,  # 45–54
    5: 0.253,  # 55+
}
region = {
    1: 0.015, 2: 0.031, 3: 0.016, 4: 0.039, 5: 0.102,
    6: 0.051, 7: 0.059, 8: 0.123, 9: 0.056, 10: 0.046,
    11: 0.006, 12: 0.010, 13: 0.408, 14: 0.023, 15: 0.013,
}
area = {1: 0.869, 2: 0.131}  # 1 urban, 2 rural

# Bicentenario Survey 2009
ses = {
    1: 0.109,
    2: 0.184,
    3: 0.261,
    4: 0.364,
    5: 0.083,
}

proportions = {
    "sex": sex,
    "agecat": agecat,
    "ses": ses,
    "region": region,
    "area": area,
}
{% endhighlight %}

## Raking with `weightpipe`

A `Recipe` starts from base weights—uniform weights of one in this
example—and then chains adjustment steps. Here I use:

- `step_calibrate(method="raking", proportions=...)` to run iterative
  proportional fitting against the population margins.
- `step_trim(max_ratio=5, reference="value")` to cap weights at five and
  redistribute the excess so that the total weight is preserved.

Unlike `anesrake`, variable selection options such as `pctlim` and `nlim` are
not part of this step. You explicitly pass the margins that you have decided to
use.

{% highlight python %}
recipe = (
    Recipe(dat, base_weight="base")
    .step_calibrate(
        method="raking",
        proportions=proportions,
        max_iter=100,
        tol=1e-8,
    )
    .step_trim(
        max_ratio=5.0,
        reference="value",
        redistribute=True,
    )
)

fitted = recipe.prep(warn=False)
weighted = collect_weights(fitted, keep_intermediate=True)

print("n =", len(weighted))
print("sum(weight) =", round(float(weighted["weight"].sum()), 3))
print(
    "min / max weight =",
    round(weighted["weight"].min(), 3),
    "/",
    round(weighted["weight"].max(), 3),
)
print("Kish deff =", round(design_effect(fitted), 3))
print(
    "converged =",
    fitted.diagnostics["steps"]["calibrate"]["converged"],
)
print(
    "iterations =",
    fitted.diagnostics["steps"]["calibrate"]["iterations"],
)
{% endhighlight %}

```
n = 1512
sum(weight) = 1512.0
min / max weight = 0.332 / 4.304
Kish deff = 1.38
converged = True
iterations = 12
```

Kish's approximate design effect from unequal weighting is again about
**1.38**, the same value obtained in the original R post. Weighting loss is:

$$L_w = \mathrm{deff} - 1 \approx 0.38$$

This is only an unequal-weighting approximation. It does not account for
clustering or other features of the sampling design.

### Approval estimates with bootstrap CIs

Approval codes are 1 = approve, 2 = disapprove, 3 = unsure, and 9 = don't know.
Instead of a hand-rolled weighted tabulation, use `estimate` on the binary
indicators. With no strata/PSU columns available in the CEP file, this is an
unequal-weight bootstrap that re-runs the full raking recipe in each replicate.

{% highlight python %}
estimate(
    recipe,
    "approve",
    estimand="proportion",
    fitted=fitted,
    variance="bootstrap",
    replicates=400,
    seed=42,
).round(3)
{% endhighlight %}

```
 estimate    se  ci_lower  ci_upper  level  R_used   estimand variable  variance
    0.298 0.013     0.272     0.325   0.95     400 proportion  approve bootstrap
```

For all categories, resample once with `bootstrap_weights` and then call
`boot_proportion` for each indicator:

{% highlight python %}
boot = bootstrap_weights(
    recipe,
    replicates=400,
    seed=42,
    point=fitted,
)

approval_ci = pd.concat(
    [
        boot_proportion(boot, name).assign(category=name)
        for name in ["approve", "disapprove", "unsure", "dk"]
    ],
    ignore_index=True,
)[["category", "estimate", "se", "ci_lower", "ci_upper"]]

approval_ci.round(3)
{% endhighlight %}

```
  category  estimate    se  ci_lower  ci_upper
   approve     0.298 0.013     0.272     0.325
disapprove     0.521 0.013     0.494     0.547
    unsure     0.161 0.010     0.141     0.181
        dk     0.020 0.003     0.013     0.027
```

## Raking on top of existing survey weights

The CEP file includes its own `pond` weights, whose maximum is about 17.6. As
in the original post, documentation of how these weights were built is thin.
We can still use them as base weights and rake on `ses` and `region`, the two
margins that were most different after applying `pond` in the 2012 analysis.

{% highlight python %}
print(dat["pond"].describe().round(3))
print(
    "Kish deff (pond) =",
    round(design_effect(dat["pond"]), 3),
)
{% endhighlight %}

```
count   1512.000
mean       1.000
std        1.044
min        0.015
25%        0.455
50%        0.786
75%        1.235
max       17.563
Kish deff (pond) = 2.088
```

{% highlight python %}
recipe_pond = (
    Recipe(dat, base_weight="pond")
    .step_calibrate(
        method="raking",
        proportions={
            "ses": proportions["ses"],
            "region": proportions["region"],
        },
        max_iter=100,
        tol=1e-8,
    )
    .step_trim(
        max_ratio=5.0,
        reference="value",
        redistribute=True,
    )
)

fitted_pond = recipe_pond.prep(warn=False)
weighted_pond = collect_weights(fitted_pond)

print(
    "Kish deff (raked pond) =",
    round(design_effect(fitted_pond), 3),
)
print(
    "min / max weight =",
    round(weighted_pond["weight"].min(), 3),
    "/",
    round(weighted_pond["weight"].max(), 3),
)
{% endhighlight %}

```
Kish deff (raked pond) = 1.81
min / max weight = 0.055 / 5.0
```

{% highlight python %}
boot_pond = bootstrap_weights(
    recipe_pond,
    replicates=400,
    seed=42,
    point=fitted_pond,
)

approval_pond_ci = pd.concat(
    [
        boot_proportion(boot_pond, name).assign(category=name)
        for name in ["approve", "disapprove", "unsure", "dk"]
    ],
    ignore_index=True,
)[["category", "estimate", "se", "ci_lower", "ci_upper"]]

approval_pond_ci.round(3)
{% endhighlight %}

```
  category  estimate    se  ci_lower  ci_upper
   approve     0.292 0.013     0.266     0.319
disapprove     0.531 0.014     0.504     0.557
    unsure     0.154 0.013     0.128     0.179
        dk     0.023 0.004     0.015     0.031
```

The results tell a similar story to the R example. Raking from uniform weights
and raking from `pond` produce similar approval estimates, and the bootstrap
intervals overlap. The larger difference is still between the original `pond`
weights and the full demographic rake, again pointing to socioeconomic
composition.

## Nonresponse adjustment, then raking

The CEP file is a respondent file: it does not include sample cases that never
answered. To show the usual cascade — nonresponse adjustment, then
calibration — I keep the CEP cases as respondents and add 400 simulated
nonrespondents with biased demographics (more men, younger, more rural). The
point is the recipe shape, not a claim about CEP field operations.

`weightpipe` supports two nonresponse methods in `step_nonresponse`:

1. **`weighting_class`** — within cells defined by `by=...` (e.g. sex × age ×
   area), multiply respondent weights by
   $$w_{\text{cell}} / w_{\text{respondents in cell}}$$
   and set nonrespondent weights to zero.
2. **`propensity`** — fit a response model with `formula=...` and
   `engine="logit"` (default), `"gbm"`, or `"forest"`, then either:
   - group units into propensity classes (`num_classes=5`, default) and apply
     a class adjustment like weighting-class, or
   - use direct inverse-propensity factors (`num_classes=None`), i.e.
     $$1/\hat{p}_i$$
     for respondents.

{% highlight python %}
rng = np.random.default_rng(42)
n_nr = 400

nonrespondents = pd.DataFrame(
    {
        "sex": rng.choice([1, 2], size=n_nr, p=[0.65, 0.35]),
        "agecat": rng.choice(
            [1, 2, 3, 4, 5],
            size=n_nr,
            p=[0.25, 0.25, 0.20, 0.15, 0.15],
        ),
        "ses": rng.choice(
            [1, 2, 3, 4, 5],
            size=n_nr,
            p=[0.05, 0.10, 0.30, 0.40, 0.15],
        ),
        "region": rng.choice(list(range(1, 16)), size=n_nr),
        "area": rng.choice([1, 2], size=n_nr, p=[0.70, 0.30]),
        "approval": np.nan,
        "responded": 0,
        "base": 1.0,
    }
)

respondents = dat.copy()
respondents["responded"] = 1
respondents["base"] = 1.0
for code, name in [
    (1, "approve"),
    (2, "disapprove"),
    (3, "unsure"),
    (9, "dk"),
]:
    respondents[name] = (respondents["approval"] == code).astype(int)
    nonrespondents[name] = 0

frame = pd.concat([respondents, nonrespondents], ignore_index=True)
print("n_sample =", len(frame))
print("n_respondents =", int(frame["responded"].sum()))
print("response rate =", round(float(frame["responded"].mean()), 3))
{% endhighlight %}

```
n_sample = 1912
n_respondents = 1512
response rate = 0.791
```

### Weighting-class nonresponse

{% highlight python %}
recipe_nr = (
    Recipe(frame, base_weight="base")
    .step_nonresponse(
        respondent="responded",
        method="weighting_class",
        by=["sex", "agecat", "area"],
    )
    .step_calibrate(
        method="raking",
        proportions=proportions,
        max_iter=100,
        tol=1e-8,
    )
    .step_trim(
        max_ratio=5.0,
        reference="value",
        redistribute=True,
    )
)

fitted_nr = recipe_nr.prep(min_cell_n=1, warn=False)
weighted_nr = collect_weights(
    fitted_nr,
    keep_intermediate=True,
    drop_zero=True,
)
factors = weight_factors(fitted_nr)

print("active units =", len(weighted_nr))
print("sum(weight) =", round(float(weighted_nr["weight"].sum()), 3))
print("Kish deff =", round(design_effect(fitted_nr), 3))
factors.loc[frame["responded"] == 1, "factor_nonresponse"].describe().round(3)
{% endhighlight %}

```
active units = 1512
sum(weight) = 1912.0
Kish deff = 1.383

count   1512.000
mean       1.265
std        0.292
min        1.047
25%        1.099
50%        1.140
75%        1.385
max        3.545
```

The sum of final weights matches the full sample size (1912): nonresponse
inflation restores the weight of nonrespondents, and raking preserves that
total while matching population margins.

{% highlight python %}
estimate(
    recipe_nr,
    "approve",
    estimand="proportion",
    fitted=fitted_nr,
    variance="bootstrap",
    replicates=200,
    seed=42,
).round(3)
{% endhighlight %}

```
 estimate    se  ci_lower  ci_upper  level  R_used   estimand variable  variance
    0.297 0.012     0.274     0.320   0.95     200 proportion  approve bootstrap
```

### Logistic propensity nonresponse

Same cascade, but response propensity is estimated with logistic regression on
`sex`, `agecat`, and `area`. With `num_classes=5`, units are grouped by
predicted $$\hat{p}$$ and adjusted within classes:

{% highlight python %}
recipe_prop = (
    Recipe(frame, base_weight="base")
    .step_nonresponse(
        respondent="responded",
        method="propensity",
        engine="logit",
        formula="~ sex + agecat + area",
        num_classes=5,
    )
    .step_calibrate(
        method="raking",
        proportions=proportions,
        max_iter=100,
        tol=1e-8,
    )
    .step_trim(
        max_ratio=5.0,
        reference="value",
        redistribute=True,
    )
)

fitted_prop = recipe_prop.prep(min_cell_n=1, warn=False)
factors_prop = weight_factors(fitted_prop)

print("Kish deff =", round(design_effect(fitted_prop), 3))
print(
    "mean propensity =",
    round(
        fitted_prop.diagnostics["steps"]["nonresponse"]["mean_propensity"],
        3,
    ),
)
factors_prop.loc[frame["responded"] == 1, "factor_nonresponse"].describe().round(3)
{% endhighlight %}

```
Kish deff = 1.381
mean propensity = 0.791

count   1512.000
mean       1.265
std        0.216
min        1.047
25%        1.101
50%        1.193
75%        1.373
max        1.679
```

{% highlight python %}
estimate(
    recipe_prop,
    "approve",
    estimand="proportion",
    fitted=fitted_prop,
    variance="bootstrap",
    replicates=200,
    seed=42,
).round(3)
{% endhighlight %}

```
 estimate    se  ci_lower  ci_upper  level  R_used   estimand variable  variance
    0.297 0.012     0.274     0.321   0.95     200 proportion  approve bootstrap
```

For direct inverse-propensity weighting instead of classes, set
`num_classes=None`:

{% highlight python %}
.step_nonresponse(
    respondent="responded",
    method="propensity",
    engine="logit",
    formula="~ sex + agecat + area",
    num_classes=None,  # factor = 1 / p_hat for respondents
)
{% endhighlight %}

On this frame that yields Kish deff ≈ 1.377 and approve ≈ 0.298 — essentially
the same point estimate, with different NR-factor dispersion (max factor about
3.1 for direct $$1/\hat{p}$$, 1.7 for propensity classes, and 3.5 for
weighting-class).

Swap `engine="gbm"` or `engine="forest"` for a tree-based response surface.
Here they track logit closely (Kish ≈ 1.38, same approval story). Prefer them
when response is clearly nonlinear in the covariates; otherwise logit stays the
transparent default.

So the variants agree on approval here; they differ mainly in how uneven the
nonresponse factors are. Weighting-class is simple when cells are not sparse;
propensity is useful when you want a response model and smoother factors across
many covariates.

### Keeping propensity classes while raking

Plain demographic raking after propensity classes can reshuffle weight across
those classes. `assist="propensity_class"` adds the post-NR class totals as an
extra raking margin so demographics are matched while class mass stays fixed.
Pass the same `proportions=` as elsewhere — weightpipe scales them to the
current weight total before attaching the class counts:

{% highlight python %}
recipe_assist = (
    Recipe(frame, base_weight="base")
    .step_nonresponse(
        respondent="responded",
        method="propensity",
        engine="logit",
        formula="~ sex + agecat + area",
        num_classes=5,
    )
    .step_calibrate(
        method="raking",
        proportions=proportions,
        assist="propensity_class",
        max_iter=100,
        tol=1e-8,
    )
    .step_trim(
        max_ratio=5.0,
        reference="value",
        redistribute=True,
    )
)

fitted_assist = recipe_assist.prep(min_cell_n=1, warn=False)
print("Kish deff =", round(design_effect(fitted_assist), 3))
estimate(
    recipe_assist,
    "approve",
    estimand="proportion",
    fitted=fitted_assist,
    variance="bootstrap",
    replicates=200,
    seed=42,
).round(3)
{% endhighlight %}

```
Kish deff = 1.447

 estimate    se  ci_lower  ci_upper  level  R_used   estimand variable  variance
    0.299 0.013     0.274     0.324   0.95     200 proportion  approve bootstrap
```

Before trimming, the five propensity-class weight totals match the post-NR
totals exactly (445, 335, 545, 317, 270). Trim can move mass a little; the
assist step is what locks the NR adjustment during calibration. Approval stays
in the same neighborhood as the unassisted cascade (0.297), with a modestly
higher Kish deff.

## The reusable recipe

In short, the updated workflow looks like this:

{% highlight python %}
from weightpipe import Recipe, collect_weights, design_effect, estimate

recipe = (
    Recipe(frame, base_weight="base")  # or respondents-only `dat`
    .step_nonresponse(
        respondent="responded",
        method="weighting_class",  # or propensity + engine="logit"|"gbm"|"forest"
        by=["sex", "agecat", "area"],
    )
    .step_calibrate(
        method="raking",
        proportions=proportions,  # + assist="propensity_class" after propensity NR
    )
    .step_trim(
        max_ratio=5.0,
        reference="value",
        redistribute=True,
    )
)

fitted = recipe.prep()
weights = collect_weights(fitted)
design_effect(fitted)

estimate(
    recipe,
    "approve",
    estimand="proportion",
    fitted=fitted,
    variance="bootstrap",
    replicates=400,
    seed=42,
)
{% endhighlight %}

For a clustered sample, pass a `Design` to `Recipe.from_design` and let
`estimate` pick up strata/PSU from the design for bootstrap or jackknife
variance. The
[weightpipe documentation](https://github.com/sdaza/weightpipe) also covers
eligibility, linear/GREG and model-assisted calibration, design-based
estimation, and sample-size planning.

***

**Related:** [Raking weights with R (2012)](/blog/2012/raking/)
