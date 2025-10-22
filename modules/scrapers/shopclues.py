# modules/scrapers/shopclues.py
import logging
import re
from modules.utilities import setup_driver, smart_scroll, parse_price
from modules.product import Product
from config import MAX_RESULTS_PER_SITE
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def scrape_shopclues(query, max_results=MAX_RESULTS_PER_SITE):
    products = []
    driver = setup_driver()
    query = query.replace(" ", "+")
    url = f"https://www.shopclues.com/search?q={query}"
    logging.info(f"Scraping ShopClues: {url}")
    driver.get(url)

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.column.col3"))
        )
        soup = smart_scroll(driver)
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