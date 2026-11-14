"""Focused negative cases for offline repository/discovery validation."""

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_repository import (
    PUBLIC_ROOT, check_compose, check_html, check_index, check_markdown,
    check_sample, check_sitemap, markdown_links,
)


class RepositoryChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name: str, text: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def page(self, canonical: str = PUBLIC_ROOT, extra: str = "") -> Path:
        meta = {
            "description": "A project description", "og:type": "website",
            "og:site_name": "Workspace", "og:title": "Project", "og:description": "Details",
            "og:url": canonical, "twitter:card": "summary", "twitter:title": "Project",
            "twitter:description": "Details",
        }
        tags = "".join(f'<meta name="{key}" content="{value}">' for key, value in meta.items())
        return self.write("demo/index.html", f'<title>Project</title><link rel="canonical" href="{canonical}">{tags}{extra}')

    def test_missing_markdown_link_reports_file_and_line(self) -> None:
        path = self.write("docs/guide.md", "# Guide\n[missing](absent.md#section)")
        self.assertEqual(check_markdown(path, self.root),
                         ["docs/guide.md:2: missing local destination: absent.md#section"])

    def test_code_external_urls_and_fragments_are_ignored(self) -> None:
        path = self.write("README.md", """[external](https://example.invalid/missing)
[section](#missing-fragment)
`[example](missing.md)`
```markdown
[example](missing.md)
```
~~~
[example](also-missing.md)
~~~
""")
        self.assertEqual(check_markdown(path, self.root), [])

    def test_reference_links_and_encoded_local_paths_are_checked(self) -> None:
        self.write("docs/my guide.md", "hello")
        path = self.write("README.md", "[guide][ref]\n[ref]: docs/my%20guide.md\n[bad][gone]\n[gone]: absent.md")
        errors = check_markdown(path, self.root)
        self.assertTrue(errors)
        self.assertTrue(all("absent.md" in error for error in errors))
        self.assertIn((1, "docs/my%20guide.md"), markdown_links(path.read_text()))

    def test_parentheses_and_angle_bracket_destinations(self) -> None:
        self.write("docs/design(v2).md", "hello")
        self.write("docs/my guide.md", "hello")
        path = self.write("README.md", '[one](docs/design(v2).md)\n[two](<docs/my guide.md> "Title")')
        self.assertEqual(check_markdown(path, self.root), [])

    def test_wrong_canonical_is_rejected(self) -> None:
        path = self.page("https://example.invalid/")
        errors = check_html(path, path.parent, PUBLIC_ROOT)
        self.assertTrue(any("canonical" in error for error in errors))
        self.assertTrue(any("og:url" in error for error in errors))

    def test_missing_html_asset_is_rejected(self) -> None:
        path = self.page(extra='<script src="./missing.js"></script>')
        self.assertTrue(any("missing.js" in error for error in check_html(path, path.parent, PUBLIC_ROOT)))

    def test_blank_metadata_is_rejected(self) -> None:
        path = self.page()
        path.write_text(path.read_text().replace('content="summary"', 'content="  "'))
        self.assertTrue(any("twitter:card" in error for error in check_html(path, path.parent, PUBLIC_ROOT)))

    def test_invalid_and_missing_jsonld_are_rejected(self) -> None:
        path = self.page(extra='<script type="application/ld+json">{invalid}</script>')
        self.assertTrue(any("invalid JSON-LD" in error for error in check_html(path, path.parent, PUBLIC_ROOT)))
        path = self.page()
        self.assertTrue(any("missing JSON-LD" in error for error in check_html(path, path.parent, PUBLIC_ROOT, require_jsonld=True)))

    def test_valid_metadata_and_local_assets_pass(self) -> None:
        self.write("demo/app.js", "// application")
        path = self.page(extra='<script src="./app.js"></script><a href="./">Home</a><script type="application/ld+json">{"@context":"https://schema.org","@type":"SoftwareSourceCode"}</script>')
        self.assertEqual(check_html(path, path.parent, PUBLIC_ROOT, require_jsonld=True), [])

    def test_sitemap_rejects_json_asset_duplicate_and_invalid_xml(self) -> None:
        urls = [PUBLIC_ROOT, PUBLIC_ROOT + "about.html", PUBLIC_ROOT + "data/sample-report.json"]
        path = self.write("demo/sitemap.xml", '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{url}</loc></url>' for url in urls) + '</urlset>')
        expected = set(urls[:2])
        self.assertTrue(check_sitemap(path, expected))
        path.write_text(path.read_text().replace(urls[2], urls[0]))
        self.assertTrue(check_sitemap(path, expected))
        path.write_text("<not-closed>")
        self.assertTrue(check_sitemap(path, expected))
        path.write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{url}</loc></url>' for url in urls[:2]) + '</urlset>')
        self.assertEqual(check_sitemap(path, expected), [])

    def test_non_json_numeric_constants_are_rejected(self) -> None:
        path = self.page(extra='<script type="application/ld+json">{"@context":"https://schema.org","@type":"SoftwareSourceCode","value":NaN}</script>')
        self.assertTrue(any("non-JSON" in error for error in check_html(path, path.parent, PUBLIC_ROOT)))

    def test_sample_rejects_real_mode(self) -> None:
        path = self.write("demo/data/sample-report.json", '{"mode":"github"}')
        self.assertTrue(check_sample(path))
        path.write_text('{"mode":"fixture"}')
        self.assertEqual(check_sample(path), [])

    def test_indexes_require_current_guides_and_existing_targets(self) -> None:
        path = self.write("llms.txt", "# Index\n[stale](https://github.com/SafetyMP/SOC-2/blob/main/docs/removed.md)")
        errors = check_index(path, self.root)
        self.assertTrue(any("missing indexed repository source" in error for error in errors))
        self.assertTrue(any("missing link to current guide" in error for error in errors))

    def test_compose_rejects_public_and_implicit_bindings(self) -> None:
        path = self.write("docker-compose.yml", 'services:\n  locker:\n    ports: ["9000:9000", "0.0.0.0:9001:9001"]\n')
        self.assertEqual(len(check_compose(path)), 2)
        path.write_text('services:\n  locker:\n    ports:\n      - "127.0.0.1:9000:9000"\n      - target: 9001\n        published: "9001"\n        host_ip: "::1"\n')
        self.assertEqual(check_compose(path), [])

    def test_malformed_compose_ports_produce_an_actionable_error(self) -> None:
        path = self.write("docker-compose.yml", 'services:\n  locker:\n    ports: 9000\n')
        self.assertEqual(check_compose(path), ["docker-compose.yml: service locker ports must be a list"])


if __name__ == "__main__":
    unittest.main()
