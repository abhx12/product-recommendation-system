# modules/scrapers/snapdeal.py
import logging
import re
from modules.utilities import setup_driver, smart_scroll, parse_price
from modules.product import Product
from config import MAX_RESULTS_PER_SITE
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def scrape_snapdeal(query, max_results=MAX_RESULTS_PER_SITE):
    products = []
    driver = setup_driver()
    query = query.replace(" ", "%20")
    url = f"https://www.snapdeal.com/search?keyword={query}"
    logging.info(f"Scraping Snapdeal: {url}")
    driver.get(url)

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-tuple-listing"))
        )
        soup = smart_scroll(driver)
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