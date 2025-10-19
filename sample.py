import time
import random
import logging
import requests
import math
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import heapq

# ------------------------------
# Logging Setup
# ------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ------------------------------
# CLASS DEFINITION
# ------------------------------
class Product:
    def __init__(self, name, price, discount, rating, link, site="Unknown"):
        self.name = name
        self.price = price
        self.discount = discount
        self.rating = rating
        self.link = link
        self.site = site

    def __repr__(self):
        return (f"[{self.site}] {self.name}\n"
                f"Price: ₹{self.price}\n"
                f"Discount: {self.discount}\n"
                f"Rating: {self.rating}\n"
                f"Link: {self.link}\n{'-'*60}")

# ------------------------------
# AVL TREE FOR RANGE QUERIES
# ------------------------------
class AVLNode:
    def __init__(self, product):
        self.product = product
        self.left = None
        self.right = None
        self.height = 1

def get_height(node):
    return node.height if node else 0

def update_height(node):
    node.height = max(get_height(node.left), get_height(node.right)) + 1

def get_balance(node):
    return get_height(node.left) - get_height(node.right) if node else 0

def left_rotate(y):
    x = y.right
    T2 = x.left
    x.left = y
    y.right = T2
    update_height(y)
    update_height(x)
    return x

def right_rotate(x):
    y = x.left
    T2 = y.right
    y.right = x
    x.left = T2
    update_height(x)
    update_height(y)
    return y

def insert_avl(root, product):
    if not root:
        return AVLNode(product)
    if product.price < root.product.price:
        root.left = insert_avl(root.left, product)
    elif product.price > root.product.price:
        root.right = insert_avl(root.right, product)
    else:
        return root  # No duplicates

    update_height(root)

    balance = get_balance(root)

    if balance > 1 and product.price < root.left.product.price:
        return right_rotate(root)

    if balance < -1 and product.price > root.right.product.price:
        return left_rotate(root)

    if balance > 1 and product.price > root.left.product.price:
        root.left = left_rotate(root.left)
        return right_rotate(root)

    if balance < -1 and product.price < root.right.product.price:
        root.right = right_rotate(root.right)
        return left_rotate(root)

    return root

def range_query_avl(node, min_price, max_price, results):
    if not node:
        return
    if min_price < node.product.price:
        range_query_avl(node.left, min_price, max_price, results)
    if min_price <= node.product.price <= max_price:
        results.append(node.product)
    if max_price > node.product.price:
        range_query_avl(node.right, min_price, max_price, results)

# ------------------------------
# AMAZON SCRAPER
# ------------------------------
def get_amazon_headers():
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    return {
        "User-Agent": random.choice(agents),
        "Accept-Language": "en-IN,en;q=0.9",
        "Referer": "https://www.google.com/",
        "DNT": "1"
    }

def get_amazon_search_url(query, page=1):
    query_enc = requests.utils.quote(query)
    return f"https://www.amazon.in/s?k={query_enc}&page={page}"

def fetch_amazon_html(url):
    try:
        res = requests.get(url, headers=get_amazon_headers(), timeout=10)
        if res.status_code == 503:
            logging.info("⚠️ Amazon returned 503 — retrying...")
            time.sleep(random.uniform(3, 6))
            res = requests.get(url, headers=get_amazon_headers(), timeout=10)
        if res.status_code == 200:
            return BeautifulSoup(res.text, "html.parser")
        else:
            logging.warning(f"⚠️ Failed with status {res.status_code} for {url}")
            return None
    except Exception as e:
        logging.error(f"⚠️ Error fetching {url}: {e}")
        return None

def parse_amazon_products(soup, max_results=10):
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

def scrape_amazon(query, max_results=10):
    all_products = []
    max_pages = (max_results + 9) // 10
    for page in range(1, max_pages + 1):
        url = get_amazon_search_url(query, page)
        logging.info(f"🔍 Scraping Amazon page {page}...")
        soup = fetch_amazon_html(url)
        page_products = parse_amazon_products(soup, max_results - len(all_products))
        logging.info(f"✅ Found {len(page_products)} products on page {page}")
        all_products.extend(page_products)
        if len(all_products) >= max_results:
            break
        time.sleep(random.uniform(2, 5))
    return all_products[:max_results]

