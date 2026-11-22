"""Validate and copy only the public website into out/ for static hosting."""
from html.parser import HTMLParser
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = {"index.html", "centers/index.html", "robots.txt", "assets/site.css", "assets/site.js",
                "assets/demo-model.js", "assets/favicon.svg", "assets/google-auth.js",
                "assets/centers.css", "assets/atlas-brand.css", "assets/atlas-main-logo.svg", "assets/atlas-tiger-shield.png", "assets/atlas-news.js", "assets/just-ai-brand.css", "assets/just-ai-icon.webp", "assets/just-ai-reference.webp"}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            assert attrs["id"] not in self.ids, f"Duplicate id: {attrs['id']}"
            self.ids.add(attrs["id"])
        for key in ("href", "src"):
            if key in attrs:
                self.targets.append(attrs[key])


def validate():
    source = ROOT / "web"
    found = {p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_file()}
    assert found == PUBLIC_FILES, f"Unexpected or missing public files: {found ^ PUBLIC_FILES}"
    for html_file in ("index.html", "centers/index.html"):
        page = (source / html_file).read_text(encoding="utf-8")
        links = Links()
        links.feed(page)
        for target in links.targets:
            if target.startswith("#"):
                assert target[1:] in links.ids, f"Missing anchor: {target}"
            elif target.startswith(("https://justai-atlas.online/sam", "https://justai-atlas.online/traders#market-analysis")):
                assert target in {"https://justai-atlas.online/sam", "https://justai-atlas.online/traders#market-analysis"}, f"Unexpected destination: {target}"
            elif target != "/":
                assert target.lstrip("/") in PUBLIC_FILES, f"Unexpected link: {target}"
    for name in PUBLIC_FILES:
        content = (source / name).read_bytes()
        for forbidden in ("sk_live_", "sk_test_", "sk-proj-", "SUPABASE_SERVICE_ROLE_KEY", "MT5_PASSWORD"):
            assert forbidden.encode() not in content, f"Private configuration in {name}"
    return source


def build():
    source = validate()
    output = ROOT / "out"
    # Fail rather than delete unexpected output left by another task.
    if output.exists():
        found = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()}
        assert found <= PUBLIC_FILES, "Unexpected files in out/; inspect before publishing"
    for name in PUBLIC_FILES:
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, destination)
    print(f"Public website validated: {len(PUBLIC_FILES)} files. Output: out/")


if __name__ == "__main__":
    build()


