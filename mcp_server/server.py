import os
from dotenv import load_dotenv  # Add this import

load_dotenv()  # Add this line to load variables from .env

from mcp.server.fastmcp import FastMCP
import logging
import traceback

from .utils import fetch_text, find_email, has_contact, extract_name
from .llm import classify_manufacturer, draft_email

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

mcp = FastMCP("company_checker")

@mcp.tool(
    annotations={
        "title": "Analyze Company Website",
        "readOnlyHint": True,
        "openWorldHint": True
    }
)
def analyze_company(url: str) -> dict:
    """
    Input: company homepage URL.
    Output: JSON {manufacturer, email, contact, mail_body}.
    """
    default_response = {
        "manufacturer": False,
        "email": None,
        "contact": False,
        "mail_body": ""
    }
    
    try:
        html_content, text_content = fetch_text(url)
        
        if not text_content:
            logger.error(f"Failed to extract text content from {url}")
            return default_response
        
        company_name = extract_name(html_content, text_content, url)
        
        is_manufacturer = classify_manufacturer(text_content)
        
        if not is_manufacturer:
            return {
                "manufacturer": False,
                "email": None,
                "contact": False,
                "mail_body": None
            }
        
        email = find_email(html_content)
        
        has_contact_page = has_contact(html_content, url)
        
        email_body = draft_email(company_name, is_manufacturer)
        
        result = {
            "manufacturer": is_manufacturer,
            "email": email,
            "contact": has_contact_page,
            "mail_body": email_body
        }
        
        return result
    
    except Exception as e:
        logger.error(f"Error analyzing {url}: {str(e)}")
        logger.error(traceback.format_exc())
        return default_response

if __name__ == "__main__":
    mcp.run(transport="sse")  # defaults to 0.0.0.0:8000
