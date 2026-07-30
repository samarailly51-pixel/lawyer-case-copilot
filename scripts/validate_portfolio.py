from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        attribute = "href" if tag in {"a", "link"} else "src" if tag in {"img", "script", "source", "video"} else None
        if attribute and values.get(attribute):
            self.references.append(values[attribute] or "")


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "portfolio"
    index = root / "index.html"
    if not index.exists():
        print("portfolio/index.html 不存在", file=sys.stderr)
        return 1
    parser = AssetParser()
    parser.feed(index.read_text(encoding="utf-8"))
    missing: list[str] = []
    for reference in parser.references:
        parsed = urlparse(reference)
        if parsed.scheme or reference.startswith("#"):
            continue
        relative = parsed.path.removeprefix("./")
        target = root / relative
        if not target.exists() or (target.is_file() and target.stat().st_size == 0):
            missing.append(reference)
    if missing:
        print("作品集存在缺失或空资源：", "、".join(missing), file=sys.stderr)
        return 1
    if not (root / ".nojekyll").exists():
        print("portfolio/.nojekyll 不存在", file=sys.stderr)
        return 1
    print(f"作品集校验通过：{len(parser.references)} 个链接或资源引用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
