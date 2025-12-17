from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class GraphNode(BaseModel):
    id: str
    label: str
    type: str # "Company", "Person", "Location", "Product", "Tech"
    properties: Dict[str, str] = {}

class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str # "works_at", "hq_at", "produces", "uses_tech"

class KeyPerson(BaseModel):
    name: str = ""
    title: str = ""
    role_category: str = "Management"
    email: Optional[str] = None
    linkedin_url: Optional[str] = None

class CompanyProfile(BaseModel):
    # Company Info
    name: str = ""
    domain: str = ""
    domain_status: str = "Active"
    company_registration_number: Optional[str] = None
    vat_number: Optional[str] = None
    acronym: Optional[str] = None
    logo_url: Optional[str] = None
    
    # Description & Industry
    description_short: str = ""
    description_long: str = ""
    industry: str = ""
    sub_industry: str = ""
    sector: str = ""
    sic_code: Optional[str] = None
    sic_text: Optional[str] = None
    tags: List[str] = []
    
    # Products & Services
    products_services: List[str] = []
    service_type: Optional[str] = None 

    # Certifications
    certifications: List[str] = []

    # Locations & Contact
    locations: List[str] = [] 
    full_address: Optional[str] = None
    hq_indicator: str = "" 
    
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    sales_phone: Optional[str] = None
    fax: Optional[str] = None
    mobile: Optional[str] = None
    other_numbers: List[str] = []
    hours_of_operation: Optional[str] = None
    
    # Social Media
    social_linkedin: Optional[str] = None
    social_facebook: Optional[str] = None
    social_twitter: Optional[str] = None 
    social_instagram: Optional[str] = None
    social_youtube: Optional[str] = None
    social_blog: Optional[str] = None
    social_articles: List[str] = []

    # Tech Stack
    tech_stack: List[str] = []
    
    # Key People
    key_people: List[KeyPerson] = []
    
    # Graph Data
    graph_nodes: List[GraphNode] = []
    graph_edges: List[GraphEdge] = []

    def to_json(self):
        return self.model_dump_json(indent=2)
