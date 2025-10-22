# modules/knapsack.py
from modules.sorting import compute_rating_price_score

def budget_knapsack_dp(products, budget, max_items=5):
    valid_products = [p for p in products if p.price != "N/A"]
    n = len(valid_products)
    if n == 0:
        return [], 0, 0
    dp = [[[0 for _ in range(max_items + 1)] 
           for _ in range(budget + 1)] 
           for _ in range(n + 1)]
    choice = [[[0 for _ in range(max_items + 1)] 
               for _ in range(budget + 1)] 
               for _ in range(n + 1)]
    for i in range(1, n + 1):
        price = valid_products[i-1].price
        score = compute_rating_price_score(valid_products[i-1])
        for w in range(budget + 1):
            for k in range(max_items + 1):
                dp[i][w][k] = dp[i-1][w][k]
                choice[i][w][k] = 0
                if price <= w and k >= 1:
                    new_score = dp[i-1][w-price][k-1] + score
                    if new_score > dp[i][w][k]:
                        dp[i][w][k] = new_score
                        choice[i][w][k] = 1
    selected = []
    total_cost = 0
    i, w, k = n, budget, max_items
    while i > 0 and w > 0 and k > 0:
        if choice[i][w][k] == 1:
            product = valid_products[i-1]
            product.temp_score = compute_rating_price_score(product)
            selected.append(product)
            total_cost += product.price
            w -= product.price
            k -= 1
        i -= 1
    return selected[::-1], dp[n][budget][max_items], total_cost