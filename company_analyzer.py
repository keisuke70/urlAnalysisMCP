import os
import csv
import logging
import argparse
import traceback
from dotenv import load_dotenv
from typing import List, Dict, Optional

# ────────────────────────────────────────────────────────────
# Local package imports
# ────────────────────────────────────────────────────────────
from mcp_server.utils import (
    fetch_text,
    find_email,
    has_contact,
    extract_name,
    extract_form_fields,  # new helper for form meta
    auto_submit_form,     # moved here from local definition
)
from mcp_server.llm import (
    classify_manufacturer,
    draft_email,
    summarize_company,
    generate_form_answers,  # new helper to craft answers
)

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

if not os.environ.get("GEMINI_API_KEY"):
    logger.warning(
        "GEMINI_API_KEY environment variable not set. LLM features will fail."
    )


# ────────────────────────────────────────────────────────────
# Core processing logic
# ────────────────────────────────────────────────────────────

def process_company(company_name: str, url: str) -> Dict[str, Optional[str]]:
    """Analyze a single company site and optionally submit the contact form."""
    logger.info(f"Processing: {company_name} ({url})")
    result = {
        "company_name": company_name,
        "mail_body": None,
        "contact_url": None,
        "email": None,
        "submitted": False,
        "error": None,
    }

    try:
        html_content, text_content = fetch_text(url)
        if not text_content:
            result["error"] = "Failed to fetch or extract text content"
            return result

        if not classify_manufacturer(text_content):
            result["error"] = "Company identified as non-manufacturer"
            return result

        # Manufacturer path
        summary = summarize_company(text_content)
        email_body = draft_email(company_name, True, summary)
        email_address = find_email(html_content)
        contact_page_url = has_contact(html_content, url)

        submitted_flag = False
        if contact_page_url:
            submitted_flag = auto_submit_form(contact_page_url, email_body)

        result.update(
            {
                "mail_body": email_body,
                "contact_url": contact_page_url,
                "email": email_address,
                "submitted": submitted_flag,
            }
        )
        return result

    except Exception as exc:
        logger.error(f"Error processing {company_name}: {exc}")
        logger.error(traceback.format_exc())
        result["error"] = f"Unexpected error: {exc}"
        return result


# ────────────────────────────────────────────────────────────
# CSV helpers (unchanged apart from new column)
# ────────────────────────────────────────────────────────────

def read_input_csv(filepath: str) -> List[Dict[str, str]]:
    companies = []
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if "CompanyName" not in reader.fieldnames or "URL" not in reader.fieldnames:
                raise ValueError("Input CSV must contain 'CompanyName' and 'URL' columns.")
            for row in reader:
                companies.append({"name": row["CompanyName"], "url": row["URL"]})
        return companies
    except Exception as exc:
        logger.error(f"Error reading CSV {filepath}: {exc}")
        return []


def write_output_csv(filepath: str, data: List[Dict[str, Optional[str]]]):
    if not data:
        logger.warning("No data to write.")
        return
    fieldnames = [
        "company_name",
        "mail_body",
        "contact_url",
        "email",
        "submitted",
        "error",
    ]
    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    except Exception as exc:
        logger.error(f"Error writing CSV {filepath}: {exc}")


# ────────────────────────────────────────────────────────────
# Main CLI
# ────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Analyze company websites & outreach.")
    ap.add_argument("-i", "--input", required=True, help="input CSV path")
    ap.add_argument("-o", "--output", default="output.csv", help="output CSV path")
    args = ap.parse_args()

    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY not set – exiting.")
        return

    companies = read_input_csv(args.input)
    results: List[Dict[str, Optional[str]]] = []
    for c in companies:
        res = process_company(c["name"], c["url"])
        if res.get("error") == "Company identified as non-manufacturer":
            continue
        results.append(res)
    write_output_csv(args.output, results)
    logger.info("Processing finished.")


if __name__ == "__main__":
    main()
