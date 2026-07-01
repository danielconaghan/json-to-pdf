from reportlab.lib.utils import ImageReader
from reportlab.platypus import Spacer

from ..accessibility import TaggedCaption, TaggedImage
from ..utils import resolve_path


def build_image(element, rl_styles, doc, base_path=None):
    src = resolve_path(element["src"], base_path)
    if src is None:
        return []

    available = doc.width
    width_spec = element.get("width", "100%")
    if isinstance(width_spec, str) and width_spec.endswith("%"):
        width = available * float(width_spec.rstrip("%")) / 100
    else:
        width = float(width_spec)

    reader = ImageReader(src)
    iw, ih = reader.getSize()
    height = width * ih / iw

    img = TaggedImage(src, width=width, height=height)
    img.hAlign = element.get("align", "left").upper()
    img._tag_alt = element.get("alt", "")

    flowables = [img]

    caption_text = element.get("caption")
    if caption_text:
        caption_style = rl_styles.get("caption") or rl_styles.get("body")
        flowables.append(Spacer(1, 4))
        flowables.append(TaggedCaption(caption_text, caption_style))

    return flowables
