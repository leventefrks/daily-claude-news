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

    prompt_template = open(os.path.join(os.path.dirname(__file__), "prompt.js"), encoding="utf-8").read()

    import re as _re
    match = _re.search(r'module\.exports\s*=\s*`(.*?)`;', prompt_template, _re.DOTALL)
    prompt = match.group(1).replace("{articles}", articles_text) if match else articles_text

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

    items_html = ""
    for i, a in enumerate(articles, 1):
        link_html = f'<a href="{a["link"]}" style="color:#1a73e8;">{a["link"]}</a>' if a["link"] else ""
        items_html += f"""
        <div style="margin-bottom:20px; padding:12px; border-left:4px solid #1a73e8; background:#f9f9f9;">
            <div style="font-size:13px; color:#888; margin-bottom:4px;">{i}. [{a['source']}]</div>
            <div style="font-weight:bold; font-size:15px; margin-bottom:6px;">{a['title']}</div>
            <div style="font-size:14px; color:#333; margin-bottom:6px;">{a['summary']}</div>
            <div style="font-size:12px;">{link_html}</div>
        </div>
        """

    html_body = f"""
    <html><body style="font-family:Arial; max-width:650px; margin:auto; padding:20px;">
    <h2 style="color:#333;">📰 Daily News Summary – {today}</h2>
    <hr style="margin-bottom:20px;">
    {items_html}
    <hr>
    <small style="color:#999;">Source: telex.hu | 444.hu</small>
    </body></html>
    """

    text_lines = [f"📰 Daily News Summary – {today}\n"]
    for i, a in enumerate(articles, 1):
        text_lines.append(f"{i}. [{a['source']}] {a['title']}")
        text_lines.append(f"   {a['summary']}")
        if a["link"]:
            text_lines.append(f"   {a['link']}")
        text_lines.append("")
    text_body = "\n".join(text_lines)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📰 Daily News Summary – {today}"
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
    send_email(articles)


if __name__ == "__main__":
    main()
