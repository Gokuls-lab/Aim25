import pandas as pd
import os
from datetime import datetime
from typing import List
from data_models import CompanyProfile
import config

def generate_bulk_excel(profiles: List[CompanyProfile], filename_prefix="Bulk_Report"):
    """
    Generates a multi-sheet Excel file from a list of CompanyProfile objects,
    matching the specific schema requirements.
    """
    
    # 1. Prepare Dataframes for each sheet
    
    # Sheet: company_information
    company_info_data = []
    for p in profiles:
        company_info_data.append({
            'domain': p.domain,
            'domain_status': p.domain_status,
            'Company Registration Number': p.company_registration_number,
            'VAT Number': p.vat_number,
            'company_name': p.name,
            'Acronym': p.acronym,
            'logo_url': p.logo_url,
            'tech_stack': ", ".join(p.tech_stack) if p.tech_stack else ""
        })
    df_company = pd.DataFrame(company_info_data)
    
    # Sheet: contact_information
    contact_data = []
    for p in profiles:
        contact_data.append({
            'domain': p.domain,
            'text': "", # Placeholder
            'company_name': p.name,
            'full_address': p.full_address,
            'phone': p.contact_phone,
            'sales phone': p.sales_phone,
            'fax': p.fax,
            'mobile': p.mobile,
            'other numbers': ", ".join(p.other_numbers) if p.other_numbers else "",
            'email': p.contact_email,
            'hours_of_operation': p.hours_of_operation,
            'HQ Indicator': p.hq_indicator
        })
    df_contact = pd.DataFrame(contact_data)
    
    # Sheet: social_media
    social_data = []
    for p in profiles:
        social_data.append({
            'domain': p.domain,
            'linkedin': p.social_linkedin,
            'facebook': p.social_facebook,
            'x': p.social_twitter,
            'Instagram': p.social_instagram,
            'Youtube': p.social_youtube,
            'blog': p.social_blog,
            'articles': ", ".join(p.social_articles) if p.social_articles else ""
        })
    df_social = pd.DataFrame(social_data)
    
    # Sheet: people_information (One-to-Many)
    people_data = []
    for p in profiles:
        if not p.key_people:
            # Add empty row to ensure domain is present
            people_data.append({
                'domain': p.domain,
                'people_name': "",
                'people_title': "",
                'people_email': "",
                'url': ""
            })
        else:
            for person in p.key_people:
                people_data.append({
                    'domain': p.domain,
                    'people_name': person.name,
                    'people_title': person.title,
                    'people_email': person.email,
                    'url': person.linkedin_url
                })
    df_people = pd.DataFrame(people_data)
    
    # Sheet: description & industry
    desc_data = []
    for p in profiles:
        desc_data.append({
            'domain': p.domain,
            'long description': p.description_long,
            'short description': p.description_short,
            'sic_code': p.sic_code,
            'sic_text': p.sic_text,
            'sub_industry': p.sub_industry,
            'industry': p.industry,
            'sector': p.sector,
            'tags': ", ".join(p.tags) if p.tags else ""
        })
    df_desc = pd.DataFrame(desc_data)
    
    # Sheet: certifications
    cert_data = []
    for p in profiles:
        cert_data.append({
            'domain': p.domain,
            'certifications': ", ".join(p.certifications) if p.certifications else ""
        })
    df_cert = pd.DataFrame(cert_data)
    
    # Sheet: services
    services_data = []
    for p in profiles:
        services_data.append({
            'domain': p.domain,
            'products & services': ", ".join(p.products_services) if p.products_services else "",
            'type': p.service_type
        })
    df_services = pd.DataFrame(services_data)
    
    # 2. Write to Excel
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f"{filename_prefix}_{timestamp}.xlsx"
    output_path = os.path.join(config.REPORT_DIR, output_filename)
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_company.to_excel(writer, sheet_name='company_information', index=False)
        df_contact.to_excel(writer, sheet_name='contact_information', index=False)
        df_social.to_excel(writer, sheet_name='social_media', index=False)
        df_people.to_excel(writer, sheet_name='people_information', index=False)
        df_desc.to_excel(writer, sheet_name='description & industry', index=False)
        df_cert.to_excel(writer, sheet_name='certifications', index=False)
        df_services.to_excel(writer, sheet_name='services', index=False)
        
    print(f"✅ Bulk Excel Report generated: {output_path}")
    return output_filename