# ------------------------------
# SELENIUM UTILITIES
# ------------------------------
def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--log-level=3')
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0'
    ]
    options.add_argument(f'--user-agent={random.choice(user_agents)}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def smart_scroll(driver, scroll_count=8, pause=2):
    for _ in range(scroll_count):
        driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
        time.sleep(pause + random.uniform(0.5, 1.5))
    return BeautifulSoup(driver.execute_script("return document.body.innerHTML"), "html.parser")

def parse_price(price_str):
    if not price_str or price_str == "N/A":
        return "N/A"
    cleaned = re.sub(r'[^\d]', '', price_str)
    try:
        return int(cleaned)
    except ValueError:
        return "N/A"

# ------------------------------
# MYNTRA SCRAPER
# ------------------------------
def scrape_myntra(query, max_results=10):
    products = []
    driver = setup_driver()
    query = query.replace(" ", "-")
    url = f"https://www.myntra.com/{query}"
    logging.info(f"🔍 Scraping Myntra: {url}")
    driver.get(url)

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "li.product-base"))
        )
        soup = smart_scroll(driver, scroll_count=8, pause=2)
        items = soup.select("li.product-base")[:max_results]

        for item in items:
            try:
                name_tag = item.select_one("h4.product-product")
                name = name_tag.text.strip() if name_tag else "N/A"

                link_tag = item.select_one("a")
                link_href = link_tag.get("href", "") if link_tag else ""
                if link_href.startswith("/"):
                    link = "https://www.myntra.com" + link_href
                elif link_href.startswith("http"):
                    link = link_href
                else:
                    link = "https://www.myntra.com/" + link_href

                price_tag = item.select_one("span.product-discountedPrice")
                price = parse_price(price_tag.text.strip() if price_tag else "N/A")

                original_price_tag = item.select_one("span.product-strike")
                discount = "N/A"
                if original_price_tag:
                    old_price = parse_price(original_price_tag.text.strip())
                    if old_price != "N/A" and price != "N/A" and old_price > price:
                        discount = f"{round(((old_price-price)/old_price)*100)}% off"

                rating_tag = item.select_one("div.product-ratingsContainer span")
                rating = rating_tag.text.strip() if rating_tag else "N/A"

                if name != "N/A" and price != "N/A":
                    products.append(Product(name, price, discount, rating, link, "Myntra"))

            except Exception:
                continue

    finally:
        driver.quit()
    return products[:max_results]

# ------------------------------
# SNAPDEAL SCRAPER
# ------------------------------
def scrape_snapdeal(query, max_results=10):
    products = []
    driver = setup_driver()
    query = query.replace(" ", "%20")
    url = f"https://www.snapdeal.com/search?keyword={query}"
    logging.info(f"🔍 Scraping Snapdeal: {url}")
    driver.get(url)

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-tuple-listing"))
        )
        soup = smart_scroll(driver, scroll_count=8, pause=2)
        items = soup.select("div.product-tuple-listing")[:max_results]

        for item in items:
            try:
                name_tag = item.select_one("p.product-title")
                name = name_tag.text.strip() if name_tag else "N/A"

                link_tag = item.find("a", href=True)
                link = link_tag['href'] if link_tag else "N/A"

                price_tag = item.select_one("span.lfloat.product-price")
                price = parse_price(price_tag.text.strip() if price_tag else "N/A")

                original_price_tag = item.select_one("span.lfloat.product-desc-price.strike")
                discount = "N/A"
                if original_price_tag:
                    old_price = parse_price(original_price_tag.text.strip())
                    if old_price != "N/A" and price != "N/A" and old_price > price:
                        discount = f"{round(((old_price-price)/old_price)*100)}% off"

                rating = "N/A"
                for selector in [
                    "span.rating-num", "div.rating-stars span", "span.rat-text",
                    "div.product-rating span", "span.ratingText", "p.ratingText"
                ]:
                    rating_tag = item.select_one(selector)
                    if rating_tag and rating_tag.text.strip():
                        match = re.search(r'\d*\.?\d+', rating_tag.text.strip())
                        if match:
                            rating = match.group()
                            break
                if rating == "N/A":
                    stars = item.select_one("span.filled-stars")
                    if stars and "style" in stars.attrs:
                        match = re.search(r'width:(\d+)%', stars["style"])
                        if match:
                            rating = str(round(int(match.group(1))/20, 1))

                if name != "N/A" and price != "N/A":
                    products.append(Product(name, price, discount, rating, link, "Snapdeal"))

            except Exception:
                continue

    finally:
        driver.quit()
    return products[:max_results]

