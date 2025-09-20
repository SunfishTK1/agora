import asyncio
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

# Async HTTP client reused across requests
_ASYNC_CLIENT: httpx.AsyncClient | None = None

def _get_async_client() -> httpx.AsyncClient:
    global _ASYNC_CLIENT
    if _ASYNC_CLIENT is None:
        _ASYNC_CLIENT = httpx.AsyncClient(follow_redirects=True, timeout=10)
    return _ASYNC_CLIENT

# robots.txt cache and per-domain controls
_ROBOTS_CACHE: dict[str, tuple | None] = {}
_DOMAIN_SEMAPHORES: dict[str, asyncio.Semaphore] = {}
_RATE_LIMITS: dict[str, tuple[int, int]] = {}  # domain -> (requests, seconds)
_LAST_REQUEST_TIMES: dict[str, list[float]] = {}
_DEFAULT_CONCURRENCY = 3

def _get_domain(url: str) -> str:
    return urlparse(url).netloc


async def read_robots_txt(url: str, user_agent: str = None):
    parsed = urlparse(url)
    scheme = parsed.scheme or "http"
    netloc = parsed.netloc or parsed.path  # handles URLs like 'example.com'

    robots_url = urlunparse((scheme, netloc, "/robots.txt", "", "", ""))
    ua = user_agent or get_user_agent()

    domain = netloc
    if domain in _ROBOTS_CACHE:
        return _ROBOTS_CACHE[domain]

    try:
        client = _get_async_client()
        response = await client.get(robots_url, headers={"User-Agent": ua})
        response.raise_for_status()
        robotstxt = response.text
    except (httpx.RequestError, httpx.HTTPStatusError):
        # Default: allow crawling when robots not reachable
        _ROBOTS_CACHE[domain] = (None, None, None, True)
        # setup default semaphore
        _DOMAIN_SEMAPHORES.setdefault(domain, asyncio.Semaphore(_DEFAULT_CONCURRENCY))
        return _ROBOTS_CACHE[domain]

    rp = Protego.parse(robotstxt)

    crawl_delay = rp.crawl_delay(ua)
    request_rate = rp.request_rate(ua)
    preferred_host = rp.preferred_host
    is_allowed = rp.can_fetch(url, ua)

    if request_rate:
        request_rate = (request_rate.requests, request_rate.seconds)

    # cache and configure controls
    _ROBOTS_CACHE[domain] = (crawl_delay, request_rate, preferred_host, is_allowed)
    # semaphore per domain based on allowed concurrency (fall back default)
    max_conc = request_rate[0] if request_rate else _DEFAULT_CONCURRENCY
    _DOMAIN_SEMAPHORES[domain] = asyncio.Semaphore(max_conc)
    if request_rate:
        _RATE_LIMITS[domain] = request_rate
        _LAST_REQUEST_TIMES.setdefault(domain, [])

    return _ROBOTS_CACHE[domain]


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


async def _enforce_rate_limit(domain: str):
    if domain not in _RATE_LIMITS:
        return
    reqs, seconds = _RATE_LIMITS[domain]
    now = time.monotonic()
    history = _LAST_REQUEST_TIMES.setdefault(domain, [])
    # drop old timestamps
    history[:] = [t for t in history if now - t < seconds]
    if len(history) >= reqs:
        sleep_time = seconds - (now - history[0])
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)
    _LAST_REQUEST_TIMES[domain].append(time.monotonic())


async def fetch(url: str):
    status = FAILED_STATUS
    content = ""
    error_message = ""

    try:
        # Choose a consistent UA for robots check and page fetch
        ua = get_user_agent()
        crawl_delay, request_rate, preferred_host, is_allowed = await read_robots_txt(url, user_agent=ua)
        # robots.txt might be unavailable; treat as allowed=True per read_robots_txt implementation

        if is_allowed is False:
            error_message = "Blocked by robots.txt"
            return status, content, error_message

        domain = _get_domain(url)
        sem = _DOMAIN_SEMAPHORES.get(domain) or asyncio.Semaphore(_DEFAULT_CONCURRENCY)
        _DOMAIN_SEMAPHORES.setdefault(domain, sem)

        async with sem:
            if crawl_delay:
                await asyncio.sleep(crawl_delay)
            await _enforce_rate_limit(domain)

            client = _get_async_client()
            r = await client.get(url, headers={"User-Agent": ua})

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


async def crawl_jobs(jobs: list):
    crawled = []
    all_child_links = []

    async def _fetch_one(url: str):
        status, html_content, error = await fetch(url)
        if status is GOOD_STATUS:
            title, child_links, content = parse_result(html_content, url)
            return (
                child_links,
                {
                    "url": url,
                    "title": title,
                    "status": status,
                    "content": content,
                    "children": child_links,
                    "error": "",
                },
            )
        else:
            return (
                [],
                {
                    "url": url,
                    "title": "",
                    "status": status,
                    "content": "",
                    "children": [],
                    "error": error,
                },
            )

    results = await asyncio.gather(*[_fetch_one(url) for url in jobs])
    for child_links, crawl_entry in results:
        crawled.append(crawl_entry)
        all_child_links.extend(child_links)

    return all_child_links, crawled


async def crawl_target(parent_url: str, recursive_depth: int = 2):

    valid_url = validate_url(parent_url)

    if not valid_url:
        return None

    crawl_result = []
    all_descendant_links = []

    next_gen = [parent_url]
    for i in range(recursive_depth):

        child_links, child_results = await crawl_jobs(next_gen)
        child_links = list(set(child_links))
        next_gen = child_links

        crawl_result.extend(child_results)
        all_descendant_links.extend(child_links)

    result = {
        "crawl_result": crawl_result,
        "descendant_links": all_descendant_links,
    }

    return result


if __name__ == "__main__":
    target = "https://www.cmu.edu/"

    async def _main():
        res = await crawl_target(target)
        print(res)
        print(len(res["crawl_result"]))

        # close shared client
        client = _get_async_client()
        await client.aclose()

    asyncio.run(_main())
