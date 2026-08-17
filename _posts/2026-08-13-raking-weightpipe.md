---
layout: post
author: Sebastian Daza
title: "Raking weights with Python and weightpipe"
date: 2026-08-13
giscus_comments: true
tags: python, survey, data science
---

In my [2012 post on raking weights in R](/blog/2012/raking/), I used `anesrake`
to adjust a Chilean public opinion survey to known population margins. In this
post, I revisit the same example in Python using
[weightpipe](https://github.com/sdaza/weightpipe), a package I wrote for survey
weighting recipes.

The basic ideas—when to use raking, how to select variables, why extreme weights
may need truncation, and how to examine the design effect—have not changed. The
original post discusses that background. Here I concentrate on the Python
workflow and extend the example to estimation and nonresponse adjustment.

Install from GitHub (not on PyPI yet):

```bash
pip install "git+https://github.com/sdaza/weightpipe.git"
# or
uv add "git+https://github.com/sdaza/weightpipe.git"
```


## Data

As in the original post, I use the CEP Public Opinion Survey from July–August
2012 to estimate presidential approval
([data](https://raw.githubusercontent.com/sdaza/sdaza.github.io/main/_R/data/cep
.csv)).
Five variables enter the raking: `sex`, `agecat`, `ses`, `region`, and `area`.



{% highlight python %}
import numpy as np
import pandas as pd

pd.set_option("display.notebook_repr_html", False)
pd.set_option("display.float_format", lambda x: f"{x:.3f}")
pd.set_option("display.width", 120)
pd.set_option("display.max_columns", None)

from weightpipe import (
    WeightPipe,
    boot_proportion,
    bootstrap_weights,
    design_effect,
    weight_factors,
)

dat = pd.read_csv(
    "https://raw.githubusercontent.com/sdaza/sdaza.github.io/main/_R/data/cep.csv"
)
for code, name in [(1, "approve"), (2, "disapprove"), (3, "unsure"), (9, "dk")]:
    dat[name] = (dat["approval"] == code).astype(int)

dat[["sex", "agecat", "ses", "region", "area", "pond", "approval"]].head()

{% endhighlight %}




       sex  agecat  ses  region  area  pond  approval
    0    1       2    2      13     1 1.977         2
    1    1       5    2      13     1 1.243         1
    2    2       2    3       9     2 0.514         2
    3    1       5    3       9     1 0.421         1
    4    1       5    4      10     1 0.526         1



Sample margins (unweighted) for the raking variables:



{% highlight python %}
for var in ["sex", "agecat", "ses", "region", "area"]:
    print(f"\n{var}")
    print(
        dat[var]
        .value_counts(normalize=True)
        .sort_index()
        .rename_axis(None)
        .round(3)
        .to_string()
    )

{% endhighlight %}


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


## Population targets

Population shares come from the Chilean Census 2002 (`sex`, `agecat`, `region`,
`area`) and the Bicentenario Survey 2009 (`ses`) — same targets as in 2012.
Rounded census vectors may not sum exactly to one; `weightpipe` renormalizes
them by default (`force1=True`), as in `anesrake`.



{% highlight python %}
# Chilean Census 2002
sex = {1: 0.49, 2: 0.51}  # 1 male, 2 female
agecat = {
    1: 0.163,  # 18-24
    2: 0.203,  # 25-34
    3: 0.195,  # 35-44
    4: 0.187,  # 45-54
    5: 0.253,  # 55+
}
region = {
    1: 0.015, 2: 0.031, 3: 0.016, 4: 0.039, 5: 0.102,
    6: 0.051, 7: 0.059, 8: 0.123, 9: 0.056, 10: 0.046,
    11: 0.006, 12: 0.010, 13: 0.408, 14: 0.023, 15: 0.013,
}
area = {1: 0.869, 2: 0.131}  # 1 urban, 2 rural

# Bicentenario Survey 2009
ses = {1: 0.109, 2: 0.184, 3: 0.261, 4: 0.364, 5: 0.083}  # abc1..e

proportions = {
    "sex": sex,
    "agecat": agecat,
    "ses": ses,
    "region": region,
    "area": area,
}

{% endhighlight %}

## Raking with `weightpipe`

`WeightPipe(dat)` now assigns unit base weights automatically when no design
weights are supplied. I then define the two adjustment steps:

- `calibrate(method="raking", proportions=...)` to run iterative proportional
fitting against the population margins.
- `trim(max_ratio=5, reference="value")` to cap weights at five and redistribute
the excess so that the total weight is preserved.

Unlike `anesrake`, this step does not select variables using options such as
`pctlim` and `nlim`. I pass the margins selected for the analysis directly.
Weights are computed on first use (`collect_weights()`, `weights`, or
`estimate()`).



{% highlight python %}
pipe = (
    WeightPipe(dat)
    .options(warn=False)
    .calibrate(
        method="raking",
        proportions=proportions,
        max_iter=100,
        tol=1e-8,
    )
    .trim(max_ratio=5.0, reference="value", redistribute=True)
)

weighted = pipe.collect_weights(keep_intermediate=True)

print("n =", len(weighted))
print("sum(weight) =", round(float(weighted["weight"].sum()), 3))
print("min / max weight =", round(weighted["weight"].min(), 3), "/", round(weighted["weight"].max(), 3))
print("Kish deff =", round(design_effect(pipe.result), 3))
print("converged =", pipe.diagnostics["steps"]["calibrate"]["converged"])
print("iterations =", pipe.diagnostics["steps"]["calibrate"]["iterations"])
weighted[["weight"]].describe().T

{% endhighlight %}

    n = 1512
    sum(weight) = 1512.0
    min / max weight = 0.332 / 4.304
    Kish deff = 1.38
    converged = True
    iterations = 12





              count  mean   std   min   25%   50%   75%   max
    weight 1512.000 1.000 0.616 0.332 0.618 0.804 1.105 4.304



Kish's approximate design effect from unequal weighting is again about **1.38**
— the same figure as in the original R post. Weighting loss is $$L_w =
\mathrm{deff} - 1 \approx 0.38$$, under the usual caveats (no clustering in this
approximation).


### Approval estimates with bootstrap CIs

Approval codes: 1 = approve, 2 = disapprove, 3 = unsure, 9 = don't know.
Use `pipe.estimate` on binary indicators instead of a custom weighted
tabulation.
With no strata/PSU in the CEP file, this is an unequal-weight bootstrap that
re-runs the full weighting cascade in each replicate.



{% highlight python %}
pipe.estimate(
    "approve",
    estimand="proportion",
    variance="bootstrap",
    replicates=400,
    seed=42,
).round(3)

{% endhighlight %}




       estimate    se  ci_lower  ci_upper  level  R_used    estimand variable   variance  design
    0     0.298 0.013     0.272     0.325  0.950     400  proportion  approve  bootstrap  custom




{% highlight python %}
boot = bootstrap_weights(
    pipe.recipe,
    replicates=400,
    seed=42,
    point=pipe.result,
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




         category  estimate    se  ci_lower  ci_upper
    0     approve     0.298 0.013     0.272     0.325
    1  disapprove     0.521 0.013     0.494     0.547
    2      unsure     0.161 0.010     0.141     0.181
    3          dk     0.020 0.003     0.013     0.027



## Raking on top of existing survey weights

The CEP file includes `pond` weights (max ≈ 17.6). As before, documentation of
how they were built is thin. We can still use them as the base weight and rake
(here only on `ses` and `region`, the margins that were most off after applying
`pond` in the 2012 analysis).



{% highlight python %}
print("pond summary")
print(dat["pond"].describe().round(3).to_string())
print("Kish deff (pond) =", round(design_effect(dat["pond"]), 3))

pipe_pond = (
    WeightPipe(dat, weight="pond")
    .options(warn=False)
    .calibrate(
        method="raking",
        proportions={"ses": proportions["ses"], "region": proportions["region"]},
        max_iter=100,
        tol=1e-8,
    )
    .trim(max_ratio=5.0, reference="value", redistribute=True)
)

weighted_pond = pipe_pond.collect_weights()

print("Kish deff (raked pond) =", round(design_effect(pipe_pond.result), 3))
print("min / max weight =", round(weighted_pond["weight"].min(), 3), "/", round(weighted_pond["weight"].max(), 3))

{% endhighlight %}

    pond summary
    count   1512.000
    mean       1.000
    std        1.044
    min        0.015
    25%        0.455
    50%        0.786
    75%        1.235
    max       17.563
    Kish deff (pond) = 2.088
    Kish deff (raked pond) = 1.81
    min / max weight = 0.055 / 5.0



{% highlight python %}
boot_pond = bootstrap_weights(
    pipe_pond.recipe,
    replicates=400,
    seed=42,
    point=pipe_pond.result,
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




         category  estimate    se  ci_lower  ci_upper
    0     approve     0.292 0.013     0.266     0.319
    1  disapprove     0.531 0.014     0.504     0.557
    2      unsure     0.154 0.013     0.128     0.179
    3          dk     0.023 0.004     0.015     0.031



The results are similar to those in the R example. Raking from uniform weights
and raking from `pond` produce comparable approval estimates, and their
bootstrap intervals overlap.

## Nonresponse adjustment, then raking

The CEP file contains respondents only; sample cases that did not answer are not
available. To illustrate nonresponse adjustment followed by calibration, I keep
the CEP observations as respondents and add simulated nonrespondents. This is
only an illustration of the method, not a claim about CEP fieldwork.

`weightpipe` supports two `nonresponse` methods:

1. **`weighting_class`** — inflate respondents within `by=` cells and set
nonrespondent weights to zero.
2. **`propensity`** — fit a response model with `engine="logit"` (default),
`"gbm"`, or `"forest"`, then use propensity classes (`num_classes=5`) or direct
inverse-propensity factors (`num_classes=None`).



{% highlight python %}
rng = np.random.default_rng(42)
n_nr = 400

nonrespondents = pd.DataFrame(
    {
        "sex": rng.choice([1, 2], size=n_nr, p=[0.65, 0.35]),
        "agecat": rng.choice([1, 2, 3, 4, 5], size=n_nr, p=[0.25, 0.25, 0.20, 0.15, 0.15]),
        "ses": rng.choice([1, 2, 3, 4, 5], size=n_nr, p=[0.05, 0.10, 0.30, 0.40, 0.15]),
        "region": rng.choice(list(range(1, 16)), size=n_nr),
        "area": rng.choice([1, 2], size=n_nr, p=[0.70, 0.30]),
        "approval": np.nan,
        "responded": 0,
    }
)

respondents = dat.copy()
respondents["responded"] = 1
for code, name in [(1, "approve"), (2, "disapprove"), (3, "unsure"), (9, "dk")]:
    respondents[name] = (respondents["approval"] == code).astype(int)
    nonrespondents[name] = 0

frame = pd.concat([respondents, nonrespondents], ignore_index=True)
print("n_sample =", len(frame))
print("n_respondents =", int(frame["responded"].sum()))
print("response rate =", round(float(frame["responded"].mean()), 3))

{% endhighlight %}

    n_sample = 1912
    n_respondents = 1512
    response rate = 0.791


### Weighting-class nonresponse



{% highlight python %}
pipe_nr = (
    WeightPipe(frame)
    .options(min_cell_n=1, warn=False)
    .nonresponse(
        respondent="responded",
        method="weighting_class",
        by=["sex", "agecat", "area"],
    )
    .calibrate(
        method="raking",
        proportions=proportions,
        max_iter=100,
        tol=1e-8,
    )
    .trim(max_ratio=5.0, reference="value", redistribute=True)
)

weighted_nr = pipe_nr.collect_weights(keep_intermediate=True, drop_zero=True)
factors = weight_factors(pipe_nr.result)

print("active units =", len(weighted_nr))
print("sum(weight) =", round(float(weighted_nr["weight"].sum()), 3))
print("Kish deff =", round(design_effect(pipe_nr.result), 3))
factors.loc[frame["responded"] == 1, "factor_nonresponse"].describe().round(3)

{% endhighlight %}

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
    Name: factor_nonresponse, dtype: float64




{% highlight python %}
pipe_nr.estimate(
    "approve",
    estimand="proportion",
    variance="bootstrap",
    replicates=200,
    seed=42,
).round(3)

{% endhighlight %}




       estimate    se  ci_lower  ci_upper  level  R_used    estimand variable   variance  design
    0     0.297 0.012     0.274     0.320  0.950     200  proportion  approve  bootstrap  custom



### Logistic propensity nonresponse

I now repeat the adjustment using a logistic response model with `sex`,
`agecat`, and `area` as predictors. With `num_classes=5`, observations are
grouped by their predicted $$\hat{p}$$ and adjusted within classes:



{% highlight python %}
pipe_prop = (
    WeightPipe(frame)
    .options(min_cell_n=1, warn=False)
    .nonresponse(
        respondent="responded",
        method="propensity",
        engine="logit",
        formula="~ sex + agecat + area",
        num_classes=5,
    )
    .calibrate(
        method="raking",
        proportions=proportions,
        max_iter=100,
        tol=1e-8,
    )
    .trim(max_ratio=5.0, reference="value", redistribute=True)
)

factors_prop = weight_factors(pipe_prop.result)

print("Kish deff =", round(design_effect(pipe_prop.result), 3))
print(
    "mean propensity =",
    round(pipe_prop.diagnostics["steps"]["nonresponse"]["mean_propensity"], 3),
)
factors_prop.loc[frame["responded"] == 1, "factor_nonresponse"].describe().round(3)

{% endhighlight %}

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
    Name: factor_nonresponse, dtype: float64




{% highlight python %}
pipe_prop.estimate(
    "approve",
    estimand="proportion",
    variance="bootstrap",
    replicates=200,
    seed=42,
).round(3)

{% endhighlight %}




       estimate    se  ci_lower  ci_upper  level  R_used    estimand variable   variance  design
    0     0.297 0.012     0.274     0.321  0.950     200  proportion  approve  bootstrap  custom



For direct inverse-propensity weighting, use `num_classes=None`
(factor = $$1/\hat{p}$$ for respondents). In this example, that gives deff ≈
1.377
and approval ≈ 0.298. The point estimate is similar to those from weighting
classes and propensity classes, although the factors have different dispersion.

We can replace `engine="logit"` with `engine="gbm"` or `engine="forest"` when
the response process is likely to be nonlinear. Here, the three engines give
almost identical results (Kish deff ≈ 1.38), so I prefer the more interpretable
logistic model.


### Keeping propensity classes while raking

Demographic raking after a propensity adjustment can redistribute weight
across propensity classes. To avoid this, I use `assist="propensity_class"`.
It adds the post-nonresponse class totals as another raking margin, preserving
them while matching the demographic targets. I can pass the same
`proportions=` used above; `weightpipe` scales them to the current weight total
before adding the class totals.



{% highlight python %}
pipe_assist = (
    WeightPipe(frame)
    .options(min_cell_n=1, warn=False)
    .nonresponse(
        respondent="responded",
        method="propensity",
        engine="logit",
        formula="~ sex + agecat + area",
        num_classes=5,
    )
    .calibrate(
        method="raking",
        proportions=proportions,
        assist="propensity_class",
        max_iter=100,
        tol=1e-8,
    )
    .trim(max_ratio=5.0, reference="value", redistribute=True)
)

print("Kish deff =", round(design_effect(pipe_assist.result), 3))
pipe_assist.estimate(
    "approve",
    estimand="proportion",
    variance="bootstrap",
    replicates=200,
    seed=42,
).round(3)

{% endhighlight %}

    Kish deff = 1.447





       estimate    se  ci_lower  ci_upper  level  R_used    estimand variable   variance  design
    0     0.299 0.013     0.274     0.324  0.950     200  proportion  approve  bootstrap  custom



Before trimming, the five propensity-class weight totals exactly match the
post-nonresponse totals. Trimming can change them slightly, but the assisted
calibration itself preserves the nonresponse adjustment. The approval estimate
remains close to the unassisted result (~0.297), although the Kish design effect
is modestly higher (~1.45).

## Putting the steps together

The complete workflow can be summarized as follows:

```python
from weightpipe import WeightPipe, design_effect

pipe = (
    WeightPipe(frame)  # or respondents-only `dat`
    # With a design: WeightPipe(frame, weight="pw", psu="psu", strata="stratum")
    .nonresponse(
        respondent="responded",
        method="weighting_class",  # or propensity +
engine="logit"|"gbm"|"forest"
        by=["sex", "agecat", "area"],
    )
    .calibrate(
        method="raking",
        proportions=proportions,  # + assist="propensity_class" after propensity
NR
    )
    .trim(max_ratio=5.0, reference="value", redistribute=True)
)

pipe.collect_weights()
design_effect(pipe.result)
pipe.estimate("approve", estimand="proportion", variance="bootstrap",
replicates=400, seed=42)
```

If strata and PSUs are available, pass them when constructing the pipe
(`psu=`, `strata=`). `estimate` then uses them for bootstrap or jackknife
variance. Other examples in the
[weightpipe documentation](https://github.com/sdaza/weightpipe) cover
eligibility adjustments, linear/GREG calibration, design-based estimation,
and sample-size planning.

***

**Related:** [Raking weights with R (2012)](/blog/2012/raking/)
