#!/usr/bin/env python3

import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import anthropic
from datetime import date
import warnings
import os
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY")
GMAIL_ADDRESS      = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def shorten_url(url: str) -> str:
    """is.gd API – ingyenes, korlátlan URL rövidítés."""
    try:
        resp = requests.get(
            "https://is.gd/create.php",
            params={"format": "simple", "url": url},
            timeout=5
        )
        if resp.status_code == 200 and resp.text.startswith("https://is.gd/"):
            return resp.text.strip()
    except:
        pass
    return url


def get_telex_news() -> list[dict]:
    resp = requests.get("https://telex.hu/rss", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")

    articles = []
    for item in soup.find_all("item"):
        title = item.find("title")
        desc  = item.find("description")
        link = ""
        link_tag = item.find("link")
        if link_tag:
            next_sib = link_tag.next_sibling
            if next_sib:
                link = str(next_sib).strip()
        if title and len(title.get_text(strip=True)) > 20:
            articles.append({
                "title": title.get_text(strip=True),
                "link": link,
                "desc": desc.get_text(strip=True) if desc else "",
                "source": "Telex"
            })
        if len(articles) >= 10:
            break
    return articles


def get_444_news() -> list[dict]:
    resp = requests.get("https://444.hu", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")

    articles = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("https://444.hu/2"):
            continue
        title = a.get_text(strip=True)
        if len(title) < 20 or href in seen:
            continue
        seen.add(href)
        articles.append({
            "title": title,
            "link": href,
            "desc": "",
            "source": "444"
        })
        if len(articles) >= 10:
            break
    return articles


def summarize_with_claude(telex: list[dict], news444: list[dict]) -> list[dict]:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    all_articles = telex + news444
    articles_text = ""
    for i, a in enumerate(all_articles):
        articles_text += f"{i}. [{a['source']}] {a['title']}\n"
        if a['desc']:
            articles_text += f"   {a['desc']}\n"
        articles_text += f"   Link: {a['link']}\n\n"

    prompt_template = open(os.path.join(os.path.dirname(__file__), "news-prompt.md"), encoding="utf-8").read()
    prompt = prompt_template.replace("{articles}", articles_text)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )

    import json, re
    raw = message.content[0].text
    raw = re.sub(r"```json|```", "", raw).strip()
    selected = json.loads(raw)

    results = []
    for item in selected:
        idx = item["index"]
        if 0 <= idx < len(all_articles):
            article = all_articles[idx].copy()
            article["summary"] = item["summary"]
            results.append(article)
    return results


def send_email(articles: list[dict]):
    today = date.today().strftime("%Y. %m. %d.")

    source_colors = {"Telex": "#00A651", "444": "#00A651"}
    source_text_colors = {"Telex": "#000000", "444": "#000000"}
    source_bg_colors = {"Telex": "#00A651", "444": "#1A1A1A"}

    items_html = ""
    for a in articles:
        color = source_colors.get(a["source"], "#00A651")
        badge_bg = source_bg_colors.get(a["source"], "#00A651")
        arrow_bg = "#00A651" if a["source"] == "Telex" else "#1A1A1A"
        link_html = f'<a href="{a["link"]}" style="display:inline-block; margin-top:10px; font-size:12px; color:#ffffff; background:{arrow_bg}; padding:4px 12px; border-radius:3px; text-decoration:none; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Tovább olvasom</a>' if a["link"] else ""
        items_html += f"""
        <div style="margin-bottom:0; padding:24px 28px; border-bottom:1px solid #e8e8e8;">
            <div style="margin-bottom:8px;">
                <span style="font-size:11px; font-weight:700; color:#fff; background:{badge_bg}; padding:2px 8px; border-radius:2px; text-transform:uppercase; letter-spacing:0.8px;">{a['source']}</span>
            </div>
            <div style="font-family:Georgia, serif; font-size:18px; font-weight:700; color:#1a1a1a; line-height:1.3; margin-bottom:10px;">{a['title']}</div>
            <div style="font-size:14px; color:#555; line-height:1.6;">{a['summary']}</div>
            {link_html}
        </div>
        """

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background:#f0f0f0; font-family:Arial, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f0f0; padding:24px 0;">
    <tr><td align="center">
      <table width="620" cellpadding="0" cellspacing="0" style="background:#fff; border-radius:4px; overflow:hidden; box-shadow:0 1px 4px rgba(0,0,0,0.1);">

        <!-- NEWS ITEMS -->
        <tr><td>{items_html}</td></tr>

        <!-- FOOTER -->
        <tr>
          <td style="background:#f8f8f8; padding:16px 28px; border-top:1px solid #e8e8e8;">
            <div style="font-size:11px; color:#999; text-align:center;">
              {today} · <a href="https://telex.hu" style="color:#999;">telex.hu</a> · <a href="https://444.hu" style="color:#999;">444.hu</a>
            </div>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    text_lines = [f"Magyar Hírek – {today}\n"]
    for i, a in enumerate(articles, 1):
        text_lines.append(f"{i}. [{a['source']}] {a['title']}")
        text_lines.append(f"   {a['summary']}")
        if a["link"]:
            text_lines.append(f"   {a['link']}")
        text_lines.append("")
    text_body = "\n".join(text_lines)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📰 Daily News – {today}"
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = GMAIL_ADDRESS
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, GMAIL_ADDRESS, msg.as_string())

    print(f"✅ Email sent: {GMAIL_ADDRESS}")


def main():
    print("📡 Downloading news...")
    telex   = get_telex_news()
    news444 = get_444_news()
    print(f"   Telex: {len(telex)} articles, 444: {len(news444)} articles")

    print("🤖 Claude is creating summaries...")
    articles = summarize_with_claude(telex, news444)
    for i, a in enumerate(articles, 1):
        print(f"{i}. [{a['source']}] {a['title']}")
        print(f"   {a['summary']}")
        print(f"   {a['link']}\n")

    print("📧 Sending email...")
    for a in articles:
        if a["link"]:
            a["link"] = shorten_url(a["link"])
    send_email(articles)


if __name__ == "__main__":
    main()
