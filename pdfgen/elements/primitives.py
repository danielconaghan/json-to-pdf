from reportlab.lib.colors import HexColor
from reportlab.platypus import HRFlowable, PageBreak, Spacer


def build_spacer(element):
    return [Spacer(1, element.get("height", 12))]


def build_page_break(element):
    return [PageBreak()]


def build_rule(element):
    return [HRFlowable(
        width="100%",
        thickness=element.get("thickness", 0.5),
        color=HexColor(element.get("color", "#cccccc")),
        spaceBefore=element.get("space_before", 6),
        spaceAfter=element.get("space_after", 6),
        lineCap="butt",
    )]
