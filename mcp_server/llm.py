import os
import time
import logging
import traceback
import google.generativeai as genai
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY = 2

def _initialize_gemini():
    """
    Initialize the Gemini API with the API key from environment variables.
    
    Raises:
        RuntimeError: If GEMINI_API_KEY is not set
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    
    genai.configure(api_key=api_key)

def _call_gemini_with_retry(prompt: str, model: str = "gemini-2.5-flash") -> Optional[str]:
    """
    Call Gemini API with retry logic for rate limiting.
    
    Args:
        prompt: The prompt to send to the model
        model: The model name to use
        
    Returns:
        str: The model's response or None if all retries failed
    """
    _initialize_gemini()
    
    for attempt in range(MAX_RETRIES):
        try:
            model_instance = genai.GenerativeModel(model)
            response = model_instance.generate_content(prompt)
            return response.text
        except Exception as e:
            error_message = str(e).lower()
            
            if "429" in error_message or "rate limit" in error_message or "quota" in error_message:
                delay = BASE_DELAY * (2 ** attempt)
                logger.warning(f"Rate limit hit. Retrying in {delay} seconds. Attempt {attempt + 1}/{MAX_RETRIES}")
                time.sleep(delay)
                
                if attempt == MAX_RETRIES - 1:
                    logger.error("Max retries reached for rate limit. Giving up.")
                    return None
            else:
                logger.error(f"Error calling Gemini API: {str(e)}")
                logger.error(traceback.format_exc())
                return None
    
    return None

def classify_manufacturer(text: str) -> bool:
    """
    Determine if a company is a manufacturer based on website text.
    
    Args:
        text: The website text content
        
    Returns:
        bool: True if the company is a manufacturer, False otherwise
        
    Raises:
        RuntimeError: If GEMINI_API_KEY is not set
    """
    prompt = f"""
    Based on the following website text, determine if this company is a manufacturer.
    
    A manufacturer is a company that:
    - Produces physical goods or products
    - Has manufacturing facilities, factories, or production lines
    - Mentions manufacturing processes, equipment, or machinery
    - Discusses product specifications, materials, or production capabilities
    - Mentions terms like "manufacturing", "production", "factory", "assembly", etc.
    
    Website text:
    {text[:8000]}  # Limit text length to avoid token limits
    
    Answer with ONLY "YES" if the company is a manufacturer, or "NO" if it is not.
    """
    
    try:
        response = _call_gemini_with_retry(prompt)
        
        if not response:
            logger.warning("Failed to get manufacturer classification from LLM. Defaulting to False.")
            return False
        
        response = response.strip().upper()
        return response == "YES"
        
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"Error classifying manufacturer: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def draft_email(company_name: str, is_manufacturer: bool) -> str:
    """
    Generate a tailored email based on company type.
    
    Args:
        company_name: The name of the company
        is_manufacturer: Whether the company is a manufacturer
        
    Returns:
        str: The generated email body
        
    Raises:
        RuntimeError: If GEMINI_API_KEY is not set
    """
    if is_manufacturer:
        prompt = f"""
        Draft a short, polite outreach email to {company_name}, which is a manufacturing company.
        
        The email should:
        - Be addressed to {company_name}
        - Mention manufacturing challenges and solutions
        - Discuss optimization of production processes
        - Mention improving efficiency and reducing costs
        - Suggest a brief call to discuss potential collaboration
        - Be professional, concise (5-7 sentences), and not overly sales-focused
        - End with a polite call to action
        
        Do not include email headers (To, From, Subject). Just write the email body.
        """
    else:
        prompt = f"""
        Draft a short, polite outreach email to {company_name}, which is not a manufacturing company.
        
        The email should:
        - Be addressed to {company_name}
        - Keep wording generic with a digital-transformation value proposition
        - Mention improving business processes and customer experience
        - Discuss data-driven decision making and automation
        - Suggest a brief call to discuss potential collaboration
        - Be professional, concise (5-7 sentences), and not overly sales-focused
        - End with a polite call to action
        
        Do not include email headers (To, From, Subject). Just write the email body.
        """
    
    try:
        response = _call_gemini_with_retry(prompt)
        
        if not response:
            logger.warning("Failed to generate email from LLM. Returning empty string.")
            return ""
        
        return response.strip()
        
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"Error drafting email: {str(e)}")
        logger.error(traceback.format_exc())
        return ""
