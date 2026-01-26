import requests
import time
import os
import re
from xml.etree import ElementTree as ET
from metapub import PubMedFetcher, FindIt

try:
    import hgvs.parser
    import hgvs.normalizer
    import hgvs.dataproviders.uta
    from hgvs.variantmapper import VariantMapper
    from hgvs.sequencevariant import SequenceVariant
    
    # Initialize HGVS components (requires UTA database or similar)
    HP = hgvs.parser.Parser()
    HDP = hgvs.dataproviders.uta.connect() # Database connection
    HN = hgvs.normalizer.Normalizer(HDP)
    HVM = VariantMapper(hdp=HDP)
    HGVS_ENABLED = True
    print("[INFO] HGVS modules imported. Using advanced normalization.")
except ImportError as err:
    print(err)
    print("[WARNING] Could not import HGVS dependencies. Falling back to simplified regex.")
    HGVS_ENABLED = False

# --- Configuration ---
# Unique email address to NCBI for identification and contact.
# NCBI requires this for all E-utility requests.
USER_EMAIL = "amelanidelahoz@oicr.on.ca"

# Set NCBI API key
# This increases the request limit from 3/sec to 10/sec.
NCBI_API_KEY = ""

# Base URLs for NCBI E-utilities
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Base URL for PubMed Central (PMC) PDF download link structure
PMC_BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{}/pdf/"

def throttle_request(last_request_time:float, requests_per_second:int=3):
    """Ensures to adhere to NCBI's usage guidelines (max 3 reqs/sec without API key)."""
    delay_time = 1.0 / requests_per_second
    elapsed = time.time() - last_request_time
    if elapsed < delay_time:
        wait = delay_time - elapsed
        time.sleep(wait)
    return time.time()

def normalize_variant_query(raw_variant: str) -> list[str]:
    """
    Generates multiple standardized search queries from a single raw variant input.
    If HGVS package is available, it is used to normalize the query.
    If not, a simplified RegEx match is used.
    
    Args:
        raw_variant: The user's input variant string.
        
    Returns:
        A list of standardized query strings for PubMed search.
    """
    queries = [raw_variant]
    
    if HGVS_ENABLED:
        try:
            print("HGVS found. Using library for normalization.")
            # 1. Parse the variant string
            variant_parsed = HP.parse_hgvs_variant(raw_variant)
            
            # 2. Normalize the variant
            # This step ensures the variant is represented canonically
            variant_normalized = HN.normalize(variant_parsed)
            
            # Add the canonical normalized form
            queries.append(str(variant_normalized))
            
            # 3. Generate alternate forms (Requires the HN object, which handles 
            # the conversion between transcript, genomic, and protein coordinates).
            # Use transcript and protein conversions to maximize search terms.
            
            try:
                g_variant = HVM.c_to_g(variant_parsed)
                
                # Check if the conversion was successful and resulted in a genomic variant
                if g_variant and g_variant.type == 'g':
                    queries.append(str(g_variant))
                    
            except Exception as e:
                # Conversion might fail if the transcript is not found or mapping is unavailable.
                print(f"Warning: Failed to convert to g. variant. Error: {e}")
                pass
                
            # Protein (p.) conversion (If variant is not already p.)
            # If the variant is a cDNA change, convert it to protein change
            if variant_normalized.type == 'c':
                try:
                    p_variant = HVM.c_to_p(variant_normalized, raw_variant.split(':')[0])
                    if p_variant:
                         queries.append(str(p_variant))
                except Exception as e:
                    print(f"Warning: Failed to convert to p. variant. Error: {e}")
                    pass
            
            # Simple AA/Codon Notation (for protein variants)
            # This handles both official p. nomenclature and the common V600E style.
            if variant_normalized.type == 'p':
                # Add the full protein notation (p.) itself
                queries.append(str(variant_normalized))
                
                if isinstance(variant_normalized, SequenceVariant) and hasattr(variant_normalized.posedit.edit, 'alt'):
                    # The HGVS accession (e.g., NP_00123456.1) often contains gene info.
                    # This is a heuristic to extract a gene symbol for searching
                    gene_match = re.search(r'([A-Z0-9]+)', variant_normalized.ac, re.IGNORECASE)
                    gene = gene_match.group(1) if gene_match else ""
                    
                    try:
                        ref_aa = variant_normalized.posedit.edit.ref
                        alt_aa = variant_normalized.posedit.edit.alt
                        position = variant_normalized.posedit.pos.end.base
                        
                        # Add the Gene + old AA notation (e.g., BRAF V600E)
                        if gene and ref_aa and position and alt_aa:
                            simple_notation = f"{ref_aa}{position}{alt_aa}"
                            queries.append(f"{gene} {simple_notation}")
                            queries.append(simple_notation) # AA change only
                    except AttributeError:
                        # Handle complex edits like deletions or frameshifts where ref/alt/pos extraction is less straightforward
                        pass

            elif variant_normalized.type == 'c':
                # Add the cDNA notation (c.)
                queries.append(str(variant_normalized))
                # Add the accession (e.g., NM_...)
                queries.append(variant_normalized.ac)
                # For c. variants, try to use the corresponding gene name (heuristic from accession)
                gene_match = re.search(r'([A-Z0-9]+)', variant_normalized.ac, re.IGNORECASE)
                gene = gene_match.group(1) if gene_match else ""
                if gene:
                    queries.append(gene)


        except Exception as e:
            # Catch parsing errors, or if the external data is not configured correctly
            print(f"[HGVS ERROR] Could not fully normalize variant '{raw_variant}': {e}. Using raw query and regex fallback.")
            # If HGVS fails, fall back to the raw query and the old regex logic below
            
            # Simplified regex fallback (for inputs like "BRAF V600E" that HGVS might not parse directly)
            match = re.search(r'([A-Z0-9]+)\s+([A-Z])(\d+)([A-Z\*])', raw_variant, re.IGNORECASE)
            
            if match:
                gene, ref_aa, position, alt_aa = match.groups()
                p_notation_search = f"{gene} p.{ref_aa}{position}{alt_aa}"
                queries.append(p_notation_search)
                aa_change_only = f"{ref_aa}{position}{alt_aa}"
                if aa_change_only not in raw_variant:
                    queries.append(aa_change_only)
            
    else:
        # Simplified regex fallback (original logic for environments without HGVS)
        print("No HGVS found. Using RegEx fallback")
        match = re.search(r'([A-Z0-9]+)\s+([A-Z])(\d+)([A-Z\*])', raw_variant, re.IGNORECASE)
        
        if match:
            gene, ref_aa, position, alt_aa = match.groups()
            p_notation_search = f"{gene} p.{ref_aa}{position}{alt_aa}"
            queries.append(p_notation_search)
            aa_change_only = f"{ref_aa}{position}{alt_aa}"
            if aa_change_only not in raw_variant:
                queries.append(aa_change_only)
    
    # Clean up and deduplicate the list of queries
    queries = [q.strip() for q in queries if q.strip()]
    unique_queries = list(set(queries))
    
    print(f"\n[STAGE 1] Generated search queries: {unique_queries}")
    return unique_queries

