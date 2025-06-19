import json
import fitz  # PyMuPDF
from pathlib import Path

def fix_broken_quote_lines(quote_lines):
    """Fix hyphenated line-breaks like 'dys-' by removing the last word and skipping the next word."""
    cleaned_lines = []
    skip_next_word = False

    for line in quote_lines:
        if skip_next_word:
            parts = line.split(' ', 1)
            line = parts[1] if len(parts) > 1 else ''
            skip_next_word = False

        if line.strip().endswith('-'):
            words = line.strip().split()
            if len(words) > 1:
                line = ' '.join(words[:-1])
            else:
                line = ''
            skip_next_word = True

        if line:
            cleaned_lines.append(line.strip())

    return cleaned_lines

def apply_highlight(doc, index, line):
    """Highlight the line on pages index*2 and index*2 + 1."""
    for page_num in [index * 2, index * 2 + 1]:
        if page_num >= len(doc):
            continue
        page = doc[page_num]
        for quad in page.search_for(line, quads=True):
            page.add_highlight_annot(quad)

def highlight_quotes_from_json(pdf_path, json_path, output_pdf):
    doc = fitz.open(pdf_path)
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    quotes_by_index = data.get("cleaned_quotes", [])

    for idx, quotes in enumerate(quotes_by_index):
        if not quotes:
            continue  # Skip empty entries

        if isinstance(quotes, str):
            quotes = [quotes]

        # Handle nested lists of quote lines
        if isinstance(quotes[0], list):
            for q_block in quotes:
                cleaned = fix_broken_quote_lines(q_block)
                for line in cleaned:
                    apply_highlight(doc, idx, line)
        else:
            # Handle flat list of quote lines
            cleaned = fix_broken_quote_lines(quotes)
            for line in cleaned:
                apply_highlight(doc, idx, line)

    Path(output_pdf).parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_pdf)
    print(f"✅ Highlighted PDF saved to: {output_pdf}")

# === Run the script for Burke ===
highlight_quotes_from_json(
    pdf_path="literature/Vantroys_2018_29783990_371.pdf",
    json_path="output_lei_with_quotes/Vantroys_lei_quotes.json",
    output_pdf="highlighted_pdfs_lei/Vantroys_highlighted.pdf"
)
