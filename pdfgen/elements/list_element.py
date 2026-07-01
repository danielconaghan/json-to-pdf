from reportlab.platypus import ListItem, Paragraph

from ..accessibility import TaggedListFlowable


def build_list(element, rl_styles):
    style = element.get("style", "bullet")
    items = element.get("items", [])
    body = rl_styles.get("body")

    bullet_type = "bullet" if style == "bullet" else "1"

    list_items = [
        ListItem(
            Paragraph(item, body),
            leftIndent=12,
            bulletColor=body.textColor if body else None,
        )
        for item in items
    ]

    return [TaggedListFlowable(
        list_items,
        bulletType=bullet_type,
        leftIndent=18,
        bulletFontName="Helvetica",
        bulletFontSize=10,
        start=None,
    )]
