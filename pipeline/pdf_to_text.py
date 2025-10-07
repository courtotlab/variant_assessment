import os
from typing import List

def convert_pdf_to_str_list(pdf_path: str, language_list=["en"], dpi=300) -> List[str]:
  """Use EasyOCR to convert the given PDF file into plain text but page by page.
  Returns a list of strings representing each page.

  Args:
    pdf_path: path to the pdf input file
    language_list: A list of languages to detect for OCR
    dpi: The scan resolution to use for OCR

  Returns:
    A list of text strings representing the document pages

  """
  # Initialize the EasyOCR reader.
  # lazy import to speed up app boot time
  from easyocr import Reader  # type: ignore

  reader = Reader(language_list)

  # Convert PDF pages to images.
  try:
    # lazy import to speed up app boot time
    from pdf2image import convert_from_path

    # You can adjust dpi if necessary.
    pages = convert_from_path(pdf_path, dpi=dpi)
  except Exception as e:
    print(f"Failed to converting PDF to images: {e}", os.EX_CONFIG)

  # lazy import to speed up app boot time
  from numpy import array

  full_text = []
  for i, page in enumerate(pages):
    print(f" - Processing page {i + 1}...")
    # Convert PIL image to numpy array.
    image_np = array(page)

    # Use EasyOCR to extract text from the image.
    try:
      results = reader.readtext(image_np, detail=0, paragraph=True)
      # Join text from detected regions.
      page_text = "\n".join(results)
      full_text.append(page_text)
    except Exception as e:
      print(f"Failed processing page {i + 1}: {e}", os.EX_DATAERR)

  return full_text


def convert_pdf_to_text(pdf_path: str, language_list=["en"], dpi=300) -> str:
  """Use EasyOCR to convert the given PDF file into plain text.
  Returns a string, with pages separated by two newline characters.

  Args:
    pdf_path: path to the pdf input file
    language_list: A list of languages to detect for OCR
    dpi: The scan resolution to use for OCR

  Returns:
    A text string of the OCR result.

  """
  pages = convert_pdf_to_str_list(pdf_path, language_list, dpi)
  return "\n\n".join(pages)