# ------------------------------
# SHOPCLUES SCRAPER
# ------------------------------
def scrape_shopclues(query, max_results=10):
    products = []
    driver = setup_driver()
    query = query.replace(" ", "+")
    url = f"https://www.shopclues.com/search?q={query}"
    logging.info(f"🔍 Scraping ShopClues: {url}")
    driver.get(url)

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.column.col3"))
        )
        soup = smart_scroll(driver, scroll_count=8, pause=2)
        items = soup.select("div.column.col3")[:max_results]

        for item in items:
            try:
                name_tag = item.select_one("h2")
                name = name_tag.text.strip() if name_tag else "N/A"

                link_tag = item.find("a", href=True)
                href = link_tag['href'] if link_tag else "#"
                if href.startswith("//"):
                    link = "https:" + href
                elif href.startswith("/"):
                    link = "https://www.shopclues.com" + href
                else:
                    link = href

                price_tag = item.select_one("span.p_price")
                price = parse_price(price_tag.text.strip() if price_tag else "N/A")

                original_price_tag = item.select_one("span.old_prices")
                discount = "N/A"
                if original_price_tag:
                    old_price = parse_price(original_price_tag.text.strip())
                    if old_price != "N/A" and price != "N/A" and old_price > price:
                        discount = f"{round(((old_price-price)/old_price)*100)}% off"

                rating = "N/A"
                for selector in [
                    "span.rating", "div.ratings span", "span.rating-stars",
                    "div.rating-block span", "span.prd_rating", "span.rating_value"
                ]:
                    rating_tag = item.select_one(selector)
                    if rating_tag and rating_tag.text.strip():
                        match = re.search(r'\d*\.?\d+', rating_tag.text.strip())
                        if match:
                            rating = match.group()
                            break

                if name != "N/A" and price != "N/A":
                    products.append(Product(name, price, discount, rating, link, "ShopClues"))

            except Exception:
                continue

    finally:
        driver.quit()
    return products[:max_results]

