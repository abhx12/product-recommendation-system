# modules/utilities.py
import logging
import random
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from config import LOGGING_CONFIG, USER_AGENTS, SCROLL_COUNT, SCROLL_PAUSE, get_random_user_agent

# Logging setup
logging.basicConfig(**LOGGING_CONFIG)

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--log-level=3')
    options.add_argument(f'--user-agent={get_random_user_agent()}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def smart_scroll(driver, scroll_count=SCROLL_COUNT, pause=SCROLL_PAUSE):
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