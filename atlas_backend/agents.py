from llm_engine import LLMEngine
from browser_engine import ResearchBrowser
from data_models import CompanyProfile, KeyPerson, GraphNode, GraphEdge
import config
import json
import time

class MicroAgent:
    def __init__(self, browser, company, log_callback=None):
        self.llm = LLMEngine()
        self.browser = browser
        self.company = company
        self.log_callback = log_callback

    def _log(self, message):
        if self.log_callback:
            self.log_callback(f"MicroAgent: {message}")
        else:
            print(f"MicroAgent: {message}")

    def fetch_logo(self, domain):
        """
        Fetches logo by actually visiting the site + fallback to Clearbit.
        """
        self._log(f"Fetching logo for {domain}...")
        scraped_logo = self.browser.extract_logo(domain)
        if scraped_logo:
            self._log(f"✅ Found dynamic logo: {scraped_logo}")
            return scraped_logo
        self._log("Dynamic logo failed. Using fallback.")
        return f"https://logo.clearbit.com/{domain}"

    def research_field(self, field_name, description, context=""):
        """
        Robust N-Attempt Pipeline with Parallel Search & Engine Swapping.
        Retries controlled by config.MAX_RETRIES.
        """
        max_retries = config.MAX_RETRIES
        data = None
        for attempt in range(1, max_retries + 1):
            if data and not self._needs_retry(data):
                break
            self._log(f"🔄 Attempt {attempt}/{max_retries} for '{field_name}'...")
            data = self._execute_step_strategy(field_name, description, attempt)
            
            if self._needs_retry(data):
                self._log(f"⚠️  Data missing/poor for '{field_name}'. Retrying...")
            else:
                self._log(f"✅ Data found for '{field_name}' in Attempt {attempt}.")
        return data

    def _execute_step_strategy(self, field_name, description, attempt):
        """
        Defines the strategy for each attempt using Google & DDG with DISTINCT queries.
        """
        q_base = f"{self.company} {description}"
        q_special = self._get_smart_query(field_name)
        
        serp_text = ""
        website_text = ""
        urls = []

        # --- STRATEGY LOGIC ---
        if attempt == 1:
            # Parallel: Google (Base) + DDG (Specialized)
            self._log("🚀 Strategy: Google (Main) + DuckDuckGo (Specialized)")
            
            # Tab 1: Google - Main Query
            g_text, g_urls = self.browser.search_google(q_base)
            
            # Tab 2: DDG - Specialized Query
            self.browser.open_new_tab()
            d_text, d_urls = self.browser.search_duckduckgo(q_special)
            self.browser.close_current_tab() 
            
            serp_text = f"GOOGLE RESULTS (Query: {q_base}):\n{g_text}\n\nDUCKDUCKGO RESULTS (Query: {q_special}):\n{d_text}"
            urls = list(set(g_urls + d_urls))

        elif attempt == 2:
            # Swap Strategies: DDG (Base) + Google (Site Specific)
            self._log("🚀 Strategy: DuckDuckGo (Main) + Google (Site Operator)")
            
            # Tab 1: DDG - Main Query
            d_text, d_urls = self.browser.search_duckduckgo(q_base)
            
            # Tab 2: Google - Site Specific
            self.browser.open_new_tab()
            site_q = f"site:linkedin.com OR site:crunchbase.com OR site:{self.company.replace(' ', '').lower()}.com {description}"
            if field_name == "key_people": site_q = f"site:linkedin.com {self.company} CEO CTO Director"
            
            g_text, g_urls = self.browser.search_google(site_q)
            self.browser.close_current_tab()
            
            serp_text = f"DDG RESULTS:\n{d_text}\n\nGOOGLE SPECIFIC:\n{g_text}"
            urls = list(set(d_urls + g_urls))

        elif attempt == 3:
            # Deep Scrape Official Site
            self._log("🚀 Strategy: Deep Official Site Scrape")
            guess_url = f"https://www.{self.company.split('.')[0].lower()}.com"
            if "." in self.company: guess_url = f"https://www.{self.company}"
            
            website_text += self.browser.scrape_text(guess_url)
            
            # Try finding "About" or "Contact" pages via search
            q = f"{self.company} contact about us management team"
            # Just use Google for this specific hunt
            _, specific_urls = self.browser.search_google(q)
            urls = specific_urls

        elif attempt == 4:
            # Broad Fallback - Google Only
            self._log("🚀 Strategy: Broad Google Search")
            q = f"{self.company} business profile info"
            serp_text, urls = self.browser.search_google(q)

        elif attempt >= 5:
            # Last Resort - DDG Only (for attempts 5+)
            self._log("🚀 Strategy: Last Resort DDG")
            q = f"{self.company} {field_name}"
            serp_text, urls = self.browser.search_duckduckgo(q)

        # --- BROWSING (Surf Top URLs) ---
        surf_limit = 3
        count = 0
        for url in urls:
            if count >= surf_limit: break
            # Skip social media profiles unless looking for them
            if any(x in url for x in ["facebook.com", "twitter.com", "instagram.com"]) and field_name != "social_media":
                continue
            
            self._log(f"Reading: {url}")
            scraped = self.browser.scrape_text(url)
            if scraped:
                website_text += f"\n--- SOURCE: {url} ---\n{scraped}\n"
                count += 1

        # --- EXTRACTION ---
        full_context = f"SEARCH CONTEXT:\n{serp_text[:8000]}\n\nBROWSED CONTENT:\n{website_text[:15000]}"
        schema_hint = self.get_schema_hint(field_name)
        
        prompt = f"""
        You are an expert Data Analyst validation agent.
        Target: '{self.company}'
        Field: '{field_name}'
        
        INSTRUCTIONS:
        1. Analyze search results from Google and DuckDuckGo.
        2. Cross-reference with browsed website content.
        3. Extract the requested data fields.
        4. If data is explicitly MISSING, return empty string "". 
        5. For multiple values, return a list.
        
        JSON SCHEMA:
        {schema_hint}
        
        DATA:
        {full_context}
        """
        
        result = self.llm.generate_json(prompt)
        data = result.get("data")
        return self._clean_data(data)

    def _get_smart_query(self, field_name):
        """Generates specialized queries for retry/parallel tab."""
        if field_name == "key_people":
            return f"{self.company} leadership executive team board members"
        elif field_name == "registration_details":
            return f"{self.company} company registration number VAT SIC code"
        elif field_name == "contact_granular":
            return f"{self.company} phone number email support contact us page"
        elif field_name == "tech_stack":
            return f"{self.company} engineering hiring stack technology used"
        return f"{self.company} {field_name} official data"

    def _needs_retry(self, data):
        """Simple validator."""
        if not data: return True
        if isinstance(data, str) and len(data) < 2: return True
        if isinstance(data, list) and len(data) == 0: return True
        if isinstance(data, dict):
             return all(not v for v in data.values())
        return False

    def get_schema_hint(self, field_name):
        if field_name == "key_people":
            return 'Return JSON: { "data": [ {"name": "Name", "title": "Title", "role_category": "Management", "email": "email", "linkedin_url": ""} ] }'
        elif field_name == "locations":
            return 'Return JSON: { "data": ["Location 1", "Location 2"] }'
        elif field_name == "products_services":
            return 'Return JSON: { "data": ["Product 1", "Product 2"], "type": "Service/Product Type" }'
        elif field_name == "tech_stack":
            return 'Return JSON: { "data": ["Tech 1", "Tech 2"] }'
        elif field_name == "social_media":
            return 'Return JSON: { "data": {"linkedin": "url", "twitter": "url", "facebook": "url", "instagram": "url", "youtube": "url", "blog": "url", "articles": ["article1"]} }'
        elif field_name == "registration_details":
            return 'Return JSON: { "data": {"vat_number": "number", "registration_number": "number", "sic_code": "code", "year_founded": "year"} }'
        elif field_name == "certifications":
            return 'Return JSON: { "data": ["ISO 27001", "GDPR"] }'
        elif field_name == "contact_granular":
             return 'Return JSON: { "data": {"phone": "main", "sales": "sales_num", "mobile": "mobile_num", "fax": "fax_num", "other": ["num1"], "email": "email", "address": "full address", "hours": "9am-5pm"} }'
        elif field_name == "industry_details":
             return 'Return JSON: { "data": {"industry": "Industry", "sub_industry": "Sub", "sector": "Sector", "tags": ["tag1", "tag2"]} }'
        elif field_name == "hq_indicator":
             return 'Return JSON: { "data": "Yes/No or Location Name" }'
        else:
            return 'Return JSON: { "data": "extracted text string" }'

    def _clean_data(self, data):
        if isinstance(data, str):
            if data.lower() in ["not found", "n/a", "unknown", "none", "no information"]:
                return ""
            return data
        elif isinstance(data, list):
            return [self._clean_data(item) for item in data if item]
        elif isinstance(data, dict):
             return {k: self._clean_data(v) for k, v in data.items()}
        return data

