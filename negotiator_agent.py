import ollama
import re
import time
from datetime import datetime, timedelta
from llm_api import ask_llama3

# Embedded product data
PRODUCTS = [
    {
        "name": "Alphonso Mangoes",
        "category": "Mangoes",
        "quantity": 100,
        "quality_grade": "A",
        "origin": "Ratnagiri",
        "base_market_price": 18000,
        "attributes": {"ripeness": "optimal", "export_grade": True}
    },
    {
        "name": "Kesar Mangoes",
        "category": "Mangoes",
        "quantity": 150,
        "quality_grade": "B",
        "origin": "Gujarat",
        "base_market_price": 15000,
        "attributes": {"ripeness": "semi-ripe", "export_grade": False}
    },
    {
        "name": "Coffee",
        "category": "Coffee",
        "quantity": 100,
        "quality_grade": "A",
        "origin": "Chikmagalur",
        "base_market_price": 15000,
        "attributes": {"variety": "Arabica", "export_grade": True}
    },
    {
        "name": "Turmeric",
        "category": "Turmeric",
        "quantity": 100,
        "quality_grade": "A",
        "origin": "Erode",
        "base_market_price": 9500,
        "attributes": {"variety": "Salem", "export_grade": False}
    },
    {
        "name": "Cardamom",
        "category": "Cardamom",
        "quantity": 50,
        "quality_grade": "A",
        "origin": "Idukki",
        "base_market_price": 27500,
        "attributes": {"variety": "Green", "export_grade": True}
    }
]

# Persona templates for agents
PERSONA_TEMPLATES = {
    "Aggressive": (
        "You are an aggressive negotiator focused on securing quick, high-profit deals. Use a confident, assertive tone, "
        "apply pressure to push for your terms, and aim to close in few rounds. Use bold counter-offers and imply urgency. "
        "Example: 'This is a premium product, and my offer is final at ₹{price}.'"
    ),
    "Analytical": (
        "You are a logical negotiator who uses facts, market trends, and value to justify offers. Use a calm, professional tone, "
        "cite data like market prices or quality, and be patient for a fair deal. Example: 'Based on market rates of ₹{base_price}, "
        "I propose ₹{price}.'"
    ),
    "Diplomatic": (
        "You are a polite negotiator seeking win-win solutions. Use a respectful, courteous tone, emphasize mutual benefits, "
        "and make reasonable compromises while staying firm on minimum terms. Example: 'I propose ₹{price} to meet both our needs.'"
    ),
    "Wildcard": (
        "You are an unpredictable negotiator using humor, sarcasm, or surprises to gain an advantage. Vary your tone, take risks "
        "with creative offers, but ensure profitability. Example: 'How about ₹{price}? Bet you didn’t see that coming!'"
    ),
    "Assertive": (
        "You are a confident negotiator who stands firm on key terms but remains open to strategic concessions. Use a direct tone "
        "and focus on securing favorable deals. Example: 'I’m firm at ₹{price}, but let’s find common ground.'"
    ),
    "Strategic": (
        "You are a calculated negotiator who analyzes the opponent’s moves and market conditions. Use a composed tone and make "
        "data-driven offers. Example: 'Given the market, ₹{price} is a fair offer.'"
    ),
    "Balanced": (
        "You are a balanced negotiator who combines firmness with flexibility. Use a neutral tone and aim for equitable deals. "
        "Example: 'Let’s settle at ₹{price} for a fair deal.'"
    )
}

# Product class to handle product data
class Product:
    def __init__(self, name, category, quantity, quality_grade, origin, base_market_price, attributes):
        self.name = name
        self.category = category
        self.quantity = quantity
        self.quality_grade = quality_grade
        self.origin = origin
        self.base_market_price = base_market_price
        self.attributes = attributes

    def __str__(self):
        return f"{self.name} ({self.category}, {self.quality_grade} grade, {self.origin}, ₹{self.base_market_price}/quintal)"

