import argparse
import csv
import logging
from typing import Dict, List, Optional

from dotenv import load_dotenv

from mcp_server.utils import fetch_text, find_email, has_contact
from mcp_server.llm import (
    classify_manufacturer,
    draft_email,
    generate_company_impression,
    generate_pain_points,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# CSV 入出力
# ────────────────────────────────────────────────────────────────────────────
def read_input_csv(filepath: str) -> List[Dict[str, str]]:
    companies: List[Dict[str, str]] = []
    with open(filepath, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or {"company", "website"} - set(reader.fieldnames):
            raise ValueError("CSV must have 'company' and 'website' columns.")
        for row in reader:
            companies.append({"company": row["company"], "website": row["website"]})
    return companies


def write_output_csv(filepath: str, data: List[Dict[str, Optional[str]]]) -> None:
    fieldnames = [
        "company_name",
        "website",
        "manufacturer",
        "email_address",
        "contact_url",
        "mail_content",
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


# ────────────────────────────────────────────────────────────────────────────
# 個別サイト処理
# ────────────────────────────────────────────────────────────────────────────
def process_website(url: str, company_name: str, row_num: int) -> Dict[str, Optional[str]]:
    logger.info("Processing row %d: %s (%s)", row_num, company_name, url)
    result: Dict[str, Optional[str]] = {
        "company_name": company_name,
        "website": url,
        "manufacturer": False,
        "email_address": None,
        "contact_url": None,
        "mail_content": None,
    }

    if not url or not url.strip():
        logger.warning(f"Row {row_num}: No URL provided for company '{company_name}'. Skipping.")
        return result

    try:
        html, text = fetch_text(url)
        if not text:
            return result

        is_manuf = classify_manufacturer(text)
        result["manufacturer"] = is_manuf  # ★ 判定結果を保存

        if not is_manuf:
            # メーカーでなければ空欄のまま返却
            return result

        # ① 感銘文
        impression = generate_company_impression(text)

        # ② 会社固有のお困りごと bullet
        pain_points = generate_pain_points(text)

        # ③ メール本文生成
        mail_content = draft_email(company_name, impression, pain_points)

        # ④ 連絡先 URL / メール抽出
        contact_url = has_contact(html, url)
        email = None
        if contact_url:
            contact_html, _ = fetch_text(contact_url)
            email = find_email(contact_html) or find_email(html)
        else:
            email = find_email(html)

        result.update(
            {
                "email_address": email,
                "contact_url": contact_url,
                "mail_content": mail_content,
            }
        )
        return result

    except Exception as exc:  # noqa: BLE001
        logger.error("Error processing %s (%s): %s", company_name, url, exc)
        return result


# ────────────────────────────────────────────────────────────────────────────
# メイン
# ────────────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser("Simple company analyzer (auto‑email)")
    ap.add_argument("-i", "--input", required=True, help="CSV with 'company','website'")
    ap.add_argument("-o", "--output", default="output_simple.csv", help="output CSV")
    args = ap.parse_args()

    companies = read_input_csv(args.input)[0:150]
    results: List[Dict[str, Optional[str]]] = []

    for idx, c in enumerate(companies, start=1):
        res = process_website(c["website"], c["company"], idx)
        results.append(res)

    write_output_csv(args.output, results)
    logger.info("Processing finished.")


if __name__ == "__main__":
    main()
