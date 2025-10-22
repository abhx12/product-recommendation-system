# modules/product.py
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