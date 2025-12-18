"""
Optimized Research Pipeline - Parallel Search & Bulk Extraction
================================================================
New 5-Step Pipeline:
1. Generate ALL search queries in single LLM call
2. Open all queries in parallel browser tabs (Google + DDG alternating)
3. Scrape & deduplicate all results
4. Extract ALL fields in single LLM call
5. Validate & targeted retry only for missing fields
"""

from llm_engine import LLMEngine
from browser_engine import ResearchBrowser
from data_models import CompanyProfile, KeyPerson, GraphNode, GraphEdge
import config
import json
import time
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse


class QueryGenerator:
    """
    Step 1: Generate W/H format search queries for each individual field.
    Uses What, Who, Where, When, How, Why question formats for better accuracy.
    """
    
    # Define all required fields from Topic1_Output_Format.xlsx
    EXCEL_FIELDS = [
        "long_description",
        "short_description", 
        "sic_code",
        "sic_text",
        "sub_industry",
        "industry",
        "sector",
        "tags"
    ]
    
    def __init__(self, llm: LLMEngine):
        self.llm = llm
    
    def generate_all_queries(self, domain: str, required_fields: List[str] = None) -> Dict[str, Dict[str, str]]:
        """
        Generates W/H format search queries for ALL individual fields.
        Each field gets separate dedicated queries for maximum accuracy.
        Returns: { "field_name": {"google": "query", "ddg": "query"}, ... }
        """
        
        # Use Excel fields as base, can be extended
        fields_to_query = required_fields or self.EXCEL_FIELDS
        
        # Generate queries using W/H question format
        queries = {}
        
        for field in fields_to_query:
            queries[field] = self._generate_wh_query(domain, field)
        
        return queries
    
    def _generate_wh_query(self, domain: str, field: str) -> Dict[str, str]:
        """
        Generate W/H (What, Who, Where, When, How, Why) format queries for a specific field.
        Returns {"google": "query", "ddg": "query"}
        """
        
        # Company name extraction for natural queries
        company_name = domain.split('.')[0].replace('-', ' ').replace('_', ' ')
        
        # W/H Question Templates for each field type
        query_templates = {
            # ===== DESCRIPTION FIELDS =====
            "long_description": {
                "google": f'"{domain}" OR "{company_name}" "about us" OR "who we are" OR "company overview" OR "our mission"',
                "ddg": f"What does {company_name} do? {domain} company overview mission about us"
            },
            "short_description": {
                "google": f'"{domain}" company description tagline "what we do"',
                "ddg": f"What is {company_name}? {domain} brief company description"
            },
            
            # ===== SIC CODE FIELDS =====
            "sic_code": {
                "google": f'"{domain}" OR "{company_name}" SIC code number classification site:companieshouse.gov.uk OR site:endole.co.uk OR site:duedil.com',
                "ddg": f"What is the SIC code for {company_name}? {domain} standard industrial classification number"
            },
            "sic_text": {
                "google": f'"{domain}" SIC description "industrial classification" business activity type',
                "ddg": f"What SIC classification does {company_name} have? {domain} industrial classification description"
            },
            
            # ===== INDUSTRY FIELDS =====
            "industry": {
                "google": f'"{domain}" OR "{company_name}" "industry" OR "business sector" -jobs -careers',
                "ddg": f"What industry is {company_name} in? {domain} primary business industry type"
            },
            "sub_industry": {
                "google": f'"{domain}" sub-industry OR "niche" OR "specialization" OR "vertical" market segment',
                "ddg": f"What sub-industry does {company_name} operate in? {domain} business niche specialization"
            },
            "sector": {
                "google": f'"{domain}" OR "{company_name}" "sector" technology OR finance OR healthcare OR retail market',
                "ddg": f"What sector is {company_name} part of? {domain} business sector category"
            },
            
            # ===== TAGS/KEYWORDS =====
            "tags": {
                "google": f'"{domain}" keywords OR services OR solutions OR products OR "what we offer" features',
                "ddg": f"What are the main services and keywords for {company_name}? {domain} products solutions features"
            },
            
            # ===== ADDITIONAL COMMON FIELDS =====
            "products_services": {
                "google": f'"{domain}" "products" OR "services" OR "solutions" OR "offerings" "what we offer"',
                "ddg": f"What products and services does {company_name} offer? {domain} offerings solutions"
            },
            "key_people": {
                "google": f'site:linkedin.com "{company_name}" CEO OR CTO OR founder OR director OR "managing director"',
                "ddg": f"Who is the CEO of {company_name}? {domain} leadership team executives founders"
            },
            "locations": {
                "google": f'"{domain}" "headquarters" OR "office" OR "location" OR "address" contact',
                "ddg": f"Where is {company_name} located? {domain} headquarters office address location"
            },
            "contact_info": {
                "google": f'"{domain}" "contact us" OR "phone" OR "email" OR "call us" support',
                "ddg": f"How to contact {company_name}? {domain} phone number email address contact"
            },
            "tech_stack": {
                "google": f'"{domain}" OR "{company_name}" technology OR stack OR "built with" OR engineering OR platform',
                "ddg": f"What technology does {company_name} use? {domain} tech stack tools platforms"
            },
            "certifications": {
                "google": f'"{domain}" ISO OR GDPR OR SOC2 OR certification OR compliance OR accredited',
                "ddg": f"What certifications does {company_name} have? {domain} ISO GDPR SOC2 compliance"
            },
            "social_media": {
                "google": f'"{company_name}" linkedin OR twitter OR facebook OR instagram official',
                "ddg": f"What are {company_name} social media profiles? {domain} linkedin twitter facebook"
            },
            "year_founded": {
                "google": f'"{domain}" OR "{company_name}" "founded" OR "established" OR "since" year history',
                "ddg": f"When was {company_name} founded? {domain} established year history"
            },
            "company_size": {
                "google": f'"{domain}" employees OR "team size" OR headcount OR staff site:linkedin.com',
                "ddg": f"How many employees does {company_name} have? {domain} company size team"
            },
            "registration_number": {
                "google": f'"{company_name}" "company number" OR "registration" site:companieshouse.gov.uk OR site:endole.co.uk',
                "ddg": f"What is {company_name} company registration number? {domain} companies house"
            },
            "vat_number": {
                "google": f'"{domain}" "VAT" OR "VAT number" OR "VAT registered" GB',
                "ddg": f"What is {company_name} VAT number? {domain} VAT registration"
            }
        }
        
        # Return specific template or generate generic W/H query
        if field in query_templates:
            return query_templates[field]
        else:
            # Generic W/H fallback for unknown fields
            return {
                "google": f'"{domain}" "{field.replace("_", " ")}"',
                "ddg": f"What is the {field.replace('_', ' ')} of {company_name}? {domain}"
            }
    
    def generate_retry_queries(self, domain: str, missing_field: str, attempt: int) -> Dict[str, str]:
        """
        Generate alternative queries for retry attempts on missing fields.
        Uses different strategies based on attempt number.
        """
        company_name = domain.split('.')[0].replace('-', ' ').replace('_', ' ')
        
        retry_strategies = {
            1: {  # Attempt 1: More specific with site operators
                "google": self._get_site_specific_query(domain, company_name, missing_field),
                "ddg": f"{company_name} {missing_field.replace('_', ' ')} official information"
            },
            2: {  # Attempt 2: Try business registries
                "google": f'"{company_name}" {missing_field.replace("_", " ")} site:companieshouse.gov.uk OR site:endole.co.uk OR site:opencorporates.com',
                "ddg": f"{domain} {missing_field.replace('_', ' ')} business registry company data"
            },
            3: {  # Attempt 3: LinkedIn/Crunchbase focus
                "google": f'"{company_name}" {missing_field.replace("_", " ")} site:linkedin.com OR site:crunchbase.com OR site:zoominfo.com',
                "ddg": f"{company_name} {missing_field.replace('_', ' ')} linkedin crunchbase profile"
            },
            4: {  # Attempt 4: News/Press releases
                "google": f'"{company_name}" {missing_field.replace("_", " ")} news OR press OR announcement',
                "ddg": f"{company_name} {missing_field.replace('_', ' ')} latest news press release"
            },
            5: {  # Attempt 5: Broad search with synonyms
                "google": self._get_synonym_query(domain, company_name, missing_field),
                "ddg": f"everything about {company_name} {domain} company information"
            }
        }
        
        # Get strategy for this attempt (cycle if beyond 5)
        attempt_key = ((attempt - 1) % 5) + 1
        return retry_strategies.get(attempt_key, retry_strategies[1])
    
    def _get_site_specific_query(self, domain: str, company_name: str, field: str) -> str:
        """Get site-specific Google query based on field type."""
        site_mappings = {
            "sic_code": f'"{company_name}" SIC site:companieshouse.gov.uk',
            "sic_text": f'"{company_name}" industrial classification site:gov.uk',
            "key_people": f'"{company_name}" CEO OR founder site:linkedin.com',
            "industry": f'"{company_name}" industry site:crunchbase.com OR site:linkedin.com',
            "locations": f'"{domain}" office location site:google.com/maps',
            "contact_info": f'site:{domain} contact OR phone OR email',
            "certifications": f'"{company_name}" certified ISO site:iso.org OR site:bsigroup.com'
        }
        return site_mappings.get(field, f'"{domain}" {field.replace("_", " ")} -jobs -careers')
    
    def _get_synonym_query(self, domain: str, company_name: str, field: str) -> str:
        """Get query with field synonyms for broader search."""
        synonym_map = {
            "long_description": "overview OR mission OR about OR description",
            "short_description": "tagline OR summary OR what we do",
            "sic_code": "SIC OR NAICS OR industry code",
            "industry": "industry OR sector OR market OR vertical",
            "sub_industry": "niche OR specialization OR focus area",
            "tags": "keywords OR services OR products OR solutions",
            "key_people": "leadership OR executives OR founders OR team",
            "contact_info": "phone OR email OR contact OR reach us"
        }
        synonyms = synonym_map.get(field, field.replace("_", " "))
        return f'"{domain}" ({synonyms})'


