"""Run the equations stored in an AnyLogic .alp file, in Python.

The post claims the AnyLogic model and the notebook model are the same model.
That claim is only worth making if something checks it, and AnyLogic itself
cannot be driven from a script here. So this module reads the .alp, extracts the
stocks, flows, auxiliaries and parameters, translates the Java expressions into
Python, and integrates them with the same explicit Euler scheme the notebook
uses. Comparing the two trajectories turns "these cannot drift apart" from an
assertion into a test.

What this does *not* do is validate AnyLogic's own solver, units, or diagram.
It validates the equations and parameter values the file contains.

Usage:
    from alp_model import AlpModel
    model = AlpModel.from_file("assets/files/marketplace_sd.alp")
    df = model.run(weeks=500, dt=0.125, overrides={"swLiquidity": 0.0})
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

# Java library calls that appear in the formulas, mapped onto Python callables.
FUNCTIONS = {
    "max": max,
    "min": min,
    "exp": math.exp,
    "log": math.log,
    "sqrt": math.sqrt,
    "abs": abs,
    "pow": lambda a, b: a ** b,
}


def _java_to_python(expr: str) -> str:
    """Translate the subset of Java used in the model formulas into Python.

    Handles the boolean operators and the ternary conditional; arithmetic and
    the function calls in FUNCTIONS already share Java and Python syntax.
    """
    expr = expr.replace("&&", " and ").replace("||", " or ")
    expr = re.sub(r"(?<![=!<>])!(?!=)", " not ", expr)
    return _rewrite_ternaries(expr)


def _rewrite_ternaries(expr: str) -> str:
    """Rewrite `cond ? a : b` as `((a) if (cond) else (b))`, innermost first.

    Scanning for the last `?` finds an innermost conditional, whose matching `:`
    is then the next one at the same bracket depth. Repeating until no `?`
    remains handles nesting without needing a full parser.
    """
    while "?" in expr:
        q = expr.rfind("?")
        depth = 0
        colon = -1
        for i in range(q + 1, len(expr)):
            ch = expr[i]
            if ch in "([":
                depth += 1
            elif ch in ")]":
                if depth == 0:
                    break
                depth -= 1
            elif ch == ":" and depth == 0:
                colon = i
                break
        if colon == -1:
            raise ValueError(f"unbalanced ternary in: {expr}")
        # The condition runs back to the start of the enclosing bracket.
        depth = 0
        start = 0
        for i in range(q - 1, -1, -1):
            ch = expr[i]
            if ch in ")]":
                depth += 1
            elif ch in "([":
                if depth == 0:
                    start = i + 1
                    break
                depth -= 1
        # The false branch runs to the end of the enclosing bracket.
        depth = 0
        end = len(expr)
        for i in range(colon + 1, len(expr)):
            ch = expr[i]
            if ch in "([":
                depth += 1
            elif ch in ")]":
                if depth == 0:
                    end = i
                    break
                depth -= 1
        cond = expr[start:q].strip()
        true_branch = expr[q + 1:colon].strip()
        false_branch = expr[colon + 1:end].strip()
        expr = (f"{expr[:start]}(({true_branch}) if ({cond}) else ({false_branch}))"
                f"{expr[end:]}")
    return expr


@dataclass
class AlpModel:
    params: dict[str, float]
    stocks: dict[str, float]                    # name -> initial value
    formulas: dict[str, str]                    # aux and flow name -> Python expression
    inflows: dict[str, list[str]] = field(default_factory=dict)
    outflows: dict[str, list[str]] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)   # evaluation order for formulas

    @classmethod
    def from_file(cls, path: str | Path) -> "AlpModel":
        xml = Path(path).read_text()

        def variables(kind: str) -> list[tuple[str, str, str]]:
            """Return (name, value-expression, element attributes) per variable class.

            The value expression is the formula for flows and auxiliaries, the
            initial value for stocks, and the default value for parameters.
            """
            out = []
            pattern = re.compile(
                rf'<Variable Class="{kind}"([^>]*)>(.*?)</Variable>', re.S)
            for m in pattern.finditer(xml):
                block = m.group(2)
                name = re.search(r"<Name><!\[CDATA\[(.*?)\]\]></Name>", block, re.S)
                expr = re.search(r"<(?:Formula|InitialValue|Code)><!\[CDATA\[(.*?)\]\]>"
                                 r"</(?:Formula|InitialValue|Code)>", block, re.S)
                if name and expr:
                    out.append((name.group(1), expr.group(1), m.group(1)))
            return out

        params: dict[str, float] = {}
        for name, code, _ in variables("Parameter"):
            try:
                params[name] = float(code)
            except ValueError:
                continue

        stocks = {n: float(v) for n, v, _ in variables("StockVariable")}

        formulas: dict[str, str] = {}
        for kind in ("Flow", "AuxVariable"):
            for name, expr, _ in variables(kind):
                formulas[name] = _java_to_python(expr)

        # Stock topology: flows carry SourceId/TargetId attributes referring to
        # the stock ids, so the ODE for each stock is inflows minus outflows.
        ids = {}
        for m in re.finditer(r'<Variable Class="StockVariable"[^>]*>(.*?)</Variable>',
                             xml, re.S):
            block = m.group(1)
            i = re.search(r"<Id>(\d+)</Id>", block)
            n = re.search(r"<Name><!\[CDATA\[(.*?)\]\]></Name>", block, re.S)
            if i and n:
                ids[i.group(1)] = n.group(1)

        inflows: dict[str, list[str]] = {s: [] for s in stocks}
        outflows: dict[str, list[str]] = {s: [] for s in stocks}
        for m in re.finditer(r'<Variable Class="Flow"[^>]*>(.*?)</Variable>', xml, re.S):
            block = m.group(1)
            n = re.search(r"<Name><!\[CDATA\[(.*?)\]\]></Name>", block, re.S)
            props = re.search(r"<Properties([^>]*)>", block)
            if not n or not props:
                continue
            src = re.search(r'SourceId="(\d+)"', props.group(1))
            tgt = re.search(r'TargetId="(\d+)"', props.group(1))
            if src and ids.get(src.group(1)) in outflows:
                outflows[ids[src.group(1)]].append(n.group(1))
            if tgt and ids.get(tgt.group(1)) in inflows:
                inflows[ids[tgt.group(1)]].append(n.group(1))

        model = cls(params=params, stocks=stocks, formulas=formulas,
                    inflows=inflows, outflows=outflows)
        model.order = model._evaluation_order()
        return model

    def _evaluation_order(self) -> list[str]:
        """Topologically sort the formulas so each is evaluated after its inputs."""
        known = set(self.params) | set(self.stocks)
        deps = {
            name: {t for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr)
                   if t in self.formulas and t != name}
            for name, expr in self.formulas.items()
        }
        order: list[str] = []
        remaining = dict(deps)
        while remaining:
            ready = [n for n, d in remaining.items() if not (d - set(order))]
            if not ready:
                raise ValueError(f"circular formula dependency among {list(remaining)}")
            for n in sorted(ready):
                order.append(n)
                remaining.pop(n)
        _ = known
        return order

    def run(self, weeks: float = 500.0, dt: float = 0.125,
            overrides: dict[str, float] | None = None) -> pd.DataFrame:
        """Integrate the model with explicit Euler, as the notebook does."""
        params = dict(self.params)
        params.update(overrides or {})
        state = dict(self.stocks)
        rows = []

        compiled = {n: compile(self.formulas[n], f"<{n}>", "eval") for n in self.order}

        for i in range(int(weeks / dt) + 1):
            t = i * dt
            scope: dict[str, object] = {**FUNCTIONS, **params, **state, "time": lambda: t}
            for name in self.order:
                scope[name] = eval(compiled[name], {"__builtins__": {}}, scope)

            rows.append({"week": t, **{k: scope[k] for k in self.stocks},
                         **{k: scope[k] for k in self.order}})

            deltas = {
                s: sum(scope[f] for f in self.inflows[s]) - sum(scope[f] for f in self.outflows[s])
                for s in state
            }
            for s in state:
                state[s] += dt * deltas[s]

        return pd.DataFrame(rows)


if __name__ == "__main__":
    m = AlpModel.from_file("assets/files/marketplace_sd.alp")
    print(f"{len(m.stocks)} stocks, {len(m.formulas)} formulas, {len(m.params)} parameters")
    df = m.run()
    print(df.iloc[::800][["week", "buyers", "sellers", "matchRate", "fillRate"]]
          .to_string(index=False))
