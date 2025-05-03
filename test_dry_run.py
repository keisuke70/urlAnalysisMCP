# Test script to preview form input values for a company URL without submitting
from mcp_server.utils import fetch_text, has_contact, auto_submit_form
from mcp_server.llm import draft_email, generate_company_impression, classify_manufacturer

url = "https://www.brics.ltd/"
company_name = "temp"  # You can use extract_name if you want to auto-detect

html, text = fetch_text(url)
if not text:
    print("Failed to fetch site text.")
elif not classify_manufacturer(text):
    print("Not a manufacturer.")
else:
    impression_text = generate_company_impression(text)
    mail_body = draft_email(company_name, impression_text)
    contact_url = has_contact(html, url)
    if not contact_url:
        print("No contact form found.")
    else:
        dry_run_result = auto_submit_form(contact_url, mail_body, dry_run=True)
        print(dry_run_result)
