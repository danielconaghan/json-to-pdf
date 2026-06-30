from dataclasses import dataclass

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, LETTER, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import BaseDocTemplate, NextPageTemplate, PageBreak, Paragraph

from .elements.image import build_image
from .elements.list_element import build_list
from .elements.primitives import build_page_break, build_rule, build_spacer
from .templates.page import make_cover_template, make_numbered_canvas_class, make_standard_template

_PAGE_SIZES = {
    "A4": A4,
    "LETTER": LETTER,
    "LEGAL": (612, 1008),
}

_ALIGN = {
    "left": TA_LEFT,
    "center": TA_CENTER,
    "right": TA_RIGHT,
    "justify": TA_JUSTIFY,
}


@dataclass
class RenderContext:
    rl_styles: dict
    doc: BaseDocTemplate
    base_path: str | None


def _page_size(page_config):
    size = _PAGE_SIZES.get(page_config.get("size", "A4").upper(), A4)
    if page_config.get("orientation", "portrait").lower() == "landscape":
        return landscape(size)
    return size


def _build_rl_style(name, style):
    kwargs = dict(
        name=name,
        fontName=style.get("font", "Helvetica"),
        fontSize=style.get("size", 11),
        leading=style.get("leading", style.get("size", 11) * 1.4),
        spaceBefore=style.get("space_before", 0),
        spaceAfter=style.get("space_after", 6),
        leftIndent=style.get("left_indent", 0),
        rightIndent=style.get("right_indent", 0),
        alignment=_ALIGN.get(style.get("alignment", "left"), TA_LEFT),
    )
    if "color" in style:
        kwargs["textColor"] = HexColor(style["color"])
    return ParagraphStyle(**kwargs)


def _build_rl_styles(resolved_styles):
    return {name: _build_rl_style(name, s) for name, s in resolved_styles.items()}


def _render_element(element, ctx):
    t = element.get("type")

    if t == "paragraph":
        style_name = element.get("style", "body")
        style = ctx.rl_styles.get(style_name) or ctx.rl_styles.get("body")
        return Paragraph(element["text"], style)

    if t == "heading":
        level = element.get("level", 1)
        style = ctx.rl_styles.get(f"h{level}") or ctx.rl_styles.get("h1")
        return Paragraph(element["text"], style)

    if t == "spacer":
        return build_spacer(element)

    if t == "page_break":
        return build_page_break(element)

    if t == "rule":
        return build_rule(element)

    if t == "list":
        return build_list(element, ctx.rl_styles)

    if t == "image":
        return build_image(element, ctx.rl_styles, ctx.doc, ctx.base_path)

    return None


def render(config, output_path, base_path=None):
    config["_base_path"] = base_path  # propagated to template drawing functions
    page_cfg = config["document"]["page"]
    margins = page_cfg["margins"]
    doc_meta = config["document"]
    has_cover = bool(config.get("cover", {}).get("title", ""))

    doc = BaseDocTemplate(
        output_path,
        pagesize=_page_size(page_cfg),
        topMargin=margins["top"],
        bottomMargin=margins["bottom"],
        leftMargin=margins["left"],
        rightMargin=margins["right"],
        title=doc_meta.get("title", ""),
        author=doc_meta.get("author", ""),
        subject=doc_meta.get("subject", ""),
    )

    templates = []
    if has_cover:
        templates.append(make_cover_template(doc, config))
    templates.append(make_standard_template(doc, config))
    doc.addPageTemplates(templates)

    ctx = RenderContext(
        rl_styles=_build_rl_styles(config["_resolved_styles"]),
        doc=doc,
        base_path=base_path,
    )

    story = []
    if has_cover:
        story.extend([NextPageTemplate("standard"), PageBreak()])

    for element in config["content"]:
        flowable = _render_element(element, ctx)
        if isinstance(flowable, list):
            story.extend(flowable)
        elif flowable is not None:
            story.append(flowable)

    NumberedCanvas = make_numbered_canvas_class(config)
    doc.build(story, canvasmaker=NumberedCanvas)
