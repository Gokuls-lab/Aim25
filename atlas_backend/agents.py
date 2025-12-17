from llm_engine import LLMEngine
from browser_engine import ResearchBrowser
from data_models import CompanyProfile, KeyPerson, GraphNode, GraphEdge
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
        
        # 1. Dynamic Scraping (Best for accuracy)
        scraped_logo = self.browser.extract_logo(domain)
        if scraped_logo:
            self._log(f"✅ Found dynamic logo: {scraped_logo}")
            return scraped_logo
        
        # 2. Heuristic Fallback
        self._log("Dynamic logo failed. Using fallback.")
        return f"https://logo.clearbit.com/{domain}"

    def research_field(self, field_name, description, context=""):
        """
        Micro-Loop: Research -> Extract -> Validate -> Retry.
        """
        # Step 1: Initial Research
        data = self._execute_research_attempt(field_name, description, attempt=1)
        
        # Step 2: Validation & Retry
        if self._needs_retry(data):
            self._log(f"⚠️ Validation failed for '{field_name}'. Retrying with deep dive...")
            
            # Logic for smarter retry query
            retry_query = f"{self.company} {description} official site"
            if field_name == "key_people":
                retry_query = f"site:linkedin.com {self.company} CEO CTO Director" # X-ray search
            elif field_name == "registration_details":
                retry_query = f"{self.company} Companies House registration VAT number details"
                
            data = self._execute_research_attempt(field_name, description, attempt=2, override_query=retry_query)
            
        return data

    def _execute_research_attempt(self, field_name, description, attempt=1, override_query=None):
        self._log(f"Researching '{field_name}' (Attempt {attempt})...")
        
        # 1. Query Gen
        query = override_query if override_query else f"{self.company} {description}"
        if not override_query:
            # Default smart queries
            if field_name == "key_people":
                query = f"{self.company} leadership text executives board"
            elif field_name == "tech_stack":
                query = f"{self.company} engineering jobs stack software used"
            elif field_name == "locations":
                query = f"{self.company} office locations map contact"
            elif field_name == "registration_details":
                query = f"{self.company} company info VAT SIC registration"

        # 2. Search & Scrape
        serp_text, urls = self.browser.search_google(query)
        website_text = ""
        
        # Surf top results (Increase count if retry)
        surf_limit = 2 if attempt == 1 else 3
        for url in urls[:surf_limit]:
            self._log(f"Reading: {url}")
            scraped = self.browser.scrape_text(url) # Now returns Title/Desc/Body
            if scraped:
                website_text += f"\n--- SOURCE: {url} ---\n{scraped}\n"

        # 3. Prompt Construction
        full_context = f"GOOGLE SEARCH CONTEXT:\n{serp_text[:6000]}\n\nBROWSED CONTENT:\n{website_text[:12000]}" # maximize context usage
        
        self._log(f"Extracting '{field_name}' data...")
        schema_hint = self.get_schema_hint(field_name)
        
        prompt = f"""
        You are an expert Data Analyst validation agent.
        Target: '{self.company}'
        Field: '{field_name}'
        
        INSTRUCTIONS:
        1. Analyze the 'GOOGLE SEARCH CONTEXT' first. It often contains the answer in the 'AI Overview' or Knowledge Panel.
        2. Then cross-reference with 'BROWSED CONTENT'.
        3. If conflicting, prefer official website data.
        4. If data is explicitly MISSING, return empty string "". 
        
        JSON SCHEMA:
        {schema_hint}
        
        DATA:
        {full_context}
        """
        
        result = self.llm.generate_json(prompt)
        data = result.get("data")
        return self._clean_data(data)

    def _needs_retry(self, data):
        """Simple validator: returns True if data is empty/insufficient."""
        if not data: return True
        if isinstance(data, str) and len(data) < 2: return True
        if isinstance(data, list) and len(data) == 0: return True
        if isinstance(data, dict):
             # For dicts, check if ALL values are empty
             return all(not v for v in data.values())
        return False

    def get_schema_hint(self, field_name):
        if field_name == "key_people":
            return 'Return JSON: { "data": [ {"name": "Name", "title": "Title", "role_category": "Management", "linkedin_url": ""} ] }'
        elif field_name == "locations":
            return 'Return JSON: { "data": ["Location 1", "Location 2"] }'
        elif field_name == "products_services":
            return 'Return JSON: { "data": ["Product 1", "Product 2"] }'
        elif field_name == "tech_stack":
            return 'Return JSON: { "data": ["Tech 1", "Tech 2"] }'
        elif field_name == "social_media":
            return 'Return JSON: { "data": {"linkedin": "url", "twitter": "url", "facebook": "url", "instagram": "url", "youtube": "url", "blog": "url"} }'
        elif field_name == "registration_details":
            return 'Return JSON: { "data": {"vat_number": "number", "registration_number": "number", "sic_code": "code", "year_founded": "year"} }'
        elif field_name == "certifications":
            return 'Return JSON: { "data": ["ISO 27001", "GDPR"] }'
        elif field_name == "contact_granular":
             return 'Return JSON: { "data": {"phone": "main", "sales": "sales_num", "email": "email", "address": "full address"} }'
        else:
            return 'Return JSON: { "data": "extracted text string" }'

    def _clean_data(self, data):
        """
        Post-processing to ensure 'Not Found' text becomes strictly empty/None.
        Small LLMs sometimes return 'N/A' despite instructions.
        """
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
        self._log(f"Initializing AutonomousLeadAgent for {company_name}...")
        
        self.company = company_name
        self._log("Initializing Browser Engine...")
        self.browser = ResearchBrowser()
        self._log("Browser Online.")
        
        self.profile = CompanyProfile(name=company_name, domain=company_name) # Assuming domain=company for init, refining later
        self.worker = MicroAgent(self.browser, company_name, log_callback)
        self._log("MicroAgent Ready.")
        
    def _log(self, message):
        if self.log_callback:
            self.log_callback(f"Leader: {message}")
        else:
            print(f"Leader: {message}")
        
    def run_pipeline(self):
        self._log(f"🚀 Starting Autonomous Research for {self.company}")
        
        # 0. Logo & Domain Check
        # If input came as a domain (e.g. google.com), use it. If company name, assume domain.
        # For this logic, we assume self.company IS the domain from the CSV if called from bulk, or query if single.
        if "." in self.company: # Simple heuristic
             self.profile.domain = self.company
             # Try to clean name
             self.profile.name = self.company.split('.')[0].title()
             
        self.profile.logo_url = self.worker.fetch_logo(self.profile.domain)

        # 1. Identity & Basics
        desc_data = self.worker.research_field("description", "company overview mission")
        if isinstance(desc_data, str) and desc_data:
            self.profile.description_long = desc_data
            self.profile.description_short = desc_data[:200] + "..."
        elif isinstance(desc_data, list) and desc_data:
             self.profile.description_long = " ".join(desc_data)

        # 2. Industry
        ind_data = self.worker.research_field("industry", "industry sector")
        if ind_data and isinstance(ind_data, str) and ind_data:
            self.profile.industry = ind_data

        # 3. Products
        prod_data = self.worker.research_field("products_services", "products services list")
        if isinstance(prod_data, list) and prod_data:
            self.profile.products_services = prod_data
            
        # 4. Locations
        loc_data = self.worker.research_field("locations", "locations offices headquarters")
        if isinstance(loc_data, list) and loc_data:
            self.profile.locations = loc_data

        # 5. Key People
        ppl_data = self.worker.research_field("key_people", "leadership executives")
        if isinstance(ppl_data, list) and ppl_data:
            for p in ppl_data:
                if isinstance(p, dict):
                    self.profile.key_people.append(KeyPerson(**p))
                    
        # 6. Tech Stack
        tech_data = self.worker.research_field("tech_stack", "technology stack software tools used")
        if isinstance(tech_data, list) and tech_data:
            self.profile.tech_stack = tech_data
            
        # 7. Contact - GRANULAR
        cont_data = self.worker.research_field("contact_granular", "contact address phone email sales support fax")
        if isinstance(cont_data, dict):
            self.profile.contact_phone = cont_data.get("phone") or ""
            self.profile.contact_email = cont_data.get("email") or ""
            self.profile.sales_phone = cont_data.get("sales") or ""
            self.profile.full_address = cont_data.get("address") or ""

        # 8. Social Media
        social_data = self.worker.research_field("social_media", "social media profiles linkedin twitter facebook instagram youtube")
        if isinstance(social_data, dict):
            self.profile.social_linkedin = social_data.get("linkedin")
            self.profile.social_twitter = social_data.get("twitter")
            self.profile.social_facebook = social_data.get("facebook")
            self.profile.social_instagram = social_data.get("instagram")
            self.profile.social_youtube = social_data.get("youtube")
            self.profile.social_blog = social_data.get("blog")
            
        # 9. IDs & Reg
        reg_data = self.worker.research_field("registration_details", "company registration number VAT number SIC code")
        if isinstance(reg_data, dict):
            self.profile.company_registration_number = reg_data.get("registration_number")
            self.profile.vat_number = reg_data.get("vat_number")
            if reg_data.get("sic_code"):
                self.profile.sic_code = str(reg_data.get("sic_code"))
            
        # 10. Certifications
        cert_data = self.worker.research_field("certifications", "certifications ISO compliance awards")
        if isinstance(cert_data, list):
            self.profile.certifications = cert_data
        
        self._log("Research complete. Shutting down browser...")
        self.browser.close()
        
        # 8. BUILD KNOWLEDGE GRAPH
        self._build_graph()
        
        return self.profile

    def _build_graph(self):
        self._log("🕸️  Building Knowledge Graph...")
        
        # Central Node
        root_id = "node_company"
        self.profile.graph_nodes.append(
            GraphNode(id=root_id, label=self.profile.name, type="Company", properties={"industry": self.profile.industry})
        )
        
        # People Nodes
        for i, person in enumerate(self.profile.key_people):
            pid = f"node_person_{i}"
            self.profile.graph_nodes.append(
                GraphNode(id=pid, label=person.name, type="Person", properties={"title": person.title})
            )
            self.profile.graph_edges.append(
                GraphEdge(source=pid, target=root_id, relation="works_at")
            )
            
        # Product Nodes
        for i, prod in enumerate(self.profile.products_services[:5]): # Limit to top 5
            pid = f"node_prod_{i}"
            self.profile.graph_nodes.append(
                GraphNode(id=pid, label=prod, type="Product")
            )
            self.profile.graph_edges.append(
                GraphEdge(source=root_id, target=pid, relation="produces")
            )
            
        # Location Nodes
        for i, loc in enumerate(self.profile.locations[:3]):
            lid = f"node_loc_{i}"
            self.profile.graph_nodes.append(
                GraphNode(id=lid, label=loc, type="Location")
            )
            self.profile.graph_edges.append(
                GraphEdge(source=root_id, target=lid, relation="has_office_in")
            )

        self._log(f"✅ Graph Built: {len(self.profile.graph_nodes)} Nodes, {len(self.profile.graph_edges)} Edges.")