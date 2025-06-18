import fitz  # PyMuPDF
import re

def normalize(text):
    return text.replace("-\n", "").replace("\n", " ").replace("- ", "").strip()

def highlight_fuzzy(page, target_phrase):
    target = target_phrase.lower().replace("-", "").replace(" ", "")
    words = page.get_text("words")  # (x0, y0, x1, y1, "word", ...)
    tokens = []
    char_stream = ""
    index_map = []

    for w in words:
        word = w[4]
        clean = re.sub(r"[^\w\-]", "", word)
        if clean.endswith("-"):
            char_stream += clean[:-1]
        else:
            char_stream += clean
            char_stream += " "
        index_map.append((w, len(char_stream)))

    flat = char_stream.lower().replace(" ", "")
    match_start = flat.find(target)
    if match_start == -1:
        return False

    match_end = match_start + len(target)
    # Highlight all matching words
    for w, end_char in index_map:
        start_char = end_char - len(re.sub(r"[^\w\-]", "", w[4]))
        if start_char < match_end and end_char > match_start:
            rect = fitz.Rect(w[0], w[1], w[2], w[3])
            page.add_highlight_annot(rect)

    return True

# === Use on your PDF ===
doc = fitz.open("Literature/Burke_2018_29120065_522.pdf")
target = "Levodopa-responsive Parkinsonism presenting in infancy or child-hood"
for page in doc:
    if highlight_fuzzy(page, target):
        break

doc.save("output.pdf")
doc.close()
print("✅ Fuzzy highlighting complete.")
