#!/usr/bin/env python3
"""Journal issue abstract extractor (dependency-light).

Given one issue URL, discover likely article links, parse article metadata/abstract,
and export one-row-per-paper records to CSV (and optional XLSX if openpyxl exists).
"""

from __future__ import annotations

import argparse
import csv
import re
import time
from dataclasses import asdict, dataclass
from html import unescape
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class PaperRow:
    title: str = ""
    journal: str = ""
    author: str = ""
    abstract: str = ""
    conclusion: str = ""
    Y: str = ""
    X: str = ""
    IV: str = ""
    data: str = ""
    method: str = ""
    country: str = ""
    population: str = ""
    source_url: str = ""


class IssueScraper:
    def __init__(self, delay: float = 0.8, timeout: int = 20) -> None:
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def get_soup(self, url: str) -> BeautifulSoup:
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")

    def extract_article_links(self, issue_url: str, max_links: int | None = None) -> list[str]:
        soup = self.get_soup(issue_url)
        base = f"{urlparse(issue_url).scheme}://{urlparse(issue_url).netloc}"

        links: set[str] = set()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            full = urljoin(base, href)
            text = a.get_text(" ", strip=True).lower()
            if any(p in full.lower() for p in ["/article", "/doi/", "/abs", "/full", "research"]):
                links.add(full)
            elif any(k in text for k in ["article", "abstract", "full text", "research"]):
                links.add(full)

        domain = urlparse(issue_url).netloc
        out: list[str] = []
        for u in sorted(links):
            pu = urlparse(u)
            if pu.netloc != domain:
                continue
            if any(u.lower().endswith(ext) for ext in (".jpg", ".png", ".css", ".js", ".zip", ".pdf")):
                continue
            out.append(u)

        return out[:max_links] if max_links else out

    @staticmethod
    def normalize(text: str) -> str:
        return re.sub(r"\s+", " ", unescape(text or "")).strip()

    def extract_text_by_selectors(self, soup: BeautifulSoup, selectors: Iterable[str]) -> str:
        for sel in selectors:
            if sel.startswith("meta:"):
                name = sel.split(":", 1)[1]
                m = soup.select_one(f"meta[name='{name}']")
                if m and m.get("content"):
                    return self.normalize(str(m["content"]))
                continue
            node = soup.select_one(sel)
            if node:
                return self.normalize(node.get_text(" ", strip=True))
        return ""

    def extract_authors(self, soup: BeautifulSoup) -> str:
        citation = [self.normalize(m.get("content", "")) for m in soup.select("meta[name='citation_author']")]
        citation = [x for x in citation if x]
        if citation:
            return "; ".join(dict.fromkeys(citation))

        for sel in (".authors", ".article-authors", "[class*='author']", "[id*='author']"):
            node = soup.select_one(sel)
            if node:
                text = self.normalize(node.get_text(" ", strip=True))
                if len(text) > 2:
                    return text
        return ""

    def extract_abstract(self, soup: BeautifulSoup) -> str:
        m = soup.select_one("meta[name='citation_abstract'], meta[name='dc.description']")
        if m and m.get("content"):
            return self.normalize(str(m["content"]))
        for sel in ("section.abstract", "div.abstract", "#abstract", "[class*='abstract']", "[id*='abstract']"):
            node = soup.select_one(sel)
            if node:
                text = self.normalize(node.get_text(" ", strip=True))
                if len(text) > 20:
                    return text
        return ""

    def analyze_abstract(self, abstract: str) -> dict[str, str]:
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", abstract) if s.strip()]

        def pick(patterns: list[str]) -> str:
            for s in sents:
                ls = s.lower()
                if any(re.search(p, ls) for p in patterns):
                    return s
            return ""

        return {
            "conclusion": pick([r"conclu", r"we find", r"results? show", r"in sum", r"overall"]),
            "Y": pick([r"outcome", r"dependent variable", r"effect on"]),
            "X": pick([r"independent variable", r"treatment", r"exposure", r"impact of"]),
            "IV": pick([r"instrument", r"instrumental variable", r"iv estimate"]),
            "data": pick([r"dataset", r"data", r"survey", r"sample", r"administrative"]),
            "method": pick([r"regression", r"difference-in-differences", r"did", r"panel", r"randomized", r"machine learning"]),
            "country": pick([r"united states|u\.s\.|china|india|uk|japan|brazil|canada|germany|france"]),
            "population": pick([r"participants?|patients?|households?|firms?|students?|adults?|children"]),
        }

    def parse_article(self, url: str) -> PaperRow:
        soup = self.get_soup(url)
        title = self.extract_text_by_selectors(soup, ["meta:citation_title", "h1", "title"])
        journal = self.extract_text_by_selectors(soup, ["meta:citation_journal_title", "meta:dc.source"])
        author = self.extract_authors(soup)
        abstract = self.extract_abstract(soup)
        analysis = self.analyze_abstract(abstract)
        return PaperRow(title=title, journal=journal, author=author, abstract=abstract, source_url=url, **analysis)


def write_csv(rows: list[PaperRow], output: str) -> None:
    fields = [
        "title", "journal", "author", "abstract", "conclusion", "Y", "X", "IV",
        "data", "method", "country", "population", "source_url",
    ]
    with open(output, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: asdict(r).get(k, "") for k in fields})


def write_xlsx_if_available(rows: list[PaperRow], output: str) -> None:
    try:
        from openpyxl import Workbook
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Output is .xlsx but openpyxl is not installed. Please install openpyxl or use .csv") from exc

    fields = [
        "title", "journal", "author", "abstract", "conclusion", "Y", "X", "IV",
        "data", "method", "country", "population", "source_url",
    ]
    wb = Workbook()
    ws = wb.active
    ws.title = "papers"
    ws.append(fields)
    for r in rows:
        d = asdict(r)
        ws.append([d.get(k, "") for k in fields])
    wb.save(output)


def run(issue_url: str, output: str, max_links: int | None, delay: float) -> None:
    scraper = IssueScraper(delay=delay)
    links = scraper.extract_article_links(issue_url=issue_url, max_links=max_links)
    if not links:
        raise RuntimeError("No candidate article links found. Try a different issue URL.")

    rows: list[PaperRow] = []
    for i, link in enumerate(links, 1):
        try:
            row = scraper.parse_article(link)
            if row.abstract:
                rows.append(row)
            print(f"[{i}/{len(links)}] parsed: {link}")
        except Exception as exc:  # noqa: BLE001
            print(f"[{i}/{len(links)}] failed: {link} -> {exc}")
        time.sleep(delay)

    if not rows:
        raise RuntimeError("No abstracts extracted from candidate links.")

    if output.lower().endswith(".xlsx"):
        write_xlsx_if_available(rows, output)
    else:
        write_csv(rows, output)
    print(f"Saved {len(rows)} papers to: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract abstracts from a journal issue URL.")
    parser.add_argument("issue_url", help="Journal issue URL")
    parser.add_argument("-o", "--output", default="papers.csv", help="Output file (.csv or .xlsx)")
    parser.add_argument("--max-links", type=int, default=80, help="Maximum candidate article links to crawl")
    parser.add_argument("--delay", type=float, default=0.8, help="Delay (seconds) between article requests")
    args = parser.parse_args()
    run(args.issue_url, args.output, args.max_links, args.delay)


if __name__ == "__main__":
    main()
