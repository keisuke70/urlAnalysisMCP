# Test script to preview form input values for a company URL without submitting
from mcp_server.utils import fetch_text, has_contact, auto_submit_form
from mcp_server.llm import draft_email, summarize_company, classify_manufacturer

url = "https://www.dic-plas.co.jp/"
company_name = "cell862 factory"  # You can use extract_name if you want to auto-detect

html, text = fetch_text(url)
if not text:
    print("Failed to fetch site text.")
elif not classify_manufacturer(text):
    print("Not a manufacturer.")
else:
    summary = summarize_company(text)
    mail_body = draft_email(company_name, True, summary)
    contact_url = has_contact(html, url)
    if not contact_url:
        print("No contact form found.")
    else:
        dry_run_result = auto_submit_form(contact_url, mail_body, dry_run=True)
        print("Form fields and answers that would be filled:")
        print(dry_run_result)
