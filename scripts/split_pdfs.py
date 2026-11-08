"""Split each PDF into parts of <=30 pages named '<doc>__pSTART-END.pdf' (1-based, inclusive).

Why: the Document Layout skill has a 5-minute per-document timeout and large PDFs exceeded it. app.py converts a
page number within a part back to the real PDF page (part page + START - 1).
Usage: python scripts/split_pdfs.py pdfs pdfs-split
"""
import glob
import os
import sys

from pypdf import PdfReader, PdfWriter

PART = 30
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
parts = pages = 0
for f in sorted(glob.glob(os.path.join(src, "*.pdf"))):
    base = os.path.basename(f)[:-4]
    r = PdfReader(f)
    n = len(r.pages)
    if n <= PART:
        w = PdfWriter()
        for p in r.pages:
            w.add_page(p)
        w.write(os.path.join(dst, f"{base}.pdf"))
        parts += 1
        pages += n
        continue
    for s in range(0, n, PART):
        e = min(s + PART, n)
        w = PdfWriter()
        for p in r.pages[s:e]:
            w.add_page(p)
        w.write(os.path.join(dst, f"{base}__p{s + 1:03d}-{e:03d}.pdf"))
        parts += 1
        pages += e - s
print(f"{parts} parts, {pages} pages")
