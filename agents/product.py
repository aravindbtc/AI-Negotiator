class Product:
    def __init__(self, name, category, quantity, quality_grade, origin, base_market_price, attributes=None):
        self.name = name
        self.category = category
        self.quantity = quantity
        self.quality_grade = quality_grade
        self.origin = origin
        self.base_market_price = base_market_price
        self.attributes = attributes or {}

    def __repr__(self):
        return f"{self.quantity}kg of {self.quality_grade} {self.name} from {self.origin}"