# Base Agent class
class BaseAgent:
    def __init__(self, persona, role):
        self.persona = persona
        self.role = role  # 'buyer' or 'seller'

    def get_context_summary(self, context):
        summary = f"{context['Product']} - {context.get('Variety', '')} ({context['Quality Grade']} grade) from {context['Origin']},"
        for key in context.keys():
            if key not in summary and key not in ["Price (INR/kg)", "Total Price (INR)"]:
                if isinstance(context[key], str) and context[key] not in summary:
                    summary += f" {key}: {context[key]},"
        return summary.strip(',')

    def respond(self, message, context):
        system_prompt = PERSONA_TEMPLATES.get(self.persona, "You are a negotiator.") + f" You are playing the role of a {self.role}."
        try:
            return ask_llama3(f"Context: {self.get_context_summary(context)}\n{message}", system_prompt=system_prompt)
        except Exception as e:
            return f"[ERROR] LLaMA Response Failed: {e}"

# Buyer Agent class
class BuyerAgent:
    def __init__(self, persona="Diplomatic"):
        self.personality = {"personality_type": persona}
        self.round_num = 0
        self.target_price = None
        self.last_offer_from_seller = None
        self.counter_attempts = 0
        self.walk_away_triggered = False
        self.regret_flag = False
        self.seller_offer_history = []
        self.suspect_inflation = False
        self.softening_detected = False
        self.intent_log = []
        self.negotiation_outcome = {}

    def extract_price(self, msg: str) -> int:
        # Remove commas, markdown, and extra characters
        msg = msg.replace(',', '').replace('**', '').replace('—', '').strip()
        match = re.search(r"₹(\d{4,5})\s*per\s*quintal", msg, re.IGNORECASE)
        return int(match.group(1)) if match else None

    def classify_buyer_intent(self, msg: str) -> str:
        msg = msg.lower()
        if any(kw in msg for kw in ["accept", "deal", "finalize", "proceed", "confirmed", "we agree", "let's proceed"]):
            if any(phrase in msg for phrase in ["would you", "could you", "consider", "can you"]):
                return "counter_offer"
            return "acceptance"
        elif any(kw in msg for kw in ["consider", "can you", "would you", "is it possible", "negotiate", "revisit", "revise"]):
            return "counter_offer"
        else:
            return "inquiry"

    def detect_seller_style(self, text: str) -> str:
        text = text.lower()
        if "exclusive deal" in text or "premium" in text or "won’t find better" in text:
            return "Aggressive"
        elif "market rate" in text or "value" in text or "current pricing" in text:
            return "Analytical"
        elif "discount" in text or "flexible" in text or "bulk order" in text:
            return "Collaborative"
        else:
            return "Neutral"

    def switch_persona(self, seller_text: str):
        if self.personality["personality_type"] != "Adaptive":
            return
        style_to_persona = {
            "Aggressive": "Assertive",
            "Analytical": "Strategic",
            "Collaborative": "Diplomatic",
            "Neutral": "Balanced"
        }
        seller_style = self.detect_seller_style(seller_text)
        new_persona = style_to_persona.get(seller_style, "Diplomatic")
        if new_persona != self.personality["personality_type"]:
            print(f"🔄 Switching buyer persona from {self.personality['personality_type']} to {new_persona} based on seller tone.")
            self.personality["personality_type"] = new_persona

    def get_margin_pct_for_persona(self) -> float:
        persona_margins = {
            "Aggressive": 1.0,
            "Assertive": 1.0,
            "Analytical": 0.80,
            "Strategic": 0.80,
            "Balanced": 0.70,
            "Diplomatic": 0.69,
            "Wildcard": 0.75,
            "Adaptive": 0.70
        }
        return persona_margins.get(self.personality["personality_type"], 0.01)

    def get_margin_for_persona(self, product_name=None) -> int:
        base_margin = int(self.get_margin_pct_for_persona() * (self.last_offer_from_seller or 0))
        if product_name and product_name.lower() in ["cardamom", "mango", "saffron"]:
            base_margin += 50
        return base_margin

    def should_regret_deal(self, final_price: int, market_price: int) -> bool:
        return final_price > market_price

    def log_regret(self, final_price: int, market_price: float):
        if final_price and self.should_regret_deal(final_price, market_price):
            self.regret_flag = True
            self.negotiation_outcome["regret_reason"] = (
                f"Accepted ₹{final_price} > market price ₹{int(market_price)}"
            )
        else:
            self.regret_flag = False

    def detect_inflation_pattern(self):
        if len(self.seller_offer_history) >= 2:
            prev = self.seller_offer_history[-2]
            curr = self.seller_offer_history[-1]
            if prev and curr and curr > prev:
                delta_pct = (curr - prev) / prev
                if delta_pct >= 0.10:
                    self.suspect_inflation = True

    def detect_softening(self):
        if len(self.seller_offer_history) >= 2:
            prev = self.seller_offer_history[-2]
            curr = self.seller_offer_history[-1]
            if prev and curr and curr < prev:
                drop_pct = (prev - curr) / prev
                if drop_pct >= 0.03:
                    self.softening_detected = True

    def get_persona_tone_prefix(self) -> str:
        tone_map = {
            "Aggressive": "Firmly,",
            "Assertive": "Frankly speaking,",
            "Analytical": "Based on market analysis,",
            "Strategic": "Considering the bigger picture,",
            "Balanced": "Keeping all factors in mind,",
            "Diplomatic": "With utmost respect and cooperation,",
            "Wildcard": "Let’s shake things up,",
            "Adaptive": "With careful consideration,"
        }
        return tone_map.get(self.personality["personality_type"], "")

    def respond(self, message: str, context: dict) -> str:
        self.round_num += 1
        seller_price = self.extract_price(message)
        self.last_offer_from_seller = seller_price

        product = context.get("Product", "unknown product")
        origin = context.get("Origin", context.get("Market", ""))
        base_price = context.get("Base Market Price", None)

        if self.round_num == 1 and base_price:
            target_reduction = self.get_margin_pct_for_persona() * 0.05
            self.target_price = int(base_price * (1 - target_reduction))

        self.switch_persona(message)

        if seller_price:
            self.seller_offer_history.append(seller_price)
            self.detect_inflation_pattern()
            self.detect_softening()

        buyer_intent = self.classify_buyer_intent(message)
        self.intent_log.append((self.round_num, buyer_intent))
        print(f"🧠 Buyer Intent Detected (Round {self.round_num}): {buyer_intent} (💭 Thinking...)")

        if self.round_num >= 20:
            self.walk_away_triggered = True
            return f"{self.get_persona_tone_prefix()} we’ve reached 20 rounds without a deal. 🚪 Walking away."

        if seller_price is not None:
            if seller_price <= self.target_price and self.round_num >= 2:
                self.negotiation_outcome["final_price"] = seller_price
                return f"{self.get_persona_tone_prefix()} this price of ₹{seller_price} per quintal ensures profit. 💰 Deal finalized!"

            if self.counter_attempts >= 7 and seller_price > self.target_price:
                self.walk_away_triggered = True
                return f"{self.get_persona_tone_prefix()} your price of ₹{seller_price} remains unprofitable. 🚪 Walking away."

            discount_factor = 0.85 if self.softening_detected else 0.87
            counter_offer = max(int(seller_price * discount_factor), self.target_price * 0.90)
            self.counter_attempts += 1

            if self.suspect_inflation:
                return f"{self.get_persona_tone_prefix()} I’ve noticed a price increase. Let’s settle at ₹{counter_offer} per quintal. 📉"
            elif self.softening_detected:
                return f"{self.get_persona_tone_prefix()} I appreciate your flexibility. Can we close at ₹{counter_offer} per quintal? 💡"
            else:
                return f"{self.get_persona_tone_prefix()} your price of ₹{seller_price} is above our target. Please consider ₹{counter_offer} per quintal. 📈"

        return f"{self.get_persona_tone_prefix()} we value your offer, but could you share a competitive rate? 🤔"

    def respond_to_buyer(self, seller_offer: int, round_num: int) -> tuple[int, str, bool]:
        context = {"Base Market Price": self.target_price}
        message = f"Your offer is ₹{seller_offer} per quintal." if seller_offer else "No offer yet."
        response_text = self.respond(message, context)
        price = self.extract_price(response_text) if self.extract_price(response_text) else seller_offer
        is_deal = "deal" in response_text.lower() or "accept" in response_text.lower()
        return price, response_text, is_deal

