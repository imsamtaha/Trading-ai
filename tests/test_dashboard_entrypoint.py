"""Regressions for the actual page served at the production root."""
from html.parser import HTMLParser

from app.dashboard import _atlas_ultimate_html


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = {}
        self.scripts = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            assert attrs["id"] not in self.elements, attrs["id"]
            self.elements[attrs["id"]] = (tag, attrs)
        if tag == "script" and "src" in attrs:
            self.scripts.append(attrs["src"])


def test_account_and_market_navigation_targets_exist_on_canonical_page():
    page = Page(_atlas_ultimate_html())
    # These links used to point to IDs that string replacement never inserted.
    for target in ("hub-account", "hub-markets"):
        assert target in page.elements, f"Broken navigation target: {target}"


def test_oauth_callback_page_contains_the_auth_bundle_dom_contract():
    page = Page(_atlas_ultimate_html())
    # OAuth redirects to /; that page must expose the controls the bundle binds.
    for target in ("account", "google-sign-in", "google-sign-out", "account-status"):
        assert target in page.elements, f"Missing auth element: {target}"
    assert page.elements["google-sign-in"][0] == "button"
    assert page.elements["account-status"][1].get("role") == "status"
    assert page.scripts.count("/assets/google-auth.js") == 1
