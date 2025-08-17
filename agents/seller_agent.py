from llm_api import ask_llama3

class SellerAgent:
    def __init__(self, persona="Analytical", min_margin=0.10, max_rounds=15):
        self.persona = persona
        self.min_margin = min_margin
        self.max_rounds = max_rounds
        self.current_round = 0
        self.accepted = False

    def respond(self, message: str, context: dict) -> str:
        self.current_round += 1

        product = context.get("Product", "unknown product")
        variety = context.get("Variety", "")
        origin = context.get("Origin", context.get("Market", ""))
        order_size = context.get("Order Size (kg)", 100)
        base_price = context.get("Base Market Price", None)
        quality = context.get("Quality Grade", "")
        attributes = context.get("Attributes", {})
        buyer_offer = context.get("Buyer Offer", None)

        # Estimate margin based on attributes
        margin = self.min_margin
        if quality == "A":
            margin += 0.05
        if attributes.get("export_grade"):
            margin += 0.05

        attr_summary = ", ".join([f"{k}: {v}" for k, v in attributes.items()]) if attributes else "no special attributes"

        prompt = (
            f"You are an {self.persona} seller offering {order_size}kg of {quality} grade {product} ({variety}) "
            f"from {origin}. The product has {attr_summary}. "
        )

        # Decision logic
        if base_price and buyer_offer:
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

        return ask_llama3(prompt)

    def reset(self):
        self.current_round = 0
        self.accepted = False
