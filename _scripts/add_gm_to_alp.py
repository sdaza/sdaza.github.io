"""Add GM analysis to an existing AnyLogic model without changing its layout.

This intentionally patches the saved .alp instead of regenerating it. Existing
coordinates, labels, links, plots, and experiment formatting remain untouched.
The new calculation and parameter are hidden; only a second line is added to
the existing GMV chart.
"""

from __future__ import annotations

import sys
from pathlib import Path


AUXILIARY = """				<Variable Class="AuxVariable">
					<Id>1790000005001</Id>
					<Name><![CDATA[weeklyGM]]></Name>
					<X>0</X><Y>0</Y>
					<Label><X>0</X><Y>0</Y></Label>
					<PublicFlag>true</PublicFlag>
					<PresentationFlag>false</PresentationFlag>
					<ShowLabel>false</ShowLabel>
					<Properties External="false" Constant="false" Array="false">
						<Formula><![CDATA[weeklyGMV * (takeRate - variableCostRate)]]></Formula>
						<Color>-3407872</Color>
					</Properties>

				</Variable>
"""

PARAMETER = """				<Variable Class="Parameter">
					<Id>1790000005002</Id>
					<Name><![CDATA[variableCostRate]]></Name>
					<Unit>dmnl</Unit> 
					<X>0</X><Y>0</Y>
					<Label><X>0</X><Y>0</Y></Label>
					<PublicFlag>false</PublicFlag>
					<PresentationFlag>false</PresentationFlag>
					<ShowLabel>false</ShowLabel>
					<Properties SaveInSnapshot="true" ModificatorType="STATIC">
						<Type><![CDATA[double]]></Type>
						<UnitType><![CDATA[NONE]]></UnitType>
						<SdArray>false</SdArray>
						<DefaultValue Class="CodeValue">
							<Code><![CDATA[0.04]]></Code>
						</DefaultValue>
						<ParameterEditor>
							<Id>1790000005003</Id>
							<EditorContolType>TEXT_BOX</EditorContolType>
							<MinSliderValue><![CDATA[0]]></MinSliderValue>
							<MaxSliderValue><![CDATA[1]]></MaxSliderValue>
							<DelimeterType>NO_DELIMETER</DelimeterType>
						</ParameterEditor>
					</Properties>                 
				</Variable>
"""

LINKS = """				<Link SourceId="1790000000030" TargetId="1790000005001" Polarity="null">
					<Height>0.0</Height>
					<PolarityPosition>0.95</PolarityPosition>
					<Direction><X>0</X><Y>0</Y></Direction>
					<Id>1790000005004</Id>
					<Name><![CDATA[weeklyGMV - weeklyGM]]></Name>
					<X>0</X><Y>0</Y>
					<Label><X>0</X><Y>0</Y></Label>
					<PublicFlag>false</PublicFlag>
					<PresentationFlag>false</PresentationFlag>
					<ShowLabel>false</ShowLabel>
					<Color>-8355712</Color>
					<LineWidth>1</LineWidth>
					<Delay>false</Delay>
				</Link>
				<Link SourceId="1790000000056" TargetId="1790000005001" Polarity="null">
					<Height>0.0</Height>
					<PolarityPosition>0.95</PolarityPosition>
					<Direction><X>0</X><Y>0</Y></Direction>
					<Id>1790000005005</Id>
					<Name><![CDATA[takeRate - weeklyGM]]></Name>
					<X>0</X><Y>0</Y>
					<Label><X>0</X><Y>0</Y></Label>
					<PublicFlag>false</PublicFlag>
					<PresentationFlag>false</PresentationFlag>
					<ShowLabel>false</ShowLabel>
					<Color>-8355712</Color>
					<LineWidth>1</LineWidth>
					<Delay>false</Delay>
				</Link>
				<Link SourceId="1790000005002" TargetId="1790000005001" Polarity="null">
					<Height>0.0</Height>
					<PolarityPosition>0.95</PolarityPosition>
					<Direction><X>0</X><Y>0</Y></Direction>
					<Id>1790000005006</Id>
					<Name><![CDATA[variableCostRate - weeklyGM]]></Name>
					<X>0</X><Y>0</Y>
					<Label><X>0</X><Y>0</Y></Label>
					<PublicFlag>false</PublicFlag>
					<PresentationFlag>false</PresentationFlag>
					<ShowLabel>false</ShowLabel>
					<Color>-8355712</Color>
					<LineWidth>1</LineWidth>
					<Delay>false</Delay>
				</Link>
"""

