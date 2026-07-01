import itertools

from reportlab.pdfbase.pdfdoc import PDFDictionary, PDFString, ViewerPreferencesPDFDictionary
from reportlab.platypus import HRFlowable, Image as RLImage, ListFlowable, Paragraph, Table

_table_id_counter = itertools.count()


# ── Phase 6A — document catalog ──────────────────────────────────────────────


def setup_document(canv, config):
    """Apply PDF/UA catalog entries: Lang, MarkInfo, DisplayDocTitle."""
    lang = config["document"].get("lang", "en-GB")
    cat = canv._doc.Catalog
    if lang:
        cat.Lang = PDFString(lang)
    cat.MarkInfo = PDFDictionary({"Marked": "true"})
    vp = ViewerPreferencesPDFDictionary()
    vp["DisplayDocTitle"] = "true"
    cat.ViewerPreferences = vp


# ── Phase 6B — MCID counter and Artifact helpers ─────────────────────────────


def next_mcid(canv):
    """Return the next per-page marked-content identifier."""
    mcid = getattr(canv, "_mcid_counter", 0)
    canv._mcid_counter = mcid + 1
    return mcid


def begin_artifact(canv, artifact_type="Layout"):
    """Open an Artifact marked-content sequence on the canvas."""
    canv.addLiteral(f"/Artifact <</Type /{artifact_type}>> BDC")


def end_artifact(canv):
    """Close a marked-content sequence on the canvas."""
    canv.addLiteral("EMC")


# ── Mixins ───────────────────────────────────────────────────────────────────


class _Tagged:
    """Wrap drawOn() with a semantic BDC/EMC marked-content pair.

    Subclasses set _tag_role (e.g. "P", "H1", "Figure") and optionally
    _tag_alt (alt text stored for the Phase 6C structure tree).
    """
    _tag_role = "P"
    _tag_alt = None

    def drawOn(self, canv, x, y, _sW=0):
        mcid = next_mcid(canv)
        tracker = getattr(canv, "_tracker", None)
        if tracker is not None:
            tracker.record(mcid, self._tag_role, self._tag_alt or "")
        canv.addLiteral(f"/{self._tag_role} <</MCID {mcid}>> BDC")
        super().drawOn(canv, x, y, _sW)
        canv.addLiteral("EMC")


class _Artifact:
    """Mark a flowable as decorative Artifact content (outside reading order)."""
    _artifact_type = "Layout"

    def drawOn(self, canv, x, y, _sW=0):
        begin_artifact(canv, self._artifact_type)
        super().drawOn(canv, x, y, _sW)
        end_artifact(canv)


# ── Concrete tagged flowable types ───────────────────────────────────────────


class TaggedParagraph(_Tagged, Paragraph):
    _tag_role = "P"


class TaggedHeading(_Tagged, Paragraph):
    """_tag_role is set per-instance after construction, e.g. p._tag_role = "H1"."""


class TaggedFigure(_Tagged, RLImage):
    _tag_role = "Figure"


# Aliases kept for call-site clarity; both are identical at runtime.
TaggedImage = TaggedFigure
TaggedChart = TaggedFigure


class TaggedCaption(_Tagged, Paragraph):
    _tag_role = "Caption"


class TaggedListFlowable(_Tagged, ListFlowable):
    _tag_role = "L"


class ArtifactRule(_Artifact, HRFlowable):
    _artifact_type = "Layout"


class TaggedTable(Table):
    """Table subclass that marks each cell with /TH or /TD BDC/EMC operators."""

    _has_header = True  # set per-instance by build_table

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._table_tag_id = next(_table_id_counter)

    def draw(self):
        old_cb = self._renderCB
        self._renderCB = self._tag_cb
        try:
            super().draw()
        finally:
            self._renderCB = old_cb

    def _tag_cb(self, table, event, *args):
        if event == "startCell":
            rowNo, colNo = args[0], args[1]
            role = "TH" if rowNo == 0 and self._has_header else "TD"
            mcid = next_mcid(self.canv)
            tracker = getattr(self.canv, "_tracker", None)
            if tracker is not None:
                tracker.record(mcid, role, "",
                               table_id=self._table_tag_id,
                               row_no=rowNo, col_no=colNo)
            self.canv.addLiteral(f"/{role} <</MCID {mcid}>> BDC")
        elif event == "endCell":
            self.canv.addLiteral("EMC")


# ── Phase 6C — element tracker and StructTreeRoot builder ────────────────────


