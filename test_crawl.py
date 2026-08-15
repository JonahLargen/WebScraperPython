import unittest

from crawl import (
    classify_links,
    decode_body,
    extract_page_data,
    get_first_paragraph_from_html,
    get_heading_from_html,
    get_images_from_html,
    get_urls_from_html,
    looks_like_binary,
    normalize_url,
    parse_retry_after,
    retry_delay,
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


class TestGetURLsFromHTML(unittest.TestCase):
    def test_get_urls_from_html_absolute(self):
        input_url = "https://crawler-test.com"
        input_body = '<html><body><a href="https://crawler-test.com"><span>Boot.dev</span></a></body></html>'
        actual = get_urls_from_html(input_body, input_url)
        expected = ["https://crawler-test.com"]
        self.assertEqual(actual, expected)

    def test_get_urls_from_html_relative(self):
        input_url = "https://crawler-test.com"
        input_body = '<html><body><a href="/about">About</a></body></html>'
        actual = get_urls_from_html(input_body, input_url)
        self.assertEqual(actual, ["https://crawler-test.com/about"])

    def test_finds_all_anchors_in_document_order(self):
        input_url = "https://crawler-test.com"
        input_body = """<html><body>
            <nav><a href="/one">One</a></nav>
            <main><div><a href="/two">Two</a></div></main>
            <footer><a href="https://other.com/three">Three</a></footer>
        </body></html>"""
        actual = get_urls_from_html(input_body, input_url)
        expected = [
            "https://crawler-test.com/one",
            "https://crawler-test.com/two",
            "https://other.com/three",
        ]
        self.assertEqual(actual, expected)

    def test_relative_to_base_url_with_a_path(self):
        input_url = "https://crawler-test.com/docs/"
        input_body = """<html><body>
            <a href="intro">Sibling</a>
            <a href="/root">Root</a>
        </body></html>"""
        actual = get_urls_from_html(input_body, input_url)
        expected = [
            "https://crawler-test.com/docs/intro",
            "https://crawler-test.com/root",
        ]
        self.assertEqual(actual, expected)

    def test_protocol_relative_url_uses_base_scheme(self):
        input_url = "https://crawler-test.com"
        input_body = '<html><body><a href="//cdn.example.com/page">CDN</a></body></html>'
        actual = get_urls_from_html(input_body, input_url)
        self.assertEqual(actual, ["https://cdn.example.com/page"])

    def test_fragment_link_resolves_against_base(self):
        input_url = "https://crawler-test.com"
        input_body = '<html><body><a href="#about">About</a></body></html>'
        actual = get_urls_from_html(input_body, input_url)
        self.assertEqual(actual, ["https://crawler-test.com#about"])

    def test_returns_empty_list_when_no_anchors(self):
        input_url = "https://crawler-test.com"
        input_body = "<html><body><p>No links here.</p></body></html>"
        actual = get_urls_from_html(input_body, input_url)
        self.assertEqual(actual, [])

    def test_returns_empty_list_for_empty_html(self):
        self.assertEqual(get_urls_from_html("", "https://crawler-test.com"), [])

    def test_skips_anchors_without_href(self):
        input_url = "https://crawler-test.com"
        input_body = """<html><body>
            <a name="anchor">No href</a>
            <a href="">Empty href</a>
            <a href="   ">Whitespace href</a>
            <a href="/real">Real link</a>
        </body></html>"""
        actual = get_urls_from_html(input_body, input_url)
        self.assertEqual(actual, ["https://crawler-test.com/real"])

    def test_skips_non_http_schemes(self):
        input_url = "https://crawler-test.com"
        input_body = """<html><body>
            <a href="mailto:hello@crawler-test.com">Email</a>
            <a href="tel:+15555555555">Call</a>
            <a href="javascript:void(0)">Click</a>
            <a href="/real">Real link</a>
        </body></html>"""
        actual = get_urls_from_html(input_body, input_url)
        self.assertEqual(actual, ["https://crawler-test.com/real"])

    def test_trims_whitespace_around_href(self):
        input_url = "https://crawler-test.com"
        input_body = '<html><body><a href="  /about  ">About</a></body></html>'
        actual = get_urls_from_html(input_body, input_url)
        self.assertEqual(actual, ["https://crawler-test.com/about"])

    def test_keeps_duplicate_links(self):
        input_url = "https://crawler-test.com"
        input_body = """<html><body>
            <a href="/about">About</a>
            <a href="/about">About again</a>
        </body></html>"""
        actual = get_urls_from_html(input_body, input_url)
        expected = ["https://crawler-test.com/about", "https://crawler-test.com/about"]
        self.assertEqual(actual, expected)

    def test_ignores_image_sources(self):
        input_url = "https://crawler-test.com"
        input_body = """<html><body>
            <a href="https://crawler-test.com">Go to Boot.dev</a>
            <img src="/logo.png" alt="Boot.dev Logo" />
        </body></html>"""
        actual = get_urls_from_html(input_body, input_url)
        self.assertEqual(actual, ["https://crawler-test.com"])


class TestGetImagesFromHTML(unittest.TestCase):
    def test_get_images_from_html_relative(self):
        input_url = "https://crawler-test.com"
        input_body = '<html><body><img src="/logo.png" alt="Logo"></body></html>'
        actual = get_images_from_html(input_body, input_url)
        expected = ["https://crawler-test.com/logo.png"]
        self.assertEqual(actual, expected)

    def test_get_images_from_html_absolute(self):
        input_url = "https://crawler-test.com"
        input_body = '<html><body><img src="https://cdn.example.com/logo.png"></body></html>'
        actual = get_images_from_html(input_body, input_url)
        self.assertEqual(actual, ["https://cdn.example.com/logo.png"])

    def test_finds_all_images_in_document_order(self):
        input_url = "https://crawler-test.com"
        input_body = """<html><body>
            <img src="/one.png" alt="One">
            <figure><img src="two.jpg"></figure>
            <img src="https://cdn.example.com/three.gif">
        </body></html>"""
        actual = get_images_from_html(input_body, input_url)
        expected = [
            "https://crawler-test.com/one.png",
            "https://crawler-test.com/two.jpg",
            "https://cdn.example.com/three.gif",
        ]
        self.assertEqual(actual, expected)

    def test_relative_to_base_url_with_a_path(self):
        input_url = "https://crawler-test.com/docs/"
        input_body = """<html><body>
            <img src="local.png">
            <img src="/root.png">
        </body></html>"""
        actual = get_images_from_html(input_body, input_url)
        expected = [
            "https://crawler-test.com/docs/local.png",
            "https://crawler-test.com/root.png",
        ]
        self.assertEqual(actual, expected)

    def test_protocol_relative_url_uses_base_scheme(self):
        input_url = "https://crawler-test.com"
        input_body = '<html><body><img src="//cdn.example.com/logo.png"></body></html>'
        actual = get_images_from_html(input_body, input_url)
        self.assertEqual(actual, ["https://cdn.example.com/logo.png"])

    def test_returns_empty_list_when_no_images(self):
        input_url = "https://crawler-test.com"
        input_body = "<html><body><p>No images here.</p></body></html>"
        actual = get_images_from_html(input_body, input_url)
        self.assertEqual(actual, [])

    def test_returns_empty_list_for_empty_html(self):
        self.assertEqual(get_images_from_html("", "https://crawler-test.com"), [])

    def test_skips_images_without_src(self):
        input_url = "https://crawler-test.com"
        input_body = """<html><body>
            <img alt="No source">
            <img src="">
            <img src="   ">
            <img srcset="/wide.png 2x">
            <img src="/real.png">
        </body></html>"""
        actual = get_images_from_html(input_body, input_url)
        self.assertEqual(actual, ["https://crawler-test.com/real.png"])

    def test_skips_data_uris(self):
        input_url = "https://crawler-test.com"
        input_body = """<html><body>
            <img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=">
            <img src="/real.png">
        </body></html>"""
        actual = get_images_from_html(input_body, input_url)
        self.assertEqual(actual, ["https://crawler-test.com/real.png"])

    def test_trims_whitespace_around_src(self):
        input_url = "https://crawler-test.com"
        input_body = '<html><body><img src="  /logo.png  "></body></html>'
        actual = get_images_from_html(input_body, input_url)
        self.assertEqual(actual, ["https://crawler-test.com/logo.png"])

    def test_ignores_anchor_hrefs(self):
        input_url = "https://crawler-test.com"
        input_body = """<html><body>
            <a href="https://crawler-test.com">Go to Boot.dev</a>
            <img src="/logo.png" alt="Boot.dev Logo" />
        </body></html>"""
        actual = get_images_from_html(input_body, input_url)
        self.assertEqual(actual, ["https://crawler-test.com/logo.png"])


class TestExtractPageData(unittest.TestCase):
    def test_extract_page_data_basic(self):
        input_url = "https://crawler-test.com"
        input_body = """<html><body>
            <h1>Test Title</h1>
            <p>This is the first paragraph.</p>
            <a href="/link1">Link 1</a>
            <img src="/image1.jpg" alt="Image 1">
        </body></html>"""
        actual = extract_page_data(input_body, input_url)
        expected = {
            "url": "https://crawler-test.com",
            "heading": "Test Title",
            "first_paragraph": "This is the first paragraph.",
            "outgoing_links": ["https://crawler-test.com/link1"],
            "internal_links": ["https://crawler-test.com/link1"],
            "external_links": [],
            "internal_link_count": 1,
            "external_link_count": 0,
            "image_urls": ["https://crawler-test.com/image1.jpg"],
        }
        self.assertEqual(actual, expected)

    def test_returns_expected_keys(self):
        actual = extract_page_data("<html></html>", "https://crawler-test.com")
        expected_keys = {
            "url",
            "heading",
            "first_paragraph",
            "outgoing_links",
            "internal_links",
            "external_links",
            "internal_link_count",
            "external_link_count",
            "image_urls",
        }
        self.assertEqual(set(actual.keys()), expected_keys)

    def test_empty_page(self):
        input_url = "https://crawler-test.com"
        actual = extract_page_data("<html><body></body></html>", input_url)
        expected = {
            "url": "https://crawler-test.com",
            "heading": "",
            "first_paragraph": "",
            "outgoing_links": [],
            "internal_links": [],
            "external_links": [],
            "internal_link_count": 0,
            "external_link_count": 0,
            "image_urls": [],
        }
        self.assertEqual(actual, expected)

    def test_uses_h2_and_main_paragraph(self):
        input_url = "https://crawler-test.com/blog/"
        input_body = """<html><body>
            <p>Outside paragraph.</p>
            <h2>Fallback Title</h2>
            <main>
                <p>Main paragraph.</p>
                <a href="post">Relative post</a>
                <img src="../shared/logo.png">
            </main>
        </body></html>"""
        actual = extract_page_data(input_body, input_url)
        expected = {
            "url": "https://crawler-test.com/blog/",
            "heading": "Fallback Title",
            "first_paragraph": "Main paragraph.",
            "outgoing_links": ["https://crawler-test.com/blog/post"],
            "internal_links": ["https://crawler-test.com/blog/post"],
            "external_links": [],
            "internal_link_count": 1,
            "external_link_count": 0,
            "image_urls": ["https://crawler-test.com/shared/logo.png"],
        }
        self.assertEqual(actual, expected)

    def test_collects_multiple_links_and_images(self):
        input_url = "https://crawler-test.com"
        input_body = """<html><body>
            <h1>Many Resources</h1>
            <p>Body copy.</p>
            <a href="/one">One</a>
            <a href="https://other.com/two">Two</a>
            <a href="mailto:hi@crawler-test.com">Mail</a>
            <img src="/one.png">
            <img alt="no src">
            <img src="//cdn.example.com/two.png">
        </body></html>"""
        actual = extract_page_data(input_body, input_url)
        expected = {
            "url": "https://crawler-test.com",
            "heading": "Many Resources",
            "first_paragraph": "Body copy.",
            "outgoing_links": [
                "https://crawler-test.com/one",
                "https://other.com/two",
            ],
            "internal_links": ["https://crawler-test.com/one"],
            "external_links": ["https://other.com/two"],
            "internal_link_count": 1,
            "external_link_count": 1,
            "image_urls": [
                "https://crawler-test.com/one.png",
                "https://cdn.example.com/two.png",
            ],
        }
        self.assertEqual(actual, expected)

    def test_subdomains_count_as_external(self):
        input_url = "https://crawler-test.com"
        input_body = """<html><body>
            <a href="/internal">Internal</a>
            <a href="https://blog.crawler-test.com/post">Subdomain</a>
        </body></html>"""
        actual = extract_page_data(input_body, input_url)
        self.assertEqual(actual["internal_links"], ["https://crawler-test.com/internal"])
        self.assertEqual(
            actual["external_links"], ["https://blog.crawler-test.com/post"]
        )

    def test_base_domain_argument_overrides_page_host(self):
        input_url = "https://cdn.crawler-test.com/mirror"
        input_body = """<html><body>
            <a href="https://crawler-test.com/home">Home</a>
            <a href="/local">Local</a>
        </body></html>"""
        actual = extract_page_data(input_body, input_url, "crawler-test.com")
        self.assertEqual(actual["internal_links"], ["https://crawler-test.com/home"])
        self.assertEqual(
            actual["external_links"], ["https://cdn.crawler-test.com/local"]
        )

    def test_counts_match_the_lists(self):
        input_url = "https://crawler-test.com"
        input_body = """<html><body>
            <a href="/one">One</a>
            <a href="/one">One again</a>
            <a href="https://other.com/a">A</a>
            <a href="https://other.com/b">B</a>
            <a href="https://third.com/c">C</a>
        </body></html>"""
        actual = extract_page_data(input_body, input_url)
        self.assertEqual(actual["internal_link_count"], 2)
        self.assertEqual(actual["external_link_count"], 3)
        self.assertEqual(actual["internal_link_count"], len(actual["internal_links"]))
        self.assertEqual(actual["external_link_count"], len(actual["external_links"]))

    def test_url_is_not_normalized(self):
        input_url = "https://WWW.Crawler-Test.com/Blog/"
        actual = extract_page_data("<html></html>", input_url)
        self.assertEqual(actual["url"], "https://WWW.Crawler-Test.com/Blog/")


class TestClassifyLinks(unittest.TestCase):
    def test_splits_internal_from_external(self):
        urls = [
            "https://crawler-test.com/one",
            "https://other.com/two",
            "http://crawler-test.com/three",
        ]
        internal, external = classify_links(urls, "crawler-test.com")
        self.assertEqual(
            internal,
            ["https://crawler-test.com/one", "http://crawler-test.com/three"],
        )
        self.assertEqual(external, ["https://other.com/two"])

    def test_scheme_and_port_do_not_change_the_domain(self):
        urls = ["http://crawler-test.com:8080/one", "https://crawler-test.com/two"]
        internal, external = classify_links(urls, "crawler-test.com")
        self.assertEqual(internal, urls)
        self.assertEqual(external, [])

    def test_host_comparison_is_case_insensitive(self):
        internal, external = classify_links(["https://Crawler-Test.COM/one"], "crawler-test.com")
        self.assertEqual(internal, ["https://Crawler-Test.COM/one"])
        self.assertEqual(external, [])

    def test_empty_list(self):
        self.assertEqual(classify_links([], "crawler-test.com"), ([], []))


class TestCrawlHelpers(unittest.TestCase):
    def test_looks_like_binary_matches_known_extensions(self):
        for url in [
            "https://crawler-test.com/manual.pdf",
            "https://crawler-test.com/photo.JPG",
            "https://crawler-test.com/archive.tar.gz",
            "https://crawler-test.com/style.css?v=2",
        ]:
            with self.subTest(url=url):
                self.assertTrue(looks_like_binary(url))

    def test_looks_like_binary_leaves_pages_alone(self):
        for url in [
            "https://crawler-test.com/",
            "https://crawler-test.com/about",
            "https://crawler-test.com/index.html",
            "https://crawler-test.com/report.pdfs",
        ]:
            with self.subTest(url=url):
                self.assertFalse(looks_like_binary(url))

    def test_decode_body_uses_the_declared_charset(self):
        self.assertEqual(decode_body("café".encode("latin-1"), "latin-1"), "café")

    def test_decode_body_falls_back_to_utf8(self):
        self.assertEqual(decode_body("café".encode("utf-8"), None), "café")

    def test_decode_body_survives_a_bogus_charset(self):
        self.assertEqual(decode_body(b"hello", "not-a-real-charset"), "hello")

    def test_decode_body_replaces_undecodable_bytes(self):
        self.assertEqual(decode_body(b"a\xffb", "utf-8"), "a�b")

    def test_parse_retry_after(self):
        self.assertEqual(parse_retry_after("12"), 12.0)
        self.assertIsNone(parse_retry_after(None))
        self.assertIsNone(parse_retry_after("-1"))
        self.assertIsNone(parse_retry_after("Wed, 21 Oct 2015 07:28:00 GMT"))

    def test_retry_delay_backs_off(self):
        self.assertEqual(retry_delay(1), 1.0)
        self.assertEqual(retry_delay(2), 2.0)
        self.assertEqual(retry_delay(3), 4.0)

    def test_retry_delay_prefers_retry_after(self):
        self.assertEqual(retry_delay(1, 7.0), 7.0)

    def test_retry_delay_is_capped(self):
        self.assertEqual(retry_delay(1, 9999.0), 30.0)
        self.assertEqual(retry_delay(20), 30.0)


if __name__ == "__main__":
    unittest.main()
