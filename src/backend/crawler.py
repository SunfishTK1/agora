import httpx
import time
import validators
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse
from protego import Protego
from itertools import cycle


GOOD_STATUS = "success"
FAILED_STATUS = "failed"

# Rotating list of realistic desktop browser User-Agents
USER_AGENTS = [
    # Chrome (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Chrome (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Firefox (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13.5; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Edge (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Safari (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

_UA_CYCLE = cycle(USER_AGENTS)

def get_user_agent() -> str:
    return next(_UA_CYCLE)


def read_robots_txt(url: str, user_agent: str = None):
    parsed = urlparse(url)
    scheme = parsed.scheme or "http"
    netloc = parsed.netloc or parsed.path  # handles URLs like 'example.com'

    robots_url = urlunparse((scheme, netloc, "/robots.txt", "", "", ""))
    ua = user_agent or get_user_agent()

    try:
        with httpx.Client(timeout=10, headers={"User-Agent": ua}) as client:
            response = client.get(robots_url)
            print(response.status_code)
            response.raise_for_status()
            robotstxt = response.text
    except (httpx.RequestError, httpx.HTTPStatusError):
        print("robots.txt not found")
        return (None, None, None, True)

    rp = Protego.parse(robotstxt)

    crawl_delay = rp.crawl_delay(ua)
    request_rate = rp.request_rate(ua)
    preferred_host = rp.preferred_host
    is_allowed = rp.can_fetch(url, ua)

    if request_rate:
        request_rate = (request_rate.requests, request_rate.seconds)

    return (crawl_delay, request_rate, preferred_host, is_allowed)


def is_sub_path(link, parent_url):
    parsed_link = urlparse(link)
    parsed_parent = urlparse(parent_url)

    if parsed_link.netloc != parsed_parent.netloc:
        return False

    link_path = parsed_link.path.rstrip("/")
    parent_path = parsed_parent.path.rstrip("/")

    if not link_path.startswith(parent_path):
        return False

    if link_path == parent_path:
        return True

    if link_path[len(parent_path)] == "/":
        return True
    else:
        return False


def get_children(soup, parent_url):
    child_links = [link.get("href") for link in soup.find_all("a")]

    for index, link in enumerate(child_links):
        if link and link.startswith("/"):
            child_links[index] = parent_url + link

    # Filter sub paths
    valid_children = [link for link in child_links if is_sub_path(link, parent_url)]

    return valid_children


def parse_result(result: str, parent_url: str):

    soup = BeautifulSoup(result, "html.parser")

    title = soup.title.string
    child_links = get_children(soup, parent_url)
    content = soup.get_text()

    return title, child_links, content


def validate_url(url: str):
    is_valid = validators.url(url)

    if is_valid is True:
        return True
    else:
        return False


def fetch(url: str):
    status = FAILED_STATUS
    content = ""
    error_message = ""

    try:
        # Choose a consistent UA for robots check and page fetch
        ua = get_user_agent()
        crawl_delay, request_rate, preferred_host, is_allowed = read_robots_txt(url, user_agent=ua)
        # robots.txt might be unavailable; treat as allowed=True per read_robots_txt implementation

        if crawl_delay:
            time.sleep(crawl_delay)

        if is_allowed is False:
            error_message = "Blocked by robots.txt"
            return status, content, error_message

        r = httpx.get(url, follow_redirects=True, headers={"User-Agent": ua})

        if r.status_code == httpx.codes.OK:
            status = GOOD_STATUS
            content = r.text
        else:
            error_message = f"HTTP {r.status_code}"
            content = ""
    except httpx.RequestError as e:
        error_message = f"Request error: {e}"
    except Exception as e:
        error_message = f"Unexpected error: {e}"

    return status, content, error_message


def crawl_jobs(jobs: list):
    crawled = []
    all_child_links = []

    for url in jobs:
        status, html_content, error = fetch(url)

        if status is GOOD_STATUS:
            title, child_links, content = parse_result(html_content, url)

            crawl_result = {
                "url": url,
                "title": title,
                "status": status,
                "content": content,
                "children": child_links,
                "error": "",
            }

            crawled.append(crawl_result)
            all_child_links.extend(child_links)
        else:
            # Record the failure with error information
            crawl_result = {
                "url": url,
                "title": "",
                "status": status,
                "content": "",
                "children": [],
                "error": error,
            }
            crawled.append(crawl_result)

    return all_child_links, crawled


def crawl_target(parent_url: str, recursive_depth: int = 2):

    valid_url = validate_url(parent_url)

    if not valid_url:
        return None

    crawl_result = []
    all_descendant_links = []

    next_gen = [parent_url]
    for i in range(recursive_depth):

        child_links, child_results = crawl_jobs(next_gen)
        child_links = list(set(child_links))
        next_gen = child_links

        crawl_result.extend(child_results)
        all_descendant_links.extend(child_links)

    result = {
        "crawl_result": crawl_result,
        "child_links": all_descendant_links,
    }

    return result


if __name__ == "__main__":
    target = "https://www.cmu.edu/"

    result = crawl_target(target)
    print(result)
    print(len(result["crawl_result"]))
