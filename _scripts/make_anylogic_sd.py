"""Generate the AnyLogic stock-and-flow model used in the marketplace post.

The equations here are the single source of truth: the same specification is
mirrored by the Python implementation in the notebook, so both produce the same
trajectory. All parameter values are synthetic.

Usage:
    .venv/bin/python _scripts/make_anylogic_sd.py assets/files/marketplace_sd.alp
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scenarios import SCENARIOS as EXPERIMENTS  # noqa: E402

# Where each experiment drops its results, relative to the folder holding the
# .alp, which is AnyLogic's working directory during a run.
EXPORT_DIR = "experiments"

# Samples each auto-created dataset must hold to cover the whole run, with a
# little headroom over the STOP_TIME + 1 weekly points actually recorded.
DATASET_CAPACITY = 600

MODEL_NAME = "marketplace_sd"
TIME_UNIT = "Week"
STOP_TIME = 500.0
TIME_STEP = 0.125

C_DEMAND = -14513374
C_SUPPLY = -13395457
C_AUX = -26624
C_MONEY = -29696
C_STRESS = -65536


@dataclass
class Stock:
    name: str
    init: str
    x: int
    y: int
    color: int = C_DEMAND
    label: tuple[int, int] = (-40, 0)
    expression: str | None = None


@dataclass
class Flow:
    name: str
    formula: str
    x: int
    y: int
    points: list[tuple[int, int]]
    source: str | None = None
    target: str | None = None
    color: int = C_DEMAND
    label: tuple[int, int] = (-25, -22)


@dataclass
class Aux:
    name: str
    formula: str
    x: int
    y: int
    color: int = C_AUX
    label: tuple[int, int] = (-25, -25)


@dataclass
class Param:
    name: str
    value: str
    unit: str
    x: int
    y: int
    label: tuple[int, int] = (-55, -25)


STOCKS = [
    Stock("buyers", "6000", 380, 250, C_DEMAND),
    Stock("sellersOnboarding", "300", 380, 600, C_SUPPLY),
    Stock("sellers", "400", 380, 760, C_SUPPLY),
    Stock("reputation", "0.80", 120, 60, C_DEMAND, label=(-45, -5)),
    Stock("perceivedEarnings", "120", 820, 940, C_SUPPLY, label=(-50, 0)),
    Stock("cumulativeGMV", "0", 1320, 640, C_MONEY),
]

FLOWS = [
    Flow("buyerJoin", "visitors * conversion",
         180, 250, [(0, 0), (100, 0), (200, 0)], None, "buyers", C_DEMAND),
    Flow("buyerChurn",
         "buyers * max(0, buyerChurnBase * (1 + swLiquidity * churnSensitivity * (matchReference - matchRate)))",
         380, 250, [(0, 0), (140, 0), (280, 0)], "buyers", None, C_DEMAND,
         label=(20, -22)),
    Flow("sellerSignup",
         "paidSellerSignups + sellerReferral * sellers * pow(earningsRatio, entryElasticity) * sellerRoom",
         180, 600, [(0, 0), (100, 0), (200, 0)], None, "sellersOnboarding", C_SUPPLY),
    Flow("sellerActivate", "sellersOnboarding / onboardingTime",
         380, 600, [(0, 0), (0, 80), (0, 160)], "sellersOnboarding", "sellers",
         C_SUPPLY, label=(20, -5)),
    Flow("sellerChurn",
         "sellers * sellerChurnBase * pow(1 / max(earningsRatio, 0.05), churnElasticity)",
         380, 760, [(0, 0), (140, 0), (280, 0)], "sellers", None, C_SUPPLY,
         label=(20, -22)),
    Flow("reputationAdjust", "(matchRate - reputation) / reputationDelay",
         -60, 60, [(0, 0), (90, 0), (180, 0)], None, "reputation", C_DEMAND),
    Flow("earningsAdjust", "(sellerEarnings - perceivedEarnings) / earningsDelay",
         620, 940, [(0, 0), (100, 0), (200, 0)], None, "perceivedEarnings", C_SUPPLY),
    Flow("gmvAccumulation", "weeklyGMV",
         1320, 500, [(0, 0), (0, 70), (0, 140)], None, "cumulativeGMV", C_MONEY,
         label=(20, -5)),
]

AUX = [
    # policy switches: a scenario is a parameter change, not a code change
    Aux("matchEfficiency",
        "matchEfficiencyBase + (time() >= policyStart && time() < policyStop ? matchEfficiencyShift : 0)",
        980, 200, C_AUX, (-50, -25)),
    Aux("effectiveConversionBase",
        "baseConversion * (time() >= policyStart && time() < policyStop ? conversionMultiplier : 1)",
        180, 150, C_AUX, (-60, -25)),
    Aux("effectivePaidVisitors",
        "paidVisitors * (time() >= policyStart && time() < policyStop ? paidVisitorMultiplier : 1)",
        -60, 200, C_AUX, (-60, -25)),
    # matching
    Aux("demandSessions", "buyers * sessionsPerBuyer", 820, 320),
    Aux("supplyCapacity", "sellers * sellerCapacity", 820, 700),
    # one matching function, seen from each side: matched = matchRate * demand
    # = fillRate * capacity, so the two views cannot disagree
    Aux("matchRate", "1 - exp(-matchEfficiency * supplyCapacity / max(demandSessions, 1))",
        1020, 420, C_AUX, (0, -25)),
    Aux("fillRate", "min(1, matchedSessions / max(supplyCapacity, 1))",
        1020, 580, C_AUX, (0, -25)),
    # demand side
    Aux("buyerRoom", "max(0, 1 - swSaturation * buyers / marketBuyers)", 60, 330, C_AUX, (-30, 20)),
    Aux("visitors",
        "effectivePaidVisitors + swWordOfMouth * referralRate * buyers * reputation * buyerRoom",
        60, 250),
    Aux("conversion",
        "max(0.01, min(0.9, effectiveConversionBase * (1 + swLiquidity * conversionSensitivity * (matchRate - matchReference))))",
        180, 60, C_AUX, (-30, -25)),
    # supply side
    Aux("sellerRoom", "max(0, 1 - swSaturation * sellers / marketSellers)", 60, 680, C_AUX, (-30, 20)),
    Aux("sellerEarnings", "fillRate * sellerCapacity * price * (1 - takeRate)",
        1180, 700, C_MONEY, (0, -25)),
    Aux("earningsRatio",
        "swCrowding > 0 ? perceivedEarnings / earningsReference : 1",
        820, 820, C_STRESS, (-40, -25)),
    # value
    Aux("matchedSessions", "matchRate * demandSessions", 1180, 480, C_MONEY, (0, -25)),
    # GMV is buyer spend. Revenue is the platform take. GM is revenue minus a
    # lumped variable-cost rate on GMV, so a take-rate cut can grow GMV and
    # shrink GM.
    Aux("weeklyGMV", "matchedSessions * price", 1320, 400, C_MONEY, (0, -25)),
    Aux("weeklyRevenue", "weeklyGMV * takeRate", 1320, 340, C_MONEY, (0, -25)),
    Aux("weeklyGM", "weeklyGMV * (takeRate - variableCostRate)", 1470, 400, C_MONEY, (0, -25)),
]

PARAMS = [
    Param("marketBuyers", "250000", "buyers", -180, 330),
    Param("marketSellers", "25000", "sellers", -180, 680),
    Param("sessionsPerBuyer", "1.0", "sessions/buyer/week", 680, 250),
    Param("sellerCapacity", "12.0", "sessions/seller/week", 680, 770),
    Param("matchEfficiencyBase", "1.0", "dmnl", 980, 100),
    Param("matchEfficiencyShift", "0.0", "dmnl", 1140, 100),
    Param("conversionMultiplier", "1.0", "dmnl", 340, 100),
    Param("policyStart", "52", "week", 1140, 150),
    Param("paidVisitors", "500", "visitors/week", -180, 200),
    Param("referralRate", "0.030", "visitors/buyer/week", -180, 250),
    Param("baseConversion", "0.32", "dmnl", 60, 150),
    Param("conversionSensitivity", "1.8", "dmnl", 340, 40),
    Param("buyerChurnBase", "0.022", "1/week", 600, 180),
    Param("churnSensitivity", "2.5", "dmnl", 600, 130),
    Param("matchReference", "0.60", "dmnl", 760, 130),
    Param("paidSellerSignups", "25", "sellers/week", -180, 560),
    Param("sellerReferral", "0.012", "sellers/seller/week", -180, 610),
    Param("entryElasticity", "2.0", "dmnl", 60, 560),
    Param("onboardingTime", "12", "week", 540, 660),
    Param("sellerChurnBase", "0.012", "1/week", 600, 830),
    Param("churnElasticity", "2.5", "dmnl", 600, 880),
    Param("earningsDelay", "8", "week", 620, 1000),
    Param("earningsReference", "120", "money/seller/week", 980, 880),
    Param("reputationDelay", "12", "week", -60, 130),
    Param("price", "20", "money/session", 1320, 780),
    Param("takeRate", "0.30", "dmnl", 1320, 830),
    Param("variableCostRate", "0.04", "dmnl", 1470, 830),
    # policy window and scenario levers
    Param("policyStop", "1.0E9", "week", 1140, 200),
    Param("paidVisitorMultiplier", "1.0", "dmnl", -60, 150),
    # loop knockout switches: 1 keeps the loop, 0 cuts it
    Param("swLiquidity", "1.0", "dmnl", 340, 150),
    Param("swWordOfMouth", "1.0", "dmnl", -180, 150),
    Param("swCrowding", "1.0", "dmnl", 1180, 820),
    Param("swSaturation", "1.0", "dmnl", -180, 400),
]

JAVA_FUNCTIONS = {"max", "min", "exp", "pow", "abs", "time", "log", "sqrt"}


def derive_links() -> list[tuple[str, str]]:
    """One dependency link per formula reference.

    AnyLogic validates the stock-and-flow diagram against the equations: a
    variable used in a formula without an incoming link raises "used but not
    expected", and a link with no corresponding reference raises the converse.
    Deriving the links from the formulas keeps both sides consistent.
    """
    names = {el.name for el in [*STOCKS, *FLOWS, *AUX, *PARAMS]}
    links: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for el in [*FLOWS, *AUX]:
        for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", el.formula):
            if token in JAVA_FUNCTIONS or token not in names:
                continue
            pair = (token, el.name)
            if pair not in seen:
                seen.add(pair)
                links.append(pair)
    return links


LINKS = derive_links()


def check_scenarios() -> None:
    """A scenario may only set parameters the model actually has.

    Without this, a typo in a scenario would silently produce an experiment
    identical to the baseline rather than an error.
    """
    known = {p.name for p in PARAMS}
    for sc in EXPERIMENTS:
        unknown = set(sc.overrides) - known
        if unknown:
            raise SystemExit(
                f"scenario {sc.name!r} sets unknown parameter(s): "
                f"{', '.join(sorted(unknown))}")


def capacity_code() -> str:
    """Java that widens the auto-created datasets before a run starts.

    AnyLogic generates those datasets with room for 100 samples and offers no
    way to change that from the .alp, so a 500-week run keeps only weeks
    401-500. Capacity is settable at runtime, though, so raising it here is what
    makes the whole series survive to the export.
    """
    return f"""// Keep the full run, not just the last 100 samples.
