"""Offline checks for documentation, public discovery assets, and demo boundaries.

Checks local destinations, not Markdown fragments or external URL availability.
JSON-LD checks cover JSON structure and declared context/type, not remote schemas.
"""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

import yaml


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = "https://safetymp.github.io/SOC-2/"
REPOSITORY_PREFIX = "https://github.com/SafetyMP/SOC-2/blob/main/"
PUBLIC_PAGES = {"index.html": PUBLIC_ROOT, "about.html": PUBLIC_ROOT + "about.html"}
INDEX_GUIDES = {"README.md", "docs/README.md", "docs/local-github-assessment.md"}


def reject_json_constant(value: str) -> None:
    """JSON does not permit JavaScript's NaN or Infinity tokens."""
    raise ValueError(f"non-JSON numeric value {value}")


def visible_markdown(text: str) -> str:
    """Remove fenced and inline code while retaining line numbers."""
    lines = []
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            lines.append("")
        elif fence is not None:
            lines.append("")
        else:
            lines.append(re.sub(r"(`+).*?\1", "", line))
    return "\n".join(lines)


def markdown_links(text: str) -> list[tuple[int, str]]:
    """Read inline and reference-style destinations used by repository docs."""
    text = visible_markdown(text)
    links = []
    references = {}
    for number, line in enumerate(text.splitlines(), 1):
        definition = re.match(r"^\s{0,3}\[([^\]]+)\]:\s*(<[^>]+>|\S+)", line)
        if definition:
            target = definition.group(2).strip("<>")
            references[" ".join(definition.group(1).lower().split())] = target
            links.append((number, target))
            continue
        for start in re.finditer(r"\]\(", line):
            pos = start.end()
            depth = 1
            end = pos
            while end < len(line) and depth:
                if line[end] == "\\":
                    end += 2
                    continue
                if line[end] == "(":
                    depth += 1
                elif line[end] == ")":
                    depth -= 1
                end += 1
            if depth:
                continue
            destination = line[pos:end - 1].strip()
            if destination.startswith("<") and ">" in destination:
                destination = destination[1:destination.index(">")]
            else:
                destination = destination.split(maxsplit=1)[0] if destination else ""
            links.append((number, re.sub(r"\\([() ])", r"\1", destination)))
    # Definitions are checked even when they occur after their references.
    for number, line in enumerate(text.splitlines(), 1):
        for match in re.finditer(r"\[([^\]]+)\](?:\[([^\]]*)\])?", line):
            key = match.group(2) or match.group(1)
            target = references.get(" ".join(key.lower().split()))
            if target:
                links.append((number, target))
    return list(dict.fromkeys(links))


def local_link_error(source: Path, target: str, root: Path,
                     *, html: bool = False) -> str | None:
    """Return a problem for a local link; external URLs and fragments are skipped."""
    try:
        parsed = urlsplit(target)
    except ValueError:
        return f"invalid URL {target!r}"
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    path = unquote(parsed.path)
    if path.startswith("/"):
        if html:
            prefix = urlsplit(PUBLIC_ROOT).path
            if not path.startswith(prefix):
                return f"site-relative link escapes the GitHub Pages project: {target}"
            path = path[len(prefix):]
        destination = root / path.lstrip("/")
    else:
        destination = source.parent / path
    destination = destination.resolve()
    if not destination.is_relative_to(root.resolve()):
        return f"local link escapes the checked root: {target}"
    if html and destination.is_dir():
        destination /= "index.html"
    if not destination.exists():
        return f"missing local destination: {target}"
    return None


def check_markdown(path: Path, root: Path) -> list[str]:
    errors = []
    for line, target in markdown_links(path.read_text(encoding="utf-8")):
        problem = local_link_error(path, target, root)
        if problem:
            errors.append(f"{path.relative_to(root)}:{line}: {problem}")
    return errors


