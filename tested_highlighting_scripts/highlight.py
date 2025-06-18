import fitz  # PyMuPDF

# Define file paths
pdf_path = "Literature/Burke_2018_29120065_522.pdf"
output_path = "Literature/Burke_2018_highlighted.pdf"

# Open the PDF
doc = fitz.open(pdf_path)

# The sentence split as it appears across 3 lines (exact match from the PDF)
lines_to_highlight = [
    "Levodopa-responsive Parkinsonism presenting in infancy or child-",
    "hood is extraordinarily rare and may occur as a comorbidity to other",
    "diseases or genetic conditions."
]

# Loop through pages and find the page where all 3 parts are present
for page in doc:
    found_all = True
    for line in lines_to_highlight:
        matches = page.search_for(line)
        if not matches:
            found_all = False
            break
    if found_all:
        # Highlight all matching lines
        for line in lines_to_highlight:
            for rect in page.search_for(line):
                page.add_highlight_annot(rect)
        break  # Stop after highlighting once

# Save the updated PDF
doc.save(output_path, garbage=4, deflate=True)
doc.close()

print(f"✅ Highlighting complete. Saved to: {output_path}")