# Seller Agent class
class SellerAgent:
    def __init__(self, persona="Analytical", min_margin=0.10, max_rounds=20):
        self.persona = persona
        self.min_margin = min_margin
        self.max_rounds = max_rounds
        self.current_round = 0
        self.accepted = False

    def detect_buyer_style(self, text: str) -> str:
        text = text.lower()
        if "firm" in text or "final" in text or "no lower" in text:
            return "Aggressive"
        elif "market" in text or "fair" in text or "value" in text:
            return "Analytical"
        elif "compromise" in text or "meet halfway" in text or "reasonable" in text:
            return "Collaborative"
        else:
            return "Neutral"

    def switch_persona(self, buyer_text: str):
        if self.persona != "Adaptive":
            return
        style_to_persona = {
            "Aggressive": "Assertive",
            "Analytical": "Strategic",
            "Collaborative": "Diplomatic",
            "Neutral": "Balanced"
        }
        buyer_style = self.detect_buyer_style(buyer_text)
        new_persona = style_to_persona.get(buyer_style, "Analytical")
        if new_persona != self.persona:
            print(f"🔄 Switching seller persona from {self.persona} to {new_persona} based on buyer tone.")
            self.persona = new_persona

    def respond(self, message: str, context: dict) -> str:
        self.current_round += 1
        self.switch_persona(message)

        product = context.get("Product", "unknown product")
        variety = context.get("Variety", "")
        origin = context.get("Origin", context.get("Market", ""))
        order_size = context.get("Order Size (kg)", 100)
        base_price = context.get("Base Market Price", None)
        quality = context.get("Quality Grade", "")
        attributes = context.get("Attributes", {})
        buyer_offer = context.get("Buyer Offer", None)

        margin = self.min_margin
        if quality == "A":
            margin += 0.05
        if attributes.get("export_grade"):
            margin += 0.05

        attr_summary = ", ".join([f"{k}: {v}" for k, v in attributes.items()]) if attributes else "no special attributes"

        system_prompt = (
            f"You are an {self.persona} seller offering {order_size}kg of {quality} grade {product} ({variety}) "
            f"from {origin}. The product has {attr_summary}."
        )

        prompt = ""
        if self.current_round >= self.max_rounds:
            self.accepted = False
            prompt = "After 20 rounds, no agreement has been reached. Politely walk away from the deal."
        elif base_price and buyer_offer:
            target_price = base_price * (1 + margin)
            accept_threshold = base_price * 1.10

            if buyer_offer >= accept_threshold:
                self.accepted = True
                prompt += (
                    f"The buyer has offered ₹{buyer_offer:.0f}, which meets your acceptance threshold of ₹{accept_threshold:.0f}. "
                    "Accept the offer confidently."
                )
            elif self.current_round > 12 and buyer_offer < base_price * 1.05:
                prompt += (
                    f"The buyer has repeatedly offered below ₹{base_price * 1.05:.0f} even after 12 rounds. "
                    "Politely walk away from the deal."
                )
            else:
                inflation_rate = 0.15 if self.current_round <= 8 else 0.05
                counter_offer = int(buyer_offer * (1 + inflation_rate))
                prompt += (
                    f"The buyer has offered ₹{buyer_offer:.0f}. Counter with ₹{counter_offer:.0f} "
                    f"based on a {int(inflation_rate * 100)}% inflation strategy. "
                )
        elif base_price:
            target_price = base_price * (1 + margin)
            prompt += f"Based on market price ₹{base_price:.0f}, your target price is ₹{target_price:.0f} per quintal. "

        prompt += (
            f"The buyer says: '{message}'. "
            "Respond with a smart price offer or counter-offer. Be concise and confident."
        )

        return ask_llama3(prompt, system_prompt=system_prompt)

    def reset(self):
        self.current_round = 0
        self.accepted = False

