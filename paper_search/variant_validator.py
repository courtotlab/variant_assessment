"""
Variant Search String Generator
=================================
Generates literature search strings for genetic variants using:
  1. Mutalyzer         — primary HGVS normalizer
                         Endpoint: GET /api/normalize/{description}
                         Description is a PATH SEGMENT, not a query parameter.
                         e.g. GET https://mutalyzer.nl/api/normalize/LRRK2:c.6055G>A
  2. VariantValidator  — fallback if Mutalyzer is unavailable
  3. Ensembl VEP       — fallback for protein consequence if neither above returns one
  4. ClinVar           — all known submission names and aliases
  5. Ollama            — typographic/free-text variants used in papers (optional)
"""

import re
import json
import time
import requests
from dataclasses import dataclass, field
from dotenv import load_dotenv
import os


# ── Configuration ─────────────────────────────────────────────────────────────
load_dotenv()
# Mutalyzer 3 — primary normalizer
# Endpoint: GET /api/normalize/{description}  (description is a PATH SEGMENT)
MUTALYZER_API = "https://mutalyzer.nl/api"

# VariantValidator — fallback if Mutalyzer unavailable
# Docs: https://rest.variantvalidator.org/webservices/variantvalidator.html
VARIANTVALIDATOR_API = "https://rest.variantvalidator.org/VariantValidator/variantvalidator"
GENOME_BUILD         = "GRCh38"   # or "GRCh37"

# Ensembl VEP REST API — fallback for protein consequence
# Docs: https://rest.ensembl.org
ENSEMBL_API = "https://rest.ensembl.org"

# NCBI ClinVar via E-utilities
CLINVAR_API  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_EMAIL   = os.getenv("NCBI_USER_EMAIL")   # required by NCBI's usage policy
NCBI_API_KEY = os.getenv("NCBI_API_KEY")      # optional — raises limit to 10 req/s

# Ollama
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL    = "llama3"


# ── Data structure ────────────────────────────────────────────────────────────

@dataclass
class SearchStringResult:
    input_variant: str
    gene: str
    hgvs: str

    # Mutalyzer (primary normalizer)
    muta_valid: bool      = False
    muta_normalized: str  = ""
    muta_protein: str     = ""
    muta_all_hgvs: list   = field(default_factory=list)
    muta_error: str       = ""

    # VariantValidator (fallback normalizer)
    vv_used: bool         = False
    vv_valid: bool        = False
    vv_normalized: str    = ""
    vv_protein: str       = ""
    vv_all_hgvs: list     = field(default_factory=list)
    vv_error: str         = ""

    # Ensembl VEP (fallback for protein consequence only)
    vep_used: bool        = False
    vep_valid: bool       = False
    vep_protein: str      = ""
    vep_error: str        = ""

    # ClinVar
    clinvar_found: bool   = False
    clinvar_id: str       = ""
    clinvar_title: str    = ""
    clinvar_aliases: list = field(default_factory=list)

    # Term sets
    api_terms: list       = field(default_factory=list)
    ollama_terms: list    = field(default_factory=list)
    all_terms: list       = field(default_factory=list)

    # Final output
    search_string: str    = ""

    def summary(self) -> str:
        lines = [
            f"\n{'='*65}",
            f"  Input:              {self.input_variant}",
            f"{'='*65}",
            f"  MUTALYZER (primary)",
            f"    Valid:            {self.muta_valid}",
        ]
        if self.muta_valid:
            lines += [
                f"    Normalized HGVS:  {self.muta_normalized}",
                f"    Protein:          {self.muta_protein or 'n/a'}",
                f"    All HGVS forms:   {self.muta_all_hgvs}",
            ]
        else:
            lines.append(f"    Error:            {self.muta_error}")

        if self.vv_used:
            lines.append(f"  VARIANTVALIDATOR (fallback)")
            if self.vv_valid:
                lines += [
                    f"    Normalized HGVS:  {self.vv_normalized}",
                    f"    Protein:          {self.vv_protein or 'n/a'}",
                ]
            else:
                lines.append(f"    Error:            {self.vv_error}")

        if self.vep_used:
            lines.append(f"  ENSEMBL VEP (protein fallback)")
            if self.vep_valid:
                lines.append(f"    Protein:          {self.vep_protein or 'n/a'}")
            else:
                lines.append(f"    Error:            {self.vep_error}")

        lines += [
            f"  CLINVAR",
            f"    Found:            {self.clinvar_found}",
        ]
        if self.clinvar_found:
            lines += [
                f"    ClinVar ID:       {self.clinvar_id}",
                f"    Title:            {self.clinvar_title}",
                f"    Aliases:          {self.clinvar_aliases or 'none'}",
            ]
        lines += [
            f"  TERMS",
            f"    From APIs:        {self.api_terms}",
            f"    From Ollama:      {self.ollama_terms or 'skipped'}",
            f"    Combined:         {self.all_terms}",
            f"  SEARCH STRING",
            f"    {self.search_string}",
            "=" * 65,
        ]
        return "\n".join(lines)


