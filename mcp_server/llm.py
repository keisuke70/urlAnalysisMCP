import os
import time
import logging
import traceback
import google.generativeai as genai
from typing import Optional, Dict, Any

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

def _call_gemini_with_retry(prompt: str, model: str = "gemini-1.5-flash-latest", max_tokens: int = None, temperature: float = None) -> Optional[str]:
    """
    Call Gemini API with retry logic for rate limiting.
    
    Args:
        prompt: The prompt to send to the model
        model: The model name to use
        max_tokens: Maximum number of tokens to generate
        temperature: Temperature for generation (0.0 to 1.0)
        
    Returns:
        str: The model's response or None if all retries failed
    """
    _initialize_gemini()
    
    for attempt in range(MAX_RETRIES):
        try:
            model_instance = genai.GenerativeModel(model)
            
            generation_config = {}
            if max_tokens is not None:
                generation_config["max_output_tokens"] = max_tokens
            if temperature is not None:
                generation_config["temperature"] = temperature
                
            if generation_config:
                response = model_instance.generate_content(prompt, generation_config=generation_config)
            else:
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

def summarize_company(text: str, max_tokens: int = 250) -> str:
    """
    Summarize company information in Japanese.
    
    Args:
        text: The website text content
        max_tokens: Maximum tokens for the summary
        
    Returns:
        str: Japanese summary of the company (≤500 characters)
        
    Raises:
        RuntimeError: If GEMINI_API_KEY is not set
    """
    prompt = f"""以下の会社紹介を500字以内で要約してください。
---
{text[:15000]}"""
    
    try:
        response = _call_gemini_with_retry(prompt, max_tokens=max_tokens)
        
        if not response:
            logger.warning("Failed to get company summary from LLM. Returning empty string.")
            return ""
        
        return response.strip()
        
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"Error summarizing company: {str(e)}")
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

def draft_email(company_name: str, is_manufacturer: bool, company_summary: str = "") -> str:
    """
    Generate a tailored Japanese email based on company type and summary.
    
    Args:
        company_name: The name of the company
        is_manufacturer: Whether the company is a manufacturer
        company_summary: Summary of the company (optional)
        
    Returns:
        str: The generated email body in Japanese
        
    Raises:
        RuntimeError: If GEMINI_API_KEY is not set
    """
    my_company_pitch = """私たちは、生成AIやアジャイル開発手法を活用し、現場業務を支援するオーダーメイドツールの開発に取り組んでいる、学生発のAIスタートアップ「株式会社 日本自動化技術」です。
現在、製造業の現場における課題やお困りごとについて、幅広くヒアリングを実施しております。
たとえば、以下のようなお悩みはありませんか？
日報や在庫管理が紙やExcel中心で煩雑になっている
熟練者に依存した作業が多く、技術継承や属人化の解消が難しい
新しい設備の導入や改修が"ぶっつけ本番"になりがちで、事前検証が困難
これまで「DXには多額の投資が必要」と導入を見送られてきた企業様にも、
私たちは従来の1/3以下のコストで、現場に本当にフィットする高精度なツールを、短期間でご提供できる可能性があります。
この背景には、私たちが持つ生成AIの技術力と柔軟な開発体制があります。"""
    
    is_mfg = "はい" if is_manufacturer else "いいえ"
    
    email_prompt = f"""
あなたは丁寧なビジネスメール生成AIです。

{my_company_pitch}

会社名: {company_name}
会社概要: {company_summary}
製造業フラグ: {is_mfg}

・上記情報に基づいて 400〜500 字の日本語メール本文を作成する
・件名は「現場DXに関するヒアリングのお願い」で固定
・敬語・改行・箇条書きを適宜使用
・最後にカレンダー予約リンクを記載
・メール本文のみを出力し、件名や署名は含めない
"""
    
    try:
        response = _call_gemini_with_retry(
            email_prompt, 
            temperature=0.4, 
            max_tokens=600
        )
        
        if not response:
            logger.warning("Failed to generate email from LLM. Returning empty string.")
            return ""
        
        email_body = response.strip()
        
        email_body = email_body.replace("\n\n", "\n")
        
        return email_body
        
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"Error drafting email: {str(e)}")
        logger.error(traceback.format_exc())
        return ""
