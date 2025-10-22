# modules/scrapers/amazon.py
import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from config import get_random_user_agent, TIMEOUT, MAX_RESULTS_PER_SITE
from modules.product import Product

def get_amazon_headers():
    return {
        "User-Agent": get_random_user_agent(),
        "Accept-Language": "en-IN,en;q=0.9",
        "Referer": "https://www.google.com/",
        "DNT": "1"
    }

def get_amazon_search_url(query, page=1):
    query_enc = requests.utils.quote(query)
    return f"https://www.amazon.in/s?k={query_enc}&page={page}"

def fetch_amazon_html(url):
    try:
        res = requests.get(url, headers=get_amazon_headers(), timeout=TIMEOUT)
        if res.status_code == 503:
            logging.info("Amazon returned 503 — retrying...")
            time.sleep(random.uniform(3, 6))
            res = requests.get(url, headers=get_amazon_headers(), timeout=TIMEOUT)
        if res.status_code == 200:
            return BeautifulSoup(res.text, "html.parser")
        else:
            logging.warning(f"Failed with status {res.status_code} for {url}")
            return None
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
        return None

def parse_amazon_products(soup, max_results=MAX_RESULTS_PER_SITE):
    products = []
    if not soup:
        return products

    items = soup.find_all("div", {"data-component-type": "s-search-result"})[:max_results]
    for item in items:
        try:
            title_elem = item.h2
            name = title_elem.text.strip() if title_elem else "N/A"
            link_tag = item.find("a", class_="a-link-normal s-no-outline")
            link = "https://www.amazon.in" + link_tag["href"] if link_tag else "N/A"
            price_elem = item.find("span", class_="a-price-whole")
            price_text = price_elem.text.strip().replace(",", "") if price_elem else "N/A"
            price = int(price_text) if price_text.isdigit() else "N/A"
            old_price_span = item.select_one("span.a-price.a-text-price span.a-offscreen")
            discount = "N/A"
            if old_price_span:
                old_price_text = re.sub(r"[^\d]", "", old_price_span.text)
                if old_price_text.isdigit() and price != "N/A":
                    old_price = int(old_price_text)
                    if old_price > price:
                        discount_percent = round(((old_price - price) / old_price) * 100)
                        if 0 < discount_percent < 100:
                            discount = f"{discount_percent}% off"
                        else:
                            logging.warning(f"Invalid discount for {name}: old_price={old_price}, price={price}")
            rating_elem = item.find("span", class_="a-icon-alt")
            rating = rating_elem.text.strip().split(" ")[0] if rating_elem else "N/A"
            if name != "N/A" and price != "N/A":
                products.append(Product(name, price, discount, rating, link, "Amazon"))
        except Exception as e:
            logging.warning(f"Error parsing Amazon item: {e}")
            continue
    return products[:max_results]

def scrape_amazon(query, max_results=MAX_RESULTS_PER_SITE):
    all_products = []
    max_pages = (max_results + 9) // 10
    for page in range(1, max_pages + 1):
        url = get_amazon_search_url(query, page)
        logging.info(f"Scraping Amazon page {page}...")
        soup = fetch_amazon_html(url)
        page_products = parse_amazon_products(soup, max_results - len(all_products))
        logging.info(f"Found {len(page_products)} products on page {page}")
        all_products.extend(page_products)
        if len(all_products) >= max_results:
            break
        time.sleep(random.uniform(2, 5))
    return all_products[:max_results]