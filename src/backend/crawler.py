import httpx
import time
import validators
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse
from protego import Protego


GOOD_STATUS = "success"
FAILED_STATUS = "failed"


def read_robots_txt(url: str, user_agent: str = "*"):
    parsed = urlparse(url)
    scheme = parsed.scheme or "http"
    netloc = parsed.netloc or parsed.path  # handles URLs like 'example.com'

    robots_url = urlunparse((scheme, netloc, "/robots.txt", "", "", ""))

    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(robots_url)
            response.raise_for_status()
            robotstxt = response.text
    except (httpx.RequestError, httpx.HTTPStatusError):
        return (None, None, None, None)

    rp = Protego.parse(robotstxt)

    crawl_delay = rp.crawl_delay(user_agent)
    request_rate = rp.request_rate(user_agent)
    preferred_host = rp.preferred_host
    is_allowed = rp.can_fetch(url, user_agent)

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

    try:

        crawl_delay, request_rate, preferred_host, is_allowed = read_robots_txt(url)

        if crawl_delay:
            time.sleep(crawl_delay)
            
        if is_allowed is False:
            return status, content

        r = httpx.get(url, follow_redirects=True)

        if r.status_code == httpx.codes.OK:
            status = GOOD_STATUS
            content = r.text
        else:
            content = ""
    except Exception as e:
        print(f"Request Failed {e}")

    return status, content


def crawl_jobs(jobs: list):
    crawled = []
    all_child_links = []

    for url in jobs:
        status, html_content = fetch(url)

        if status is GOOD_STATUS:
            title, child_links, content = parse_result(html_content, url)

            crawl_result = {
                "url": url,
                "title": title,
                "status": status,
                "content": content,
                "children": child_links,
            }

            crawled.append(crawl_result)
            all_child_links.extend(child_links)

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
    target = "https://www.cmu.edu/cmufront/"

    result = crawl_target(target)
    print(result)
    # print(len(result["crawl_result"]))