class ParallelBrowserEngine:
    """Step 2 & 3: Execute parallel searches and deduplicated scraping."""
    
    def __init__(self, browser: ResearchBrowser, log_callback=None):
        self.browser = browser
        self.log_callback = log_callback
        self.all_urls: Dict[str, str] = {}  # url -> field that found it
        self.scraped_content: Dict[str, str] = {}  # url -> content
        self.search_results: Dict[str, str] = {}  # field -> SERP text
    
    def _log(self, message: str):
        if self.log_callback:
            self.log_callback(f"🌐 Browser: {message}")
        else:
            print(f"🌐 Browser: {message}")
    
    def execute_parallel_searches(self, queries: Dict[str, Dict[str, str]]) -> Tuple[Dict[str, str], List[str]]:
        """
        Opens all searches in parallel tabs (alternating Google/DDG).
        Returns: (field_serp_texts, all_unique_urls)
        """
        self._log(f"🚀 Starting parallel search for {len(queries)} fields...")
        
        tab_info = []  # List of (tab_index, field, engine, query)
        current_tab = 0
        
        # Prepare all tabs - alternate between Google and DDG
        fields = list(queries.keys())
        for i, field in enumerate(fields):
            query_set = queries[field]
            
            # Alternate: even index starts with Google, odd with DDG
            if i % 2 == 0:
                engines = [("google", query_set.get("google", "")), ("ddg", query_set.get("ddg", ""))]
            else:
                engines = [("ddg", query_set.get("ddg", "")), ("google", query_set.get("google", ""))]
            
            for engine, query in engines:
                if query:
                    tab_info.append((current_tab, field, engine, query))
                    current_tab += 1
        
        self._log(f"📑 Opening {len(tab_info)} search tabs...")
        
        # Open all tabs first (without waiting for results)
        for idx, (tab_idx, field, engine, query) in enumerate(tab_info):
            if idx == 0:
                # First tab - use existing window
                self._execute_search(engine, query, field)
            else:
                # New tabs
                self.browser.open_new_tab()
                self._execute_search(engine, query, field)
            
            # Small delay to prevent rate limiting
            time.sleep(0.3)
        
        self._log(f"⏳ Waiting for all tabs to load...")
        time.sleep(2)  # Let all tabs finish loading
        
        # Now collect results from all tabs
        all_urls = []
        handles = self.browser.driver.window_handles
        
        for idx, (tab_idx, field, engine, query) in enumerate(tab_info):
            if idx < len(handles):
                self.browser.driver.switch_to.window(handles[idx])
                time.sleep(0.5)
                
                # Get SERP text
                try:
                    serp_text = self.browser.driver.find_element("tag name", "body").text
                    existing = self.search_results.get(field, "")
                    self.search_results[field] = f"{existing}\n\n--- {engine.upper()} RESULTS ---\n{serp_text[:5000]}"
                except:
                    pass
                
                # Extract URLs
                urls = self._extract_urls_from_current_page(engine)
                for url in urls:
                    if url not in self.all_urls:
                        self.all_urls[url] = field
                    all_urls.append(url)
                
                self._log(f"✓ Tab {idx+1}: {engine.upper()} for '{field}' - Found {len(urls)} URLs")
        
        # Close extra tabs, keep only first
        while len(self.browser.driver.window_handles) > 1:
            self.browser.driver.switch_to.window(self.browser.driver.window_handles[-1])
            self.browser.driver.close()
        self.browser.driver.switch_to.window(self.browser.driver.window_handles[0])
        
        unique_urls = list(set(all_urls))
        self._log(f"📊 Total unique URLs found: {len(unique_urls)}")
        
        return self.search_results, unique_urls
    
    def _execute_search(self, engine: str, query: str, field: str):
        """Execute search on current tab without waiting for full load."""
        try:
            if engine == "google":
                self.browser.driver.get(f"https://www.google.com/search?q={query.replace(' ', '+')}")
            else:
                self.browser.driver.get(f"https://duckduckgo.com/?q={query.replace(' ', '+')}")
        except Exception as e:
            self._log(f"⚠️ Search error for {field}: {e}")
    
    def _extract_urls_from_current_page(self, engine: str) -> List[str]:
        """Extract result URLs from current search page."""
        urls = []
        try:
            if engine == "google":
                elements = self.browser.driver.find_elements("css selector", "div.g a")
                for el in elements[:6]:
                    try:
                        href = el.get_attribute("href")
                        if href and "google.com" not in href and href.startswith("http"):
                            urls.append(href)
                    except:
                        continue
            else:  # DuckDuckGo
                elements = self.browser.driver.find_elements("css selector", "a[data-testid='result-title-a']")
                for el in elements[:6]:
                    try:
                        href = el.get_attribute("href")
                        if href and href.startswith("http"):
                            urls.append(href)
                    except:
                        continue
        except Exception as e:
            self._log(f"URL extraction error: {e}")
        
        return urls
    
    def scrape_deduplicated_urls(self, urls: List[str], max_urls: int = 10) -> str:
        """
        Scrapes unique URLs and returns combined content.
        Each URL is only scraped once regardless of how many fields found it.
        """
        self._log(f"📄 Scraping top {min(len(urls), max_urls)} unique URLs...")
        
        combined_content = ""
        scraped_count = 0
        
        # Skip social media and irrelevant domains
        skip_domains = ["facebook.com", "twitter.com", "instagram.com", "youtube.com", "tiktok.com"]
        
        for url in urls[:max_urls * 2]:  # Check more in case some are skipped
            if scraped_count >= max_urls:
                break
            
            # Skip already scraped
            if url in self.scraped_content:
                combined_content += f"\n\n--- CACHED: {url} ---\n{self.scraped_content[url]}"
                continue
            
            # Skip social media
            domain = urlparse(url).netloc.lower()
            if any(skip in domain for skip in skip_domains):
                continue
            
            try:
                self._log(f"  → Scraping: {url[:60]}...")
                content = self.browser.scrape_text(url)
                if content:
                    self.scraped_content[url] = content
                    combined_content += f"\n\n--- SOURCE: {url} ---\n{content}"
                    scraped_count += 1
            except Exception as e:
                self._log(f"  ⚠️ Failed: {url[:40]}... ({e})")
        
        self._log(f"✅ Successfully scraped {scraped_count} pages")
        return combined_content