class Page(HTMLParser):
    """Collect HTML metadata and local resources without executing scripts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[int, str]] = []
        self.canonicals: list[str] = []
        self.metadata: dict[str, list[str]] = {}
        self.titles: list[str] = []
        self.structured_data: list[str] = []
        self._capture: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        for key in ("href", "src", "poster"):
            if attr.get(key) is not None:
                self.links.append((self.getpos()[0], attr[key] or ""))
        if attr.get("srcset") and not attr["srcset"].startswith("data:"):
            for candidate in attr["srcset"].split(","):
                if candidate.strip():
                    self.links.append((self.getpos()[0], candidate.strip().split()[0]))
        if tag == "link" and "canonical" in (attr.get("rel") or "").split():
            self.canonicals.append(attr.get("href") or "")
        if tag == "meta":
            key = attr.get("property") or attr.get("name")
            if key:
                self.metadata.setdefault(key, []).append(attr.get("content") or "")
        if tag == "title" or (tag == "script" and attr.get("type") == "application/ld+json"):
            self._capture = tag
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._capture == tag:
            value = "".join(self._parts).strip()
            if tag == "title":
                self.titles.append(value)
            else:
                self.structured_data.append(value)
            self._capture = None


def check_html(path: Path, public_dir: Path, canonical: str,
               *, require_jsonld: bool = False) -> list[str]:
    page = Page()
    page.feed(path.read_text(encoding="utf-8"))
    label = f"demo/{path.name}"
    errors = []
    if page.canonicals != [canonical]:
        errors.append(f"{label}: expected one canonical URL {canonical!r}, got {page.canonicals!r}")
    if len(page.titles) != 1 or not page.titles[0]:
        errors.append(f"{label}: expected one nonempty title")
    required = ("description", "og:type", "og:site_name", "og:title", "og:description",
                "og:url", "twitter:card", "twitter:title", "twitter:description")
    for key in required:
        values = page.metadata.get(key, [])
        if len(values) != 1 or not values[0].strip():
            errors.append(f"{label}: expected one nonempty {key} metadata value")
    if page.metadata.get("og:url") != [canonical]:
        errors.append(f"{label}: og:url must match its canonical URL")
    for line, target in page.links:
        problem = local_link_error(path, target, public_dir, html=True)
        if problem:
            errors.append(f"{label}:{line}: {problem}")
    if require_jsonld and not page.structured_data:
        errors.append(f"{label}: missing JSON-LD project metadata")
    for number, value in enumerate(page.structured_data, 1):
        try:
            data = json.loads(value, parse_constant=reject_json_constant)
            entries = data if isinstance(data, list) else [data]
            if not entries or any(not isinstance(entry, dict) or not entry.get("@context")
                                  or not (entry.get("@type") or entry.get("@graph"))
                                  for entry in entries):
                raise ValueError("expected objects with @context and @type or @graph")
            for entry in entries:
                if "url" in entry and entry["url"] != canonical:
                    raise ValueError("url must match the page canonical")
        except (ValueError, TypeError) as exc:
            errors.append(f"{label}: invalid JSON-LD block {number}: {exc}")
    return errors


def check_sitemap(path: Path, expected: set[str]) -> list[str]:
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except (OSError, ET.ParseError) as exc:
        return [f"demo/sitemap.xml: cannot parse sitemap: {exc}"]
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    if root.tag != ns + "urlset":
        return ["demo/sitemap.xml: expected the sitemap namespace and a urlset root"]
    if any(child.tag != ns + "url" for child in root):
        return ["demo/sitemap.xml: urlset must contain only url entries"]
    entries = root.findall(ns + "url")
    urls = [(entry.findtext(ns + "loc") or "").strip() for entry in entries]
    if set(urls) != expected or len(urls) != len(expected):
        return [f"demo/sitemap.xml: expected exactly the canonical HTML URLs {sorted(expected)}, got {urls}"]
    if any(len(entry.findall(ns + "loc")) != 1 for entry in entries):
        return ["demo/sitemap.xml: each url entry must contain exactly one loc"]
    return []


def check_index(path: Path, root: Path) -> list[str]:
    label = str(path.relative_to(root))
    if not path.is_file() or not path.read_text(encoding="utf-8").strip():
        return [f"{label}: missing or empty project reading index"]
    errors = []
    guides = set()
    for line, target in markdown_links(path.read_text(encoding="utf-8")):
        if target.startswith(REPOSITORY_PREFIX):
            local = unquote(urlsplit(target).path.split("/blob/main/", 1)[1])
            guides.add(local)
            destination = (root / local).resolve()
            if not destination.is_relative_to(root.resolve()) or not destination.exists():
                errors.append(f"{label}:{line}: missing indexed repository source: {local}")
        elif target.startswith(PUBLIC_ROOT):
            relative = urlsplit(target).path[len(urlsplit(PUBLIC_ROOT).path):] or "index.html"
            if relative not in PUBLIC_PAGES:
                errors.append(f"{label}:{line}: unknown public project page: {target}")
        else:
            problem = local_link_error(path, target, root)
            if problem:
                errors.append(f"{label}:{line}: {problem}")
            if not urlsplit(target).scheme:
                local = (path.parent / unquote(urlsplit(target).path)).resolve()
                if local.is_relative_to(root.resolve()):
                    guides.add(str(local.relative_to(root.resolve())))
    for guide in sorted(INDEX_GUIDES - guides):
        errors.append(f"{label}: missing link to current guide {guide}")
    return errors


def check_sample(path: Path) -> list[str]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_json_constant)
    except (OSError, ValueError) as exc:
        return [f"demo/data/sample-report.json: cannot read sample report: {exc}"]
    if not isinstance(report, dict) or report.get("mode") != "fixture":
        return ["demo/data/sample-report.json: public sample mode must be fixture"]
    return []


def check_compose(path: Path) -> list[str]:
    """Optional development services must bind every published port to loopback."""
    if not path.exists():
        return []
    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        services = config["services"]
        if not isinstance(services, dict):
            raise ValueError("services must be a mapping")
    except (OSError, ValueError, TypeError, KeyError, yaml.YAMLError) as exc:
        return [f"docker-compose.yml: cannot read services: {exc}"]
    errors = []
    for name, service in services.items():
        if not isinstance(service, dict):
            errors.append(f"docker-compose.yml: service {name} must be a mapping")
            continue
        if service.get("network_mode") == "host":
            errors.append(f"docker-compose.yml: service {name} uses unrestricted host networking")
        ports = service.get("ports", []) or []
        if not isinstance(ports, list):
            errors.append(f"docker-compose.yml: service {name} ports must be a list")
            continue
        for port in ports:
            host = ""
            if isinstance(port, dict):
                host = str(port.get("host_ip", ""))
            elif isinstance(port, str):
                parts = port.rsplit(":", 2)
                if len(parts) == 3:
                    host = parts[0].strip("[]")
            try:
                loopback = ipaddress.ip_address(host).is_loopback
            except ValueError:
                loopback = False
            if not loopback:
                errors.append(f"docker-compose.yml: service {name} port {port!r} needs an explicit loopback host IP")
    return errors


def markdown_paths(root: Path) -> list[Path]:
    """Include tracked Markdown and pending unignored additions, including .github."""
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others",
         "--exclude-standard", "--", "*.md"],
        capture_output=True, check=False,
    )
    if result.returncode:
        raise RuntimeError("cannot list repository Markdown with git ls-files")
    return sorted({root / name.decode("utf-8") for name in result.stdout.split(b"\0")
                   if name and (root / name.decode("utf-8")).is_file()})


def check_repository(root: Path) -> tuple[list[str], int]:
    errors = []
    paths = markdown_paths(root)
    for path in paths:
        errors.extend(check_markdown(path, root))
    for name, canonical in PUBLIC_PAGES.items():
        path = root / "demo" / name
        if not path.is_file():
            errors.append(f"demo/{name}: required public HTML page is missing")
            continue
        errors.extend(check_html(path, root / "demo", canonical, require_jsonld=name == "about.html"))
    errors.extend(check_sitemap(root / "demo/sitemap.xml", set(PUBLIC_PAGES.values())))
    for relative in ("llms.txt", "demo/llms.txt"):
        errors.extend(check_index(root / relative, root))
    errors.extend(check_sample(root / "demo/data/sample-report.json"))
    errors.extend(check_compose(root / "docker-compose.yml"))
    return errors, len(paths)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository checkout to validate")
    args = parser.parse_args()
    try:
        errors, count = check_repository(args.root.resolve())
    except (OSError, UnicodeError, RuntimeError) as exc:
        print(f"repository check: {exc}", file=sys.stderr)
        return 1
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print(f"repository check: {len(errors)} problem(s)", file=sys.stderr)
        return 1
    print(f"repository check: {count} Markdown files, 2 public pages, discovery indexes, fixture mode, and local port bindings OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