# ── Input parser ──────────────────────────────────────────────────────────────

def parse_input(variant_input: str) -> tuple[str, str]:
    """
    Parse 'GENE HGVS' into (gene, hgvs).
    E.g. 'LRRK2 c.6055G>A' -> ('LRRK2', 'c.6055G>A')
    """
    parts = variant_input.strip().split(maxsplit=1)
    if len(parts) != 2:
        raise ValueError(
            f"Expected 'GENE HGVS' (e.g. 'LRRK2 c.6055G>A'), got: '{variant_input}'"
        )
    return parts[0], parts[1]


# ── Mutalyzer 3 ───────────────────────────────────────────────────────────────

# Priority order when selecting a transcript from a Mutalyzer 422 response.
# Mutalyzer groups options by genome build; within each build entries may be
# tagged "MANE Select" or "RefSeq Select" — we prefer those.
_MUTALYZER_BUILD_PRIORITY = ("GRCH38", "T2T", "GRCH37")
_MUTALYZER_TAG_PRIORITY   = ("MANE Select", "RefSeq Select")


def _best_description_from_422(err_body: dict) -> str:
    """
    When Mutalyzer returns 422 for a gene-symbol description like
    'LRRK2:c.6055G>A', the response body contains a rich 'options' dict
    under custom.errors[].options that maps genome builds to lists of
    candidate descriptions, some tagged 'MANE Select' or 'RefSeq Select'.

    This function picks the best description using the priority order:
      1. GRCH38 MANE Select
      2. GRCH38 RefSeq Select
      3. T2T MANE Select / RefSeq Select
      4. GRCH37 RefSeq Select
      5. First available entry in GRCH38

    Returns the full corrected description string, e.g.:
      "NC_000012.12(NM_198578.4):c.6055G>A"
    or None if nothing useful was found.
    """
    errors = (err_body.get("custom") or {}).get("errors", [])
    for error in errors:
        options = error.get("options", {})
        if not options:
            continue

        # Try preferred builds in order
        for build in _MUTALYZER_BUILD_PRIORITY:
            candidates = options.get(build, [])
            if not candidates:
                continue

            # First pass: look for a tagged preferred transcript
            for tag in _MUTALYZER_TAG_PRIORITY:
                for candidate in candidates:
                    if candidate.get("tag") == tag:
                        return candidate["description"]

            # Second pass: just take the first entry in the preferred build
            if candidates:
                return candidates[0]["description"]

    return None


def _normalize_description(description: str) -> dict:
    """
    Call GET /api/normalize/{description} and return the parsed result.
    Handles 200 success and non-422 errors. Does NOT handle 422 — the
    caller is responsible for that (to allow the retry logic to work).

    Returns dict: success (bool), data (dict|None), error (str)
    """
    encoded = requests.utils.quote(description, safe="")
    url     = f"{MUTALYZER_API}/normalize/{encoded}"

    try:
        resp = requests.get(url, timeout=20)
        if resp.status_code == 200:
            return {"success": True, "status": 200, "data": resp.json(), "error": ""}
        else:
            try:
                body = resp.json()
            except Exception:
                body = {}
            return {"success": False, "status": resp.status_code, "data": body,
                    "error": f"HTTP {resp.status_code}"}

    except requests.Timeout:
        return {"success": False, "status": None, "data": {},
                "error": "Mutalyzer request timed out (>20s)."}
    except requests.ConnectionError as e:
        return {"success": False, "status": None, "data": {},
                "error": f"Could not connect to Mutalyzer: {e}"}
    except requests.RequestException as e:
        return {"success": False, "status": None, "data": {}, "error": str(e)}


