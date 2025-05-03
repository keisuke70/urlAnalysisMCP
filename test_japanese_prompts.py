import os
import sys
import logging
from dotenv import load_dotenv

# Load .env file from the root directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the processing function from the new script
from company_analyzer import process_company

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_test(company_name: str, url: str):
    """Runs the analysis for a single company and logs results."""
    logger.info(f"Testing URL: {url} for Company: {company_name}")

    # Check if API key is available, otherwise skip LLM parts gracefully if possible
    if not os.environ.get("GEMINI_API_KEY"):
        logger.warning("GEMINI_API_KEY not set. LLM-dependent results might be empty or default.")

    result = process_company(company_name, url) # Use the new function

    logger.info(f"--- Results for {company_name} ---")
    logger.info(f"Email Found: {result.get('email')}")
    logger.info(f"Contact URL Found: {result.get('contact_url')}")
    mail_body_preview = (result.get('mail_body') or "")[:100]
    logger.info(f"Mail body preview: {mail_body_preview}...")
    if result.get('error'):
         logger.warning(f"Processing Error: {result['error']}")
    logger.info("-" * (23 + len(company_name))) # Separator

    return result

if __name__ == "__main__":
    logger.info("Testing company analysis script...")

    # Test case 1: Expected Manufacturer
    manufacturer_result = run_test("Nissen Co", "https://nissen-co.co.jp/rivet/")

    # Test case 2: Expected Non-Manufacturer (or different type)
    non_manufacturer_result = run_test("Example Consulting Firm", "https://example.com/consulting")

    logger.info("Testing complete!")

    # Optional: Add asserts here if you want automated checks
    # assert manufacturer_result.get('mail_body') is not None
    # assert non_manufacturer_result.get('error') == "Company identified as non-manufacturer"