class BulkExtractor:
    """
    Step 4: Extract ALL fields in a single LLM call.
    Prioritizes Excel output format fields.
    """
    
    def __init__(self, llm: LLMEngine):
        self.llm = llm
    
    def extract_all_fields(self, domain: str, search_results: Dict[str, str], 
                           scraped_content: str, required_fields: List[str]) -> Dict:
        """
        Extracts all required fields from combined context in one LLM call.
        Focuses on Excel output format fields first.
        """
        
        # Build context from search results - prioritize by field
        serp_context = "\n".join([f"=== {field.upper()} SEARCH ===\n{text[:4000]}" 
                                   for field, text in search_results.items()])
        
        company_name = domain.split('.')[0].replace('-', ' ').replace('_', ' ')
        
        prompt = f"""You are an expert business data extraction AI. Extract comprehensive company information from the provided data.

TARGET COMPANY: {domain} ({company_name})

=== SEARCH ENGINE RESULTS ===
{serp_context[:15000]}

=== WEBSITE CONTENT ===
{scraped_content[:25000]}

=== PRIMARY EXTRACTION TASK (EXCEL OUTPUT FIELDS) ===
These are the MOST IMPORTANT fields - extract with highest priority:

1. "long_description" (CRITICAL): 
   - A comprehensive 2-3 paragraph description
   - What the company does, their mission, services, target market
   - Include any acronym meanings if applicable

2. "short_description" (CRITICAL):
   - A brief one-sentence description or tagline
   - Maximum 200 characters

3. "sic_code" (IMPORTANT):
   - Standard Industrial Classification code number
   - Format: 5-digit number (e.g., "62020")
   - UK companies often have this on Companies House

4. "sic_text" (IMPORTANT):
   - The text description for the SIC code
   - E.g., "Information technology consultancy activities"

5. "sub_industry" (IMPORTANT):
   - Specific sub-industry or niche
   - E.g., "Cybersecurity", "E-commerce", "Data Analytics"

6. "industry" (CRITICAL):
   - Primary industry category
   - E.g., "Information Technology", "Healthcare", "Finance"

7. "sector" (CRITICAL):
   - Business sector
   - E.g., "Technology", "Financial Services", "Retail"

8. "tags" (IMPORTANT):
   - Array of relevant keywords describing products/services
   - E.g., ["cloud computing", "ai solutions", "data security"]

=== REQUIRED OUTPUT FORMAT (JSON) ===
Return ONLY valid JSON with these fields:

{{
    "long_description": "Comprehensive 2-3 paragraph company description...",
    "short_description": "One-sentence company tagline/summary",
    "sic_code": "62020",
    "sic_text": "Information technology consultancy activities",
    "sub_industry": "Specific niche/sub-industry",
    "industry": "Primary Industry Category",
    "sector": "Business Sector",
    "tags": ["keyword1", "keyword2", "keyword3"],
    "description_long": "Same as long_description for compatibility",
    "description_short": "Same as short_description for compatibility"
}}

=== EXTRACTION RULES ===
1. Extract REAL data ONLY - never make up information
2. If a field cannot be determined from the data, use empty string "" or empty array []
3. Cross-reference multiple sources for accuracy
4. For UK companies, look for SIC codes from Companies House data
5. For tags, include: service types, technology keywords, industry terms
6. Prefer official website content over third-party sources

Return ONLY the JSON. No markdown formatting, no explanations."""

        result = self.llm.generate_json(prompt)
        
        # Ensure backwards compatibility - copy fields both ways
        if result:
            # Map long_description <-> description_long
            if result.get("long_description") and not result.get("description_long"):
                result["description_long"] = result["long_description"]
            elif result.get("description_long") and not result.get("long_description"):
                result["long_description"] = result["description_long"]
            
            # Map short_description <-> description_short
            if result.get("short_description") and not result.get("description_short"):
                result["description_short"] = result["short_description"]
            elif result.get("description_short") and not result.get("short_description"):
                result["short_description"] = result["description_short"]
        
        return result if result else {}


