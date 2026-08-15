import unittest

from crawl import normalize_url


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


if __name__ == "__main__":
    unittest.main()
