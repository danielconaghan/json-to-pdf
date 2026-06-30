from pathlib import Path

from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, Spacer


def build_image(element, rl_styles, doc, base_path=None):
    src = element["src"]
    if base_path and not Path(src).is_absolute():
        src = str(Path(base_path) / src)

    # Resolve width: percentage of content width, or explicit points
    available = doc.width
    width_spec = element.get("width", "100%")
    if isinstance(width_spec, str) and width_spec.endswith("%"):
        width = available * int(width_spec.rstrip("%")) / 100
    else:
        width = float(width_spec)

    # Height: auto-calculated to maintain aspect ratio
    reader = ImageReader(src)
    iw, ih = reader.getSize()
    height = width * ih / iw

    img = RLImage(src, width=width, height=height)
    img.hAlign = element.get("align", "left").upper()

    flowables = [img]

    caption_text = element.get("caption")
    if caption_text:
        caption_style = rl_styles.get("caption") or rl_styles.get("body")
        flowables.append(Spacer(1, 4))
        flowables.append(Paragraph(caption_text, caption_style))

    return flowables
