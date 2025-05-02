import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.server import analyze_company

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_manufacturer_url():
    """Test with a manufacturer URL"""
    url = "https://nissen-co.co.jp/rivet/"
    logger.info(f"Testing manufacturer URL: {url}")
    
    result = analyze_company(url)
    
    logger.info(f"Manufacturer: {result['manufacturer']}")
    logger.info(f"Email: {result['email']}")
    logger.info(f"Contact: {result['contact']}")
    logger.info(f"Mail body preview (first 100 chars): {result['mail_body'][:100]}...")
    
    return result

def test_non_manufacturer_url():
    """Test with a non-manufacturer URL"""
    url = "https://www.tsj-argo.co.jp/?page_id=33"
    logger.info(f"Testing non-manufacturer URL: {url}")
    
    result = analyze_company(url)
    
    logger.info(f"Manufacturer: {result['manufacturer']}")
    logger.info(f"Email: {result['email']}")
    logger.info(f"Contact: {result['contact']}")
    logger.info(f"Mail body: {result['mail_body']}")
    
    return result

if __name__ == "__main__":
    logger.info("Testing Japanese prompts and summarization...")
    
    manufacturer_result = test_manufacturer_url()
    
    non_manufacturer_result = test_non_manufacturer_url()
    
    logger.info("Testing complete!")