# ------------------------------
# FLIPKART SCRAPER
# ------------------------------
def scrape_flipkart(query, max_results=10):
    products = []
    driver = setup_driver()
    query = query.replace(" ", "%20")
    url = f"https://www.flipkart.com/search?q={query}"
    logging.info(f"🔍 Scraping Flipkart: {url}")
    
    try:
        driver.get(url)
        
        # Wait for product listings to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-id]"))
        )
        
        # Scroll to load more products
        soup = smart_scroll(driver, scroll_count=8, pause=2)
        
        # Get product containers
        items = soup.select("div[data-id]")
        
        if not items:
            items = soup.select("div._1AtVbE")
        
        if not items:
            items = soup.select("div._2kHMtA")
        
        logging.info(f"📦 Found {len(items)} product containers")
        items = items[:max_results]

        for idx, item in enumerate(items, 1):
            try:
                # Product name - primary selector that works
                name = "N/A"
                name_tag = item.select_one("a.wjcEIp")
                
                if name_tag and name_tag.text.strip():
                    name = name_tag.text.strip()
                else:
                    # Fallback selectors if primary fails
                    name_selectors = [
                        "div.KzDlHZ", "a.WKTcLC", "div.syl9yP", 
                        "div._2WkVRV", "a.IRpwTa", "a.s1Q9rs",
                        "div._4rR01T", "a._2rpwqI", "div.tUxRFH",
                        "a.CGtC98", "div._2B099V"
                    ]
                    
                    for selector in name_selectors:
                        name_tag = item.select_one(selector)
                        if name_tag and name_tag.text.strip():
                            name = name_tag.text.strip()
                            if len(name) > 10:
                                break
                
                # If still not found, try getting text from any link
                if name == "N/A":
                    links = item.find_all("a", href=True)
                    for link in links:
                        text = link.get_text(strip=True)
                        if text and 15 < len(text) < 200:
                            name = text
                            break

                # Product link
                link_tag = item.find("a", href=True)
                link_href = link_tag['href'] if link_tag else ""
                if link_href.startswith("/"):
                    link = "https://www.flipkart.com" + link_href
                elif link_href.startswith("http"):
                    link = link_href
                else:
                    link = "https://www.flipkart.com/" + link_href if link_href else "N/A"

                # Current price
                price_tag = (item.select_one("div._30jeq3") or 
                            item.select_one("div._3I9_wc") or
                            item.select_one("div._25b18c") or
                            item.select_one("div.Nx9bqj") or
                            item.select_one("div.hl05eU"))
                price = parse_price(price_tag.text.strip() if price_tag else "N/A")

                # Original price and discount calculation
                original_price_tag = (item.select_one("div._3Ay6Sb") or 
                                     item.select_one("div._2_R_DZ") or
                                     item.select_one("div._3I9_wc._2p6lqe") or
                                     item.select_one("div.yRaY8j"))
                discount = "N/A"
                
                if original_price_tag:
                    old_price = parse_price(original_price_tag.text.strip())
                    if old_price != "N/A" and price != "N/A" and old_price > price:
                        discount = f"{round(((old_price-price)/old_price)*100)}% off"
                
                # Sometimes Flipkart shows discount directly
                if discount == "N/A":
                    discount_tag = (item.select_one("div._3Ay6Sb._31Dcoz") or 
                                   item.select_one("div._3xFhiH") or
                                   item.select_one("div.UkUFwK span"))
                    if discount_tag:
                        discount_text = discount_tag.text.strip()
                        if "off" in discount_text.lower():
                            discount = discount_text

                # Rating
                rating = "N/A"
                rating_selectors = [
                    "div.XQDdHH", "div._3LWZlK", "span._1lRcqv",
                    "div.CGtC98", "div._2c2kV-", "div.Rsc7Yb"
                ]
                
                for selector in rating_selectors:
                    rating_tag = item.select_one(selector)
                    if rating_tag and rating_tag.text.strip():
                        rating_text = rating_tag.text.strip()
                        match = re.search(r'\d*\.?\d+', rating_text)
                        if match:
                            rating = match.group()
                            break
                
                # Fallback: Estimate rating from star width
                if rating == "N/A":
                    star_container = item.select_one("div.tV2F7c") or item.select_one("div._1fV99m")
                    if star_container:
                        star_span = star_container.find("span", style=True)
                        if star_span and "width" in star_span.get("style", ""):
                            match = re.search(r'width:(\d+)%', star_span["style"])
                            if match:
                                width = int(match.group(1))
                                rating = str(round(width / 20, 1))
                                logging.info(f"Estimated rating {rating} from star width for {name}")

                if rating == "N/A":
                    logging.warning(f"No rating found for product: {name}")

                if name != "N/A" and price != "N/A":
                    products.append(Product(name, price, discount, rating, link, "Flipkart"))

            except Exception as e:
                logging.warning(f"Error parsing Flipkart item {idx}: {e}")
                continue

    except Exception as e:
        logging.error(f"Error loading Flipkart page: {e}")

    finally:
        driver.quit()
    
    return products[:max_results]

# ------------------------------
# HEAP-BASED SORTING FUNCTIONS
# ------------------------------
def parse_discount(discount):
    if discount == "N/A":
        return 0
    try:
        return int(re.sub(r"[^\d]", "", discount))
    except ValueError:
        return 0

def parse_rating(rating):
    if rating == "N/A":
        return 0.0
    try:
        return float(rating)
    except ValueError:
        return 0.0

def sort_by_discount(products, max_results=10):
    heap = []
    for i, product in enumerate(products):
        if product.price != "N/A":
            discount = parse_discount(product.discount)
            heapq.heappush(heap, (-discount, i, product))  # Max heap for discount
    top_products = []
    for _ in range(min(max_results, len(heap))):
        if heap:
            top_products.append(heapq.heappop(heap)[2])
    return top_products

