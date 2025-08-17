from llm_api import ask_llama3
import re

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

    # ---------------------------
    # UTILITY FUNCTIONS
    # ---------------------------
    def extract_price(self, msg: str) -> int:
        match = re.search(r"₹(\d{4,5})\s*per\s*quintal", msg)
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
        style_to_persona = {
            "Aggressive": "Assertive",
            "Analytical": "Strategic",
            "Collaborative": "Diplomatic",
            "Neutral": "Balanced"
        }
        seller_style = self.detect_seller_style(seller_text)
        new_persona = style_to_persona.get(seller_style, self.personality["personality_type"])
        if new_persona != self.personality["personality_type"]:
            print(f"🔄 Switching buyer persona from {self.personality['personality_type']} to {new_persona} based on seller tone.")
            self.personality["personality_type"] = new_persona

    # ---------------------------
    # PERSONA MARGIN & COUNTER LOGIC
    # ---------------------------
    def get_margin_pct_for_persona(self) -> float:
        persona_margins = {
            "Assertive": 1.0,  # More aggressive target
            "Strategic": 0.80,
            "Balanced": 0.70,
            "Diplomatic": 0.69
        }
        return persona_margins.get(self.personality["personality_type"], 0.01)

    def get_margin_for_persona(self, product_name=None) -> int:
        base_margin = int(self.get_margin_pct_for_persona() * self.last_offer_from_seller)
        if product_name and product_name.lower() in ["cardamom", "mango", "saffron"]:
            base_margin += 50
        return base_margin

    # ---------------------------
    # REGRET LOGIC
    # ---------------------------
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

    # ---------------------------
    # DETECTION LOGIC
    # ---------------------------
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

    # ---------------------------
    # PERSONA TONE
    # ---------------------------
    def get_persona_tone_prefix(self) -> str:
        tone_map = {
            "Assertive": "Frankly speaking,",
            "Strategic": "Considering the bigger picture,",
            "Balanced": "Keeping all factors in mind,",
            "Diplomatic": "With utmost respect and cooperation,"
        }
        return tone_map.get(self.personality["personality_type"], "")

    # ---------------------------
    # MAIN RESPONSE LOGIC — PROFIT-ORIENTED ALWAYS NEGOTIATE
    # ---------------------------
    def respond(self, message: str, context: dict) -> str:
        self.round_num += 1
        seller_price = self.extract_price(message)
        self.last_offer_from_seller = seller_price

        product = context.get("Product", "unknown product")
        origin = context.get("Origin", context.get("Market", ""))
        base_price = context.get("Base Market Price", None)

        # Always set target_price to a dynamic percentage based on persona
        if self.round_num == 1 and base_price:
            target_reduction = self.get_margin_pct_for_persona() * 0.05  # Adjust target based on persona
            self.target_price = int(base_price * (1 - target_reduction))  # E.g., 95% for Diplomatic, 90% for Assertive

        self.switch_persona(message)

        if seller_price:
            self.seller_offer_history.append(seller_price)
            self.detect_inflation_pattern()
            self.detect_softening()

        buyer_intent = self.classify_buyer_intent(message)
        self.intent_log.append((self.round_num, buyer_intent))
        print(f"🧠 Buyer Intent Detected (Round {self.round_num}): {buyer_intent} (💭 Thinking...)")

        if seller_price is not None:
            # Only accept if price is below target and after at least 2 rounds
            if seller_price <= self.target_price and self.round_num >= 2:
                self.negotiation_outcome["final_price"] = seller_price
                return f"{self.get_persona_tone_prefix()} this price of ₹{seller_price} per quintal ensures profit. 💰 Deal finalized!"

            # Walk away if price remains above target after 5 attempts
            if self.counter_attempts >= 7 and seller_price > self.target_price:
                self.walk_away_triggered = True
                return f"{self.get_persona_tone_prefix()} your price of ₹{seller_price} remains unprofitable. 🚪 Walking away."

            # Aggressive counter-offer strategy
            discount_factor = 0.85 if self.softening_detected else 0.87  # More aggressive discounts
            counter_offer = max(int(seller_price * discount_factor), self.target_price * 0.90)
            self.counter_attempts += 1

            if self.suspect_inflation:
                return f"{self.get_persona_tone_prefix()} I’ve noticed a price increase. Let’s settle at ₹{counter_offer} per quintal. 📉"
            elif self.softening_detected:
                return f"{self.get_persona_tone_prefix()} I appreciate your flexibility. Can we close at ₹{counter_offer} per quintal? 💡"
            else:
                return f"{self.get_persona_tone_prefix()} your price of ₹{seller_price} is above our target. Please consider ₹{counter_offer} per quintal. 📈"

        return f"{self.get_persona_tone_prefix()} we value your offer, but could you share a competitive rate? 🤔"

    # ---------------------------
    # RESPONSE TO SELLER OFFER
    # ---------------------------
    def respond_to_buyer(self, seller_offer: int, round_num: int) -> tuple[int, str, bool]:
        """Generate buyer's response to seller's offer."""
        context = {"Base Market Price": self.target_price}
        message = f"Your offer is ₹{seller_offer} per quintal." if seller_offer else "No offer yet."
        response_text = self.respond(message, context)
        price = self.extract_price(response_text) if self.extract_price(response_text) else seller_offer
        is_deal = "deal" in response_text.lower() or "accept" in response_text.lower()
        return price, response_text, is_deal