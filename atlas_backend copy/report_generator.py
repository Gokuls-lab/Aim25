from fpdf import FPDF
import datetime
import config
import os
from data_models import CompanyProfile

class ModernReport(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.report_header_color = (0, 51, 102) # Navy Blue
        self.report_accent_color = (200, 200, 200) # Light Grey
        self.body_text_color = (50, 50, 50) # Dark Grey

    def header(self):
        if self.page_no() > 1:
            self.set_font('Arial', 'B', 8)
            self.set_text_color(*self.report_header_color)
            self.cell(0, 10, 'ATLAS INTELLIGENCE DOSSIER', 0, 0, 'L')
            self.cell(0, 10, f'CONFIDENTIAL', 0, 0, 'R')
            self.ln(5)
            self.set_draw_color(*self.report_accent_color)
            self.line(10, 15, 200, 15)
            self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def draw_cover_page(self, company_name):
        self.add_page()
        self.set_fill_color(245, 247, 250)
        self.rect(0, 0, 210, 297, 'F')
        
        self.set_y(60)
        self.set_font('Arial', 'B', 36)
        self.set_text_color(*self.report_header_color)
        self.cell(0, 15, "INTELLIGENCE", 0, 1, 'C')
        self.cell(0, 15, "DOSSIER", 0, 1, 'C')
        
        self.ln(20)
        self.set_font('Arial', '', 14)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, "TARGET ENTITY", 0, 1, 'C')
        self.set_font('Arial', 'B', 24)
        self.set_text_color(0, 0, 0)
        self.cell(0, 15, company_name.upper(), 0, 1, 'C')
        
        self.ln(30)
        self.set_y(260)
        self.set_font('Arial', '', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1, 'C')
        self.cell(0, 5, "Agent: ATLAS v2.0", 0, 1, 'C')

    def chapter_title(self, label):
        self.ln(5)
        self.set_font('Arial', 'B', 16)
        self.set_text_color(*self.report_header_color)
        self.cell(0, 10, label.upper(), 0, 1, 'L')
        self.set_draw_color(*self.report_header_color)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def chapter_body(self, text):
        self.set_font('Arial', '', 11)
        self.set_text_color(*self.body_text_color)
        self.multi_cell(0, 6, text)
        self.ln(5)

def generate_json_file(profile: CompanyProfile):
    filename = f"{config.REPORT_DIR}/{profile.name.replace(' ', '_')}_profile.json"
    with open(filename, "w") as f:
        f.write(profile.to_json())
    print(f"✅ JSON Profile saved: {filename}")
    return filename

def generate_report(profile: CompanyProfile):
    # 1. Save JSON First (Primary Requirement)
    json_path = generate_json_file(profile)
    
    # 2. Generate PDF (Secondary)
    pdf = ModernReport()
    pdf.draw_cover_page(profile.name)
    pdf.add_page()
    
    # Map fields to chapters
    chapters = [
        ("Identity", f"{profile.description_short}\n\n{profile.description_long}"),
        ("Industry", profile.industry),
        ("Products & Services", ", ".join(profile.products_services)),
        ("Locations", ", ".join(profile.locations)),
        ("Key People", "\n".join([f"{p.name} ({p.title})" for p in profile.key_people])),
        ("Tech Stack", ", ".join(profile.tech_stack))
    ]
    
    for title, content in chapters:
        if content:
            pdf.chapter_title(title)
            # UTF-8 sanitizer
            safe_text = content.encode('latin-1', 'replace').decode('latin-1')
            pdf.chapter_body(safe_text)
            
    pdf_filename = f"{config.REPORT_DIR}/{profile.name.replace(' ', '_')}_Dossier.pdf"
    pdf.output(pdf_filename)
    print(f"📄 PDF Report generated: {pdf_filename}")