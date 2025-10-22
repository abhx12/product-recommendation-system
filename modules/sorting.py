# modules/sorting.py
import heapq
import math
import re
from config import MAX_RESULTS_PER_SITE

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

def sort_by_discount(products, max_results=MAX_RESULTS_PER_SITE):
    heap = []
    for i, product in enumerate(products):
        if product.price != "N/A":
            discount = parse_discount(product.discount)
            heapq.heappush(heap, (-discount, i, product))
    top_products = []
    for _ in range(min(max_results, len(heap))):
        if heap:
            top_products.append(heapq.heappop(heap)[2])
    return top_products

def sort_by_price_asc(products, max_results=MAX_RESULTS_PER_SITE):
    heap = []
    valid_count = 0
    for i, product in enumerate(products):
        if product.price != "N/A":
            heapq.heappush(heap, (product.price, i, product))
            valid_count += 1
    top_products = []
    for _ in range(min(max_results, valid_count)):
        if heap:
            top_products.append(heapq.heappop(heap)[2])
    return top_products

def sort_by_price_desc(products, max_results=MAX_RESULTS_PER_SITE):
    heap = []
    valid_count = 0
    for i, product in enumerate(products):
        if product.price != "N/A":
            heapq.heappush(heap, (-product.price, i, product))
            valid_count += 1
    top_products = []
    for _ in range(min(max_results, valid_count)):
        if heap:
            top_products.append(heapq.heappop(heap)[2])
    return top_products

def sort_by_rating(products, max_results=MAX_RESULTS_PER_SITE):
    heap = []
    for i, product in enumerate(products):
        if product.price != "N/A":
            rating = parse_rating(product.rating)
            heapq.heappush(heap, (-rating, i, product))
    top_products = []
    for _ in range(min(max_results, len(heap))):
        if heap:
            top_products.append(heapq.heappop(heap)[2])
    return top_products

def compute_rating_price_score(product):
    rating = parse_rating(product.rating)
    price = product.price
    if price <= 0:
        price = 1
    return (rating ** 2) / math.log10(price)

def get_rating_price_recommendations(products, max_results=MAX_RESULTS_PER_SITE):
    valid_products = [p for p in products if p.price != "N/A"]
    if not valid_products:
        return [], 0
    heap = []
    for i, product in enumerate(valid_products):
        score = compute_rating_price_score(product)
        heapq.heappush(heap, (-score, i, product))
    top_products = []
    for _ in range(min(max_results, len(heap))):
        if heap:
            score, _, product = heapq.heappop(heap)
            product.score = -score
            top_products.append(product)
    return top_products, len(valid_products)

def impute_na_ratings(products):
    valid_ratings = [parse_rating(p.rating) for p in products if parse_rating(p.rating) > 0]
    avg_rating = sum(valid_ratings) / len(valid_ratings) if valid_ratings else 4.0
    na_count = sum(1 for p in products if parse_rating(p.rating) == 0)
    for product in products:
        if parse_rating(product.rating) == 0:
            product.rating = f"{avg_rating:.1f}"
    return na_count, avg_rating