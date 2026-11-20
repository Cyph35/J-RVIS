import re
import webbrowser
from urllib.parse import quote_plus, urlparse


def open_website(url: str) -> str:
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    host = parsed.hostname or ""
    valid_host = host == "localhost" or ("." in host and re.fullmatch(r"[a-z0-9.-]+", host, re.I))
    if parsed.scheme not in ("http", "https") or not valid_host or " " in url:
        raise ValueError(f"Not a valid web address: {url!r}")
    if not webbrowser.open(url):
        raise RuntimeError("The browser could not be opened.")
    return f"Opened {url}"


def search_web(query: str) -> str:
    query = query.strip()
    if not query:
        raise ValueError("Search query is empty.")
    return open_website("https://www.google.com/search?q=" + quote_plus(query))
