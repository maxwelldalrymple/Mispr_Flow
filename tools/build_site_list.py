"""Write mispr/assets/sites.txt: the ~1,000 most popular websites people visit, so a misheard
site name ("you two tab", "chat gbt dot com") can be assumed to be the real one.

Source: the Majestic Million (https://majestic.com/reports/majestic-million, CC BY 3.0),
ranked by links, minus technical domains nobody visits (ad, analytics, CDN, font, link-shortener
and API hosts), plus popular apps it ranks low (ChatGPT, Claude, Notion…).

    curl -s https://downloads.majestic.com/majestic_million.csv | head -n 3000 > /tmp/mm.csv
    .venv/bin/python tools/build_site_list.py /tmp/mm.csv
"""

import csv
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "mispr" / "assets" / "sites.txt"
TARGET = 1000

# Hosts that serve pages' parts, not pages people open.
TECHNICAL = re.compile(
    r"(?:^|\.)(?:googletagmanager|googleapis|gstatic|googleusercontent|googlesyndication|googleadservices|doubleclick|"
    r"google-analytics|ggpht|ytimg|fbcdn|cdninstagram|twimg|akamai\w*|cloudfront|cloudflare\w*|fastly\w*|jsdelivr|unpkg|"
    r"jquery|bootstrapcdn|fontawesome|typekit|gravatar|addthis|sharethis|disqus|recaptcha|hotjar|newrelic|segment|"
    r"amazonaws|azureedge|edgekey|edgesuite|schema|ogp|w3|gmpg|feedburner|statcounter|histats|sitemeter|"
    r"wp|s\.w|creativecommons|nginx|f5|apache|php|mysql|digicert|letsencrypt|godaddysites|europa)\.|"
    r"^(?:goo\.gl|youtu\.be|t\.me|wa\.me|bit\.ly|t\.co|ow\.ly|tinyurl\.com|maps\.app\.goo\.gl|lnkd\.in|fb\.me|amzn\.to|"
    r"buff\.ly|is\.gd|rebrand\.ly)$|^(?:api|cdn|static|fonts|img|images|assets|policies|support|accounts|play)\.|\.gov\.|"
    r"\.(?:gov|mil|int)$")

EXTRA = """chatgpt.com claude.ai gemini.google.com perplexity.ai notion.so figma.com slack.com discord.com
reddit.com netflix.com spotify.com twitch.tv mail.google.com calendar.google.com meet.google.com
docs.google.com drive.google.com sheets.google.com outlook.com outlook.live.com teams.microsoft.com
zoom.us canva.com airbnb.com uber.com doordash.com ebay.com etsy.com walmart.com target.com
stackoverflow.com medium.com substack.com quora.com duckduckgo.com bing.com yahoo.com hulu.com
disneyplus.com primevideo.com max.com paypal.com venmo.com coinbase.com robinhood.com chase.com
bankofamerica.com wellsfargo.com notion.com trello.com asana.com monday.com linear.app vercel.com
gitlab.com bitbucket.org npmjs.com pypi.org huggingface.co openai.com anthropic.com cursor.com
espn.com nytimes.com cnn.com bbc.com bbc.co.uk theguardian.com weather.com zillow.com indeed.com
glassdoor.com duolingo.com khanacademy.org coursera.org udemy.com icloud.com""".split()


def main(source):
    sites, seen = [], set()
    for site in EXTRA:
        if site not in seen:
            seen.add(site)
            sites.append(site)
    with open(source, newline="") as f:
        for row in csv.DictReader(f):
            domain = row["Domain"].lower().strip()
            if domain in seen or TECHNICAL.search(domain) or len(sites) >= TARGET:
                continue
            seen.add(domain)
            sites.append(domain)
    OUT.write_text("# The most visited websites (Majestic Million, CC BY 3.0, filtered; tools/build_site_list.py)\n"
                   + "\n".join(sites) + "\n")
    print(f"{len(sites)} sites -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
