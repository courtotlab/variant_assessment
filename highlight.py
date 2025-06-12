import fitz  # PyMuPDF
import os

# Define file paths
pdf_path = os.path.join("Literature", "Burke_2018_29120065_522.pdf")
output_path = os.path.join("Literature", "Burke_2018_highlighted_sequence_fixed.pdf")

# Target phrase
target_phrase = (
    "Levodopa-responsive Parkinsonism presenting in infancy or child-hood"
)
target_words = target_phrase.split()

# Open the PDF
doc = fitz.open(pdf_path)

for page in doc:
    words = page.get_text("words")  # [x0, y0, x1, y1, "word", block_no, line_no, word_no]
    words.sort(key=lambda w: (w[1], w[0]))  # sort top-to-bottom, then left-to-right

    seq_len = len(target_words)
    i = 0
    while i < len(words) - seq_len + 1:
        match = True
        rects = []
        for j in range(seq_len):
            word_text = words[i + j][4]
            if word_text != target_words[j]:
                match = False
                break
            rects.append(fitz.Rect(words[i + j][:4]))
        if match:
            # Create one annotation spanning all words
            union_rect = rects[0]
            for r in rects[1:]:
                union_rect |= r  # union of all rects
            page.add_highlight_annot(union_rect)
            print("Match found and highlighted.")
            break  # stop after first match
        i += 1

# Save the result
doc.save(output_path, garbage=4, deflate=True)
doc.close()
print(f"Saved to: {output_path}")
