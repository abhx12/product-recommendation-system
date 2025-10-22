# modules/avl_tree.py
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