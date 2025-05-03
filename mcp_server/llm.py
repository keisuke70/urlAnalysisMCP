import os
import time
import logging
import traceback
import google.generativeai as genai
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name%s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY = 2

# ────────────────────────────────────────────────────────────────────────────
# 追加: メール末尾に必ず付けるクロージングブロック
# ────────────────────────────────────────────────────────────────────────────
CLOSING_BLOCK = """今回のご連絡は「ご提案」ではなく、現場のリアルなお声をお聞かせいただくためのヒアリングのお願いです。
Zoomなどのオンラインで、10〜15分程度のお時間を頂戴できましたら幸いです。
また、ご希望に応じて、超低コスト（場合により無償）での試作ツールのご提供も可能です。
少しでもご興味をお持ちいただけましたら、以下のカレンダーよりご都合の良い時間をご予約いただくか、候補日時をいくつかご返信いただけますと幸いです。
▼カレンダー予約リンク
https://calendar.app.google/jM8gesybkVQEGhww6

株式会社 日本自動化技術
橋本 武士（はしもと たけし）
https://japan-automation-technology.vercel.app"""

# ────────────────────────────────────────────────────────────────────────────
# Gemini 基本処理
# ────────────────────────────────────────────────────────────────────────────
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

def _call_gemini_with_retry(prompt: str, model:  str = "gemini-2.0-flash") -> Optional[str]:
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

# ────────────────────────────────────────────────────────────────────────────
# 会社印象文生成（旧 summarize_company）
# ────────────────────────────────────────────────────────────────────────────
def generate_company_impression(text: str) -> str:
    """
    会社ホームページを見て感銘を受けた一文を生成する。
    Args:
        text: 会社のウェブサイトテキスト
    Returns:
        str: 感銘を受けた一文（例: 御社の〇〇に感銘を受けました）
    """
    prompt = f"""あなたは日本語のビジネスメールAIです。下記の会社紹介文を読み、
ホームページを拝見した印象として、御社の強みや特徴に感銘を受けた一文（敬語、50〜120字程度）を生成してください。
---
{text[:15000]}"""
    try:
        response = _call_gemini_with_retry(prompt)
        if not response:
            logger.warning("Failed to get company impression from LLM. Returning empty string.")
            return ""
        return response.strip()
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"Error generating company impression: {str(e)}")
        logger.error(traceback.format_exc())
        return ""

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
    以下のウェブサイトテキストに基づいて、この会社が製造業かどうかを判断してください。
    
    製造業の特徴:
    - 物理的な商品や製品を生産している
    - 製造施設、工場、生産ラインを持っている
    - 製造プロセス、設備、機械について言及している
    - 製品仕様、材料、生産能力について説明している
    - 「製造」「生産」「工場」「組立」などの用語が使われている
    
    ウェブサイトテキスト:
    {text[:8000]}
    
    会社が製造業である場合は「YES」、そうでない場合は「NO」だけで答えてください。
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

# ────────────────────────────────────────────────────────────────────────────
# メール生成
# ────────────────────────────────────────────────────────────────────────────
def draft_email(company_name: str, impression_text: str) -> str:
    """
    会社名と感銘文を受け取り、決まったテンプレートでメール本文を合成する。
    Args:
        company_name: 会社名
        impression_text: 感銘を受けた一文
    Returns:
        str: メール本文
    """
    template = f"""突然のご連絡失礼いたします。\n\n株式会社 日本自動化技術の橋本と申します。\n\n弊社は、生成AIや最先端の開発手法を活用し、製造業の現場業務を支援するオーダーメイドツールの開発に取り組んでいる、学生発のAIスタートアップです。\n\n{impression_text}\n\nつきましては、大変恐縮ではございますが、製造業の現場における課題やお困りごとについて、幅広くヒアリングさせて頂きたくご連絡いたしました。\n\nたとえば、以下のようなお悩みはありませんでしょうか？\n\n*   日報や在庫管理が紙やExcel中心で煩雑になっている\n*   熟練者に依存した作業が多く、技術継承や属人化の解消が難しい\n\n弊社は、従来の1/3以下のコストで、現場に本当にフィットする高精度なツールを短期間でご提供できる可能性があります。\n\nこの背景には、弊社の持つ生成AIの技術力と柔軟な開発体制があります。\n\n貴社が現在抱えていらっしゃる課題や、将来的な展望についてお聞かせいただければ幸いです。\n\n{CLOSING_BLOCK}"""
    return template

