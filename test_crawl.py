import unittest

from crawl import (
    get_first_paragraph_from_html,
    get_heading_from_html,
    normalize_url,
)


class TestNormalizeURL(unittest.TestCase):
    def test_normalize_url(self):
        input_url = "https://www.boot.dev/blog/path"
        actual = normalize_url(input_url)
        expected = "www.boot.dev/blog/path"
        self.assertEqual(actual, expected)

    def test_strips_trailing_slash(self):
        actual = normalize_url("https://www.boot.dev/blog/path/")
        self.assertEqual(actual, "www.boot.dev/blog/path")

    def test_strips_http_scheme(self):
        actual = normalize_url("http://www.boot.dev/blog/path")
        self.assertEqual(actual, "www.boot.dev/blog/path")

    def test_strips_http_scheme_and_trailing_slash(self):
        actual = normalize_url("http://www.boot.dev/blog/path/")
        self.assertEqual(actual, "www.boot.dev/blog/path")

    def test_all_variants_match(self):
        urls = [
            "https://www.boot.dev/blog/path/",
            "https://www.boot.dev/blog/path",
            "http://www.boot.dev/blog/path/",
            "http://www.boot.dev/blog/path",
            "HTTPS://WWW.BOOT.DEV/blog/path/",
            "https://www.boot.dev:443/blog/path",
            "  https://www.boot.dev/blog/path  ",
            "www.boot.dev/blog/path",
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(normalize_url(url), "www.boot.dev/blog/path")

    def test_lowercases_host_only(self):
        actual = normalize_url("https://WWW.Boot.Dev/Blog/Path")
        self.assertEqual(actual, "www.boot.dev/Blog/Path")

    def test_strips_query_string(self):
        actual = normalize_url("https://www.boot.dev/blog/path?sort=new&page=2")
        self.assertEqual(actual, "www.boot.dev/blog/path")

    def test_strips_fragment(self):
        actual = normalize_url("https://www.boot.dev/blog/path#section-1")
        self.assertEqual(actual, "www.boot.dev/blog/path")

    def test_strips_query_and_fragment_with_trailing_slash(self):
        actual = normalize_url("https://www.boot.dev/blog/path/?a=1#top")
        self.assertEqual(actual, "www.boot.dev/blog/path")

    def test_strips_default_https_port(self):
        actual = normalize_url("https://www.boot.dev:443/blog/path")
        self.assertEqual(actual, "www.boot.dev/blog/path")

    def test_strips_default_http_port(self):
        actual = normalize_url("http://www.boot.dev:80/blog/path")
        self.assertEqual(actual, "www.boot.dev/blog/path")

    def test_keeps_non_default_port(self):
        actual = normalize_url("http://localhost:8080/blog/path/")
        self.assertEqual(actual, "localhost:8080/blog/path")

    def test_strips_userinfo(self):
        actual = normalize_url("https://user:pass@www.boot.dev/blog/path")
        self.assertEqual(actual, "www.boot.dev/blog/path")

    def test_handles_missing_scheme(self):
        actual = normalize_url("www.boot.dev/blog/path/")
        self.assertEqual(actual, "www.boot.dev/blog/path")

    def test_handles_protocol_relative_url(self):
        actual = normalize_url("//www.boot.dev/blog/path")
        self.assertEqual(actual, "www.boot.dev/blog/path")

    def test_strips_surrounding_whitespace(self):
        actual = normalize_url("\n  https://www.boot.dev/blog/path/ \t")
        self.assertEqual(actual, "www.boot.dev/blog/path")

    def test_root_url(self):
        self.assertEqual(normalize_url("https://www.boot.dev/"), "www.boot.dev")
        self.assertEqual(normalize_url("https://www.boot.dev"), "www.boot.dev")

    def test_strips_repeated_trailing_slashes(self):
        actual = normalize_url("https://www.boot.dev/blog/path///")
        self.assertEqual(actual, "www.boot.dev/blog/path")

    def test_keeps_path_with_extension(self):
        actual = normalize_url("https://www.boot.dev/blog/index.html")
        self.assertEqual(actual, "www.boot.dev/blog/index.html")

    def test_different_subdomains_are_different_pages(self):
        self.assertNotEqual(
            normalize_url("https://www.boot.dev/blog/path"),
            normalize_url("https://blog.boot.dev/blog/path"),
        )

    def test_different_paths_are_different_pages(self):
        self.assertNotEqual(
            normalize_url("https://www.boot.dev/blog/path"),
            normalize_url("https://www.boot.dev/blog/other"),
        )

    def test_ipv6_host(self):
        actual = normalize_url("http://[::1]:8080/blog/path/")
        self.assertEqual(actual, "[::1]:8080/blog/path")

    def test_empty_url_raises(self):
        with self.assertRaises(ValueError):
            normalize_url("")

    def test_whitespace_only_url_raises(self):
        with self.assertRaises(ValueError):
            normalize_url("   ")

    def test_url_without_host_raises(self):
        with self.assertRaises(ValueError):
            normalize_url("https:///blog/path")

    def test_non_string_url_raises(self):
        with self.assertRaises(TypeError):
            normalize_url(None)


class TestGetHeadingFromHTML(unittest.TestCase):
    def test_get_heading_from_html_basic(self):
        input_body = "<html><body><h1>Test Title</h1></body></html>"
        actual = get_heading_from_html(input_body)
        expected = "Test Title"
        self.assertEqual(actual, expected)

    def test_falls_back_to_h2(self):
        input_body = "<html><body><h2>Second Level</h2><p>Body.</p></body></html>"
        actual = get_heading_from_html(input_body)
        self.assertEqual(actual, "Second Level")

    def test_prefers_h1_over_earlier_h2(self):
        input_body = """<html><body>
            <h2>Sidebar Heading</h2>
            <h1>Real Title</h1>
        </body></html>"""
        actual = get_heading_from_html(input_body)
        self.assertEqual(actual, "Real Title")

    def test_returns_empty_string_when_no_heading(self):
        input_body = "<html><body><p>Just a paragraph.</p></body></html>"
        actual = get_heading_from_html(input_body)
        self.assertEqual(actual, "")

    def test_returns_empty_string_for_empty_html(self):
        self.assertEqual(get_heading_from_html(""), "")

    def test_returns_first_h1_when_multiple(self):
        input_body = "<html><body><h1>First</h1><h1>Second</h1></body></html>"
        actual = get_heading_from_html(input_body)
        self.assertEqual(actual, "First")

    def test_includes_text_of_nested_tags(self):
        input_body = "<h1>Welcome to <em>Boot.dev</em>!</h1>"
        actual = get_heading_from_html(input_body)
        self.assertEqual(actual, "Welcome to Boot.dev!")

    def test_collapses_surrounding_whitespace(self):
        input_body = """<html><body>
            <h1>
                Test    Title
            </h1>
        </body></html>"""
        actual = get_heading_from_html(input_body)
        self.assertEqual(actual, "Test Title")

    def test_finds_heading_nested_in_other_tags(self):
        input_body = """<html><body>
            <header><div class="hero"><h1>Nested Title</h1></div></header>
        </body></html>"""
        actual = get_heading_from_html(input_body)
        self.assertEqual(actual, "Nested Title")

    def test_handles_unclosed_tag(self):
        actual = get_heading_from_html("<html><body><h1>Unclosed Title")
        self.assertEqual(actual, "Unclosed Title")

    def test_empty_h1_does_not_fall_back_to_h2(self):
        input_body = "<html><body><h1></h1><h2>Second Level</h2></body></html>"
        actual = get_heading_from_html(input_body)
        self.assertEqual(actual, "")


class TestGetFirstParagraphFromHTML(unittest.TestCase):
    def test_get_first_paragraph_from_html_main_priority(self):
        input_body = """<html><body>
            <p>Outside paragraph.</p>
            <main>
                <p>Main paragraph.</p>
            </main>
        </body></html>"""
        actual = get_first_paragraph_from_html(input_body)
        expected = "Main paragraph."
        self.assertEqual(actual, expected)

    def test_first_paragraph_without_main(self):
        input_body = """<html><body>
            <p>First paragraph.</p>
            <p>Second paragraph.</p>
        </body></html>"""
        actual = get_first_paragraph_from_html(input_body)
        self.assertEqual(actual, "First paragraph.")

    def test_first_paragraph_inside_main(self):
        input_body = """<html><body>
            <main>
                <p>Main paragraph.</p>
                <p>Another main paragraph.</p>
            </main>
        </body></html>"""
        actual = get_first_paragraph_from_html(input_body)
        self.assertEqual(actual, "Main paragraph.")

    def test_returns_empty_string_when_no_paragraph(self):
        input_body = "<html><body><h1>Only a title</h1></body></html>"
        actual = get_first_paragraph_from_html(input_body)
        self.assertEqual(actual, "")

    def test_returns_empty_string_for_empty_html(self):
        self.assertEqual(get_first_paragraph_from_html(""), "")

    def test_falls_back_when_main_has_no_paragraph(self):
        input_body = """<html><body>
            <p>Outside paragraph.</p>
            <main><h1>Title only</h1></main>
        </body></html>"""
        actual = get_first_paragraph_from_html(input_body)
        self.assertEqual(actual, "Outside paragraph.")

    def test_finds_paragraph_nested_inside_main(self):
        input_body = """<html><body>
            <p>Outside paragraph.</p>
            <main><article><div><p>Deeply nested.</p></div></article></main>
        </body></html>"""
        actual = get_first_paragraph_from_html(input_body)
        self.assertEqual(actual, "Deeply nested.")

    def test_includes_text_of_nested_tags(self):
        input_body = "<p>Learn to code by building <b>real</b> projects.</p>"
        actual = get_first_paragraph_from_html(input_body)
        self.assertEqual(actual, "Learn to code by building real projects.")

    def test_collapses_surrounding_whitespace(self):
        input_body = """<html><body><main>
            <p>
                Main      paragraph.
            </p>
        </main></body></html>"""
        actual = get_first_paragraph_from_html(input_body)
        self.assertEqual(actual, "Main paragraph.")

    def test_handles_unclosed_tag(self):
        actual = get_first_paragraph_from_html("<html><body><p>Unclosed paragraph.")
        self.assertEqual(actual, "Unclosed paragraph.")


if __name__ == "__main__":
    unittest.main()
