import pytest
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock

import crawler


def test_is_sub_path():
    parent = "https://example.com/path"

    # Same path
    assert crawler.is_sub_path("https://example.com/path", parent) is True
    # Subpath
    assert crawler.is_sub_path("https://example.com/path/sub", parent) is True
    # Not a subpath (different path)
    assert crawler.is_sub_path("https://example.com/other", parent) is False
    # Different domain
    assert crawler.is_sub_path("https://other.com/path", parent) is False
    # Edge case: subpath without trailing slash
    assert crawler.is_sub_path("https://example.com/pathsub", parent) is False
    # Trailing slash on parent and link
    assert (
        crawler.is_sub_path("https://example.com/path/", "https://example.com/path/")
        is True
    )


def test_get_children():
    parent_url = "https://example.com"

    html = """
    <html><body>
    <a href="https://example.com/path1">Link 1</a>
    <a href="/path2">Link 2</a>
    <a href="https://other.com/path3">Link 3</a>
    <a>Link without href</a>
    </body></html>
    """
    soup = BeautifulSoup(html, "html.parser")

    children = crawler.get_children(soup, parent_url)
    # Should include only links that are subpaths of parent_url
    assert "https://example.com/path1" in children
    assert "https://example.com/path2" in children
    assert all(link.startswith(parent_url) for link in children)


def test_parse_result():
    parent_url = "https://example.com"

    html = """
    <html><head><title>Test Page</title></head>
    <body><a href="/child1">Child1</a><p>Hello World</p></body></html>
    """

    title, children, content = crawler.parse_result(html, parent_url)
    assert title == "Test Page"
    assert "https://example.com/child1" in children
    assert "Hello World" in content


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://valid.url", True),
        ("invalid-url", False),
        ("ftp://example.com", True),  # validators.url accepts ftp
        ("http://", False),
        ("", False),
    ],
)
def test_validate_url(url, expected):
    assert crawler.validate_url(url) == expected


@patch("crawler.httpx.get")
def test_fetch_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "content"
    mock_get.return_value = mock_response

    status, content = crawler.fetch("https://example.com")
    assert status == crawler.GOOD_STATUS
    assert content == "content"


@patch("crawler.httpx.get")
def test_fetch_failure_status_code(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not found"
    mock_get.return_value = mock_response

    status, content = crawler.fetch("https://example.com")
    assert status == crawler.FAILED_STATUS
    assert content == ""


@patch("crawler.httpx.get")
def test_fetch_exception(mock_get):
    mock_get.side_effect = Exception("Network error")

    status, content = crawler.fetch("https://example.com")
    assert status == crawler.FAILED_STATUS
    assert content == ""


@patch("crawler.fetch")
def test_crawl_jobs(mock_fetch):
    # Mock fetch to return success and some HTML content
    html = """
    <html><head><title>Page</title></head>
    <body><a href="/child1">Child1</a></body></html>
    """

    mock_fetch.return_value = (crawler.GOOD_STATUS, html)

    jobs = ["https://example.com"]
    children, crawled = crawler.crawl_jobs(jobs)

    assert len(crawled) == 1
    assert crawled[0]["url"] == jobs[0]
    assert crawled[0]["status"] == crawler.GOOD_STATUS
    assert "https://example.com/child1" in crawled[0]["children"]
    assert "https://example.com/child1" in children


@patch("crawler.crawl_jobs")
@patch("crawler.validate_url")
def test_crawl_target(mock_validate_url, mock_crawl_jobs):
    parent_url = "https://example.com"
    mock_validate_url.return_value = True

    # Simulate two rounds of crawling
    mock_crawl_jobs.side_effect = [
        (
            ["https://example.com/child1"],
            [
                {
                    "url": parent_url,
                    "title": "Title",
                    "status": crawler.GOOD_STATUS,
                    "content": "text",
                    "children": ["https://example.com/child1"],
                }
            ],
        ),
        ([], []),
    ]

    result = crawler.crawl_target(parent_url, recursive_depth=2)

    assert result is not None
    assert "crawl_result" in result
    assert "child_links" in result
    assert len(result["crawl_result"]) == 1
    assert "https://example.com/child1" in result["child_links"]


@patch("crawler.validate_url")
def test_crawl_target_invalid_url(mock_validate_url):
    mock_validate_url.return_value = False
    result = crawler.crawl_target("invalid-url")
    assert result is None
