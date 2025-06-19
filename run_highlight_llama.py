import json
import fitz  # PyMuPDF
from pathlib import Path

def fix_broken_quote_lines(quote_lines):
    """Clean up quote lines by stripping whitespace and skipping empty lines."""
    return [line.strip() for line in quote_lines if line.strip()]

def try_highlight(page, text):
    """Try to highlight the text on the page. Return True if any match was found."""
    if not text.strip():
        return False
    for quad in page.search_for(text, quads=True):
        page.add_highlight_annot(quad)
        print(f"✅ Highlighted: '{text}'")
        return True
    print(f"❌ Not found: '{text}'")
    return False

def apply_highlight(doc, index, line):
    """Try full line. If it fails and the line contains hyphens, split and try parts."""
    for page_num in [index * 2, index * 2 + 1]:
        if page_num >= len(doc):
            continue
        page = doc[page_num]

        # Step 1: Try full line
        if try_highlight(page, line):
            return  # Stop if full line matched

        # Step 2: Fallback — try parts around hyphenated words
        words = line.split()
        for i, word in enumerate(words):
            if '-' in word:
                # Part before the hyphenated word
                part1 = ' '.join(words[:i])
                # Part after the word following the hyphenated word
                part2 = ' '.join(words[i+2:]) if i + 2 < len(words) else ''

                if part1:
                    try_highlight(page, part1)
                if part2:
                    try_highlight(page, part2)

def highlight_quotes_from_json(pdf_path, json_path, output_pdf):
    doc = fitz.open(pdf_path)
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    quotes_by_index = data.get("quote_snippets", [])

    for idx, quotes in enumerate(quotes_by_index):
        if not quotes:
            continue

        if isinstance(quotes, str):
            quotes = [quotes]

        if isinstance(quotes[0], list):
            for q_block in quotes:
                cleaned = fix_broken_quote_lines(q_block)
                for line in cleaned:
                    apply_highlight(doc, idx, line)
        else:
            cleaned = fix_broken_quote_lines(quotes)
            for line in cleaned:
                apply_highlight(doc, idx, line)

    Path(output_pdf).parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_pdf)
    print(f"\n✅ Highlighted PDF saved to: {output_pdf}")


highlight_quotes_from_json(
    pdf_path="literature/Vantroys_2018_29783990_371.pdf",
    json_path="output_llama_with_quotes/Vantroys_llama.json",
    output_pdf="highlighted_pdfs_llama/Vantroys_highlighted.pdf"
)
