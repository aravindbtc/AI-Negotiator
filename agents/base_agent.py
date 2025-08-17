import ollama

PERSONA_TEMPLATES = {
    "Aggressive": "You are an aggressive negotiator aiming for quick high-profit deals.",
    "Analytical": "You are a logical negotiator who reasons using facts, price trends, and value.",
    "Diplomatic": "You are polite and seek win-win solutions in negotiations.",
    "Wildcard": "You are unpredictable. Use humor, sarcasm, or surprise strategies."
}

class BaseAgent:
    def __init__(self, persona, role):
        self.persona = persona
        self.role = role  # 'buyer' or 'seller'

    def get_context_summary(self, context):
        summary = f"{context['Product Type']} - {context['Variety']} ({context['Grade']} grade) from {context['Origin']} in {context['Season']},"
        for key in context.keys():
            if key not in summary and key not in ["Price (INR/kg)", "Total Price (INR)"]:
                if isinstance(context[key], str) and context[key] not in summary:
                    summary += f" {key}: {context[key]},"
        return summary.strip(',')

    def respond(self, message, context):
        system_prompt = PERSONA_TEMPLATES.get(self.persona, "You are a negotiator.") + f" You are playing the role of a {self.role}."
        try:
            result = ollama.chat(model='llama3', messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context: {self.get_context_summary(context)}"},
                {"role": "user", "content": message}
            ])
            return result['message']['content']
        except Exception as e:
            return f"[ERROR] LLaMA Response Failed: {e}"
