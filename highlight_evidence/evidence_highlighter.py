import fitz
import json

def highlight_pdf(pdf_path:str, json_path:str)->None:
    print(f"Highlighting {pdf_path}...")

    # Open the document
    doc = fitz.open(pdf_path)

    # Load the JSON output
    with open(json_path, "r") as fh:
        output = json.load(fh)
        output = json.loads(output)
    print(type(output))
    # Get all collected evidence to highlight
    #   EXPLICIT evidence is taken as-is
    #   For IMPLICIT evidence, the <quote> tag must be extracted to get the text
    evidence = output['evidence_used']
    for field in evidence:
        text_to_hilite = []
        # Add EXPLICIT evidence
        text_to_hilite.extend(evidence[field]["EXPLICIT"])
        # Search for quotes in the IMPLICIT evidence
        for imp_ev in evidence[field]["IMPLICIT"]:
            quote_tag_index = imp_ev.find("<quote>")
            if quote_tag_index > -1:
                tag_end = imp_ev.find("</quote>")
                # Extract the quote and add to the list
                ev_substr = imp_ev[quote_tag_index+len("<quote>"):tag_end]
                text_to_hilite.append(ev_substr)
        
        # Highlight in the document
        for page in doc:
            for text in text_to_hilite:
                text_instances = page.search_for(text)
                for inst in text_instances:
                    # Create the highlight
                    highlight = page.add_highlight_annot(inst)

                    # Attach pop-up comment next to the highlighted text
                    popup_rect = fitz.Rect(inst.x1+10, inst.y0, inst.x1+40, inst.y0+30)
                    highlight.set_popup(rect=popup_rect)
                    comment = output["explanation"][field]
                    highlight.set_info(title=field+" = "+str(output[field]),content=comment)
                    highlight.update()
                    
    
    # Save and close the document
    hilite_out_path = pdf_path[:-4]+"_highlighted.pdf"
    doc.save(hilite_out_path, garbage=4, deflate=True)
    doc.close()

    print(f"DONE!!! Highlighted PDF at {hilite_out_path}")

# TEST ONLY
highlight_pdf("./test_data/ABCA4/c.514G_A/Battu_2015_25922843.pdf", "./test_out_data_new/2_pass/few_shot_COT/gpt-oss:120b/ABCA4/c.514G_A/Battu_2015_25922843_2_pass_few_shot_COT_gpt-oss:120b.json")
            



