from reportlab.platypus.tableofcontents import TableOfContents

from ..accessibility import TaggedHeading


def build_toc(element, rl_styles):
    """Return a list of flowables for a table-of-contents block.

    The optional ``title`` is rendered as an h1 heading but is deliberately
    NOT marked with ``_toc_entry``, so the heading itself does not appear as
    an entry in the TOC it labels.

    ``depth`` (default 2) controls how many heading levels are listed; the
    TableOfContents flowable ignores notifications for levels beyond
    len(levelStyles), so setting depth=2 naturally limits to h1 and h2.
    """
    flowables = []

    title = element.get("title", "")
    if title:
        style = rl_styles.get("h1") or rl_styles["body"]
        heading = TaggedHeading(title, style)
        heading._tag_role = "H1"
        flowables.append(heading)

    depth = min(element.get("depth", 2), 3)
    toc = TableOfContents()
    toc.dotsMinLevel = 0  # dot leaders on all levels
    toc.levelStyles = [
        rl_styles.get(f"toc_h{i + 1}") or rl_styles["body"]
        for i in range(depth)
    ]

    flowables.append(toc)
    return flowables
