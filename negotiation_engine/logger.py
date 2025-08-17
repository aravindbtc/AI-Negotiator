import os
from datetime import datetime

LOG_FILE = "data/negotiation_log.txt"

def log_round(context, buyer_persona, seller_persona, rounds):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        # Start of log entry with timestamp
        f.write(f"--- Negotiation [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ---\n")
        
        # Robust field access using .get() with fallback options
        product = context.get('Product') or context.get('Product Type', 'Unknown')
        variety = context.get('Variety', 'N/A')
        origin = context.get('Origin') or context.get('State', 'Unknown')
        season = context.get('Season', 'N/A')
        order_size = context.get('Order Size (kg)', '?')
        base_price = context.get('Base Market Price', 'N/A')
        opening_price = context.get('opening_price', 'N/A')
        final_price = context.get('final_price', 'N/A')
        walked_away = context.get('walked_away', False)
        regret = context.get('regret', False)

        # Calculate margin and profit/loss if prices are available
        if isinstance(base_price, (int, float)) and isinstance(final_price, (int, float)) and final_price != 'N/A':
            margin = base_price - final_price
            margin_type = "Profit" if margin > 0 else "Loss"
            profit_percent = (margin / base_price) * 100 if base_price else 0
            seller_margin = final_price - (base_price * 0.9)  # Assuming 90% as seller's base
            seller_profit_percent = (seller_margin / base_price) * 100 if base_price else 0
        else:
            margin = None
            margin_type = "N/A"
            profit_percent = 0
            seller_margin = None
            seller_profit_percent = 0

        # Write detailed log
        f.write(f"Product: {product} | Variety: {variety}\n")
        f.write(f"Origin: {origin} | Season: {season}\n")
        f.write(f"Buyer Persona: {buyer_persona} | Seller Persona: {seller_persona}\n")
        f.write(f"Order Size: {order_size} kg | Base Market Price: ₹{base_price}\n")
        f.write(f"Opening Price: ₹{opening_price} | Final Price: ₹{final_price}\n")
        f.write(f"Total Rounds: {rounds}\n")
        f.write(f"Margin: ₹{abs(margin) if margin else 'N/A'} ({margin_type}, {profit_percent:.2f}%) | Seller Margin: ₹{abs(seller_margin) if seller_margin else 'N/A'} (Profit, {seller_profit_percent:.2f}%)\n")
        f.write(f"Walked Away: {walked_away} | Regret: {regret}\n")
        f.write("-" * 50 + "\n")