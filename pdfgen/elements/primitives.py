from reportlab.lib.colors import HexColor
from reportlab.platypus import HRFlowable, PageBreak, Spacer


def build_spacer(element):
    return Spacer(1, element.get("height", 12))


def build_page_break(_element):
    return PageBreak()


def build_rule(element):
    color = element.get("color", "#cccccc")
    thickness = element.get("thickness", 0.5)
    space_before = element.get("space_before", 6)
    space_after = element.get("space_after", 6)
    return HRFlowable(
        width="100%",
        thickness=thickness,
        color=HexColor(color),
        spaceBefore=space_before,
        spaceAfter=space_after,
        lineCap="butt",
    )
