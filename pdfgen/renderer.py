from dataclasses import dataclass

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, LETTER, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import NextPageTemplate, PageBreak, Paragraph

from .accessibility import TaggedHeading, TaggedParagraph, build_struct_tree
from .elements.chart import build_chart
from .elements.image import build_image
from .elements.list_element import build_list
from .elements.primitives import build_page_break, build_rule, build_spacer
from .elements.table import build_table
from .elements.toc import build_toc
from .templates.doc import PDFDocTemplate
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
    doc: PDFDocTemplate
    base_path: str | None
    config: dict


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


def _build_paragraph(element, ctx):
    style = ctx.rl_styles.get(element.get("style", "body")) or ctx.rl_styles.get("body")
    return [TaggedParagraph(element["text"], style)]


def _build_heading(element, ctx):
    level = element.get("level", 1)
    style = ctx.rl_styles.get(f"h{level}") or ctx.rl_styles.get("h1")
    p = TaggedHeading(element["text"], style)
    p._tag_role = f"H{level}"
    p._toc_entry = (level - 1, element["text"])
    return [p]


_BUILDERS = {
    "paragraph":  _build_paragraph,
    "heading":    _build_heading,
    "spacer":     lambda el, ctx: build_spacer(el),
    "page_break": lambda el, ctx: build_page_break(el),
    "rule":       lambda el, ctx: build_rule(el),
    "list":       lambda el, ctx: build_list(el, ctx.rl_styles),
    "image":      lambda el, ctx: build_image(el, ctx.rl_styles, ctx.doc, ctx.base_path),
    "table":      lambda el, ctx: build_table(el, ctx),
    "toc":        lambda el, ctx: build_toc(el, ctx.rl_styles),
    "chart":      lambda el, ctx: build_chart(el, ctx.rl_styles, ctx.doc, ctx.config),
}


def _render_element(element, ctx):
    builder = _BUILDERS.get(element.get("type"))
    return builder(element, ctx) if builder else []


def render(config, output_path, base_path=None):
    config["_base_path"] = base_path  # propagated to template drawing functions
    page_cfg = config["document"]["page"]
    margins = page_cfg["margins"]
    doc_meta = config["document"]
    has_cover = bool(config.get("cover", {}).get("title", ""))

    doc = PDFDocTemplate(
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
    doc.keywords = doc_meta.get("keywords") or []

    templates = []
    if has_cover:
        templates.append(make_cover_template(doc, config))
    templates.append(make_standard_template(doc, config))
    doc.addPageTemplates(templates)

    ctx = RenderContext(
        rl_styles=_build_rl_styles(config["_resolved_styles"]),
        doc=doc,
        base_path=base_path,
        config=config,
    )

    story = []
    if has_cover:
        story.extend([NextPageTemplate("standard"), PageBreak()])

    for element in config["content"]:
        story.extend(_render_element(element, ctx))

    NumberedCanvas = make_numbered_canvas_class(config)
    has_toc = any(e.get("type") == "toc" for e in config["content"])
    if has_toc:
        doc.multiBuild(story, canvasmaker=NumberedCanvas)
    else:
        doc.build(story, canvasmaker=NumberedCanvas)

    build_struct_tree(config["_struct_tracker"], output_path)