def _extract_mutalyzer_result(data: dict, fallback_description: str) -> dict:
    """
    Parse a successful Mutalyzer 200 response into our standard result dict.
    """
    result = {
        "valid": True,
        "normalized": data.get("normalized_description", fallback_description),
        "protein": "",
        "all_hgvs": [],
        "error": "",
    }

    protein = data.get("protein", {}) or {}
    result["protein"] = protein.get("description", "")

    hgvs_set = {result["normalized"]}
    if result["protein"]:
        hgvs_set.add(result["protein"])
    for eq in (data.get("equivalent_descriptions") or {}).values():
        for item in (eq if isinstance(eq, list) else [eq]):
            if isinstance(item, str):
                hgvs_set.add(item)
            elif isinstance(item, dict):
                desc = item.get("description", "")
                if desc:
                    hgvs_set.add(desc)

    result["all_hgvs"] = [h for h in hgvs_set if h]
    return result


def query_mutalyzer(gene: str, hgvs: str) -> dict:
    """
    Normalize a variant using Mutalyzer 3.

    Endpoint: GET /api/normalize/{description}
    The description is a URL PATH SEGMENT — not a query parameter.

    Strategy (two-pass):
      Pass 1 — Send GENE:HGVS (e.g. 'LRRK2:c.6055G>A') directly.
                Mutalyzer will return 422 for a gene symbol reference,
                but the 422 body contains the correct MANE Select /
                RefSeq Select descriptions under custom.errors[].options.

      Pass 2 — Parse the 422 to pick the best description
                (preferring GRCH38 MANE Select), then retry /normalize
                with that corrected description.

    This avoids a separate /gene_to_transcripts round-trip and uses
    Mutalyzer's own recommendation for the canonical transcript.

    Returns dict: valid, normalized, protein, all_hgvs, error
    """
    failed = {
        "valid": False, "normalized": "", "protein": "",
        "all_hgvs": [], "error": ""
    }

    # ── Pass 1: try with gene symbol directly ────────────────────────────────
    gene_description = f"{gene}:{hgvs}"
    attempt = _normalize_description(gene_description)

    if attempt["success"]:
        # Gene symbol worked directly (unlikely but possible in future versions)
        return _extract_mutalyzer_result(attempt["data"], gene_description)

    if attempt["status"] != 422:
        # A non-422 error (404, timeout, etc.) — nothing to retry
        failed["error"] = attempt["error"]
        return failed

    # ── Pass 2: parse 422, extract best description, retry ───────────────────
    err_body         = attempt["data"]
    best_description = _best_description_from_422(err_body)

    if not best_description:
        failed["error"] = (
            f"Mutalyzer returned 422 for '{gene_description}' but no usable "
            f"transcript options were found in the error response."
        )
        return failed

    print(f"  Mutalyzer suggested: {best_description} — retrying ...")
    retry = _normalize_description(best_description)

    if retry["success"]:
        return _extract_mutalyzer_result(retry["data"], best_description)

    # Retry also failed
    failed["error"] = (
        f"Mutalyzer retry with '{best_description}' failed: {retry['error']}"
    )
    return failed


# ── VariantValidator (fallback) ───────────────────────────────────────────────

def query_variantvalidator(gene: str, hgvs: str) -> dict:
    """
    Normalize a variant using the VariantValidator REST API.

    Endpoint:
      GET /VariantValidator/variantvalidator/{genome_build}/{variant}/select
      where {variant} = GENE:HGVS  e.g. LRRK2:c.6055G>A

    'select' tells VV to automatically pick the canonical transcript.

    Returns dict: valid, normalized, protein, all_hgvs, error
    """
    result = {
        "valid": False, "normalized": "", "protein": "",
        "all_hgvs": [], "error": ""
    }

    variant_str = f"{gene}:{hgvs}"
    url = (
        f"{VARIANTVALIDATOR_API}/{GENOME_BUILD}"
        f"/{requests.utils.quote(variant_str, safe='')}"
        f"/select"
    )

    try:
        resp = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=30,
        )

        if resp.status_code == 200:
            data    = resp.json()
            hgvs_set = set()

            for key, val in data.items():
                if key in ("flag", "metadata") or not isinstance(val, dict):
                    continue

                hgvs_c = val.get("hgvs_transcript_variant", "")
                if hgvs_c:
                    hgvs_set.add(hgvs_c)
                    if not result["normalized"]:
                        result["normalized"] = hgvs_c

                protein_block = val.get("hgvs_predicted_protein_consequence") or {}
                for pkey in ("tlr", "slr"):
                    pval = protein_block.get(pkey, "")
                    if pval and "Non-coding" not in pval:
                        hgvs_set.add(pval)
                        if not result["protein"]:
                            result["protein"] = pval

                hgvs_g  = val.get("hgvs_genomic_description", "")
                hgvs_ng = val.get("hgvs_refseqgene_variant", "")
                for h in (hgvs_g, hgvs_ng):
                    if h:
                        hgvs_set.add(h)

            if result["normalized"]:
                result["valid"]    = True
                result["all_hgvs"] = [h for h in hgvs_set if h]
            else:
                result["error"] = (
                    f"VariantValidator returned no normalized description. "
                    f"Flag: {data.get('flag', 'n/a')}"
                )
        else:
            result["error"] = f"HTTP {resp.status_code}: {resp.text[:300]}"

    except requests.Timeout:
        result["error"] = "VariantValidator request timed out (>30s)."
    except requests.RequestException as e:
        result["error"] = str(e)

    return result


