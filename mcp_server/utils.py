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

def extract_form_fields(html: str) -> list[dict[str, str]]:
    """
    `<form>` 内の主要フィールド (input/textarea/select) 情報を抽出。
    戻り値: [{"name": "email", "label": "メールアドレス", "type": "email"}, ...]
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    form = soup.find("form")
    if not form:
        return []
    fields = []
    for tag in form.find_all(["input", "textarea", "select"]):
        name = tag.get("name") or tag.get("id") or ""
        ftype = tag.get("type", tag.name)
        # ラベル文字列を推測
        label = ""
        if tag.get("aria-label"):
            label = tag["aria-label"]
        elif tag.get("placeholder"):
            label = tag["placeholder"]
        else:
            lbl = tag.find_parent("label")
            label = lbl.get_text(strip=True) if lbl else ""
        if name:
            fields.append({"name": name, "label": label, "type": ftype})
    return fields

def auto_submit_form(contact_url: str, email_body: str, dry_run: bool = False) -> bool | dict:
    """Return True if submission appears to succeed, False otherwise. If dry_run, return the field values instead of submitting."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("playwright not installed – skipping form submission.")
        return False

    # Fetch HTML once for field extraction
    html, _ = fetch_text(contact_url)
    if not html:
        logger.warning("Could not fetch contact page for field extraction.")
        return False

    fields_meta = extract_form_fields(html)
    if email_body and not any(f["name"] == "message" for f in fields_meta):
        # add manual message field meta if site didn't expose name attr
        fields_meta.append({"name": "message", "label": "お問い合わせ内容", "type": "textarea"})

    from mcp_server.llm import generate_form_answers
    answers = generate_form_answers(fields_meta)
    if "message" in answers:
        # Overwrite with our crafted body to keep consistency
        answers["message"] = email_body

    if dry_run:
        # Return what would be filled in the form
        return {"fields": fields_meta, "answers": answers}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(contact_url, timeout=25_000)

            for f in fields_meta:
                selector = f'[name="{f["name"]}"]'
                if page.locator(selector).count() == 0:
                    continue
                value = answers.get(f["name"], "")
                ftype = f.get("type", "text")
                if ftype in ("checkbox", "radio"):
                    if str(value).lower() in ("yes", "true", "on", "1"):
                        page.locator(selector).first.check()
                elif ftype == "select":
                    page.locator(selector).first.select_option(label=value)
                else:
                    page.locator(selector).first.fill(value)

            # try clicking submit
            if page.locator("button[type=submit]").count():
                page.locator("button[type=submit]").first.click()
            elif page.locator("input[type=submit]").count():
                page.locator("input[type=submit]").first.click()
            else:
                page.keyboard.press("Enter")

            page.wait_for_load_state("networkidle", timeout=10_000)
            browser.close()
            return True
    except Exception as exc:
        logger.warning(f"Auto form submission failed: {exc}")
        return False