class ValidationEngine:
    """
    Step 5: Validate extracted data and identify missing fields.
    Based on Topic1_Output_Format.xlsx required fields.
    """
    
    # Fields from Topic1_Output_Format.xlsx - ALL are important
    EXCEL_REQUIRED_FIELDS = [
        "long_description",  # -> description_long
        "short_description", # -> description_short
        "sic_code",
        "sic_text", 
        "sub_industry",
        "industry",
        "sector",
        "tags"
    ]
    
    # Field name mappings (Excel name -> internal name)
    FIELD_MAPPING = {
        "long_description": "description_long",
        "short_description": "description_short",
        "sic_code": "sic_code",
        "sic_text": "sic_text",
        "sub_industry": "sub_industry",
        "industry": "industry",
        "sector": "sector",
        "tags": "tags"
    }
    
    # Critical fields that MUST have data
    CRITICAL_FIELDS = ["long_description", "industry", "sector"]
    
    # Important fields (should have data, but not blocking)
    IMPORTANT_FIELDS = ["short_description", "sic_code", "sic_text", "sub_industry", "tags"]
    
    def __init__(self):
        pass
    
    def validate_extraction(self, data: Dict) -> Tuple[bool, List[str]]:
        """
        Validates extracted data against Excel required fields.
        Returns (is_sufficient, missing_fields_list).
        """
        missing_fields = []
        
        # Check ALL Excel required fields
        for excel_field in self.EXCEL_REQUIRED_FIELDS:
            internal_field = self.FIELD_MAPPING.get(excel_field, excel_field)
            value = data.get(internal_field) or data.get(excel_field)
            
            is_missing = False
            
            if not value:
                is_missing = True
            elif isinstance(value, str):
                # String fields - check if meaningful content
                cleaned = value.strip().lower()
                if len(cleaned) < 5 or cleaned in ["not found", "n/a", "unknown", "none", ""]:
                    is_missing = True
            elif isinstance(value, list):
                # List fields (like tags) - check if has items
                if len(value) == 0:
                    is_missing = True
            
            if is_missing:
                missing_fields.append(excel_field)
        
        # Determine if data is sufficient (critical fields present)
        critical_missing = [f for f in missing_fields if f in self.CRITICAL_FIELDS]
        is_sufficient = len(critical_missing) == 0
        
        return is_sufficient, missing_fields
    
    def get_field_priority(self, field: str) -> int:
        """Returns priority of field for retry ordering (1=highest)."""
        if field in self.CRITICAL_FIELDS:
            return 1
        elif field in self.IMPORTANT_FIELDS:
            return 2
        else:
            return 3
    
    def sort_missing_by_priority(self, missing_fields: List[str]) -> List[str]:
        """Sort missing fields by priority for retry order."""
        return sorted(missing_fields, key=self.get_field_priority)