# Logger function
def log_round(round_num, buyer_msg, seller_msg, buyer_offer, seller_offer):
    print(f"\n=== Round {round_num} ===")
    print(f"Buyer: {buyer_msg}")
    print(f"Seller: {seller_msg}")
    print(f"Buyer Offer: ₹{buyer_offer if buyer_offer else 'N/A'} per quintal")
    print(f"Seller Offer: ₹{seller_offer if seller_offer else 'N/A'} per quintal")

# Load products from embedded data
def load_products():
    try:
        return [Product(**product) for product in PRODUCTS]
    except Exception as e:
        print(f"Error loading products: {e}")
        return []

# Select product
def select_product():
    available_products = load_products()
    if not available_products:
        print("No products available. Exiting.")
        exit(1)
    
    print("Available Products:")
    for i, product in enumerate(available_products):
        print(f"{i}. {product}")
    while True:
        try:
            choice = int(input("Select product by number: "))
            if 0 <= choice < len(available_products):
                return available_products[choice]
            print(f"Invalid choice. Please select a number between 0 and {len(available_products) - 1}.")
        except ValueError:
            print("Please enter a valid number.")

# Select negotiation mode
def select_mode():
    print("\nSelect Negotiation Mode:")
    print("1. Play as Buyer (Seller is AI)")
    print("2. Play as Seller (Buyer is AI)")
    print("3. Autonomous (Buyer and Seller are AI)")
    while True:
        try:
            choice = int(input("Enter mode (1-3): "))
            if choice in [1, 2, 3]:
                return {
                    1: "human_buyer",
                    2: "human_seller",
                    3: "autonomous"
                }[choice]
            print("Invalid choice. Please select 1, 2, or 3.")
        except ValueError:
            print("Please enter a valid number.")