# 追加: フォーム回答用の当社固定情報 ------------------------------
BASE_COMPANY_INFO = {
    "company_name": "株式会社 日本自動化技術",
    "contact_person": "橋本 武士",
    "email": "info@jat-example.co.jp",
    "phone": "03-1234-5678",
    "address": "東京都千代田区丸の内1-1-1",
    "zip_code": "2360042",
    "industry": "ソフトウェア開発 / DX コンサル",
    "employees": "2",
    "website": "https://japan-automation-technology.vercel.app",
    "budget_range": "〜300万円程度",
    # 分割住所用
    "pref": "東京都",
    "address1": "千代田区丸の内",
    "address2": "1-1-1",
}

# Mapping for Japanese field names/labels to BASE_COMPANY_INFO keys
JP_FIELD_MAP = {
    "御社名": "company_name",
    "会社名": "company_name",
    "お名前": "contact_person",
    "氏名": "contact_person",
    "メールアドレス": "email",
    "e-mail": "email",
    "電話番号": "phone",
    "ご住所": "address",
    "住所": "address",
    "部署名": "department",
    "業種": "industry",
    "従業員数": "employees",
    "ホームページ": "website",
    "ご予算": "budget_range",
    "郵便番号": "zip_code",
    "zip": "zip_code",
    "addr": "address",
}

# ---------------------------------------------------------------

def generate_form_answers(fields: list[dict[str, str]],
                          base_info: dict[str, str] = BASE_COMPANY_INFO,
                          mail_body: str = None) -> dict[str, str]:
    """
    LLMの意味推論を最大限活用し、どんな日本語フォームでも最適な値を自動割当する。
    fields: {name, label, type, ...} のリスト
    base_info: 会社情報（dict）
    mail_body: メインのメッセージ欄に必ず入れる本文（あれば）
    """
    import json
    # メール本文を会社情報に追加（LLMが使いやすいように）
    info = dict(base_info)
    if mail_body:
        info["mail_body"] = mail_body
    # LLMへのプロンプト
    prompt = f"""
あなたは日本語の問い合わせフォーム自動入力AIです。
下記の会社情報（info）をもとに、fields一覧の各項目に最適な値をJSON形式で割り当ててください。
- name, label, type, placeholder, などから意味を推論し、姓・名・郵便番号・電話番号・メール・会社名・部署・カナ・確認欄なども正確に分割して割り当ててください。
- メインのメッセージ欄（お問い合わせ内容・ご質問・ご要望など）にはmail_bodyを必ず入れてください。
- "確認"や"再入力"などの確認欄には、対応する値をそのままコピーしてください。
- 50文字以内が望ましい場合は自動で短縮してください。
- 出力は {{name: value, ...}} のJSON形式のみで返してください。

# info
{json.dumps(info, ensure_ascii=False)}

# fields
{json.dumps(fields, ensure_ascii=False)}
"""
    raw = _call_gemini_with_retry(prompt, model="gemini-2.0-flash")
    try:
        import re
        json_txt = re.search(r"\{.*\}", raw, re.S).group(0)
        answers = json.loads(json_txt)
        return answers
    except Exception:
        logger.warning("Failed to parse Gemini JSON, falling back to空回答")
        # fallback: 全て空
        return {f["name"]: "" for f in fields}