class AutonomousLeadAgent:
    def __init__(self, company_name, log_callback=None):
        self.log_callback = log_callback
        self.company = company_name
        self.browser = ResearchBrowser()
        self.profile = CompanyProfile(name=company_name, domain=company_name)
        self.worker = MicroAgent(self.browser, company_name, log_callback)
        
    def _log(self, message):
        if self.log_callback:
            self.log_callback(f"Leader: {message}")
        else:
            print(f"Leader: {message}")
        
    def run_pipeline(self):
        self._log(f"🚀 Starting Dual-Engine Pipeline (Google + DDG) for {self.company}")
        
        # 0. Logo & Domain
        if "." in self.company: 
             self.profile.domain = self.company
             self.profile.name = self.company.split('.')[0].title()
        self.profile.logo_url = self.worker.fetch_logo(self.profile.domain)

        # 1. Identity & Basics
        desc_data = self.worker.research_field("description", "company overview mission acronym")
        if isinstance(desc_data, str) and desc_data:
            self.profile.description_long = desc_data
            self.profile.description_short = desc_data[:200] + "..."
        
        # 2. Industry Deep Dive
        ind_data = self.worker.research_field("industry_details", "industry sub-industry sector tags")
        if isinstance(ind_data, dict):
            self.profile.industry = ind_data.get("industry", "")
            self.profile.sub_industry = ind_data.get("sub_industry", "")
            self.profile.sector = ind_data.get("sector", "")
            self.profile.tags = ind_data.get("tags", [])

        # 3. Products & Services
        prod_data = self.worker.research_field("products_services", "products services list type of offering")
        if isinstance(prod_data, dict):
            self.profile.service_type = prod_data.get("type", "")
            self.profile.products_services.extend(prod_data.get("data", []))
        elif isinstance(prod_data, list):
             self.profile.products_services = prod_data

        # 4. Locations & HQ
        loc_data = self.worker.research_field("locations", "locations offices headquarters indicator")
        if isinstance(loc_data, list):
            self.profile.locations = loc_data
        
        hq_data = self.worker.research_field("hq_indicator", "headquarters address indicator")
        if isinstance(hq_data, str):
            self.profile.hq_indicator = hq_data

        # 5. Key People
        ppl_data = self.worker.research_field("key_people", "leadership executives email")
        if isinstance(ppl_data, list):
            for p in ppl_data:
                if isinstance(p, dict):
                    self.profile.key_people.append(KeyPerson(**p))
                    
        # 6. Tech Stack
        tech_data = self.worker.research_field("tech_stack", "technology stack software tools used")
        if isinstance(tech_data, list):
            self.profile.tech_stack = tech_data
            
        # 7. Contact
        cont_data = self.worker.research_field("contact_granular", "contact phone mobile sales support fax hours email")
        if isinstance(cont_data, dict):
            self.profile.contact_phone = cont_data.get("phone") or ""
            self.profile.contact_email = cont_data.get("email") or ""
            self.profile.sales_phone = cont_data.get("sales") or ""
            self.profile.mobile = cont_data.get("mobile") or ""
            self.profile.fax = cont_data.get("fax") or ""
            self.profile.other_numbers = cont_data.get("other", [])
            self.profile.full_address = cont_data.get("address") or ""
            self.profile.hours_of_operation = cont_data.get("hours") or ""

        # 8. Social
        social_data = self.worker.research_field("social_media", "social media profiles articles blog")
        if isinstance(social_data, dict):
            self.profile.social_linkedin = social_data.get("linkedin")
            self.profile.social_twitter = social_data.get("twitter")
            self.profile.social_facebook = social_data.get("facebook")
            self.profile.social_instagram = social_data.get("instagram")
            self.profile.social_youtube = social_data.get("youtube")
            self.profile.social_blog = social_data.get("blog")
            self.profile.social_articles = social_data.get("articles", [])

        self._log("Research complete. Shutting down browser...")
        self.browser.close()
        self._build_graph()
        return self.profile

    def _build_graph(self):
        self._log("🕸️  Building Knowledge Graph...")
        root_id = "node_company"
        self.profile.graph_nodes.append(
            GraphNode(id=root_id, label=self.profile.name, type="Company", properties={"industry": self.profile.industry})
        )
        for i, person in enumerate(self.profile.key_people):
            pid = f"node_person_{i}"
            self.profile.graph_nodes.append(
                GraphNode(id=pid, label=person.name, type="Person", properties={"title": person.title})
            )
            self.profile.graph_edges.append(
                GraphEdge(source=pid, target=root_id, relation="works_at")
            )