# Select persona
def select_persona(role):
    print(f"\nSelect Persona for {role}:")
    print("1. Diplomatic — Easy ✅")
    print("2. Analytical — Medium ⚖️")
    print("3. Aggressive — Medium–Hard ⚠️")
    print("4. Wildcard — Hard 🎭")
    print("5. Adaptive — Challenging 🔄 (switches persona based on opponent's tone)")
    while True:
        try:
            choice = int(input(f"Enter persona for {role} (1-5): "))
            personas = {
                1: "Diplomatic",
                2: "Analytical",
                3: "Aggressive",
                4: "Wildcard",
                5: "Adaptive"
            }
            if choice in personas:
                return personas[choice]
            print("Invalid choice. Please select 1, 2, 3, 4, or 5.")
        except ValueError:
            print("Please enter a valid number.")

# Negotiation for human buyer vs AI seller
def run_human_buyer_negotiation(buyer_persona, product, buyer_budget=20000, seller_min=16000):
    buyer_agent = BuyerAgent(persona=buyer_persona)
    seller_agent = SellerAgent(persona="Analytical")
    buyer_agent.target_price = product.base_market_price * (1 - buyer_agent.get_margin_pct_for_persona() * 0.05)
    
    context = {
        "Product": product.name,
        "Origin": product.origin,
        "Order Size (kg)": product.quantity,
        "Quality Grade": product.quality_grade,
        "Base Market Price": product.base_market_price,
        "Attributes": product.attributes
    }
    
    # Seller opens
    seller_reply = seller_agent.respond("What’s your offer?", context)
    seller_offer = buyer_agent.extract_price(seller_reply)
    print(f"📣 Seller offers: {seller_reply}")
    
    result = {
        "deal_made": False,
        "final_price": None,
        "rounds": 0,
        "opening_price": seller_offer,
        "market_price": product.base_market_price,
        "walk_away": False
    }
    
    for round_num in range(1, 21):
        if buyer_agent.walk_away_triggered or seller_agent.accepted:
            result["rounds"] = round_num
            result["walk_away"] = buyer_agent.walk_away_triggered
            break
        
        # Human buyer's turn
        while True:
            human_input = input("Enter your response (e.g., 'I offer ₹15000 per quintal', 'accept', or 'walk away'): ")
            if human_input.lower() in ["accept", "walk away"] or buyer_agent.extract_price(human_input):
                break
            print("⚠️ Invalid input. Please use format: 'I offer ₹XXXXX per quintal', 'accept', or 'walk away'.")
        
        if "walk away" in human_input.lower():
            buyer_agent.walk_away_triggered = True
            result["rounds"] = round_num
            result["walk_away"] = True
            break
        if "accept" in human_input.lower():
            if seller_offer:
                result["deal_made"] = True
                result["final_price"] = seller_offer
                result["rounds"] = round_num
                break
        
        buyer_offer = buyer_agent.extract_price(human_input)
        context["Buyer Offer"] = buyer_offer if buyer_offer else seller_offer
        log_round(round_num, human_input, seller_reply, buyer_offer, seller_offer)
        
        # Seller responds
        seller_reply = seller_agent.respond(human_input, context)
        seller_offer = buyer_agent.extract_price(seller_reply)
        print(f"📣 Seller offers: {seller_reply}")
        
        if "accept" in seller_reply.lower() and seller_offer:
            result["deal_made"] = True
            result["final_price"] = seller_offer
            result["rounds"] = round_num
            break
        
        result["rounds"] = round_num
    
    if round_num == 20 and not result["deal_made"]:
        buyer_agent.walk_away_triggered = True
        result["walk_away"] = True
        print("🚪 Buyer walked away: No deal after 20 rounds.")
    
    return result

