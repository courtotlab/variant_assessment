import pymupdf  # PyMuPDF

# Open the PDF
doc = pymupdf.open("literature\\Burke_2018_29120065_522.pdf")
page = doc[0]

# Define the search term
needle = "Levodopa-responsive Parkinsonism"

# Get all text blocks (x0, y0, x1, y1, "text", block_no, block_type)
blocks = page.get_text("blocks")

# Get rectangles where the needle is found
results = page.search_for(needle)

# Loop over all found rectangles
for j, rect in enumerate(results):
    # Loop over blocks to find which block contains this rectangle
    for i, b in enumerate(blocks):
        block_rect = pymupdf.Rect(b[0], b[1], b[2], b[3])
        if block_rect.contains(rect):
            print(f"Match {j} is in block {i}: {b[4][:50]}...")

            # Only highlight if it's in a certain block (example: block #2)
            if i == 2:
                page.add_highlight_annot(rect)
            break

# Save result
doc.save("output.pdf")
print("Done.")