def fetch_pmid_list(query:str, max_results:int=10, last_request_time:float=0):
    """
    Searches PubMed for the given query and returns a list of PMIDs (PubMed IDs).
    """
    print(f"\n--- Searching PubMed for: '{query}' ---")
    last_request_time = throttle_request(last_request_time)

    params = {
        "db": "pubmed",
        "term": query,
        "retmax": str(max_results),
        "retmode": "json",
        "email": USER_EMAIL
    }

    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    
    try:
        response = requests.get(ESEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        id_list = data.get('esearchresult', {}).get('idlist', [])
        count = data.get('esearchresult', {}).get('count', '0')

        print(f"Found {len(id_list)} of {count} total results matching the query.")
        return id_list, last_request_time
    except requests.RequestException as e:
        print(f"Error during ESearch API call: {e}")
        return [], last_request_time
    except Exception as e:
        print(f"An unexpected error occurred during search: {e}")
        return [], last_request_time

def fetch_paper_details(pmid_list:list, last_request_time:float):
    """
    Retrieves detailed XML metadata for a list of PMIDs using EFetch.
    """
    if not pmid_list:
        return [], last_request_time

    ids = ",".join(pmid_list)
    print(f"Fetching full metadata for {len(pmid_list)} articles...")
    last_request_time = throttle_request(last_request_time)

    params = {
        "db": "pubmed",
        "id": ids,
        "retmode": "xml", # XML is the standard for EFetch full records
        "email": USER_EMAIL
    }

    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY

    try:
        response = requests.get(EFETCH_URL, params=params)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)

        papers = []
        # XML parsing for key fields
        for article in root.findall('.//PubmedArticle'):
            medline_citation = article.find('MedlineCitation')
            pubmed_data = article.find('PubmedData')
            article_info = medline_citation.find('Article') if medline_citation is not None else None

            # 1. Extract Title
            title = article_info.find('ArticleTitle').text if article_info is not None and article_info.find('ArticleTitle') is not None else "N/A"
            title = title.strip() if title else "N/A"

            # 2. Extract Journal
            journal = article_info.find('Journal/Title').text if article_info is not None and article_info.find('Journal/Title') is not None else "N/A"
            
            # 3. Extract IDs (PMID, PMCID, DOI)
            pmid = medline_citation.find('PMID').text if medline_citation is not None and medline_citation.find('PMID') is not None else "N/A"
            
            doi = "N/A"
            pmcid = "N/A"
            
            for article_id in pubmed_data.findall('./ArticleIdList/ArticleId') if pubmed_data is not None else []:
                id_type = article_id.get('IdType')
                if id_type == 'doi':
                    doi = article_id.text
                elif id_type == 'pmc':
                    # Extract the numerical part of the PMCID
                    print(article_id.text)
                    pmcid = article_id.text.replace('PMC', '')

            papers.append({
                "title": title,
                "pmid": pmid,
                "pmcid": pmcid,
                "doi": doi,
                "journal": journal
            })
        
        return papers, last_request_time
    
    except requests.RequestException as e:
        print(f"Error during EFetch API call: {e}")
        return [], last_request_time
    except ET.ParseError:
        print("Error parsing XML response from NCBI.")
        return [], last_request_time
    except Exception as e:
        print(f"An unexpected error occurred during detail fetching: {e}")
        return [], last_request_time