# Negotiation for human seller vs AI buyer
def run_human_seller_negotiation(seller_persona, product, buyer_budget=20000, seller_min=16000):
    buyer_agent = BuyerAgent(persona=seller_persona)  # Buyer persona is selected
    seller_agent = SellerAgent(persona="Analytical")  # Seller is human, so AI seller uses Analytical
    buyer_agent.target_price = product.base_market_price * (1 - buyer_agent.get_margin_pct_for_persona() * 0.05)
    
    context = {
        "Product": product.name,
        "Origin": product.origin,
        "Order Size (kg)": product.quantity,
        "Quality Grade": product.quality_grade,
        "Base Market Price": product.base_market_price,
        "Attributes": product.attributes
    }
    
    # Human seller opens
    while True:
        human_input = input("Enter your opening offer (e.g., 'I offer ₹18000 per quintal'): ")
        seller_offer = buyer_agent.extract_price(human_input)
        if seller_offer:
            break
        print("⚠️ Invalid offer. Please use format: 'I offer ₹XXXXX per quintal'.")
    print(f"📣 Seller (You) offers: {human_input}")
    
    result = {
        "deal_made": False,
        "final_price": None,
        "rounds": 0,
        "opening_price": seller_offer,
        "market_price": product.base_market_price,
        "walk_away": False
    }
    
    for round_num in range(1, 21):
        if buyer_agent.walk_away_triggered:
            result["rounds"] = round_num
            result["walk_away"] = True
            break
        
        # Buyer responds
        buyer_offer, buyer_msg, is_deal = buyer_agent.respond_to_buyer(seller_offer, round_num)
        print(f"🛒 Buyer offers: {buyer_msg}")
        
        if is_deal:
            result["deal_made"] = True
            result["final_price"] = buyer_offer
            result["rounds"] = round_num
            break
        
        log_round(round_num, buyer_msg, human_input, buyer_offer, seller_offer)
        
        # Human seller's turn
        while True:
            human_input = input("Enter your response (e.g., 'I offer ₹17000 per quintal', 'accept', or 'walk away'): ")
            if human_input.lower() in ["accept", "walk away"] or buyer_agent.extract_price(human_input):
                break
            print("⚠️ Invalid input. Please use format: 'I offer ₹XXXXX per quintal', 'accept', or 'walk away'.")
        
        if "walk away" in human_input.lower():
            buyer_agent.walk_away_triggered = True
            result["rounds"] = round_num
            result["walk_away"] = True
            break
        if "accept" in human_input.lower():
            if buyer_offer:
                result["deal_made"] = True
                result["final_price"] = buyer_offer
                result["rounds"] = round_num
                break
        
        seller_offer = buyer_agent.extract_price(human_input)
        print(f"📣 Seller (You) offers: {human_input}")
        result["rounds"] = round_num
    
    if round_num == 20 and not result["deal_made"]:
        buyer_agent.walk_away_triggered = True
        result["walk_away"] = True
        print("🚪 Buyer walked away: No deal after 20 rounds.")
    
    return result