try {{
    com.anylogic.engine.Agent exRoot = getEngine().getRoot();
    if (exRoot != null) {{
        for (Class<?> exClass = exRoot.getClass(); exClass != null;
                exClass = exClass.getSuperclass()) {{
            for (java.lang.reflect.Field exField : exClass.getDeclaredFields()) {{
                if (!com.anylogic.engine.analysis.BasicDataSet.class
                        .isAssignableFrom(exField.getType())) {{
                    continue;
                }}
                exField.setAccessible(true);
                Object exValue = exField.get(exRoot);
                if (exValue != null) {{
                    ((com.anylogic.engine.analysis.BasicDataSet) exValue)
                        .setCapacity({DATASET_CAPACITY});
                }}
            }}
        }}
    }}
}} catch (Exception exError) {{
    traceln("could not widen datasets: " + exError);
}}
"""


def export_code(scenario: str) -> str:
    """Java that writes one run's weekly series to experiments/<scenario>.csv.

    AnyLogic auto-creates a dataset per stock, flow and auxiliary, but the field
    names it generates are an internal detail. Rather than assume a naming
    convention, this walks the root agent's datasets and matches each one to the
    longest model variable name its field name contains, so `sellersOnboarding`
    is never mistaken for `sellers`.
    """
    names = [el.name for el in [*STOCKS, *FLOWS, *AUX]]
    known = ", ".join(f'"{n}"' for n in names)
    # Every local is prefixed: AnyLogic drops this into a method that already
    # has locals of its own (`root` among them), and Java rejects a redeclared
    # local rather than shadowing it.
    return f"""// Writes this run's weekly series next to the model file.