def download_paper(paper_metadata:dict, download_dir:str, last_request_time:float):
    """
    Attempts to download the PDF using the PMCID (PubMed Central Open Access route).
    """
    pmcid = paper_metadata.get("pmcid")
    pmid = paper_metadata.get("pmid")
    doi = paper_metadata.get("doi")
    title = paper_metadata.get("title")

    # Clean up the title for a safe filename
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_')).rstrip()
    filename = f"{safe_title[:50]}_PMC{pmcid}.pdf"
    filepath = os.path.join(download_dir, filename)

    last_request_time = throttle_request(last_request_time, requests_per_second=1)
    metapub_download_helper(pmid, download_dir, filename)
    
    print()
    return last_request_time

def metapub_download_helper(pmid:str, dwnld_dir:str, file_name:str):
    #fetch = PubMedFetcher()
    try:
        #article = fetch.article_by_pmid(pmid)
        pdf_url = FindIt(pmid).url
        
        if pdf_url:
            response = requests.get(pdf_url)
            filename = f"{dwnld_dir}/{file_name}.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded PDF for PMID {pmid}")
        else:
            print(f"No PDF available for PMID {pmid}")
    except Exception as e:
        print(f"Error downloading {pmid}: {e}")


def run_miner(variant_query:str, max_papers:int=5, download_dir:str="genomic_papers"):
    """
    Main function to execute the literature mining pipeline.
    """
    os.makedirs(download_dir, exist_ok=True)
    print(f"\n[INFO] Download directory set to: '{download_dir}'")

    last_request_time = 0

    #STAGE 1: Variant Normalization
    os.environ['HGVS_SEQREPO_DIR'] = '/usr/local/share/seqrepo/2024-12-20'
    search_queries = normalize_variant_query(variant_query)
    
    # STAGE 2: Search and Metadata Retrieval
    all_pmids = set()
    
    for query in search_queries:
        pmid_list, last_request_time = fetch_pmid_list(
            query=f'{query}',
            max_results=max_papers,
            last_request_time=last_request_time
        )
        all_pmids.update(pmid_list)
        
    final_pmid_list = list(all_pmids)[:max_papers] # Limit to max_papers overall

    if not final_pmid_list:
        print("\nNo relevant papers found for any query. Exiting.")
        return

    papers_metadata, last_request_time = fetch_paper_details(final_pmid_list, last_request_time)
    
    print("\n--- Summary of Found Articles ---")
    for i, p in enumerate(papers_metadata):
        print(f"[{i+1}] Title: {p['title']}")
        print(f"    PMID: {p['pmid']} | PMCID: {p['pmcid']} | DOI: {p['doi']}")
        print(f"    Journal: {p['journal']}")

    # STAGE 3: Paper Download
    print("\n--- Attempting PDF Downloads ---")
    for paper in papers_metadata:
        last_request_time = download_paper(paper, download_dir, last_request_time)
        # Add an extra small pause between papers for safety
        time.sleep(0.5)

    print("\n\nPipeline complete. Check the 'genomic_papers' directory for downloads.")

if __name__ == "__main__":

    #VARIANT_TO_SEARCH = "GALC c.956A_G" 
    #VARIANT_TO_SEARCH = "BRAF V600E"
    VARIANT_TO_SEARCH = "TSC1:c.359T>C"
    # Specify the number of papers to fetch
    MAX_RESULTS = 5
    
    run_miner(VARIANT_TO_SEARCH, MAX_RESULTS)