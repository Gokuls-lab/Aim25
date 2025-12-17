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

    def research_field(self, field_name, description, context=""):
        """
        Targeted research for a specific field in the CompanyProfile.
        Returns the raw data extracted for that field.
        """
        self._log(f"Researching '{field_name}'...")
        
        # 1. Search Query Generation
        query = f"{self.company} {description}"
        if field_name == "key_people":
            query = f"{self.company} leadership board key executives"
        elif field_name == "tech_stack":
            query = f"{self.company} technology stack engineering blog jobs"
        elif field_name == "locations":
            query = f"{self.company} office locations headquarters"
            
        # 2. Search & Scrape
        serp_text, urls = self.browser.search_google(query)
        website_text = ""
        
        # Surf top 1 result (or 2 if needed)
        for url in urls[:1]:
            self._log(f"Reading: {url}")
            scraped = self.browser.scrape_text(url)
            if scraped:
                website_text += f"\n[Source: {url}]\n{scraped[:8000]}"
                
        full_context = f"GOOGLE SEARCH:\n{serp_text[:4000]}\n\nWEBSITE CONTENT:\n{website_text}"
        
        # 3. Extraction Prompt
        self._log(f"Extracting structured data via LLM...")
        schema_hint = ""
        if field_name == "key_people":
            schema_hint = 'Return JSON: { "data": [ {"name": "Name", "title": "Title", "role_category": "Management"} ] }'
        elif field_name == "locations":
            schema_hint = 'Return JSON: { "data": ["Location 1", "Location 2"] }'
        elif field_name == "products_services":
            schema_hint = 'Return JSON: { "data": ["Product 1", "Product 2"] }'
        elif field_name == "tech_stack":
            schema_hint = 'Return JSON: { "data": ["Tech 1", "Tech 2"] }'
        else:
            schema_hint = 'Return JSON: { "data": "extracted text string" }'

        prompt = f"""
        Task: Extract '{field_name}' for '{self.company}'.
        Context Provided Below.
        
        {schema_hint}
        
        Extract ONLY distinct factual info.
        
        DATA:
        {full_context}
        """
        
        result = self.llm.generate_json(prompt)
        return result.get("data")

class AutonomousLeadAgent:
    def __init__(self, company_name, log_callback=None):
        self.log_callback = log_callback
        self._log(f"Initializing AutonomousLeadAgent for {company_name}...")
        
        self.company = company_name
        self._log("Initializing Browser Engine...")
        self.browser = ResearchBrowser()
        self._log("Browser Online.")
        
        self.profile = CompanyProfile(name=company_name, domain=company_name)
        self.worker = MicroAgent(self.browser, company_name, log_callback)
        self._log("MicroAgent Ready.")
        
    def _log(self, message):
        if self.log_callback:
            self.log_callback(f"Leader: {message}")
        else:
            print(f"Leader: {message}")
        
    def run_pipeline(self):
        self._log(f"🚀 Starting Autonomous Research for {self.company}")
        
        # 1. Identity & Basics
        desc_data = self.worker.research_field("description", "company overview mission")
        if isinstance(desc_data, str):
            self.profile.description_long = desc_data
            self.profile.description_short = desc_data[:200] + "..."
        elif isinstance(desc_data, list):
             self.profile.description_long = " ".join(desc_data)

        # 2. Industry
        ind_data = self.worker.research_field("industry", "industry sector")
        if ind_data and isinstance(ind_data, str):
            self.profile.industry = ind_data

        # 3. Products
        prod_data = self.worker.research_field("products_services", "products services list")
        if isinstance(prod_data, list):
            self.profile.products_services = prod_data
            
        # 4. Locations
        loc_data = self.worker.research_field("locations", "locations offices headquarters")
        if isinstance(loc_data, list):
            self.profile.locations = loc_data

        # 5. Key People
        ppl_data = self.worker.research_field("key_people", "leadership executives")
        if isinstance(ppl_data, list):
            for p in ppl_data:
                if isinstance(p, dict):
                    self.profile.key_people.append(KeyPerson(**p))
                    
        # 6. Tech Stack
        tech_data = self.worker.research_field("tech_stack", "technology stack software tools used")
        if isinstance(tech_data, list):
            self.profile.tech_stack = tech_data
            
        # 7. Contact
        contact_data = self.worker.research_field("contact_details", "contact email phone support page")
        if isinstance(contact_data, str):
            if "@" in contact_data: self.profile.contact_email = contact_data
        
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