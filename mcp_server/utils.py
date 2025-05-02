import requests
import re
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin, urlparse
import traceback
import ssl  # Add ssl module import

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_text(url: str) -> tuple:
    """
    Fetch HTML content from a URL and extract text.
    
    Args:
        url: The URL to fetch
        
    Returns:
        tuple: (html_content, text_content)
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            # First attempt with default settings
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.SSLError as ssl_err:
            # Check if it's specifically a DH_KEY_TOO_SMALL error
            if 'DH_KEY_TOO_SMALL' in str(ssl_err):
                # Create a custom session with less strict SSL settings
                session = requests.Session()
                # Create a custom context that accepts legacy DH key parameters
                context = ssl.create_default_context()
                context.set_ciphers('DEFAULT@SECLEVEL=1')  # Lower security level to accept weaker DH keys
                session.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))
                
                # Override the session's SSL configuration
                session.verify = True
                session.adapters['https://'].poolmanager.connection_pool_kw['ssl_context'] = context
                
                # Retry with the custom session
                response = session.get(url, headers=headers, timeout=10)
                response.raise_for_status()
            else:
                # Re-raise if it's a different SSL error
                raise
        
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for script_or_style in soup(['script', 'style', 'meta', 'noscript']):
            script_or_style.decompose()
            
        text_content = soup.get_text(separator=' ', strip=True)
        
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        return html_content, text_content
        
    except Exception as e:
        logger.error(f"Error fetching {url}: {str(e)}")
        logger.error(traceback.format_exc())
        return "", ""

def find_email(html_content: str) -> str:
    """
    Extract the first email address from HTML content.
    
    Args:
        html_content: HTML content to search
        
    Returns:
        str: First email address found or None
    """
    try:
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        
        emails = re.findall(email_pattern, html_content)
        
        return emails[0] if emails else None
        
    except Exception as e:
        logger.error(f"Error finding email: {str(e)}")
        return None

def has_contact(html_content: str, base_url: str) -> str:
    """
    Detect if the site has a contact page or form.
    
    Args:
        html_content: HTML content to search
        base_url: Base URL for resolving relative links
        
    Returns:
        str: URL to the contact page/form if found, None otherwise
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        forms = soup.find_all('form')
        for form in forms:
            form_text = form.get_text().lower()
            form_action = form.get('action', '').lower()
            form_id = form.get('id', '').lower()
            form_class = form.get('class', [])
            form_class = ' '.join(form_class).lower() if form_class else ''
            
            contact_indicators = ['contact', 'message', 'email us', 'get in touch', 'reach out']
            
            for indicator in contact_indicators:
                if (indicator in form_text or 
                    indicator in form_action or 
                    indicator in form_id or 
                    indicator in form_class):
                    if form.get('action'):
                        return urljoin(base_url, form.get('action'))
                    return base_url
        
        links = soup.find_all('a')
        for link in links:
            href = link.get('href', '')
            link_text = link.get_text().lower()
            
            contact_indicators = ['contact', 'get in touch', 'reach out', 'email us']
            
            for indicator in contact_indicators:
                if indicator in link_text or indicator in href.lower():
                    if href:
                        return urljoin(base_url, href)
        
        contact_elements = soup.find_all(['div', 'section', 'footer'], 
                                       class_=lambda c: c and ('contact' in c.lower() if c else False))
        if contact_elements:
            for element in contact_elements:
                links = element.find_all('a')
                if links:
                    href = links[0].get('href', '')
                    if href:
                        return urljoin(base_url, href)
            return base_url
            
        return None
        
    except Exception as e:
        logger.error(f"Error checking for contact: {str(e)}")
        return None

def extract_name(html_content: str, text_content: str, url: str) -> str:
    """
    Extract company name from website content.
    
    Args:
        html_content: HTML content
        text_content: Extracted text content
        url: Website URL
        
    Returns:
        str: Company name or generic "Company"
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        title = soup.title.string if soup.title else ""
        
        domain = urlparse(url).netloc
        domain = domain.replace('www.', '')
        domain_parts = domain.split('.')
        domain_name = domain_parts[0] if domain_parts else ""
        
        meta_name = None
        meta_tags = soup.find_all('meta', property=['og:site_name', 'og:title'])
        if meta_tags:
            meta_name = meta_tags[0].get('content', '')
        
        logo_alt = None
        logo = soup.find('img', class_=lambda c: c and ('logo' in c.lower() if c else False))
        if logo:
            logo_alt = logo.get('alt', '')
        
        if meta_name and len(meta_name) < 50:
            return meta_name
        elif logo_alt and len(logo_alt) < 50:
            return logo_alt
        elif title:
            title = re.sub(r'\s*[|:]\s*.+$', '', title)
            title = re.sub(r'\s*-\s*.+$', '', title)
            if len(title) < 50:
                return title
        
        if domain_name:
            return domain_name.capitalize()
            
        return "Company"
        
    except Exception as e:
        logger.error(f"Error extracting company name: {str(e)}")
        return "Company"
