import re
from bs4 import BeautifulSoup, Comment



def clean_html(raw_html):
    soup = BeautifulSoup(raw_html, "lxml")
    
    # Prevent extremely large pages from blowing memory
    if len(raw_html) > 8_000_000:
        raw_html = raw_html[:8_000_000]
    
    # Remove Wayback banner
    banner = soup.find(id="wm-ipp")
    if banner:
        banner.decompose()

    # Remove style + noscript only
    for tag in soup(["style", "noscript"]):
        tag.decompose()

    # Strip inline script content but KEEP script tags with src
    for script in soup.find_all("script"):
        if not script.get("src"):
            script.string = ""

    # Remove comments
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    html_str = str(soup)

    # Remove Wayback URL prefixes
    html_str = re.sub(r"https?://web\.archive\.org/web/\d+/", "", html_str)

    # Put each tag on its own line so difflib has meaningful units to compare
    html_str = re.sub(r">\s+<", ">\n<", html_str)

    # Collapse spaces and tabs only (do NOT collapse newlines)
    html_str = re.sub(r"[ \t]+", " ", html_str)

    return html_str.strip().splitlines()
