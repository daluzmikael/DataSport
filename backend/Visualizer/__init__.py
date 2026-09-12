"""Chart selection for analyst answers.

The chart is a pure function of the router plan and the frame it produced. Nothing
here calls a model or writes SQL — by the time the analyst runs, the pipeline already
knows who was asked about, over what span, ranked by what, and with which filters
applied. Choosing a picture from that is deterministic, costs no tokens, and cannot
disagree with the sentence beside it, because both are built from the same rows.
"""
from Visualizer.chart_spec import ChartKind, ChartSpec, FieldSpec
from Visualizer.selector import chart_hint_line, select_charts

__all__ = [
    "ChartKind",
    "ChartSpec",
    "FieldSpec",
    "chart_hint_line",
    "select_charts",
]