# ── Ensembl VEP (protein consequence fallback) ────────────────────────────────

def query_ensembl_vep(gene: str, hgvs: str) -> dict:
    """
    Use Ensembl VEP to get a protein consequence when the normalizers
    don't return one.

    Endpoint: GET /vep/human/hgvs/{GENE:HGVS}
    Docs: https://rest.ensembl.org/documentation/info/vep_hgvs_get

    Returns dict: valid, protein, error
    """
    result = {"valid": False, "protein": "", "error": ""}

    notation = f"{gene}:{hgvs}"
    url      = f"{ENSEMBL_API}/vep/human/hgvs/{requests.utils.quote(notation, safe='')}"

    try:
        resp = requests.get(
            url,
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
        if resp.status_code == 200:
            data = resp.json()
            for hit in data:
                for tc in hit.get("transcript_consequences", []):
                    hgvsp = tc.get("hgvsp", "")
                    if hgvsp:
                        result["valid"]   = True
                        result["protein"] = hgvsp
                        return result
            result["error"] = "No protein consequence found in VEP response."
        else:
            result["error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"

    except requests.Timeout:
        result["error"] = "Ensembl VEP request timed out."
    except requests.RequestException as e:
        result["error"] = str(e)

    return result


# ── ClinVar ───────────────────────────────────────────────────────────────────

def query_clinvar(gene: str, hgvs: str) -> dict:
    """
    Search ClinVar for the variant and collect all known names/aliases.
    Uses NCBI E-utilities: esearch -> esummary.
    """
    result = {"found": False, "clinvar_id": "", "title": "", "aliases": []}

    change = re.sub(r'^[cgpnm]\.', '', hgvs)
    query  = f"{gene}[gene] AND {change}"

    params = {
        "db": "clinvar", "term": query,
        "retmax": 5, "retmode": "json", "email": NCBI_EMAIL,
    }
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY

    try:
        search_resp = requests.get(
            f"{CLINVAR_API}/esearch.fcgi", params=params, timeout=15
        )
        search_resp.raise_for_status()
        ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return result

        clinvar_id           = ids[0]
        result["found"]      = True
        result["clinvar_id"] = clinvar_id

        time.sleep(0.34)   # NCBI rate-limit courtesy pause

        summary_params = {
            "db": "clinvar", "id": clinvar_id,
            "retmode": "json", "email": NCBI_EMAIL,
        }
        if NCBI_API_KEY:
            summary_params["api_key"] = NCBI_API_KEY

        summary_resp = requests.get(
            f"{CLINVAR_API}/esummary.fcgi", params=summary_params, timeout=15
        )
        summary_resp.raise_for_status()
        doc = summary_resp.json().get("result", {}).get(str(clinvar_id), {})

        result["title"] = doc.get("title", "")

        aliases = set()
        for var in doc.get("variation_set", []):
            for name_entry in var.get("variant_name_list", []):
                name = name_entry.get("name", "")
                if name:
                    aliases.add(name)
            for f in ("cdna_change", "protein_change"):
                val = var.get(f, "")
                if val:
                    aliases.add(val)
        for alias in doc.get("aliases", []):
            aliases.add(alias)

        result["aliases"] = sorted(aliases)

    except requests.RequestException as e:
        result["title"] = f"Request error: {e}"

    return result


# ── Term extraction helpers ───────────────────────────────────────────────────

def _short_change(hgvs_or_alias: str) -> str:
    """Strip transcript prefix: 'NM_198578.4:c.6055G>A' -> 'c.6055G>A'"""
    if ":" in hgvs_or_alias:
        return hgvs_or_alias.split(":", 1)[1].strip()
    return hgvs_or_alias.strip()


_AA3TO1 = {
    "Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C",
    "Gln": "Q", "Glu": "E", "Gly": "G", "His": "H", "Ile": "I",
    "Leu": "L", "Lys": "K", "Met": "M", "Phe": "F", "Pro": "P",
    "Ser": "S", "Thr": "T", "Trp": "W", "Tyr": "Y", "Val": "V",
    "Ter": "*", "Sec": "U", "Pyl": "O",
}

def _three_to_one_aa(protein_change: str) -> str:
    """Convert p.Gly2019Ser -> G2019S, or None if pattern not matched."""
    m = re.match(r'p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2}|\*|=)', protein_change)
    if not m:
        return None
    return (
        f"{_AA3TO1.get(m.group(1), '?')}"
        f"{m.group(2)}"
        f"{_AA3TO1.get(m.group(3), m.group(3))}"
    )


def build_api_terms(
    gene: str,
    all_hgvs: list[str],
    protein: str,
    clinvar: dict,
) -> list[str]:
    """
    Assemble all verified terms from the normalizer(s) + ClinVar.
    Includes both full HGVS forms and short forms (without transcript prefix).
    """
    terms = {gene}

    for h in all_hgvs:
        terms.add(h)                  # full:  NM_198578.4:c.6055G>A
        terms.add(_short_change(h))   # short: c.6055G>A

    if protein:
        short = _short_change(protein)
        terms.add(short)              # p.Gly2019Ser
        one_letter = _three_to_one_aa(short)
        if one_letter:
            terms.add(one_letter)     # G2019S

    for alias in clinvar.get("aliases", []):
        terms.add(alias)
        terms.add(_short_change(alias))

    return sorted(t for t in terms if t)


# ── Ollama enrichment ─────────────────────────────────────────────────────────

def query_ollama(gene: str, hgvs: str, known_terms: list[str]) -> list[str]:
    """
    Ask a local Ollama model for informal typographic variants of the
    nucleotide change (e.g. '6055G->A', '6055G/A') not found in databases.

    The LLM is grounded with verified terms so it enriches rather than invents.
    """
    change = _short_change(hgvs)

    prompt = f"""You are a bioinformatics assistant helping build literature search strings.

A researcher wants to search for papers about the genetic variant:
  Gene: {gene}
  HGVS coding change: {change}

We already have these verified terms from official databases:
{json.dumps(known_terms, indent=2)}

Your task: generate ONLY the informal typographic variants of the nucleotide
change "{change}" that researchers commonly write in free text in published papers.
These are NOT official HGVS — they are shorthand writing styles, such as:
  - Replacing ">" with "->", "-->", "/", "to"
  - Omitting the "c." prefix
  - Positional shorthand like "6055G>A"

Rules:
- Output ONLY a JSON array of strings. No explanation, no markdown, no preamble.
- Do NOT repeat terms already in the verified list above.
- Do NOT invent protein names or gene synonyms — only typographic nucleotide variants.
- Maximum 8 terms.

Example output for c.6055G>A:
["6055G>A", "6055G->A", "6055G-->A", "6055G/A", "6055GtoA"]
"""

    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "").strip()

        raw   = re.sub(r'^```[a-z]*\n?', '', raw)
        raw   = re.sub(r'\n?```$', '', raw)
        match = re.search(r'\[.*?\]', raw, re.DOTALL)
        if match:
            terms = json.loads(match.group())
            return [str(t).strip() for t in terms if str(t).strip()]

    except requests.ConnectionError:
        print("  [Ollama] Could not connect - is Ollama running? Skipping enrichment.")
    except Exception as e:
        print(f"  [Ollama] Error: {e}. Skipping enrichment.")

    return []


# ── Search string assembler ───────────────────────────────────────────────────

def assemble_search_string(gene: str, variant_terms: list[str]) -> str:
    """
    Build a Boolean search string for Google Scholar or PubMed.
    Format: "GENE" AND ("term1" OR "term2" OR ...)
    The gene is always required (AND); variant forms are alternatives (OR).
    """
    non_gene = [t for t in variant_terms if t.lower() != gene.lower()]
    if not non_gene:
        return f'"{gene}"'
    inner = " OR ".join(f'"{t}"' for t in non_gene)
    return f'"{gene}" AND ({inner})'


# ── Main pipeline ─────────────────────────────────────────────────────────────

def generate_search_string(
    variant_input: str,
    use_ollama: bool = True,
) -> SearchStringResult:
    """
    Full generation pipeline.

    Args:
        variant_input:  e.g. "LRRK2 c.6055G>A"
        use_ollama:     set False to skip the Ollama enrichment step

    Returns:
        SearchStringResult with generated search string and full audit trail.
    """
    gene, hgvs = parse_input(variant_input)

    result = SearchStringResult(
        input_variant=variant_input,
        gene=gene,
        hgvs=hgvs,
    )

    # ── Step 1: Mutalyzer (primary) ──────────────────────────────────────────
    print(f"[1/4] Querying Mutalyzer for: {gene} {hgvs} ...")
    muta = query_mutalyzer(gene, hgvs)
    result.muta_valid      = muta["valid"]
    result.muta_normalized = muta["normalized"]
    result.muta_protein    = muta["protein"]
    result.muta_all_hgvs   = muta["all_hgvs"]
    result.muta_error      = muta["error"]

    all_hgvs = muta["all_hgvs"]
    protein  = muta["protein"]

    # ── Step 1b: VariantValidator (fallback if Mutalyzer failed) ────────────
    if not muta["valid"]:
        print(f"  Mutalyzer failed: {muta['error'][:100]}")
        print(f"  Falling back to VariantValidator ...")
        result.vv_used = True
        vv = query_variantvalidator(gene, hgvs)
        result.vv_valid      = vv["valid"]
        result.vv_normalized = vv["normalized"]
        result.vv_protein    = vv["protein"]
        result.vv_all_hgvs   = vv["all_hgvs"]
        result.vv_error      = vv["error"]

        if vv["valid"]:
            all_hgvs = vv["all_hgvs"]
            protein  = vv["protein"]
        else:
            print(f"  VariantValidator also failed: {vv['error'][:80]}")
            print("  Continuing with ClinVar only.")

    # ── Step 1c: Ensembl VEP (fallback if no protein consequence yet) ────────
    if not protein:
        print(f"  No protein consequence found, trying Ensembl VEP ...")
        result.vep_used = True
        vep = query_ensembl_vep(gene, hgvs)
        result.vep_valid   = vep["valid"]
        result.vep_protein = vep["protein"]
        result.vep_error   = vep["error"]
        if vep["valid"]:
            protein = vep["protein"]
        else:
            print(f"  Ensembl VEP: {vep['error'][:80]}")

    # ── Step 2: ClinVar ──────────────────────────────────────────────────────
    print(f"[2/4] Querying ClinVar for aliases ...")
    cv = query_clinvar(gene, hgvs)
    result.clinvar_found   = cv["found"]
    result.clinvar_id      = cv["clinvar_id"]
    result.clinvar_title   = cv["title"]
    result.clinvar_aliases = cv["aliases"]

    if not cv["found"]:
        print("  Warning: Variant not found in ClinVar.")

    # ── Step 3: Build verified API terms ─────────────────────────────────────
    print(f"[3/4] Assembling verified terms ...")
    result.api_terms = build_api_terms(gene, all_hgvs, protein, cv)

    # ── Step 4: Ollama enrichment ─────────────────────────────────────────────
    if use_ollama:
        print(f"[4/4] Enriching with Ollama ({OLLAMA_MODEL}) for typographic variants ...")
        ollama_terms   = query_ollama(gene, hgvs, result.api_terms)
        existing_lower = {t.lower() for t in result.api_terms}
        result.ollama_terms = [
            t for t in ollama_terms if t.lower() not in existing_lower
        ]
    else:
        print("[4/4] Skipping Ollama enrichment (use_ollama=False).")

    # ── Step 5: Combine, deduplicate, assemble ────────────────────────────────
    seen, deduped = set(), []
    for t in result.api_terms + result.ollama_terms:
        key = t.lower().strip()
        if key not in seen:
            seen.add(key)
            deduped.append(t)

    result.all_terms     = deduped
    result.search_string = assemble_search_string(gene, deduped)

    return result

"""
if __name__ == "__main__":

    result = generate_search_string(
        variant_input="LRRK2 c.6055G>A",
        use_ollama=True,       # set False if Ollama is not running
    )
    print(result.summary())

    # ── Batch example (uncomment to use) ─────────────────────────────────────
    # variants = [
    #     "BRCA1 c.5266dupC",
    #     "CFTR c.1521_1523delCTT",
    #     "BRAF c.1799T>A",
    # ]
    # for v in variants:
    #     r = generate_search_string(v, use_ollama=True)
    #     print(r.search_string)
    #     print()
"""