def sort_by_price_asc(products, max_results=10):
    heap = []
    valid_count = 0
    for i, product in enumerate(products):
        if product.price != "N/A":
            heapq.heappush(heap, (product.price, i, product))  # Min heap for price
            valid_count += 1
    top_products = []
    for _ in range(min(max_results, valid_count)):
        if heap:
            top_products.append(heapq.heappop(heap)[2])
    return top_products

def sort_by_price_desc(products, max_results=10):
    heap = []
    valid_count = 0
    for i, product in enumerate(products):
        if product.price != "N/A":
            heapq.heappush(heap, (-product.price, i, product))  # Max heap for price
            valid_count += 1
    top_products = []
    for _ in range(min(max_results, valid_count)):
        if heap:
            top_products.append(heapq.heappop(heap)[2])
    return top_products

def sort_by_rating(products, max_results=10):
    heap = []
    for i, product in enumerate(products):
        if product.price != "N/A":
            rating = parse_rating(product.rating)
            heapq.heappush(heap, (-rating, i, product))  # Max heap for rating
    top_products = []
    for _ in range(min(max_results, len(heap))):
        if heap:
            top_products.append(heapq.heappop(heap)[2])
    return top_products

# ------------------------------
# RATING-PRICE RECOMMENDATION SYSTEM
# ------------------------------
def compute_rating_price_score(product):
    rating = parse_rating(product.rating)
    price = product.price
    if price <= 0:  # Avoid log(0) or negative
        price = 1
    return (rating ** 2) / math.log10(price)

def get_rating_price_recommendations(products, max_results=10):
    # Filter products with valid prices
    valid_products = [p for p in products if p.price != "N/A"]
    if not valid_products:
        return [], 0

    # Compute scores and use max heap
    heap = []
    for i, product in enumerate(valid_products):
        score = compute_rating_price_score(product)
        heapq.heappush(heap, (-score, i, product))  # Max heap

    top_products = []
    for _ in range(min(max_results, len(heap))):
        if heap:
            score, _, product = heapq.heappop(heap)
            product.score = -score  # Store score for display
            top_products.append(product)

    return top_products, len(valid_products)

# ------------------------------
# KNAPSACK-BASED RANGE QUERY
# ------------------------------
def knapsack_range_query(products, min_price, max_price, max_results=10):
    # Filter products in price range using AVL tree
    root = None
    for product in products:
        if product.price != "N/A":
            root = insert_avl(root, product)

    if not root:
        return [], 0

    range_products = []
    range_query_avl(root, min_price, max_price, range_products)
    if not range_products:
        return [], 0

    # Compute scores
    scores = [compute_rating_price_score(p) for p in range_products]

    # Greedy selection (approximation for knapsack)
    indexed_products = [(scores[i], i, range_products[i]) for i in range(len(range_products))]
    indexed_products.sort(reverse=True)  # Sort by score descending
    top_products = []
    for score, _, product in indexed_products[:min(max_results, len(range_products))]:
        product.score = score
        top_products.append(product)

    return top_products, len(range_products)

# ------------------------------
# RATING IMPUTATION
# ------------------------------
def impute_na_ratings(products):
    # Compute average rating from valid ratings
    valid_ratings = [parse_rating(p.rating) for p in products if parse_rating(p.rating) > 0]
    avg_rating = sum(valid_ratings) / len(valid_ratings) if valid_ratings else 4.0  # Default 4.0
    na_count = sum(1 for p in products if parse_rating(p.rating) == 0)

    # Update products with "N/A" ratings
    for product in products:
        if parse_rating(product.rating) == 0:
            product.rating = f"{avg_rating:.1f}"

    return na_count, avg_rating

