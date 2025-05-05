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
    ウェブサイトテキストから「自社で製品を製造している製造業」かどうかを厳密に判定する。
    - 「販売」「取扱」「代理店」「ショップ」「通販」などの記述が中心の場合は製造業ではないと判定する。
    - 「自社工場」「自社開発」「自社生産」「生産ライン」などの記述が明確にある場合のみ製造業と判定する。
    """
    prompt = f"""
以下のウェブサイトテキストに基づいて、この会社が「自社で物理的な製品を製造している製造業」かどうかを厳密に判断してください。

【製造業の特徴】
- 自社で工場や生産設備を持ち、製品を生産している
- 「自社製造」「自社工場」「自社開発」「生産ライン」などの記述がある
- 「販売」「取扱」「代理店」「ショップ」「通販」などの記述が中心の場合は製造業ではありません

ウェブサイトテキスト:
{text[:8000]}

会社が「自社で製造している製造業」の場合は「YES」、そうでない場合（販売会社・代理店・通販サイト等）は「NO」だけで答えてください。
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
# 追加: メール末尾に必ず付けるクロージングブロック
# ────────────────────────────────────────────────────────────────────────────
CLOSING_BLOCK = """つきましては、オンライン（Zoom／Google Meet）にて10～15分ほど、次のような現場のお困りごとをお聞かせいただけないでしょうか？
図面や構想段階からのヒアリング～材料選定フローの履歴管理の属人化\n\nNCルーターやパネルソーによる切断・切削パラメータの記録と再利用の難しさ\n\n溶接・接着・フレームライニングなど複数工程にまたがる品質検査データの一元管理\n\n小ロット多品種製造時の在庫・納期管理および協力工場との情報共有の手間\n\nまた、貴社の業務フローやお困りごとをヒアリングさせていただくことで、弊社の技術力を活かした最適なツール化の方向性を検討させていただきます。\n\n
当社は生成AIを活用したアジャイル開発により、従来の1/3以下のコストで現場にフィットするツールを短期間にご提供できる強みがあります。今回のヒアリングは“ご提案”ではなく、貴社の“生の声”を把握し、最適なツール化の方向性を検討するためのものです。\n\n
ご興味をお持ちいただけましたら、ご都合の良い日時をいくつかご返信いただくか、以下リンクよりご予約ください。\n\n
 https://calendar.app.google/jM8gesybkVQEGhww6 \n\n
清水工業所様の高品質なプラスチック加工現場DXに、ぜひお手伝いさせていただければ幸いです。 \n\n
 何卒よろしくお願い申し上げます。
――――――――――
 株式会社日本自動化技術
 橋本 武士（はしもと たけし）
 https://japan-automation-technology.vercel.app
 メール：htakeshi0614@gmail.com
 Zoom／Google Meet対応可
 ――――――――――
"""



# ────────────────────────────────────────────────────────────────────────────
# メール生成
# ────────────────────────────────────────────────────────────────────────────
def draft_email(company_name:str, impression_text: str) -> str:
    """
    感銘文を受け取り、決まったテンプレートでメール本文を合成する。
    Args:
        impression_text: 感銘を受けた一文
    Returns:
        str: メール本文
    """
    template = f"""株式会社{company_name} ご担当者様\n\nはじめまして。学生発AIスタートアップ「株式会社日本自動化技術」の橋本と申します。まず本メールはお見積もり依頼ではなく、貴社の現場課題を伺うためのヒアリング依頼であることをお詫び申し上げます。\n\n{impression_text}\n\n{CLOSING_BLOCK}"""
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
        # --- Always set subject fields to the fixed phrase ---
        subject_phrase = "【株式会社 日本自動化技術より】製造現場の課題に関するヒアリングのお願い"
        for f in fields:
            label = f.get("label", "")
            name = f.get("name", "")
            if ("件名" in label) or ("subject" in label.lower()) or ("件名" in name) or ("subject" in name.lower()):
                answers[f["name"]] = subject_phrase
        return answers
    except Exception:
        logger.warning("Failed to parse Gemini JSON, falling back to空回答")
        # fallback: 全て空
        return {f["name"]: "" for f in fields}