GM_SERIES = """					<DatasetExpression>  
						<Title><![CDATA[Weekly GM (platform)]]></Title>
					<Id>1790000005007</Id>
					<Expression><![CDATA[weeklyGM]]></Expression>
					<Color>-3407872</Color>
					<Expression2><![CDATA[weeklyGM]]></Expression2>
					<Expression2Flag>true</Expression2Flag>
						<PointStyle>NONE</PointStyle>
						<LineWidth>1.0</LineWidth>
					</DatasetExpression>
"""

EXPERIMENT_PARAMETER = """				<Parameter>
					<ParameterName><![CDATA[variableCostRate]]></ParameterName>
				</Parameter>
"""


def replace_once(text: str, old: str, new: str, description: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{description}: expected 1 match, found {count}")
    return text.replace(old, new, 1)


def patch(path: Path) -> None:
    text = path.read_text()
    if "<![CDATA[weeklyGM]]>" in text:
        print(f"{path} already contains weeklyGM; no changes made")
        return

    weekly_gmv_end = """				</Variable>
				<Variable Class="StockVariable">
					<Id>1790000000002</Id>"""
    text = replace_once(
        text,
        weekly_gmv_end,
        f"				</Variable>\n{AUXILIARY}"
        """				<Variable Class="StockVariable">
					<Id>1790000000002</Id>""",
        "weeklyGM auxiliary insertion",
    )

    policy_start = """				</Variable>
				<Variable Class="Parameter">
					<Id>1790000000057</Id>"""
    text = replace_once(
        text,
        policy_start,
        f"				</Variable>\n{PARAMETER}"
        """				<Variable Class="Parameter">
					<Id>1790000000057</Id>""",
        "variableCostRate parameter insertion",
    )

    dependence_end = """				</Link>
			</Dependences>"""
    text = replace_once(
        text,
        dependence_end,
        f"				</Link>\n{LINKS}			</Dependences>",
        "hidden dependence insertion",
    )

    old_chart_tail = """					</DatasetExpression>
					<SamplesToKeep>2000</SamplesToKeep>
					<TimeWindowExpression><![CDATA[1000]]></TimeWindowExpression>
					<FillAreaUnderLine>false</FillAreaUnderLine>
					<LabelFormat>MODEL_TIME_UNITS</LabelFormat>
    			</TimePlot>"""
    chart_start = text.index("<Name><![CDATA[plotGMV]]></Name>")
    chart_tail = text.index(old_chart_tail, chart_start)
    text = (
        text[:chart_tail]
        + text[chart_tail:].replace(
            old_chart_tail,
            f"					</DatasetExpression>\n{GM_SERIES}"
            """					<SamplesToKeep>2000</SamplesToKeep>
					<TimeWindowExpression><![CDATA[1000]]></TimeWindowExpression>
					<FillAreaUnderLine>false</FillAreaUnderLine>
					<LabelFormat>MODEL_TIME_UNITS</LabelFormat>
    			</TimePlot>""",
            1,
        )
    )
    text = text.replace(
        "<Title><![CDATA[Weekly GMV]]></Title>",
        "<Title><![CDATA[Weekly GMV (buyer spend)]]></Title>",
        1,
    )

    old_export_tail = '"weeklyGMV"};'
    export_count = text.count(old_export_tail)
    if export_count != 18:
        raise RuntimeError(
            f"experiment exports: expected 18 matches, found {export_count}"
        )
    text = text.replace(old_export_tail, '"weeklyGMV", "weeklyGM"};')

    # Keep each cumulative stock next to the flow and weekly rate it comes from,
    # so the exported columns stay readable.
    text = text.replace('"cumulativeGMV", "buyerJoin"',
                        '"cumulativeGMV", "cumulativeGM", "buyerJoin"')
    text = text.replace('"gmvAccumulation", "matchEfficiency"',
                        '"gmvAccumulation", "gmAccumulation", "matchEfficiency"')

    take_rate_parameter = """				<Parameter>
					<ParameterName><![CDATA[takeRate]]></ParameterName>"""
    parameter_count = text.count(take_rate_parameter)
    if parameter_count != 19:
        raise RuntimeError(
            f"experiment parameter lists: expected 19 matches, found {parameter_count}"
        )
    text = text.replace(
        take_rate_parameter,
        f"{EXPERIMENT_PARAMETER}{take_rate_parameter}",
    )

    path.write_text(text)
    print(
        f"patched {path}: hidden weeklyGM + variableCostRate, "
        "GM chart series, and 18 CSV exports"
    )


if __name__ == "__main__":
    destination = Path(
        sys.argv[1] if len(sys.argv) > 1 else "assets/files/marketplace_sd.alp"
    )
    patch(destination)