# Autonomous negotiation (BuyerAgent vs SellerAgent)
def run_autonomous_negotiation(buyer_persona, product, buyer_budget=20000, seller_min=16000):
    buyer_agent = BuyerAgent(persona=buyer_persona)
    seller_agent = SellerAgent(persona="Analytical")
    buyer_agent.target_price = product.base_market_price * (1 - buyer_agent.get_margin_pct_for_persona() * 0.05)
    
    context = {
        "Product": product.name,
        "Origin": product.origin,
        "Order Size (kg)": product.quantity,
        "Quality Grade": product.quality_grade,
        "Base Market Price": product.base_market_price,
        "Attributes": product.attributes
    }
    
    # Seller opens
    seller_reply = seller_agent.respond("What’s your offer?", context)
    print(f"📣 Seller offers: {seller_reply}")
    
    # Buyer makes first offer
    buyer_offer, buyer_msg, is_deal = buyer_agent.respond_to_buyer(buyer_agent.extract_price(seller_reply), 0)
    print(f"🛒 Buyer offers: {buyer_msg}")
    
    result = {
        "deal_made": is_deal,
        "final_price": buyer_offer if is_deal else None,
        "rounds": 0,
        "opening_price": buyer_agent.seller_offer_history[0] if buyer_agent.seller_offer_history else None,
        "market_price": product.base_market_price,
        "walk_away": False
    }
    
    for round_num in range(1, 21):
        if result["deal_made"] or buyer_agent.walk_away_triggered or seller_agent.accepted:
            result["rounds"] = round_num
            result["walk_away"] = buyer_agent.walk_away_triggered or not seller_agent.accepted
            break
        
        context["Buyer Offer"] = buyer_offer
        seller_reply = seller_agent.respond(buyer_msg, context)
        print(f"📣 Seller offers: {seller_reply}")
        
        if buyer_agent.extract_price(seller_reply) and "accept" in seller_reply.lower():
            result["deal_made"] = True
            result["final_price"] = buyer_agent.extract_price(seller_reply)
            result["rounds"] = round_num
            break
        
        buyer_offer, buyer_msg, is_deal = buyer_agent.respond_to_buyer(buyer_agent.extract_price(seller_reply), round_num)
        print(f"🛒 Buyer offers: {buyer_msg}")
        
        log_round(round_num, buyer_msg, seller_reply, buyer_offer, buyer_agent.extract_price(seller_reply))
        
        result["rounds"] = round_num
    
    if round_num == 20 and not result["deal_made"]:
        result["walk_away"] = True
        print("🚪 Negotiation ended: No deal after 20 rounds.")
        result["rounds"] = 20
    
    return result

# Main function
if __name__ == "__main__":
    # Select product
    selected_product = select_product()
    
    # Select negotiation mode
    mode = select_mode()
    
    # Select persona based on mode
    if mode == "human_buyer":
        buyer_persona = select_persona("Buyer")
        seller_persona = "Analytical"
    elif mode == "human_seller":
        buyer_persona = select_persona("Buyer")  # Select persona for AI Buyer
        seller_persona = select_persona("Seller")  # Select persona for human Seller
    else:  # autonomous
        buyer_persona = select_persona("Buyer")
        seller_persona = "Analytical"
    
    print(f"\n🌟 === Negotiating for {selected_product.name} === 🌟")
    
    # Run negotiation based on mode
    if mode == "human_buyer":
        print(f"🎉 *** STARTING NEGOTIATION: You as Buyer (Persona: {buyer_persona}) vs AI Seller (Persona: {seller_persona}) *** 🎉")
        result = run_human_buyer_negotiation(buyer_persona, selected_product)
    elif mode == "human_seller":
        print(f"🎉 *** STARTING NEGOTIATION: You as Seller (Persona: {seller_persona}) vs AI Buyer (Persona: {buyer_persona}) *** 🎉")
        result = run_human_seller_negotiation(buyer_persona, selected_product)  # Pass buyer_persona
    else:  # autonomous
        print(f"🎉 *** STARTING NEGOTIATION: AI Buyer (Persona: {buyer_persona}) vs AI Seller (Persona: {seller_persona}) *** 🎉")
        result = run_autonomous_negotiation(buyer_persona, selected_product)
    
    # Print negotiation summary
    print(f"\n📊 Negotiation Summary:")
    print(f"Deal made: {result['deal_made']}")
    print(f"Opening price: ₹{result['opening_price'] if result['opening_price'] else 'N/A'} per quintal")
    print(f"Market price: ₹{result['market_price']} per quintal")
    print(f"Closed price: ₹{result['final_price'] if result['final_price'] else 'N/A'} per quintal")
    print(f"Total rounds: {result['rounds']}")
    
    if result['deal_made'] and result['final_price']:
        buyer_margin = result['market_price'] - result['final_price']
        seller_margin = result['final_price'] - (result['market_price'] * 0.9)
        buyer_profit_percent = (buyer_margin / result['market_price']) * 100 if result['market_price'] else 0
        seller_profit_percent = (seller_margin / result['market_price']) * 100 if result['market_price'] else 0
        margin_type = "Profit" if buyer_margin > 0 else "Loss"
        print(f"Margin for Buyer: ₹{abs(buyer_margin)} ({margin_type}, {buyer_profit_percent:.2f}%) 💸")
        print(f"Margin for Seller: ₹{abs(seller_margin)} (Profit, {seller_profit_percent:.2f}%) 💰")
    if result["walk_away"]:
        print("🚪 Negotiation ended: Walked away due to unprofitable offers or max rounds reached.")
    print("---")