class _StructTracker:
    """Accumulates tagged-element records during rendering.

    Resets at the start of each canvas pass so only the final multiBuild
    pass contributes to the structure tree.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        # pages[i] = list of records drawn on page i, in MCID order
        self.pages = [[]]
        # ordered = flat list of all records with page index attached
        self.ordered = []

    def new_page(self):
        self.pages.append([])

    def record(self, mcid, role, alt="", table_id=None, row_no=None, col_no=None):
        page_idx = len(self.pages) - 1
        rec = {"mcid": mcid, "role": role, "alt": alt, "page_idx": page_idx,
               "table_id": table_id, "row_no": row_no, "col_no": col_no}
        self.pages[-1].append(rec)
        self.ordered.append(rec)


def build_struct_tree(tracker, output_path):
    """Post-process the rendered PDF to add a PDF/UA-conformant StructTreeRoot.

    Opens the file with pikepdf, builds Document > Sect > element tree from
    the tracker records, wires up the ParentTree number-tree, adds StructParents
    to every page, sets StructTreeRoot on the catalog, and overwrites the file.
    """
    import pikepdf

    pdf = pikepdf.open(output_path, allow_overwriting_input=True)
    try:
        n_pages = len(pdf.pages)

        # ── Build struct tree skeleton ──────────────────────────────────────

        struct_root = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array(),
        ))

        doc_elem = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name("/StructElem"),
            S=pikepdf.Name("/Document"),
            P=struct_root,
            K=pikepdf.Array(),
        ))
        struct_root.K = pikepdf.Array([doc_elem])

        # ── Group records into sections (split on H1) ───────────────────────

        sections = []
        current = []
        for rec in tracker.ordered:
            if rec["role"] == "H1" and current:
                sections.append(current)
                current = []
            current.append(rec)
        if current:
            sections.append(current)

        # ── Create struct elements; collect per-page MCID → elem mappings ───

        page_parents = [{} for _ in range(n_pages)]

        for section_records in sections:
            sect = pdf.make_indirect(pikepdf.Dictionary(
                Type=pikepdf.Name("/StructElem"),
                S=pikepdf.Name("/Sect"),
                P=doc_elem,
                K=pikepdf.Array(),
            ))
            doc_elem.K.append(sect)

            for item in _group_section_items(section_records):
                if isinstance(item, list):
                    _build_table_struct(pikepdf, pdf, sect, item, page_parents, n_pages)
                else:
                    rec = item
                    page_idx = rec["page_idx"]
                    if page_idx >= n_pages:
                        continue
                    elem_dict = pikepdf.Dictionary(
                        Type=pikepdf.Name("/StructElem"),
                        S=pikepdf.Name(f'/{rec["role"]}'),
                        P=sect,
                        Pg=pdf.pages[page_idx].obj,
                        K=pikepdf.Integer(rec["mcid"]),
                    )
                    if rec.get("alt"):
                        elem_dict.Alt = pikepdf.String(rec["alt"])
                    elem = pdf.make_indirect(elem_dict)
                    sect.K.append(elem)
                    page_parents[page_idx][rec["mcid"]] = elem

        # ── Build ParentTree and set StructParents on each page ─────────────

        parent_tree_entries = []
        for page_idx in range(n_pages):
            mcid_map = page_parents[page_idx]
            if mcid_map:
                max_mcid = max(mcid_map.keys())
                parent_arr = pikepdf.Array(
                    [mcid_map.get(m, pikepdf.Dictionary()) for m in range(max_mcid + 1)]
                )
            else:
                parent_arr = pikepdf.Array()
            parent_tree_entries.append(pikepdf.Integer(page_idx))
            parent_tree_entries.append(parent_arr)
            pdf.pages[page_idx].StructParents = pikepdf.Integer(page_idx)

        parent_tree = pdf.make_indirect(pikepdf.Dictionary(
            Nums=pikepdf.Array(parent_tree_entries),
        ))
        struct_root.ParentTree = parent_tree
        struct_root.ParentTreeNextKey = pikepdf.Integer(n_pages)

        # ── Wire into catalog and save ───────────────────────────────────────

        pdf.Root.StructTreeRoot = struct_root
        pdf.save(output_path)
    finally:
        pdf.close()


def _group_section_items(records):
    """Partition a section's records into plain items and table groups.

    Returns a list where each element is either a single record dict (plain
    content) or a list of record dicts that all share the same table_id
    (table cells).
    """
    result = []
    current_table_id = None
    current_table_cells = []

    for rec in records:
        tid = rec.get("table_id")
        if tid is not None:
            if tid != current_table_id:
                if current_table_cells:
                    result.append(current_table_cells)
                current_table_cells = []
                current_table_id = tid
            current_table_cells.append(rec)
        else:
            if current_table_cells:
                result.append(current_table_cells)
                current_table_cells = []
                current_table_id = None
            result.append(rec)

    if current_table_cells:
        result.append(current_table_cells)

    return result


def _build_table_struct(pikepdf, pdf, parent_elem, cells, page_parents, n_pages):
    """Build /Table > /TR > /TH, /TD struct elements for one table."""
    table_elem = pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/StructElem"),
        S=pikepdf.Name("/Table"),
        P=parent_elem,
        K=pikepdf.Array(),
    ))
    parent_elem.K.append(table_elem)

    # Group cells by row number, preserving column order
    rows = {}
    for rec in cells:
        rn = rec.get("row_no", 0)
        rows.setdefault(rn, []).append(rec)

    for row_no in sorted(rows):
        tr_elem = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name("/StructElem"),
            S=pikepdf.Name("/TR"),
            P=table_elem,
            K=pikepdf.Array(),
        ))
        table_elem.K.append(tr_elem)

        for rec in sorted(rows[row_no], key=lambda r: r.get("col_no", 0)):
            page_idx = rec["page_idx"]
            if page_idx >= n_pages:
                continue
            cell_elem = pdf.make_indirect(pikepdf.Dictionary(
                Type=pikepdf.Name("/StructElem"),
                S=pikepdf.Name(f'/{rec["role"]}'),
                P=tr_elem,
                Pg=pdf.pages[page_idx].obj,
                K=pikepdf.Integer(rec["mcid"]),
            ))
            tr_elem.K.append(cell_elem)
            page_parents[page_idx][rec["mcid"]] = cell_elem