class OptimizedResearchAgent:
    """
    Main orchestrator for the optimized 5-step pipeline.
    Uses Excel fields (Topic1_Output_Format.xlsx) as the source of truth.
    Implements configurable retry attempts for missing fields.
    """
    
    # Excel Output Fields - These are the actual required fields
    EXCEL_FIELDS = [
        "long_description",
        "short_description", 
        "sic_code",
        "sic_text",
        "sub_industry",
        "industry",
        "sector",
        "tags"
    ]
    
    def __init__(self, domain: str, log_callback=None):
        self.domain = domain
        self.log_callback = log_callback
        self.llm = LLMEngine()
        self.browser = ResearchBrowser()
        self.profile = CompanyProfile(name=domain.split('.')[0].title(), domain=domain)
        
        # Initialize components
        self.query_generator = QueryGenerator(self.llm)
        self.parallel_browser = ParallelBrowserEngine(self.browser, log_callback)
        self.bulk_extractor = BulkExtractor(self.llm)
        self.validator = ValidationEngine()
        
        # Retry configuration from config
        self.max_retries = config.MAX_RETRIES
    
    def _log(self, message: str):
        if self.log_callback:
            self.log_callback(f"🎯 Pipeline: {message}")
        else:
            print(f"🎯 Pipeline: {message}")
    
    def run_pipeline(self) -> CompanyProfile:
        """Execute the optimized 5-step pipeline with Excel fields."""
        
        self._log(f"═══════════════════════════════════════════════════")
        self._log(f"🚀 OPTIMIZED PIPELINE START: {self.domain}")
        self._log(f"═══════════════════════════════════════════════════")
        
        # ----- STEP 1: Generate W/H Queries for Each Excel Field -----
        self._log("📝 STEP 1: Generating W/H format queries for each field...")
        queries = self.query_generator.generate_all_queries(self.domain, self.EXCEL_FIELDS)
        self._log(f"   Generated {len(queries)} field-specific queries")
        for field in queries:
            self._log(f"      • {field}: G + DDG queries ready")
        
        # ----- STEP 2: Parallel Browser Search (All tabs at once) -----
        self._log("🌐 STEP 2: Opening parallel search tabs...")
        search_results, all_urls = self.parallel_browser.execute_parallel_searches(queries)
        self._log(f"   Collected {len(all_urls)} URLs from {len(search_results)} searches")
        
        # ----- STEP 3: Deduplicated Scraping -----
        self._log("📄 STEP 3: Scraping unique URLs (deduplicating)...")
        scraped_content = self.parallel_browser.scrape_deduplicated_urls(all_urls, max_urls=10)
        
        # ----- STEP 4: Bulk Extraction (Single LLM Call) -----
        self._log("🧠 STEP 4: Bulk extraction - all fields in single LLM call...")
        extracted_data = self.bulk_extractor.extract_all_fields(
            self.domain, search_results, scraped_content, self.EXCEL_FIELDS
        )
        self._log(f"   Extracted {len(extracted_data)} data points")
        
        # ----- STEP 5: Validation & Targeted Retry Per Missing Field -----
        self._log("✅ STEP 5: Validating against Excel fields...")
        is_sufficient, missing_fields = self.validator.validate_extraction(extracted_data)
        
        if missing_fields:
            # Sort by priority (critical first)
            prioritized_missing = self.validator.sort_missing_by_priority(missing_fields)
            self._log(f"   ⚠️ Missing {len(missing_fields)} fields: {prioritized_missing}")
            
            # Targeted retry for EACH missing field
            extracted_data = self._retry_missing_fields(extracted_data, prioritized_missing)
        else:
            self._log(f"   ✓ All Excel fields populated!")
        
        # ----- Populate Profile -----
        self._populate_profile(extracted_data)
        
        # ----- Fetch Logo -----
        self._log("🖼️  Fetching company logo...")
        self.profile.logo_url = self._fetch_logo()
        
        # ----- Final Validation Report -----
        self._log_final_status(extracted_data)
        
        # ----- Cleanup -----
        self._log("🏁 Pipeline complete! Closing browser...")
        self.browser.close()
        
        self._build_graph()
        
        return self.profile
    
    def _retry_missing_fields(self, data: Dict, missing_fields: List[str]) -> Dict:
        """
        Retry each missing field individually with multiple attempts.
        Uses W/H format retry queries with different strategies per attempt.
        """
        self._log(f"🔄 Starting targeted retry for {len(missing_fields)} missing fields...")
        
        for field in missing_fields:
            self._log(f"   📌 Retrying field: {field}")
            
            field_found = False
            
            for attempt in range(1, self.max_retries + 1):
                if field_found:
                    break
                
                self._log(f"      Attempt {attempt}/{self.max_retries}...")
                
                # Get retry queries for this attempt
                retry_queries = self.query_generator.generate_retry_queries(
                    self.domain, field, attempt
                )
                
                # Execute searches for this field
                field_data = self._execute_field_retry(field, retry_queries, attempt)
                
                if field_data:
                    # Validate the result
                    if self._is_valid_field_data(field_data):
                        # Map to correct internal field name
                        internal_field = self.validator.FIELD_MAPPING.get(field, field)
                        data[internal_field] = field_data
                        data[field] = field_data  # Also store with original name
                        
                        self._log(f"      ✓ Found data for {field}!")
                        field_found = True
                    else:
                        self._log(f"      ✗ Data insufficient, trying next attempt...")
                else:
                    self._log(f"      ✗ No data found, trying next attempt...")
            
            if not field_found:
                self._log(f"      ❌ Could not find data for {field} after {self.max_retries} attempts")
        
        return data
    
    def _execute_field_retry(self, field: str, queries: Dict[str, str], attempt: int) -> Optional[str]:
        """Execute retry search for a specific field."""
        try:
            # Alternate between Google and DDG based on attempt
            if attempt % 2 == 1:
                # Odd attempts: Google first
                serp_text, urls = self.browser.search_google(queries.get("google", ""))
                if not urls:
                    self.browser.open_new_tab()
                    serp_text2, urls = self.browser.search_duckduckgo(queries.get("ddg", ""))
                    serp_text += "\n" + serp_text2
                    self.browser.close_current_tab()
            else:
                # Even attempts: DDG first
                serp_text, urls = self.browser.search_duckduckgo(queries.get("ddg", ""))
                if not urls:
                    self.browser.open_new_tab()
                    serp_text2, urls = self.browser.search_google(queries.get("google", ""))
                    serp_text += "\n" + serp_text2
                    self.browser.close_current_tab()
            
            # Scrape top URLs
            scraped = ""
            for url in urls[:2]:
                try:
                    content = self.browser.scrape_text(url)
                    if content:
                        scraped += f"\n{content}"
                except:
                    pass
            
            # Extract field with LLM
            if serp_text or scraped:
                return self._extract_single_field(field, serp_text, scraped)
            
        except Exception as e:
            self._log(f"      ⚠️ Retry error: {e}")
        
        return None
    
    def _extract_single_field(self, field: str, serp_text: str, scraped_content: str) -> Optional[str]:
        """Extract a single field from search results using LLM."""
        
        field_descriptions = {
            "long_description": "A comprehensive 2-3 paragraph description of what the company does, their mission, and services",
            "short_description": "A brief one-sentence description/tagline of the company",
            "sic_code": "The Standard Industrial Classification (SIC) code number (e.g., 62020)",
            "sic_text": "The description/text for the SIC code (e.g., 'Information technology consultancy activities')",
            "sub_industry": "The specific sub-industry or niche the company operates in",
            "industry": "The primary industry category (e.g., Information Technology, Healthcare)",
            "sector": "The business sector (e.g., Technology, Finance, Retail)",
            "tags": "Relevant keywords and tags describing the company's services/products (comma-separated or as array)"
        }
        
        prompt = f"""Extract the following specific field for the company:

COMPANY: {self.domain}
FIELD TO EXTRACT: {field}
FIELD DESCRIPTION: {field_descriptions.get(field, field)}

SEARCH RESULTS:
{serp_text[:5000]}

WEBSITE CONTENT:
{scraped_content[:8000]}

INSTRUCTIONS:
1. Extract ONLY the requested field value
2. If it's "tags", return as JSON array: ["tag1", "tag2", ...]
3. For other fields, return as plain text
4. If data cannot be found, return empty string ""
5. Do NOT make up information

Return the extracted value ONLY. No explanations."""

        try:
            result = self.llm.generate(prompt)
            if result:
                cleaned = result.strip().strip('"').strip("'")
                # Handle tags specially
                if field == "tags" and not cleaned.startswith("["):
                    # Convert comma-separated to list
                    if "," in cleaned:
                        tags = [t.strip() for t in cleaned.split(",") if t.strip()]
                        return tags
                return cleaned
        except:
            pass
        
        return None
    
    def _is_valid_field_data(self, data) -> bool:
        """Check if field data is valid/meaningful."""
        if not data:
            return False
        
        if isinstance(data, str):
            cleaned = data.strip().lower()
            if len(cleaned) < 3:
                return False
            if cleaned in ["not found", "n/a", "unknown", "none", "null", ""]:
                return False
            return True
        
        if isinstance(data, list):
            return len(data) > 0
        
        return True
    
    def _log_final_status(self, data: Dict):
        """Log final status of all Excel fields."""
        self._log("📊 Final Field Status:")
        for field in self.EXCEL_FIELDS:
            internal_field = self.validator.FIELD_MAPPING.get(field, field)
            value = data.get(internal_field) or data.get(field)
            if value and self._is_valid_field_data(value):
                preview = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                self._log(f"   ✓ {field}: {preview}")
            else:
                self._log(f"   ✗ {field}: MISSING")
    
    def _fetch_logo(self) -> str:
        """Fetch company logo."""
        try:
            logo = self.browser.extract_logo(self.domain)
            if logo:
                return logo
        except:
            pass
        return f"https://logo.clearbit.com/{self.domain}"
    
    def _populate_profile(self, data: Dict):
        """Populate CompanyProfile from extracted data."""
        
        # Basic info
        self.profile.description_long = data.get("description_long", "")
        self.profile.description_short = data.get("description_short", "")
        
        # Industry
        self.profile.industry = data.get("industry", "")
        self.profile.sub_industry = data.get("sub_industry", "")
        self.profile.sector = data.get("sector", "")
        self.profile.sic_code = data.get("sic_code")
        self.profile.sic_text = data.get("sic_text")
        self.profile.tags = data.get("tags", [])
        
        # Products
        self.profile.products_services = data.get("products_services", [])
        self.profile.service_type = data.get("service_type")
        
        # Locations
        self.profile.locations = data.get("locations", [])
        self.profile.hq_indicator = data.get("hq_indicator", "")
        self.profile.full_address = data.get("full_address")
        
        # Contact
        self.profile.contact_phone = data.get("contact_phone")
        self.profile.contact_email = data.get("contact_email")
        self.profile.sales_phone = data.get("sales_phone")
        self.profile.mobile = data.get("mobile")
        self.profile.fax = data.get("fax")
        self.profile.other_numbers = data.get("other_numbers", [])
        self.profile.hours_of_operation = data.get("hours_of_operation")
        
        # Social
        self.profile.social_linkedin = data.get("social_linkedin")
        self.profile.social_twitter = data.get("social_twitter")
        self.profile.social_facebook = data.get("social_facebook")
        self.profile.social_instagram = data.get("social_instagram")
        self.profile.social_youtube = data.get("social_youtube")
        self.profile.social_blog = data.get("social_blog")
        self.profile.social_articles = data.get("social_articles", [])
        
        # Tech & Certs
        self.profile.tech_stack = data.get("tech_stack", [])
        self.profile.certifications = data.get("certifications", [])
        
        # Registration
        self.profile.company_registration_number = data.get("company_registration_number")
        self.profile.vat_number = data.get("vat_number")
        
        # Key People
        people_data = data.get("key_people", [])
        if isinstance(people_data, list):
            for p in people_data:
                if isinstance(p, dict) and p.get("name"):
                    try:
                        self.profile.key_people.append(KeyPerson(**p))
                    except:
                        pass
    
    def _build_graph(self):
        """Build knowledge graph from profile data."""
        self._log("🕸️  Building Knowledge Graph...")
        
        root_id = "node_company"
        self.profile.graph_nodes.append(
            GraphNode(id=root_id, label=self.profile.name, type="Company", 
                     properties={"industry": self.profile.industry, "domain": self.profile.domain})
        )
        
        # Add people nodes
        for i, person in enumerate(self.profile.key_people):
            pid = f"node_person_{i}"
            self.profile.graph_nodes.append(
                GraphNode(id=pid, label=person.name, type="Person", 
                         properties={"title": person.title})
            )
            self.profile.graph_edges.append(
                GraphEdge(source=pid, target=root_id, relation="works_at")
            )
        
        # Add location nodes
        for i, loc in enumerate(self.profile.locations):
            lid = f"node_location_{i}"
            self.profile.graph_nodes.append(
                GraphNode(id=lid, label=loc, type="Location", properties={})
            )
            self.profile.graph_edges.append(
                GraphEdge(source=root_id, target=lid, relation="located_at")
            )