String exScenario = "{scenario}";
String[] exKnown = {{{known}}};
try {{
    com.anylogic.engine.Agent exRoot = getEngine().getRoot();
    java.util.Map<String, com.anylogic.engine.analysis.BasicDataSet> exFound =
        new java.util.HashMap<String, com.anylogic.engine.analysis.BasicDataSet>();
    for (Class<?> exClass = exRoot.getClass(); exClass != null;
            exClass = exClass.getSuperclass()) {{
        for (java.lang.reflect.Field exField : exClass.getDeclaredFields()) {{
            if (!com.anylogic.engine.analysis.BasicDataSet.class
                    .isAssignableFrom(exField.getType())) {{
                continue;
            }}
            exField.setAccessible(true);
            Object exValue = exField.get(exRoot);
            if (exValue == null) {{
                continue;
            }}
            String exBest = null;
            for (String exName : exKnown) {{
                if (exField.getName().contains(exName)
                        && (exBest == null || exName.length() > exBest.length())) {{
                    exBest = exName;
                }}
            }}
            if (exBest != null && !exFound.containsKey(exBest)) {{
                exFound.put(exBest,
                    (com.anylogic.engine.analysis.BasicDataSet) exValue);
            }}
        }}
    }}
    java.util.List<String> exColumns = new java.util.ArrayList<String>();
    int exRows = Integer.MAX_VALUE;
    for (String exName : exKnown) {{
        if (exFound.containsKey(exName)) {{
            exColumns.add(exName);
            exRows = Math.min(exRows, exFound.get(exName).size());
        }}
    }}
    if (exColumns.isEmpty() || exRows == 0 || exRows == Integer.MAX_VALUE) {{
        traceln("no datasets recorded for " + exScenario
                + "; enable 'create datasets for stocks/flows' on Main");
    }} else {{
        java.io.File exDir = new java.io.File("{EXPORT_DIR}");
        exDir.mkdirs();
        java.io.File exFile = new java.io.File(exDir, exScenario + ".csv");
        java.io.PrintWriter exWriter = new java.io.PrintWriter(exFile, "UTF-8");
        StringBuilder exHeader = new StringBuilder("week");
        for (String exName : exColumns) {{
            exHeader.append(",").append(exName);
        }}
        exWriter.println(exHeader.toString());
        for (int exIndex = 0; exIndex < exRows; exIndex++) {{
            StringBuilder exLine = new StringBuilder();
            exLine.append(exFound.get(exColumns.get(0)).getX(exIndex));
            for (String exName : exColumns) {{
                exLine.append(",").append(exFound.get(exName).getY(exIndex));
            }}
            exWriter.println(exLine.toString());
        }}
        exWriter.close();
        traceln("wrote " + exFile.getAbsolutePath() + " (" + exRows + " rows, "
                + exColumns.size() + " series)");
    }}
}} catch (Exception exError) {{
    traceln("export failed for " + exScenario + ": " + exError);
}}
"""

PLOTS = [
    ("plotBuyersSellers", 50, 1120, [("Active buyers", "buyers", -9728477),
                                     ("Active sellers", "sellers", -3407872)]),
    ("plotMatchFill", 420, 1120, [("Match rate (demand side)", "matchRate", -9728477),
                                  ("Fill rate (supply side)", "fillRate", -3407872)]),
    ("plotGMV", 790, 1120, [("Weekly GMV (buyer spend)", "weeklyGMV", -9728477),
                           ("Weekly GM (platform)", "weeklyGM", -3407872)]),
]


class IdGen:
    def __init__(self, start: int = 1790000000000):
        self._n = start

    def __call__(self) -> int:
        self._n += 1
        return self._n


def cdata(v: str) -> str:
    return f"<![CDATA[{v}]]>"


def build(path: Path) -> None:
    check_scenarios()
    nid = IdGen()
    main_id = nid()
    ids: dict[str, int] = {}
    for el in [*STOCKS, *FLOWS, *AUX, *PARAMS]:
        ids[el.name] = nid()

    out: list[str] = []
    w = out.append

    w('<?xml version="1.0" encoding="UTF-8"?>')
    w("<!--")
    w("*************************************************")
    w("\t         AnyLogic Project File")
    w("*************************************************")
    w("-->")
    w('<AnyLogicWorkspace WorkspaceVersion="1.9" AnyLogicVersion="8.9.9.202607020844" AlpVersion="8.9.9">')
    w("<Model>")
    w(f"\t<Id>{nid()}</Id>")
    w(f"\t<Name>{cdata(MODEL_NAME)}</Name>")
    w("\t<EngineVersion>6</EngineVersion>")
    w(f"\t<JavaPackageName>{cdata(MODEL_NAME)}</JavaPackageName>")
    w(f"\t<ModelTimeUnit>{cdata(TIME_UNIT)}</ModelTimeUnit>")
    w("\t<Folders>\n\t</Folders>")
    w("\t<ActiveObjectClasses>")
    w("\t\t<!--   =========   Active Object Class   ========  -->")
    w("\t\t<ActiveObjectClass>")
    w(f"\t\t\t<Id>{main_id}</Id>")
    w(f"\t\t\t<Name>{cdata('Main')}</Name>")
    w("\t\t\t<Generic>false</Generic>")
    gp_id = nid()
    w("\t\t\t<GenericParameter>")
    w(f"\t\t\t\t<Id>{gp_id}</Id>")
    w(f"\t\t\t\t<Name>{cdata(str(gp_id))}</Name>")
    w('\t\t\t\t<GenericParameterValue Class="CodeValue">')
    w(f"\t\t\t\t\t<Code>{cdata('T extends Agent')}</Code>")
    w("\t\t\t\t</GenericParameterValue>")
    w(f"\t\t\t\t<GenericParameterLabel>{cdata('Generic parameter:')}</GenericParameterLabel>")
    w("\t\t\t</GenericParameter>")
    w("\t\t\t<FlowChartsUsage>ENTITY</FlowChartsUsage>")
    # This is what sizes the auto-created datasets. 100 is AnyLogic's default
    # and is why earlier exports only kept weeks 401-500.
    w(f"\t\t\t<SamplesToKeep>{DATASET_CAPACITY}</SamplesToKeep>")
    w("\t\t\t<LimitNumberOfArrayElements>false</LimitNumberOfArrayElements>")
    w("\t\t\t<ElementsLimitValue>100</ElementsLimitValue>")
    w("\t\t\t<MakeDefaultViewArea>true</MakeDefaultViewArea>")
    w("\t\t\t<SceneGridColor/>")
    w("\t\t\t<SceneBackgroundColor>-4144960</SceneBackgroundColor>")
    w("\t\t\t<EnvironmentResourceRef></EnvironmentResourceRef>")
    w("\t\t\t<EnvironmentType>NONE</EnvironmentType>")
    w("\t\t\t<EnvironmentRotationX>0</EnvironmentRotationX>")
    w("\t\t\t<EnvironmentRotationY>0</EnvironmentRotationY>")
    w("\t\t\t<EnvironmentRotationZ>0</EnvironmentRotationZ>")
    w("\t\t\t<EnvironmentIntensity>1</EnvironmentIntensity>")
    w("\t\t\t<AgentProperties>")
    w("\t\t\t\t<EnvironmentDefinesInitialLocation>true</EnvironmentDefinesInitialLocation>")
    w("\t\t\t\t<RotateAnimationTowardsMovement>true</RotateAnimationTowardsMovement>")
    w("\t\t\t\t<RotateAnimationVertically>false</RotateAnimationVertically>")
    w('\t\t\t\t<VelocityCode Class="CodeUnitValue">')
    w(f"\t\t\t\t\t<Code>{cdata('10')}</Code>")
    w(f'\t\t\t\t\t<Unit Class="SpeedUnits">{cdata("MPS")}</Unit>')
    w("\t\t\t\t</VelocityCode>")
    for tag in ("PhysicalLength", "PhysicalWidth", "PhysicalHeight"):
        w(f'\t\t\t\t<{tag} Class="CodeUnitValue">')
        w(f"\t\t\t\t\t<Code>{cdata('1')}</Code>")
        w(f'\t\t\t\t\t<Unit Class="LengthUnits">{cdata("METER")}</Unit>')
        w(f"\t\t\t\t</{tag}>")
    w("\t\t\t</AgentProperties>")
    w("\t\t\t<EnvironmentProperties>")
    w("\t\t\t\t<EnableSteps>false</EnableSteps>")
    w('\t\t\t\t<StepDurationCode Class="CodeUnitValue">')
    w(f"\t\t\t\t\t<Code>{cdata('1.0')}</Code>")
    w(f'\t\t\t\t\t<Unit Class="TimeUnits">{cdata("SECOND")}</Unit>')
    w("\t\t\t\t</StepDurationCode>")
    w("\t\t\t\t<SpaceType>CONTINUOUS</SpaceType>")
    w(f"\t\t\t\t<WidthCode>{cdata('500')}</WidthCode>")
    w(f"\t\t\t\t<HeightCode>{cdata('500')}</HeightCode>")
    w(f"\t\t\t\t<ZHeightCode>{cdata('0')}</ZHeightCode>")
    w(f"\t\t\t\t<ColumnsCountCode>{cdata('100')}</ColumnsCountCode>")
    w(f"\t\t\t\t<RowsCountCode>{cdata('100')}</RowsCountCode>")
    w("\t\t\t\t<NeigborhoodType>MOORE</NeigborhoodType>")
    w("\t\t\t\t<LayoutType>USER_DEF</LayoutType>")
    w("\t\t\t\t<NetworkType>USER_DEF</NetworkType>")
    w(f"\t\t\t\t<ConnectionsPerAgentCode>{cdata('2')}</ConnectionsPerAgentCode>")
    w(f"\t\t\t\t<ConnectionsRangeCode>{cdata('50')}</ConnectionsRangeCode>")
    w(f"\t\t\t\t<NeighborLinkFractionCode>{cdata('0.95')}</NeighborLinkFractionCode>")
    w(f"\t\t\t\t<MCode>{cdata('10')}</MCode>")
    w("\t\t\t</EnvironmentProperties>")
    # Auto-created datasets record every stock, flow and auxiliary once a week,
    # which is what the experiments export after a run.
    w("\t\t\t<DatasetsCreationProperties>")
    w("\t\t\t\t<AutoCreate>true</AutoCreate>")
    w(f"\t\t\t\t<Id>{nid()}</Id>")
    w("\t\t\t\t<OccurrenceAtTime>true</OccurrenceAtTime>")
    w("\t\t\t\t<OccurrenceDate>1784620800000</OccurrenceDate>")
    w('\t\t\t\t<OccurrenceTime Class="CodeUnitValue">')
    w(f"\t\t\t\t\t<Code>{cdata('0')}</Code>")
    w(f'\t\t\t\t\t<Unit Class="TimeUnits">{cdata("WEEK")}</Unit>')
    w("\t\t\t\t</OccurrenceTime>")
    w('\t\t\t\t<RecurrenceCode Class="CodeUnitValue">')
    w(f"\t\t\t\t\t<Code>{cdata('1')}</Code>")
    w(f'\t\t\t\t\t<Unit Class="TimeUnits">{cdata("WEEK")}</Unit>')
    w("\t\t\t\t</RecurrenceCode>")
    w("\t\t\t</DatasetsCreationProperties>")
    ruler_id = nid()
    w("\t\t\t<ScaleRuler>")
    w(f"\t\t\t\t<Id>{ruler_id}</Id>")
    w(f"\t\t\t\t<Name>{cdata('scale')}</Name>")
    w("\t\t\t\t<X>0</X><Y>-150</Y>")
    w("\t\t\t\t<PublicFlag>false</PublicFlag>")
    w("\t\t\t\t<PresentationFlag>false</PresentationFlag>")
    w("\t\t\t\t<ShowLabel>false</ShowLabel>")
    w("\t\t\t\t<DrawMode>SHAPE_DRAW_2D3D</DrawMode>")
    w("\t\t\t\t<Length>100</Length>")
    w("\t\t\t\t<Rotation>0</Rotation>")
    w("\t\t\t\t<ScaleType>BASED_ON_LENGTH</ScaleType>")
    w("\t\t\t\t<ModelLength>10</ModelLength>")
    w("\t\t\t\t<LengthUnits>METER</LengthUnits>")
    w("\t\t\t\t<Scale>10</Scale>")
    w("\t\t\t\t<InheritedFromParentAgentType>true</InheritedFromParentAgentType>")
    w("\t\t\t</ScaleRuler>")
    level_id = nid()
    conn_id = nid()
    w(f"\t\t\t<CurrentLevel>{level_id}</CurrentLevel>")
    w(f"\t\t\t<ConnectionsId>{conn_id}</ConnectionsId>")

    # ---- variables ----
    w("\t\t\t<Variables>")
    for s in STOCKS:
        w('\t\t\t\t<Variable Class="StockVariable">')
        w(f"\t\t\t\t\t<Id>{ids[s.name]}</Id>")
        w(f"\t\t\t\t\t<Name>{cdata(s.name)}</Name>")
        w(f"\t\t\t\t\t<X>{s.x}</X><Y>{s.y}</Y>")
        w(f"\t\t\t\t\t<Label><X>{s.label[0]}</X><Y>{s.label[1]}</Y></Label>")
        w("\t\t\t\t\t<PublicFlag>true</PublicFlag>")
        w("\t\t\t\t\t<PresentationFlag>true</PresentationFlag>")
        w("\t\t\t\t\t<ShowLabel>true</ShowLabel>")
        w('\t\t\t\t\t<Properties Array="false">')
        style = "custom" if s.expression else "classic"
        w(f"\t\t\t\t\t<EquationStyle>{style}</EquationStyle>")
        w("\t\t\t\t\t<Width>170</Width>")
        w("\t\t\t\t\t<Height>55</Height>")
        if s.expression:
            w(f"\t\t\t\t\t\t<Expression>{cdata(s.expression)}</Expression>")
        w(f"\t\t\t\t\t\t<InitialValue>{cdata(s.init)}</InitialValue>")
        w(f"\t\t\t\t\t\t<Color>{s.color}</Color>")
        w("\t\t\t\t\t</Properties>")
        w("\t\t\t\t</Variable>")

    for f in FLOWS:
        attrs = []
        if f.source:
            attrs.append(f'SourceId="{ids[f.source]}"')
        if f.target:
            attrs.append(f'TargetId="{ids[f.target]}"')
        attrs += ['External="false"', 'Constant="false"', 'Array="false"']
        w('\t\t\t\t<Variable Class="Flow">')
        w(f"\t\t\t\t\t<Id>{ids[f.name]}</Id>")
        w(f"\t\t\t\t\t<Name>{cdata(f.name)}</Name>")
        w(f"\t\t\t\t\t<X>{f.x}</X><Y>{f.y}</Y>")
        w(f"\t\t\t\t\t<Label><X>{f.label[0]}</X><Y>{f.label[1]}</Y></Label>")
        w("\t\t\t\t\t<PublicFlag>true</PublicFlag>")
        w("\t\t\t\t\t<PresentationFlag>true</PresentationFlag>")
        w("\t\t\t\t\t<ShowLabel>true</ShowLabel>")
        w(f"\t\t\t\t\t<Properties {' '.join(attrs)}>")
        w(f"\t\t\t\t\t\t<Formula>{cdata(f.formula)}</Formula>")
        w(f"\t\t\t\t\t\t<Color>{f.color}</Color>")
        w("\t\t\t\t\t\t<ValveIndex>1</ValveIndex>")
        w("\t\t\t\t\t\t<Points>")
        for px, py in f.points:
            w(f"\t\t\t\t\t\t\t<Point><X>{px}</X><Y>{py}</Y></Point>")
        w("\t\t\t\t\t\t</Points>")
        w("\t\t\t\t\t</Properties>")
        w("\t\t\t\t</Variable>")

    for a in AUX:
        w('\t\t\t\t<Variable Class="AuxVariable">')
        w(f"\t\t\t\t\t<Id>{ids[a.name]}</Id>")
        w(f"\t\t\t\t\t<Name>{cdata(a.name)}</Name>")
        w(f"\t\t\t\t\t<X>{a.x}</X><Y>{a.y}</Y>")
        w(f"\t\t\t\t\t<Label><X>{a.label[0]}</X><Y>{a.label[1]}</Y></Label>")
        w("\t\t\t\t\t<PublicFlag>true</PublicFlag>")
        w("\t\t\t\t\t<PresentationFlag>true</PresentationFlag>")
        w("\t\t\t\t\t<ShowLabel>true</ShowLabel>")
        w('\t\t\t\t\t<Properties External="false" Constant="false" Array="false">')
        w(f"\t\t\t\t\t\t<Formula>{cdata(a.formula)}</Formula>")
        w(f"\t\t\t\t\t\t<Color>{a.color}</Color>")
        w("\t\t\t\t\t</Properties>")
        w("\t\t\t\t</Variable>")

    for p in PARAMS:
        w('\t\t\t\t<Variable Class="Parameter">')
        w(f"\t\t\t\t\t<Id>{ids[p.name]}</Id>")
        w(f"\t\t\t\t\t<Name>{cdata(p.name)}</Name>")
        w(f"\t\t\t\t\t<Unit>{p.unit}</Unit>")
        w(f"\t\t\t\t\t<X>{p.x}</X><Y>{p.y}</Y>")
        w(f"\t\t\t\t\t<Label><X>{p.label[0]}</X><Y>{p.label[1]}</Y></Label>")
        w("\t\t\t\t\t<PublicFlag>true</PublicFlag>")
        w("\t\t\t\t\t<PresentationFlag>true</PresentationFlag>")
        w("\t\t\t\t\t<ShowLabel>true</ShowLabel>")
        w('\t\t\t\t\t<Properties SaveInSnapshot="true" ModificatorType="STATIC">')
        w(f"\t\t\t\t\t\t<Type>{cdata('double')}</Type>")
        w(f"\t\t\t\t\t\t<UnitType>{cdata('NONE')}</UnitType>")
        w("\t\t\t\t\t\t<SdArray>false</SdArray>")
        w('\t\t\t\t\t\t<DefaultValue Class="CodeValue">')
        w(f"\t\t\t\t\t\t\t<Code>{cdata(p.value)}</Code>")
        w("\t\t\t\t\t\t</DefaultValue>")
        w("\t\t\t\t\t\t<ParameterEditor>")
        w(f"\t\t\t\t\t\t\t<Id>{nid()}</Id>")
        w("\t\t\t\t\t\t\t<EditorContolType>TEXT_BOX</EditorContolType>")
        w(f"\t\t\t\t\t\t\t<MinSliderValue>{cdata('0')}</MinSliderValue>")
        w(f"\t\t\t\t\t\t\t<MaxSliderValue>{cdata('100')}</MaxSliderValue>")
        w("\t\t\t\t\t\t\t<DelimeterType>NO_DELIMETER</DelimeterType>")
        w("\t\t\t\t\t\t</ParameterEditor>")
        w("\t\t\t\t\t</Properties>")
        w("\t\t\t\t</Variable>")
    w("\t\t\t</Variables>")

    # ---- causal links ----
    w("\t\t\t<Dependences>")
    for src, tgt in LINKS:
        w(f'\t\t\t\t<Link SourceId="{ids[src]}" TargetId="{ids[tgt]}" Polarity="null">')
        w("\t\t\t\t\t<Height>18.0</Height>")
        w("\t\t\t\t\t<PolarityPosition>0.95</PolarityPosition>")
        w("\t\t\t\t\t<Direction><X>60</X><Y>0</Y></Direction>")
        w(f"\t\t\t\t\t<Id>{nid()}</Id>")
        w(f"\t\t\t\t\t<Name>{cdata(f'{src} - {tgt}')}</Name>")
        w("\t\t\t\t\t<X>0</X><Y>0</Y>")
        w("\t\t\t\t\t<Label><X>10</X><Y>0</Y></Label>")
        w("\t\t\t\t\t<PublicFlag>false</PublicFlag>")
        w("\t\t\t\t\t<PresentationFlag>true</PresentationFlag>")
        w("\t\t\t\t\t<ShowLabel>false</ShowLabel>")
        w("\t\t\t\t\t<Color>-8355712</Color>")
        w("\t\t\t\t\t<LineWidth>1</LineWidth>")
        w("\t\t\t\t\t<Delay>false</Delay>")
        w("\t\t\t\t</Link>")
    w("\t\t\t</Dependences>")

    w("\t\t\t<AgentLinks>")
    w("\t\t\t\t<AgentLink>")
    w(f"\t\t\t\t\t<Id>{conn_id}</Id>")
    w(f"\t\t\t\t\t<Name>{cdata('connections')}</Name>")
    w("\t\t\t\t\t<X>-40</X><Y>-40</Y>")
    w("\t\t\t\t\t<Label><X>15</X><Y>0</Y></Label>")
    w("\t\t\t\t\t<PublicFlag>false</PublicFlag>")
    w("\t\t\t\t\t<PresentationFlag>false</PresentationFlag>")
    w("\t\t\t\t\t<ShowLabel>false</ShowLabel>")
    w("\t\t\t\t\t<HandleReceiveInConnections>false</HandleReceiveInConnections>")
    w("\t\t\t\t\t<AgentLinkType>COLLECTION_OF_LINKS</AgentLinkType>")
    w("\t\t\t\t\t<AgentLinkBidirectional>true</AgentLinkBidirectional>")
    w(f"\t\t\t\t\t<MessageType>{cdata('Object')}</MessageType>")
    w("\t\t\t\t\t<LineStyle>SOLID</LineStyle>")
    w("\t\t\t\t\t<LineWidth>1</LineWidth>")
    w("\t\t\t\t\t<LineColor>-16777216</LineColor>")
    w("\t\t\t\t\t<LineZOrder>UNDER_AGENTS</LineZOrder>")
    w("\t\t\t\t\t<LineArrow>NONE</LineArrow>")
    w("\t\t\t\t\t<LineArrowPosition>END</LineArrowPosition>")
    w("\t\t\t\t</AgentLink>")
    w("\t\t\t</AgentLinks>")

    # ---- presentation: time plots ----
    w("\t\t\t<Presentation>")
    w("\t\t\t\t<Level>")
    w(f"\t\t\t\t\t<Id>{level_id}</Id>")
    w(f"\t\t\t\t\t<Name>{cdata('level')}</Name>")
    w("\t\t\t\t\t<X>0</X><Y>0</Y>")
    w("\t\t\t\t\t<Label><X>10</X><Y>0</Y></Label>")
    w("\t\t\t\t\t<PublicFlag>true</PublicFlag>")
    w("\t\t\t\t\t<PresentationFlag>true</PresentationFlag>")
    w("\t\t\t\t\t<ShowLabel>false</ShowLabel>")
    w("\t\t\t\t\t<DrawMode>SHAPE_DRAW_2D3D</DrawMode>")
    w("\t\t\t\t\t<Z>0</Z>")
    w("\t\t\t\t\t<LevelVisibility>HIDE_NON_CURRENT</LevelVisibility>")
    w("\t\t\t<Presentation>")
    for name, px, py, series in PLOTS:
        w("\t\t\t\t<TimePlot>")
        w(f"\t\t\t\t\t<Id>{nid()}</Id>")
        w(f"\t\t\t\t\t<Name>{cdata(name)}</Name>")
        w(f"\t\t\t\t\t<X>{px}</X><Y>{py}</Y>")
        w("\t\t\t\t\t<Label><X>0</X><Y>-10</Y></Label>")
        w("\t\t\t\t\t<PublicFlag>true</PublicFlag>")
        w("\t\t\t\t\t<PresentationFlag>true</PresentationFlag>")
        w("\t\t\t\t\t<ShowLabel>false</ShowLabel>")
        w("\t\t\t\t\t<DrawMode>SHAPE_DRAW_2D3D</DrawMode>")
        w("\t\t\t\t\t<AutoUpdate>true</AutoUpdate>")
        w("\t\t\t\t\t<RecurrenceProperties>")
        w(f"\t\t\t\t\t\t<Id>{nid()}</Id>")
        w("\t\t\t\t\t\t<OccurrenceAtTime>true</OccurrenceAtTime>")
        w("\t\t\t\t\t\t<OccurrenceDate>1784620800000</OccurrenceDate>")
        w('\t\t\t\t\t\t<OccurrenceTime Class="CodeUnitValue">')
        w(f"\t\t\t\t\t\t\t<Code>{cdata('0')}</Code>")
        w(f'\t\t\t\t\t\t\t<Unit Class="TimeUnits">{cdata("WEEK")}</Unit>')
        w("\t\t\t\t\t\t</OccurrenceTime>")
        w('\t\t\t\t\t\t<RecurrenceCode Class="CodeUnitValue">')
        w(f"\t\t\t\t\t\t\t<Code>{cdata('1')}</Code>")
        w(f'\t\t\t\t\t\t\t<Unit Class="TimeUnits">{cdata("WEEK")}</Unit>')
        w("\t\t\t\t\t\t</RecurrenceCode>")
        w("\t\t\t\t\t</RecurrenceProperties>")
        w("\t\t\t\t\t<EmbeddedIcon>false</EmbeddedIcon>")
        w("\t\t\t\t\t<Width>330</Width>")
        w("\t\t\t\t\t<Height>220</Height>")
        w("\t\t\t\t\t<BackgroundColor/>")
        w("\t\t\t\t\t<BorderColor/>")
        w("\t\t\t\t\t<ChartArea>")
        w("\t\t\t\t\t\t<XOffset>50</XOffset>")
        w("\t\t\t\t\t\t<YOffset>30</YOffset>")
        w("\t\t\t\t\t\t<Width>250</Width>")
        w("\t\t\t\t\t\t<Height>130</Height>")
        w("\t\t\t\t\t\t<BackgroundColor>-1</BackgroundColor>")
        w("\t\t\t\t\t\t<BorderColor>-16777216</BorderColor>")
        w("\t\t\t\t\t\t<GridColor>-12566464</GridColor>")
        w("\t\t\t\t\t</ChartArea>")
        w("\t\t\t\t\t<Legend>")
        w("\t\t\t\t\t\t<Place>SOUTH</Place>")
        w("\t\t\t\t\t\t<TextColor>-16777216</TextColor>")
        w("\t\t\t\t\t\t<Size>30</Size>")
        w("\t\t\t\t\t</Legend>")
        w("\t\t\t\t\t<Labels>")
        w("\t\t\t\t\t\t<HorLabelsPosition>DEFAULT</HorLabelsPosition>")
        w("\t\t\t\t\t\t<VerLabelsPosition>DEFAULT</VerLabelsPosition>")
        w("\t\t\t\t\t\t<TextColor>-12566464</TextColor>")
        w("\t\t\t\t\t</Labels>")
        w("\t\t\t\t\t<ShowLegend>true</ShowLegend>")
        w("\t\t\t\t\t<TimeWindowsMovementType>MOVEMENT_WITH_TIME</TimeWindowsMovementType>")
        w("\t\t\t\t\t<TimeWindowUnits>MODEL_TIME_UNIT</TimeWindowUnits>")
        w(f"\t\t\t\t\t<VerScaleFromExpression>{cdata('0')}</VerScaleFromExpression>")
        w(f"\t\t\t\t\t<VerScaleToExpression>{cdata('1')}</VerScaleToExpression>")
        w("\t\t\t\t\t<VerScaleType>AUTO</VerScaleType>")
        w("\t\t\t\t\t<DrawLine>true</DrawLine>")
        w("\t\t\t\t\t<Interpolation>LINEAR</Interpolation>")
        for title, expr, color in series:
            w("\t\t\t\t\t<DatasetExpression>")
            w(f"\t\t\t\t\t\t<Title>{cdata(title)}</Title>")
            w(f"\t\t\t\t\t<Id>{nid()}</Id>")
            w(f"\t\t\t\t\t<Expression>{cdata(expr)}</Expression>")
            w(f"\t\t\t\t\t<Color>{color}</Color>")
            w(f"\t\t\t\t\t<Expression2>{cdata(expr)}</Expression2>")
            w("\t\t\t\t\t<Expression2Flag>true</Expression2Flag>")
            w("\t\t\t\t\t\t<PointStyle>NONE</PointStyle>")
            w("\t\t\t\t\t\t<LineWidth>1.0</LineWidth>")
            w("\t\t\t\t\t</DatasetExpression>")
        w("\t\t\t\t\t<SamplesToKeep>2000</SamplesToKeep>")
        w(f"\t\t\t\t\t<TimeWindowExpression>{cdata('1000')}</TimeWindowExpression>")
        w("\t\t\t\t\t<FillAreaUnderLine>false</FillAreaUnderLine>")
        w("\t\t\t\t\t<LabelFormat>MODEL_TIME_UNITS</LabelFormat>")
        w("\t\t\t\t</TimePlot>")
    w("\t\t\t</Presentation>")
    w("\t\t\t\t</Level>")
    w("\t\t\t</Presentation>")
    w("\t\t</ActiveObjectClass>")
    w("\t</ActiveObjectClasses>")

    w("\t<DifferentialEquationsMethod>EULER</DifferentialEquationsMethod>")
    w("\t<MixedEquationsMethod>RK45_NEWTON</MixedEquationsMethod>")
    w("\t<AlgebraicEquationsMethod>MODIFIED_NEWTON</AlgebraicEquationsMethod>")
    w("\t<AbsoluteAccuracy>1.0E-5</AbsoluteAccuracy>")
    w(f"\t<FixedTimeStep>{TIME_STEP}</FixedTimeStep>")
    w("\t<RelativeAccuracy>1.0E-5</RelativeAccuracy>")
    w("\t<TimeAccuracy>1.0E-5</TimeAccuracy>")
    w("\t<Frame>")
    w(f"\t\t<Id>{nid()}</Id>")
    w("\t\t<Width>1460</Width>")
    w("\t\t<Height>1120</Height>")
    w("\t</Frame>")
    w("\t<Database>")
    w(f"\t\t<Id>{nid()}</Id>")
    w("\t\t<Logging>false</Logging>")
    w("\t\t<AutoExport>false</AutoExport>")
    w("\t\t<ShutdownCompact>false</ShutdownCompact>")
    w("\t\t<ImportSettings>\n\t\t</ImportSettings>")
    w("\t\t<ExportSettings>\n\t\t</ExportSettings>")
    w("\t</Database>")

    w(f'\t<RunConfiguration ActiveObjectClassId="{main_id}">')
    w(f"\t\t<Id>{nid()}</Id>")
    w(f"\t\t<Name>{cdata('RunConfiguration')}</Name>")
    w("\t\t<MaximumMemory>512</MaximumMemory>")
    w("\t\t<ModelTimeProperties>")
    w(f"\t\t\t<StopOption>{cdata('Stop at specified time')}</StopOption>")
    w(f"\t\t\t<InitialTime>{cdata('0.0')}</InitialTime>")
    w(f"\t\t\t<FinalTime>{cdata(str(STOP_TIME))}</FinalTime>")
    w("\t\t</ModelTimeProperties>")
    w("\t\t<AnimationProperties>")
    w("\t\t\t<StopNever>true</StopNever>")
    w("\t\t\t<ExecutionMode>realTimeScaled</ExecutionMode>")
    w("\t\t\t<RealTimeScale>1.0</RealTimeScale>")
    w("\t\t\t<EnableZoomAndPanning>true</EnableZoomAndPanning>")
    w("\t\t\t<EnableDeveloperPanel>false</EnableDeveloperPanel>")
    w("\t\t\t<ShowDeveloperPanelOnStart>false</ShowDeveloperPanelOnStart>")
    w("\t\t</AnimationProperties>")
    w("\t\t<Inputs>\n\t\t</Inputs>")
    w("\t\t<Outputs>\n\t\t</Outputs>")
    w("\t</RunConfiguration>")

    w("\t<Experiments>")
    for sc in EXPERIMENTS:
        w("\t\t<!--   =========   Simulation Experiment   ========  -->")
        w(f'\t\t<SimulationExperiment ActiveObjectClassId="{main_id}">')
        w(f"\t\t\t<Id>{nid()}</Id>")
        w(f"\t\t\t<Name>{cdata(sc.name)}</Name>")
        w(f"\t\t\t<CommandLineArguments>{cdata('')}</CommandLineArguments>")
        w("\t\t\t<MaximumMemory>512</MaximumMemory>")
        w("\t\t\t<RandomNumberGenerationType>fixedSeed</RandomNumberGenerationType>")
        w("\t\t\t<CustomGeneratorCode>new Random()</CustomGeneratorCode>")
        w("\t\t\t<SeedValue>1</SeedValue>")
        w("\t\t\t<SelectionModeForSimultaneousEvents>LIFO</SelectionModeForSimultaneousEvents>")
        w(f"\t\t\t<VmArgs>{cdata('')}</VmArgs>")
        w("\t\t\t<LoadRootFromSnapshot>false</LoadRootFromSnapshot>")
        w(f"\t\t\t<BeforeSimulationRunCode>{cdata(capacity_code())}"
          f"</BeforeSimulationRunCode>")
        w(f"\t\t\t<AfterSimulationRunCode>{cdata(export_code(sc.name))}"
          f"</AfterSimulationRunCode>")
        w("\t\t\t<Presentation>")
        w("\t\t\t\t<Text>")
        w(f"\t\t\t\t\t<Id>{nid()}</Id>")
        w(f"\t\t\t\t\t<Name>{cdata('text')}</Name>")
        w("\t\t\t\t\t<X>50</X><Y>30</Y>")
        w("\t\t\t\t\t<Label><X>10</X><Y>0</Y></Label>")
        w("\t\t\t\t\t<PublicFlag>true</PublicFlag>")
        w("\t\t\t\t\t<PresentationFlag>true</PresentationFlag>")
        w("\t\t\t\t\t<ShowLabel>false</ShowLabel>")
        w("\t\t\t\t\t<DrawMode>SHAPE_DRAW_2D3D</DrawMode>")
        w("\t\t\t\t\t<EmbeddedIcon>false</EmbeddedIcon>")
        w("\t\t\t\t\t<Z>0</Z>")
        w("\t\t\t\t\t<Rotation>0.0</Rotation>")
        w("\t\t\t\t\t<Color>-12490271</Color>")
        w(f"\t\t\t\t\t<Text>{cdata(sc.name + ' (synthetic)')}</Text>")
        w("\t\t\t\t\t<Font>")
        w("\t\t\t\t\t\t<Name>SansSerif</Name>")
        w("\t\t\t\t\t\t<Size>24</Size>")
        w("\t\t\t\t\t\t<Style>0</Style>")
        w("\t\t\t\t\t</Font>")
        w("\t\t\t\t\t<Alignment>LEFT</Alignment>")
        w("\t\t\t\t</Text>")
        w("\t\t\t</Presentation>")
        # A scenario is expressed only as parameter values, so the experiments
        # differ from each other by nothing but the numbers below.
        w("\t\t\t<Parameters>")
        for p in PARAMS:
            w("\t\t\t\t<Parameter>")
            w(f"\t\t\t\t\t<ParameterName>{cdata(p.name)}</ParameterName>")
            if p.name in sc.overrides:
                value = f"{sc.overrides[p.name]:.12g}"
                w('\t\t\t\t\t<ParameterValue Class="CodeValue">')
                w(f"\t\t\t\t\t\t<Code>{cdata(value)}</Code>")
                w("\t\t\t\t\t</ParameterValue>")
            w("\t\t\t\t</Parameter>")
        w("\t\t\t</Parameters>")
        w("\t\t\t<PresentationProperties>")
        w("\t\t\t\t<EnableZoomAndPanning>true</EnableZoomAndPanning>")
        # Virtual time, not real time: a 500-week run should finish in about a
        # second, otherwise each experiment would take minutes of wall clock.
        w(f"\t\t\t\t<ExecutionMode>{cdata('virtualTime')}</ExecutionMode>")
        w(f"\t\t\t\t<Title>{cdata(f'{MODEL_NAME} : {sc.name}')}</Title>")
        w("\t\t\t\t<EnableDeveloperPanel>true</EnableDeveloperPanel>")
        w("\t\t\t\t<ShowDeveloperPanelOnStart>false</ShowDeveloperPanelOnStart>")
        w("\t\t\t\t<RealTimeScale>1.0</RealTimeScale>")
        w("\t\t\t</PresentationProperties>")
        w("\t\t\t<ModelTimeProperties>")
        w(f"\t\t\t\t<StopOption>{cdata('Stop at specified time')}</StopOption>")
        w(f"\t\t\t\t<InitialTime>{cdata('0.0')}</InitialTime>")
        w(f"\t\t\t\t<FinalTime>{cdata(str(STOP_TIME))}</FinalTime>")
        w("\t\t\t</ModelTimeProperties>")
        w("\t\t\t<BypassInitialScreen>true</BypassInitialScreen>")
        w("\t\t</SimulationExperiment>")
    w("\t</Experiments>")
    w("</Model>")
    w("</AnyLogicWorkspace>")

    path.write_text("\n".join(out) + "\n")
    print(f"wrote {path} ({len(out)} lines): "
          f"{len(STOCKS)} stocks, {len(FLOWS)} flows, {len(AUX)} auxiliaries, "
          f"{len(PARAMS)} parameters, {len(LINKS)} links, "
          f"{len(EXPERIMENTS)} experiments")


if __name__ == "__main__":
    dest = Path(sys.argv[1] if len(sys.argv) > 1 else "assets/files/marketplace_sd.alp")
    dest.parent.mkdir(parents=True, exist_ok=True)
    build(dest)
