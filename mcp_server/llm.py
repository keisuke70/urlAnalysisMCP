import os
import time
import logging
import traceback
from typing import Optional

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY = 2


# ────────────────────────────────────────────────────────────────────────────
# Gemini 基本処理
# ────────────────────────────────────────────────────────────────────────────
def _initialize_gemini() -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    genai.configure(api_key=api_key)


def _call_gemini_with_retry(prompt: str, model: str = "gemini-2.0-flash") -> Optional[str]:
    _initialize_gemini()
    for attempt in range(MAX_RETRIES):
        try:
            model_instance = genai.GenerativeModel(model)
            response = model_instance.generate_content(prompt)
            return response.text
        except Exception as e:  # noqa: BLE001
            err = str(e).lower()
            if "429" in err or "rate limit" in err or "quota" in err:
                delay = BASE_DELAY * (2 ** attempt)
                logger.warning("Rate limit. retrying in %s sec (%s/%s)", delay, attempt + 1, MAX_RETRIES)
                time.sleep(delay)
            else:
                logger.error("Gemini error: %s\n%s", e, traceback.format_exc())
                return None
    logger.error("Max retries exceeded.")
    return None


# ────────────────────────────────────────────────────────────────────────────
# 各社向け感銘ポイント生成
# ────────────────────────────────────────────────────────────────────────────
def generate_company_impression(text: str) -> str:
    prompt = f"""
あなたは日本語のビジネスメール AI です。下記の会社紹介・実績を読み、
【フォーマット】に従い 2〜3 文（180〜250 字）で敬語文を作成してください。

【フォーマット】
1行目: 「数ある◯◯会社様の中で＜会社名＞様をお選びした理由は、…ためです。」
2行目以降: 強みや姿勢を 1〜2 点挙げ「特に…と感じております。」で締める

【ルール】
- Web テキスト中の固有名詞や素材・設備等のキーワードを必ず入れる
- 将来的な協業メリット（DX での相性など）を 1 文含める

--- 会社紹介抜粋 ---
{text[:15000]}
"""
    res = _call_gemini_with_retry(prompt)
    return res.strip() if res else ""


# ────────────────────────────────────────────────────────────────────────────
# 各社向け「お困りごと」リスト生成
# ────────────────────────────────────────────────────────────────────────────
_CAPABILITIES = (
    "【弊社の強み】生成AI × アジャイル開発で、"
    "- 図面・工程データの自動取り込み／一元管理 "
    "- 品質検査・在庫・納期の可視化ダッシュボード "
    "- 協力工場とのクラウド情報共有 "
    "- 社内マニュアル特化AIの作成・音声対話 AI による社内マニュアル即時検索・ハンズフリー作業支援 "
    "──を最短 2〜4 週間・1/3 コストで内製化支援できます。"
)

def generate_pain_points(text: str) -> str:
    """
    会社サイトを参考に、**弊社で解決できる** 製造現場の課題を
    “3〜4 行だけ” 箇条書きで生成する。

    出力例
    ●　在庫・納期を可視化して遅延防止
    ●　NC 加工条件をAIで最適化
    ●　検査結果を自動集計し不良低減
    """
    prompt = f"""
あなたは製造業 DX ソリューションのプリセールス AI です。
下記 2 つの情報を読み取り、＜対象会社＞が抱えそうな
「弊社ソリューションで解決できる課題」を **3〜4 行だけ** 箇条書きで作成してください。

{_CAPABILITIES}

【出力ルール】
・行頭は必ず「●　」(全角中黒＋全角空白2つ)  
・**ちょうど 3〜4 行**、改行以外の空行を入れない  
・各行 **全角 25〜35 字以内**、1 行で完結させる  
・抽象語を避け、対象会社の製品・工程キーワードを含める  
・句読点は任意、語尾は「する／できる」などで揃える  
・行末に句点 (。) を **付けない**

--- 対象会社 Web 抜粋 ---
{text[:10000]}
"""
    res = _call_gemini_with_retry(prompt)
    return res.strip() if res else ""


# ────────────────────────────────────────────────────────────────────────────
# 製造業判定
# ────────────────────────────────────────────────────────────────────────────
def classify_manufacturer(text: str) -> bool:
    prompt = f"""
以下のテキストを読み、この会社が「自社で物理的製品を製造しているか」を判定せよ。
YES / NO のみで回答。

【判断指針】
- 自社工場・自社生産ライン等の明記 → YES
- 取扱・販売代理が中心 → NO

--- テキスト ---
{text[:8000]}
"""
    res = _call_gemini_with_retry(prompt)
    return res.strip().upper() == "YES" if res else False


# ────────────────────────────────────────────────────────────────────────────
# メールテンプレート
# ────────────────────────────────────────────────────────────────────────────
CLOSING_BLOCK_HEADER = """つきましては、オンライン（Zoom／Google Meet）にて10～15分ほど、
次のような現場のお困りごとをお聞かせいただけないでしょうか？

"""

CLOSING_BLOCK_FOOTER = """
当社は生成AIを活用したアジャイル開発により、従来の1/3以下のコストで現場にフィットするツールを短期間にご提供できます。
今回のヒアリングは“ご提案”ではなく、“生の声”を伺い最適な方向性を検討するためのものです。

ご興味ございましたら、ご都合の良い日時をいくつかご返信いただくか、下記よりご予約ください。
https://calendar.app.google/jM8gesybkVQEGhww6

何卒よろしくお願い申し上げます。
――――――――――
株式会社日本自動化技術
橋本 武士（はしもと たけし）
https://japan-automation-technology.vercel.app
メール：htakeshi0614@gmail.com
Zoom／Google Meet 対応可
――――――――――
"""


def draft_email(company_name: str, impression_text: str, pain_points_text: str) -> str:
    return (
        f"株式会社{company_name} ご担当者様\n\n"
        "はじめまして。学生発AIスタートアップ「株式会社日本自動化技術」の橋本と申します。"
        "まず本メールはお見積もり依頼ではなく、貴社の現場課題を伺うためのヒアリング依頼であることをお詫び申し上げます。\n\n"
        f"{impression_text}\n\n"
        f"{CLOSING_BLOCK_HEADER}"
        f"{pain_points_text}\n"
        f"{CLOSING_BLOCK_FOOTER}"
    )
