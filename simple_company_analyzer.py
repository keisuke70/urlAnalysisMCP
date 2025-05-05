import os
import csv
import logging
from dotenv import load_dotenv
from typing import List, Dict, Optional
from mcp_server.utils import fetch_text, find_email, has_contact
from mcp_server.llm import classify_manufacturer, draft_email, generate_company_impression

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def read_input_csv(filepath: str) -> List[Dict[str, str]]:
    companies = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if "website" not in reader.fieldnames:
            raise ValueError("Input CSV must contain 'website' column.")
        for row in reader:
            companies.append({"website": row["website"]})
    return companies


def write_output_csv(filepath: str, data: List[Dict[str, Optional[str]]]):
    fieldnames = ["website", "contact_url", "mail_content", "email_address"]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def process_website(url: str) -> Dict[str, Optional[str]]:
    logger.info(f"Processing: {url}")
    result = {"website": url, "contact_url": None, "mail_content": None, "email_address": None}
    try:
        html_content, text_content = fetch_text(url)
        if not text_content:
            return result
        if not classify_manufacturer(text_content):
            return result
        impression_text = generate_company_impression(text_content)
        mail_content = draft_email(impression_text)
        contact_url = has_contact(html_content, url)
        email_address = None
        if contact_url:
            contact_html, _ = fetch_text(contact_url)
            email_address = find_email(contact_html)
            if not email_address:
                email_address = find_email(html_content)
        else:
            email_address = find_email(html_content)
        result.update({
            "contact_url": contact_url,
            "mail_content": mail_content,
            "email_address": email_address
        })
        return result
    except Exception as exc:
        logger.error(f"Error processing {url}: {exc}")
        return result


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Simple company analyzer (no form logic)")
    ap.add_argument("-i", "--input", required=True, help="input CSV path (must have 'website' column)")
    ap.add_argument("-o", "--output", default="output_simple.csv", help="output CSV path")
    args = ap.parse_args()

    companies = read_input_csv(args.input)
    results = []
    for c in companies:
        res = process_website(c["website"])
        # Only output for manufacturer
        if res["mail_content"]:
            results.append(res)
    write_output_csv(args.output, results)
    logger.info("Processing finished.")


if __name__ == "__main__":
    main()
