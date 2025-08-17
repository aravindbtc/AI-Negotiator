from flask import Flask, render_template, request, jsonify
import json
import time
import re
from agents.buyer_agent import BuyerAgent
from agents.seller_agent import SellerAgent
from negotiation_engine.logger import log_round

app = Flask(__name__)

# Load dataset from JSON file once
with open('products.json', 'r') as f:
    products_data = json.load(f)

@app.route("/")
def index():
    products = [product["name"] for product in products_data]
    return render_template("index.html", products=products)

@app.route("/negotiate", methods=["POST"])
def negotiate():
    data = request.get_json()
    buyer_persona = data.get("buyerPersona", "Diplomatic")
    seller_persona = data.get("sellerPersona", "Analytical")
    selected_product = data.get("product")

    # Filter product based on selection
    context = next((p for p in products_data if p["name"] == selected_product), None)
    if not context:
        return jsonify({"error": "No data found for selected product."}), 400

    context["Order Size (kg)"] = context.get("quantity", 100)
    context["Product Type"] = context.get("category", context["name"])
    context["Origin"] = context.get("origin", "")
    context["Base Market Price"] = context.get("base_market_price", 0)
    context["Attributes"] = context.get("attributes", {})

    seller = SellerAgent(persona=seller_persona)
    buyer = BuyerAgent(persona=buyer_persona)

    messages = []
    round_num = 1
    max_rounds = 15
    min_required_rounds = 4
    start_time = time.time()
    max_duration = 180
    opening_price = None
    final_price = None

    def deal_reached(buyer_msg, seller_msg):
        keywords = ["finalize", "agreed", "let's proceed", "deal", "confirmed", "move forward"]
        return any(kw in buyer_msg.lower() for kw in keywords) or any(kw in seller_reply.lower() for kw in keywords)

    def extract_final_price(messages):
        for msg in reversed(messages):
            if msg["sender"] in ["Buyer", "Seller"]:
                match = re.search(r"₹(\d{4,5})\s*per\s*quintal", msg["text"])
                if match:
                    return int(match.group(1))
        return None

    def extract_opening_price(messages):
        for msg in messages:
            if msg["sender"] == "Seller":
                match = re.search(r"₹(\d{4,5})\s*per\s*quintal", msg["text"])
                if match:
                    return int(match.group(1))
        return None

    # Round 1: Buyer initiates with price inquiry
    message = f"What’s your offer for {context['Order Size (kg)']}kg of {context.get('Variety', '')} {context['Product Type']} from {context['Origin']}?"
    messages.append({"sender": "Buyer", "text": message})

    while time.time() - start_time < max_duration and round_num <= max_rounds:
        seller_reply = seller.respond(message, context)
        messages.append({"sender": "Seller", "text": f"📣 {seller_reply}"})

        if round_num == 1:
            opening_price = extract_opening_price(messages)

        buyer.switch_persona(seller_reply)
        message = buyer.respond(seller_reply, context)
        messages.append({"sender": "Buyer", "text": f"🛒 {message}"})

        # 🚪 Walk-away logic
        if buyer.walk_away_triggered:
            messages.append({"sender": "System", "text": "🚪 Buyer walked away — negotiation ended."})
            log_round(context, buyer.personality["personality_type"], seller.persona, round_num)
            return jsonify({
                "context": context,
                "messages": messages,
                "rounds": {"current": round_num, "max": max_rounds},
                "finalPrice": None,
                "buyerPersona": buyer.personality,
                "marginUsed": buyer.get_margin_for_persona(context["name"]),
                "summary": {
                    "openingPrice": opening_price,
                    "finalPrice": None,
                    "marketPrice": context["Base Market Price"],
                    "margin": None,
                    "marginType": "Walkaway",
                    "buyerPersona": buyer.personality["personality_type"],
                    "sellerPersona": seller.persona,
                    "totalRounds": round_num,
                    "regret": False,
                    "walkedAway": True
                }
            })

        if deal_reached(message, seller_reply):
            if round_num < min_required_rounds:
                messages.append({"sender": "System", "text": f"⛔ Deal attempt blocked — minimum {min_required_rounds} rounds required."})
                round_num += 1
                continue

            messages.append({"sender": "System", "text": "🤝 Deal reached — negotiation ended."})
            final_price = extract_final_price(messages)
            buyer.log_regret(final_price, float(context["Base Market Price"]))  # Ensure float for consistency
            log_round(context, buyer.personality["personality_type"], seller.persona, round_num)

            margin = context["Base Market Price"] - final_price if final_price else 0
            margin_type = "Profit" if margin > 0 else "Loss"
            buyer_profit_percent = (margin / context["Base Market Price"]) * 100 if context["Base Market Price"] else 0
            seller_margin = final_price - (context["Base Market Price"] * 0.9)  # Assuming 90% as seller's base
            seller_profit_percent = (seller_margin / context["Base Market Price"]) * 100 if context["Base Market Price"] else 0

            return jsonify({
                "context": context,
                "messages": messages,
                "rounds": {"current": round_num, "max": max_rounds},
                "finalPrice": final_price,
                "buyerPersona": buyer.personality,
                "marginUsed": buyer.get_margin_for_persona(context["name"]),
                "summary": {
                    "openingPrice": opening_price,
                    "finalPrice": final_price,
                    "marketPrice": context["Base Market Price"],
                    "margin": abs(round(margin, 2)),
                    "marginType": margin_type,
                    "buyerProfitPercent": round(buyer_profit_percent, 2),
                    "sellerProfitPercent": round(seller_profit_percent, 2),
                    "buyerPersona": buyer.personality["personality_type"],
                    "sellerPersona": seller.persona,
                    "totalRounds": round_num,
                    "regret": buyer.regret_flag,
                    "walkedAway": False
                }
            })

        round_num += 1

    messages.append({"sender": "System", "text": "⏳ Fallback triggered — negotiation ended."})
    final_price = extract_final_price(messages)
    opening_price = opening_price or extract_opening_price(messages)
    buyer.log_regret(final_price, float(context["Base Market Price"]))  # Ensure float for consistency
    log_round(context, buyer.personality["personality_type"], seller.persona, round_num)

    margin = context["Base Market Price"] - final_price if final_price else 0
    margin_type = "Profit" if margin > 0 else "Loss"
    buyer_profit_percent = (margin / context["Base Market Price"]) * 100 if context["Base Market Price"] else 0
    seller_margin = final_price - (context["Base Market Price"] * 0.9)  # Assuming 90% as seller's base
    seller_profit_percent = (seller_margin / context["Base Market Price"]) * 100 if context["Base Market Price"] else 0

    return jsonify({
        "context": context,
        "messages": messages,
        "rounds": {"current": round_num, "max": max_rounds},
        "finalPrice": final_price,
        "buyerPersona": buyer.personality,
        "marginUsed": buyer.get_margin_for_persona(context["name"]),
        "summary": {
            "openingPrice": opening_price,
            "finalPrice": final_price,
            "marketPrice": context["Base Market Price"],
            "margin": abs(round(margin, 2)),
            "marginType": margin_type,
            "buyerProfitPercent": round(buyer_profit_percent, 2),
            "sellerProfitPercent": round(seller_profit_percent, 2),
            "buyerPersona": buyer.personality["personality_type"],
            "sellerPersona": seller.persona,
            "totalRounds": round_num,
            "regret": buyer.regret_flag,
            "walkedAway": False
        }
    })

@app.route("/health")
def health_check():
    try:
        return f"✅ Data available with {len(products_data)} products.", 200
    except Exception as e:
        return f"❌ Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)