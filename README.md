# 📰 Claude Newsroom

An AI-powered newsletter application that uses the Anthropic Claude API to generate content and delivers it via Gmail.

## Requirements

- Python 3.9+
- Anthropic API key
- Gmail account with an app password

## Installation

```bash
git clone https://github.com/yourusername/newsroom.git
cd newsroom
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=sk-ant-...
GMAIL_ADDRESS=example@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

> **Note:** You can generate a Gmail app password in your Google Account:
> Google Account → Security → 2-Step Verification → App Passwords

## Usage

```bash
python main.py
```

The application will:

1. Fetch the latest news from https://wwww.telex.hu & https://www.444.hu
2. Summarize and format it using Claude
3. Send the newsletter to the configured email address

## Security

**Never commit your `.env` file to GitHub.** Make sure it's listed in `.gitignore`:

```
.env
```
