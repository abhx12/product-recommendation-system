# modules/scrapers/flipkart.py
import logging
import re
from modules.utilities import setup_driver, smart_scroll, parse_price
from modules.product import Product
from config import MAX_RESULTS_PER_SITE
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def scrape_flipkart(query, max_results=MAX_RESULTS_PER_SITE):
    products = []
    driver = setup_driver()
    query = query.replace(" ", "%20")
    url = f"https://www.flipkart.com/search?q={query}"
    logging.info(f"Scraping Flipkart: {url}")
    
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-id]"))
        )
        soup = smart_scroll(driver)
        items = soup.select("div[data-id]")
        if not items:
            items = soup.select("div._1AtVbE")
        if not items:
            items = soup.select("div._2kHMtA")
        logging.info(f"Found {len(items)} product containers")
        items = items[:max_results]

        for idx, item in enumerate(items, 1):
            try:
                name = "N/A"
                name_tag = item.select_one("a.wjcEIp")
                if name_tag and name_tag.text.strip():
                    name = name_tag.text.strip()
                else:
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
                if name == "N/A":
                    links = item.find_all("a", href=True)
                    for link in links:
                        text = link.get_text(strip=True)
                        if text and 15 < len(text) < 200:
                            name = text
                            break
                link_tag = item.find("a", href=True)
                link_href = link_tag['href'] if link_tag else ""
                if link_href.startswith("/"):
                    link = "https://www.flipkart.com" + link_href
                elif link_href.startswith("http"):
                    link = link_href
                else:
                    link = "https://www.flipkart.com/" + link_href if link_href else "N/A"
                price_tag = (item.select_one("div._30jeq3") or 
                            item.select_one("div._3I9_wc") or
                            item.select_one("div._25b18c") or
                            item.select_one("div.Nx9bqj") or
                            item.select_one("div.hl05eU"))
                price = parse_price(price_tag.text.strip() if price_tag else "N/A")
                original_price_tag = (item.select_one("div._3Ay6Sb") or 
                                     item.select_one("div._2_R_DZ") or
                                     item.select_one("div._3I9_wc._2p6lqe") or
                                     item.select_one("div.yRaY8j"))
                discount = "N/A"
                if original_price_tag:
                    old_price = parse_price(original_price_tag.text.strip())
                    if old_price != "N/A" and price != "N/A" and old_price > price:
                        discount = f"{round(((old_price-price)/old_price)*100)}% off"
                if discount == "N/A":
                    discount_tag = (item.select_one("div._3Ay6Sb._31Dcoz") or 
                                   item.select_one("div._3xFhiH") or
                                   item.select_one("div.UkUFwK span"))
                    if discount_tag:
                        discount_text = discount_tag.text.strip()
                        if "off" in discount_text.lower():
                            discount = discount_text
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