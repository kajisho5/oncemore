"""The project site (site/, published by .github/workflows/pages.yml): every
page links only to files that will be there, the two languages point to each
other, and the sharing image is the one in the repository."""

import os
import re
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
SITE = os.path.join(ROOT, "site")
PAGES = {"index.html": "en", os.path.join("ja", "index.html"): "ja"}
URL = "https://kajisho5.github.io/oncemore/"


def published(rel):
    """Where a site path comes from (the workflow copies docs/images in)."""
    if rel.startswith("images/"):
        name = rel[len("images/"):]
        if name == "favicon.svg":
            return os.path.join(ROOT, "oncemore", "gui", "static", "favicon.svg")
        return os.path.join(ROOT, "docs", "images", name)
    return os.path.join(SITE, rel)


class TestSite(unittest.TestCase):
    def read(self, page):
        with open(os.path.join(SITE, page), encoding="utf-8") as f:
            return f.read()

    def test_local_links_resolve(self):
        for page in PAGES:
            html = self.read(page)
            base = os.path.dirname(page)
            for ref in re.findall(r'(?:src|href)="([^"#]+)"', html):
                if ref.startswith(("https://", "mailto:")):
                    continue
                rel = os.path.normpath(os.path.join(base, ref)).replace(os.sep, "/")
                path = published(rel)
                if ref.endswith("/"):
                    path = os.path.join(SITE, rel, "index.html") if rel != "." else \
                        os.path.join(SITE, "index.html")
                self.assertTrue(os.path.exists(path), f"{page}: {ref} -> {path}")

    def test_sharing_image(self):
        for page, lang in PAGES.items():
            html = self.read(page)
            self.assertIn(f'<html lang="{lang}">', html)
            image = re.search(r'property="og:image" content="([^"]+)"', html)[1]
            self.assertTrue(image.startswith(URL + "images/"), image)
            with open(published(image[len(URL):]), "rb") as f:
                head = f.read(24)
            # a PNG of 1280 x 640, the size GitHub and X show best
            self.assertEqual((head[:8], int.from_bytes(head[16:20], "big"),
                              int.from_bytes(head[20:24], "big")),
                             (b"\x89PNG\r\n\x1a\n", 1280, 640))
            self.assertLess(os.path.getsize(published(image[len(URL):])), 1_000_000)
            self.assertIn('name="twitter:card" content="summary_large_image"', html)
            # both languages name each other
            self.assertIn(f'hreflang="en" href="{URL}"', html)
            self.assertIn(f'hreflang="ja" href="{URL}ja/"', html)

    def test_no_third_party_product_names(self):
        for page in PAGES:
            html = self.read(page).lower()
            for name in ("encore", "adobe", "final cut", "dvd studio", "idvd", "dvdstyler"):
                self.assertNotIn(name, html, page)
