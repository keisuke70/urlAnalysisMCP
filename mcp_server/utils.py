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
    Detect if the site has a contact page or form (Japanese-focused).
    Args:
        html_content: HTML content to search
        base_url: Base URL for resolving relative links
    Returns:
        str: URL to the contact page/form if found, None otherwise
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Japanese and English indicators
        contact_indicators = [
            'お問い合わせ', 'お問合せ', '問合せ', '連絡', 'inquiry', 'otoiawase',
            'contact', 'get in touch', 'reach out', 'email us'
        ]

        # 1. Check forms
        forms = soup.find_all('form')
        for form in forms:
            form_text = form.get_text().lower()
            form_action = form.get('action', '').lower()
            form_id = form.get('id', '').lower()
            form_class = form.get('class', [])
            form_class = ' '.join(form_class).lower() if form_class else ''
            for indicator in contact_indicators:
                if (indicator in form_text or 
                    indicator in form_action or 
                    indicator in form_id or 
                    indicator in form_class):
                    if form.get('action'):
                        return urljoin(base_url, form.get('action'))
                    return base_url

        # 2. Check links
        links = soup.find_all('a')
        for link in links:
            href = link.get('href', '')
            link_text = link.get_text().lower()
            for indicator in contact_indicators:
                if indicator in link_text or indicator in href.lower():
                    if href:
                        return urljoin(base_url, href)

        # 3. Check for elements with contact-related class names
        contact_elements = soup.find_all(
            ['div', 'section', 'footer'], 
            class_=lambda c: c and any(ind in c.lower() for ind in contact_indicators)
        )
        if contact_elements:
            for element in contact_elements:
                links = element.find_all('a')
                if links:
                    href = links[0].get('href', '')
                    if href:
                        return urljoin(base_url, href)
            return base_url

        # 4. Fallback: look for URLs ending with inquiry.html or similar
        for link in links:
            href = link.get('href', '')
            if href and (href.lower().endswith('inquiry.html') or href.lower().endswith('otoiawase.html')):
                return urljoin(base_url, href)

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
    全ての<form>内の主要フィールド (input/textarea/select) を重複なく抽出。
    テーブル型フォームにも対応。name/idがなければclassやラベルから生成。
    hiddenフィールドやname属性が空のinputは除外。
    tr内の全input/textarea/selectを個別に抽出し、thラベルをlabelとして割り当てる。
    placeholder属性も含める。
    selectフィールドやラジオボタンの場合、選択肢 (value/text) を含める。
    戻り値: [{"name": ..., "label": ..., "type": ..., "placeholder": ..., "options": [...]}]
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    fields = []
    seen = set()
    for form in soup.find_all("form"):
        # --- Collect radio groups by name ---
        radio_groups = {}
        for radio in form.find_all("input", {"type": "radio"}):
            name = radio.get("name") or radio.get("id")
            if not name:
                continue
            if name not in radio_groups:
                radio_groups[name] = []
            # Try to get label: from <label> or sibling <span>
            label = ""
            parent_label = radio.find_parent("label")
            if parent_label:
                label = parent_label.get_text(strip=True)
            else:
                # Try next sibling span
                next_span = radio.find_next_sibling("span")
                if next_span:
                    label = next_span.get_text(strip=True)
            radio_groups[name].append({
                "value": radio.get("value", ""),
                "text": label or radio.get("value", "")
            })
        # --- Add radio groups as fields ---
        for name, options in radio_groups.items():
            if name in seen:
                continue
            seen.add(name)
            # Try to get a group label from the first radio's parent or a nearby label
            group_label = ""
            first_radio = form.find("input", {"type": "radio", "name": name})
            if first_radio:
                # Look for a label element before the radio group
                prev = first_radio.find_previous(["label", "div", "th"])
                if prev:
                    group_label = prev.get_text(strip=True)
            fields.append({
                "name": name,
                "label": group_label,
                "type": "radio",
                "placeholder": "",
                "options": options
            })
        # --- Table fields (unchanged) ---
        for tr in form.find_all("tr"):
            th = tr.find("th")
            label = th.get_text(strip=True) if th else ""
            for tag in tr.find_all(["input", "textarea", "select"]):
                ftype = tag.get("type", tag.name)
                name = tag.get("name") or tag.get("id") or ""
                if ftype == "hidden" or not name:
                    continue
                if name in seen:
                    continue
                seen.add(name)
                placeholder = tag.get("placeholder", "")
                options = []
                if tag.name == "select":
                    for opt in tag.find_all("option"):
                        options.append({"value": opt.get("value", ""), "text": opt.get_text(strip=True)})
                field = {"name": name, "label": label, "type": ftype, "placeholder": placeholder}
                if options:
                    field["options"] = options
                fields.append(field)
        # --- Non-table fields (unchanged, but skip radios) ---
        for tag in form.find_all(["input", "textarea", "select"]):
            ftype = tag.get("type", tag.name)
            name = tag.get("name") or tag.get("id") or ""
            if ftype == "hidden" or not name or ftype == "radio":
                continue
            if name in seen:
                continue
            seen.add(name)
            label = ""
            if tag.get("aria-label"):
                label = tag["aria-label"]
            elif tag.get("placeholder"):
                label = tag["placeholder"]
            else:
                lbl = tag.find_parent("label")
                label = lbl.get_text(strip=True) if lbl else ""
            placeholder = tag.get("placeholder", "")
            options = []
            if tag.name == "select":
                for opt in tag.find_all("option"):
                    options.append({"value": opt.get("value", ""), "text": opt.get_text(strip=True)})
            field = {"name": name, "label": label, "type": ftype, "placeholder": placeholder}
            if options:
                field["options"] = options
            fields.append(field)
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
    # Only add manual message field if no textarea exists at all
    if email_body and not any(f["type"] == "textarea" for f in fields_meta):
        fields_meta.append({"name": "message", "label": "お問い合わせ内容", "type": "textarea"})

    from mcp_server.llm import generate_form_answers
    answers = generate_form_answers(fields_meta, mail_body=email_body)
    if "message" in answers:
        # Overwrite with our crafted body to keep consistency
        answers["message"] = email_body

    if dry_run:
        # Return only the answers dict for dry run
        return answers

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(contact_url, timeout=25_000)

            for f in fields_meta:
                selector = f'[name="{f["name"]}"]'
                loc = page.locator(selector).first
                # hiddenなフィールドは無視し、visibleなフィールドだけ自動入力
                if loc.count() == 0 or not loc.is_visible():
                    continue
                value = answers.get(f["name"], "")
                ftype = f.get("type", "text")
                if ftype in ("checkbox", "radio"):
                    if str(value).lower() in ("yes", "true", "on", "1"):
                        loc.check()
                elif ftype == "select":
                    loc.select_option(label=value)
                else:
                    loc.fill(value)

            # --- 送信ボタンの内容でフィルタリング ---
            skip_keywords = ["資料", "ダウンロード", "カタログ", "catalog", "download"]
            def is_skip_button(el):
                text = (el.inner_text() or "") + " " + (el.get_attribute("value") or "") + " " + (el.get_attribute("name") or "")
                text = text.lower()
                return any(k in text for k in skip_keywords)

            # button[type=submit]
            submit_buttons = page.locator("button[type=submit],input[type=submit]")
            found = False
            for i in range(submit_buttons.count()):
                btn = submit_buttons.nth(i)
                try:
                    if is_skip_button(btn):
                        continue
                    btn.click()
                    found = True
                    break
                except Exception:
                    continue
            if not found:
                # fallback: Enter
                page.keyboard.press("Enter")

            page.wait_for_load_state("networkidle", timeout=10_000)
            browser.close()
            return True
    except Exception as exc:
        logger.warning(f"Auto form submission failed: {exc}")
        return False
