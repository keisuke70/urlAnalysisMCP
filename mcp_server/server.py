import os
from dotenv import load_dotenv  # Add this import
import asyncio

load_dotenv()  # Add this line to load variables from .env

from mcp.server.fastmcp import FastMCP
import logging
import traceback

from .utils import fetch_text, find_email, has_contact, extract_name
from .llm import classify_manufacturer, draft_email, summarize_company

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

mcp = FastMCP("company_checker")

async def _analyze_company_async(url: str) -> dict:
    """
    Input: company homepage URL.
    Output: JSON {manufacturer, email, contact, contact_url, mail_body}.
    """
    default_response = {
        "manufacturer": False,
        "email": None,
        "contact": False,
        "contact_url": None,
        "mail_body": ""
    }
    
    try:
        html_content, text_content = fetch_text(url)
        
        if not text_content:
            logger.error(f"Failed to extract text content from {url}")
            return default_response
        
        company_name = extract_name(html_content, text_content, url)
        
        company_summary = summarize_company(text_content)
        
        is_manufacturer = classify_manufacturer(text_content)
        
        if not is_manufacturer:
            return {
                "manufacturer": False,
                "email": None,
                "contact": False,
                "contact_url": None,
                "mail_body": None
            }
        
        email_task = asyncio.to_thread(find_email, html_content)
        contact_task = asyncio.to_thread(has_contact, html_content, url)
        email_body_task = asyncio.to_thread(draft_email, company_name, is_manufacturer, company_summary)
        
        email, contact_url, email_body = await asyncio.gather(
            email_task, contact_task, email_body_task
        )
        
        has_contact_page = contact_url is not None
        
        result = {
            "manufacturer": is_manufacturer,
            "email": email,
            "contact": has_contact_page,
            "contact_url": contact_url,
            "mail_body": email_body
        }
        
        return result
    
    except Exception as e:
        logger.error(f"Error analyzing {url}: {str(e)}")
        logger.error(traceback.format_exc())
        return default_response

def analyze_company_sync(url: str) -> dict:
    """
    Synchronous version for direct calls outside of FastMCP.
    Input: company homepage URL.
    Output: JSON {manufacturer, email, contact, contact_url, mail_body}.
    """
    return asyncio.run(_analyze_company_async(url))

@mcp.tool(
    annotations={
        "title": "Analyze Company Website",
        "readOnlyHint": True,
        "openWorldHint": True
    }
)
async def analyze_company(url: str) -> dict:
    """
    Input: company homepage URL.
    Output: JSON {manufacturer, email, contact, contact_url, mail_body}.
    
    This is the async version that FastMCP will use.
    """
    return await _analyze_company_async(url)

if __name__ == "__main__":
    mcp.run()  # defaults to stdio transport