# ------------------------------
# RANGE QUERY HANDLER
# ------------------------------
def handle_range_query(products):
    try:
        min_price = input("Enter minimum price (₹): ").strip()
        max_price = input("Enter maximum price (₹): ").strip()
        min_price = float(min_price)
        max_price = float(max_price)
        if min_price < 0 or max_price < 0:
            print("Prices must be non-negative.")
            return [], None, None
        if min_price > max_price:
            print("Minimum price cannot exceed maximum price.")
            return [], None, None

        # Get top 10 products in range using knapsack
        top_products, valid_count = knapsack_range_query(products, min_price, max_price)
        return top_products, min_price, max_price

    except ValueError:
        print("Invalid input. Please enter numeric values for prices.")
        return [], None, None

# ------------------------------
# MENU-DRIVEN PROGRAM
# ------------------------------
def display_menu():
    print("\nChoose option:")
    print("1) Price (High to Low)")
    print("2) Price (Low to High)")
    print("3) Rating (High to Low)")
    print("4) Discount (High to Low)")
    print("5) Price Range Query (Top 10 by Rating-Price Recommendation)")
    print("6) Exit")
    return input("Enter choice (1-6): ").strip()

def main():
    product_name = input("Enter product name to search: ").strip()
    logging.info(f"🔍 Searching for '{product_name}' across Amazon, Myntra, Snapdeal, ShopClues, and Flipkart...\n")

    # Store all scraped products in a Python list
    all_products = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_scraper = {
            executor.submit(scrape_amazon, product_name, 10): "Amazon",
            executor.submit(scrape_myntra, product_name, 10): "Myntra",
            executor.submit(scrape_snapdeal, product_name, 10): "Snapdeal",
            executor.submit(scrape_shopclues, product_name, 10): "ShopClues",
            executor.submit(scrape_flipkart, product_name, 10): "Flipkart"
        }
        for future in as_completed(future_to_scraper):
            try:
                products = future.result()
                all_products.extend(products)
                logging.info(f"✅ {future_to_scraper[future]}: {len(products)} products scraped")
            except Exception as e:
                logging.error(f"Error in {future_to_scraper[future]}: {e}")

    if not all_products:
        print("❌ No products scraped.")
        return

    # Impute "N/A" ratings globally
    na_count, avg_rating = impute_na_ratings(all_products)
    print(f"\nImputed {na_count} 'N/A' ratings with average {avg_rating:.1f}")

    # Rating-Price Recommendation
    print("\n🎯 Rating-Price Recommendation (Top 10 Products)")
    print("="*60)
    top_products, valid_count = get_rating_price_recommendations(all_products)
    if not top_products:
        print("No products available for recommendation.")
    else:
        if len(top_products) < 10:
            print(f"Note: Only {len(top_products)} products available.")
        for i, product in enumerate(top_products, start=1):
            print(f"{i}. {product}Score: {product.score:.2f}")
    print(f"Total Valid Products: {valid_count}")
    print("="*60)

    print(f"\n🎯 Total Products Found: {len(all_products)}\n{'='*60}")

    # Menu-driven loop
    while True:
        choice = display_menu()
        if choice == "1":
            top_products = sort_by_price_desc(all_products)
            print("\nTop 10 Products Sorted by Price (High to Low):")
        elif choice == "2":
            top_products = sort_by_price_asc(all_products)
            print("\nTop 10 Products Sorted by Price (Low to High):")
        elif choice == "3":
            top_products = sort_by_rating(all_products)
            print("\nTop 10 Products Sorted by Rating (High to Low):")
        elif choice == "4":
            top_products = sort_by_discount(all_products)
            print("\nTop 10 Products Sorted by Discount (High to Low):")
        elif choice == "5":
            top_products, min_price, max_price = handle_range_query(all_products)
            if min_price is not None and max_price is not None:
                print(f"\nTop 10 Products in Price Range ₹{min_price:.2f} to ₹{max_price:.2f} (Rating-Price Recommendation):")
        elif choice == "6":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 6.")
            continue

        # Display results
        if not top_products:
            print("No products available for this criterion.")
        else:
            if choice in ["1", "2", "3", "4"] and len(top_products) < 10:
                print(f"Note: Only {len(top_products)} products available.")
            for i, product in enumerate(top_products, start=1):
                score_text = f"Score: {product.score:.2f}" if hasattr(product, 'score') else ""
                print(f"{i}. {product}{score_text}")

if __name__ == "__main__":
    main()