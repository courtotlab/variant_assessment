import requests
import time
import os
import re
from xml.etree import ElementTree as ET
from metapub import PubMedFetcher, FindIt
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# --- Configuration ---

load_dotenv()
# Unique email address to NCBI for identification and contact.
# NCBI requires this for all E-utility requests.
USER_EMAIL = os.getenv("NCBI_USER_EMAIL")

# Set NCBI API key
# This increases the request limit from 3/sec to 10/sec.
NCBI_API_KEY = os.getenv("NCBI_API_KEY")

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

def fetch_pmid_list(query:str, max_results:int=10, last_request_time:float=0, min_date:str='2023', max_date:str=None):
    """
    Searches PubMed for the given query and returns a list of PMIDs (PubMed IDs).
    """
    print(f"\n--- Searching PubMed for: '{query}' ---")
    last_request_time = throttle_request(last_request_time)

    if max_date is None:
        from datetime import date
        today = date.today()
        max_date = today.year

    params = {
        "db": "pubmed",
        "term": query,
        "retmax": str(max_results),
        "retmode": "json",
        "mindate":min_date,
        "maxdate":max_date,
        "datetype":"pdat", # Use publication date to filter
        "email": USER_EMAIL
    }

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
        pdf = FindIt(pmid)
        pdf_url = pdf.url
        
        if pdf_url:
            response = requests.get(pdf_url)
            filename = f"{dwnld_dir}/{file_name}.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded PDF for PMID {pmid}")
        else:
            print(f"No PDF available for PMID {pmid}")
            print(pdf.reason)
    except Exception as e:
        print(f"Error downloading {pmid}: {e}")


def generate_variant_search_string(variant_query:str, prompt_path:str)->str:
    prompt_file = open(prompt_path, "r")
    sys_prompt = prompt_file.read()

    if "GOOGLE_API_KEY" not in os.environ:
        load_dotenv()
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2
    )

    messages = [
        ("system", sys_prompt),
        ("human", variant_query)
    ]

    response = llm.invoke(messages)

    return response.content

def run_miner(variant_query:str, max_papers:int=5, min_date:str='2023', max_date:str=None, download_dir:str="genomic_papers"):
    """
    Main function to execute the literature mining pipeline.
    """
    os.makedirs(download_dir, exist_ok=True)
    print(f"\n[INFO] Download directory set to: '{download_dir}'")

    last_request_time = 0

    query = generate_variant_search_string(variant_query, "../prompts/variant_search/variant_search_query.txt")
    print("GEMINI-GENERATED QUERY:\n", query)

    all_pmids = set()
    
    pmid_list, last_request_time = fetch_pmid_list(
        query=f'{query}',
        max_results=max_papers,
        last_request_time=last_request_time,
        min_date=min_date,
        max_date=max_date
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
    VARIANT_TO_SEARCH = "LRRK2 c.6055G>A"
    #VARIANT_TO_SEARCH = "GALC c.956A_G" 
    # Specify the number of papers to fetch
    MAX_RESULTS = 10
    
    run_miner(VARIANT_TO_SEARCH, MAX_RESULTS, min_date=2024)