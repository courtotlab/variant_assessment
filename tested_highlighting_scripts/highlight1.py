import pymupdf  # import package PyMuPDF

# open input PDF
doc = pymupdf.open("literature\\Burke_2018_29120065_522.pdf")

# load desired page (0-based page number)
pno = 6
page = doc[pno]

# the sentence you want to highlight (can span multiple lines)
needle = """Biallelic mutations in mitochondrial tryptophanyl-tRNA synthetase cause Levodopa-responsive infantile-onset"""

# search for sentence and return list of rectangles
quads = page.search_for(needle, quads=True)

for quad in quads:
    page.add_highlight_annot(quad)

# save the result
doc.save("output.pdf")

