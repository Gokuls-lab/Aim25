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
    name: str = "Unknown"
    title: str = "Unknown"
    role_category: str = "Management" # Management, Engineering, Founder, etc.

class CompanyProfile(BaseModel):
    name: str = "Unknown"
    domain: str = ""
    logo_url: Optional[str] = None
    description_short: str = ""
    description_long: str = ""
    industry: str = "Unknown"
    sub_industry: str = "Unknown"
    
    # Lists
    products_services: List[str] = []
    locations: List[str] = [] # e.g. ["San Francisco (HQ)", "London", "Bangalore"]
    key_people: List[KeyPerson] = []
    
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_page: Optional[str] = None
    
    tech_stack: List[str] = [] # e.g. ["React", "AWS", "Python"]
    
    # Graph Data
    graph_nodes: List[GraphNode] = []
    graph_edges: List[GraphEdge] = []

    def to_json(self):
        return self.model_dump_json(indent=2)
