AI Negotiation Agent Project 🤝💰
🎯 Overview
Build an AI-powered negotiation system with BuyerAgent and SellerAgent for trading perishable goods like mangoes and coffee. Choose from three modes: human buyer vs. AI seller, human seller vs. AI buyer, or fully autonomous AI negotiation. Agents use distinct personas (Aggressive, Analytical, Diplomatic, Wildcard) to strategize, adapt, and maximize profits, powered by LLaMA-3 via Ollama.
Features:

Personality-driven negotiations with dynamic persona switching 📣
Regret logic to evaluate deal profitability 📉
Support for human-in-the-loop and autonomous modes 🧠
Product data from products.json (e.g., Coffee, Cardamom) 🍋

Goal: Secure profitable deals within 15 rounds while maintaining persona consistency.

🛠️ Setup 🚀
Prerequisites

Python 3.6+
Ollama server with llama3:8b model
products.json in project directory also in main directory that is nagotiator_agent.py

Steps

Install Dependencies:
pip install -r requirements.txt

requirements.txt:
ollama==0.3.3
requests==2.32.3


Set Up Ollama:
ollama pull llama3:8b
ollama run llama3:8b


Run the Script:
python negotiator_agent.py




🎮 Usage 📋

Select Product: Choose from products.json (e.g., 2 for Coffee ☕).
Choose Mode:
1: Human Buyer vs. AI Seller 🛒
2: Human Seller vs. AI Buyer 📦
3: Autonomous AI Negotiation 🤖


Interact (Human Modes): Enter offers (e.g., I offer ₹15000 per quintal), accept, or walk away.
Output: View round logs and a summary with deal status, prices, and margins 💸.

Example:
🌟 Negotiating for Coffee ☕ 🌟
📣 Seller: I offer ₹16500 per quintal.
🛒 Buyer: With utmost respect, please consider ₹14025 per quintal. 📈
...
📊 Summary: Deal made at ₹14500 (Profit: ₹500, 3.33%) 💰


📂 Project Structure 🗂️
ai_negotiator/
├── negotiator_agent.py  # Buyer and Seller agents 🤝
├── llm_api.py          # LLM interaction via Ollama 🧠
├── products.json       # Product data 🍋
├── requirements.txt    # Dependencies 📦
├── README.md           # This file 📝


🧪 Scenarios 📊

Coffee: Market ₹15,000/quintal, Budget ~₹16,500, Seller Min ~₹13,500 ☕
Kesar Mangoes: Market ₹15,000/quintal, Budget ~₹14,250, Seller Min ~₹13,500 🥭
Cardamom: Market ₹27,500/quintal, Budget ~₹26,125, Seller Min ~₹24,750 🌿


💡 Tips 💡

Strategies: Use Aggressive for quick wins, Diplomatic for win-win deals, or Wildcard for surprises 🎭.
Debugging: Check logs for offer patterns and verify Ollama connectivity 🔍.
Avoid Pitfalls: Ensure Ollama is running, import llm_api.py, and stay within budget 🚫.


❓ FAQ ❓
Q: Ollama server not responding?A: Run ollama run llama3:8b and test with curl http://localhost:11434/api/chat.
Q: Can I customize personas?A: Yes, update PERSONA_TEMPLATES in negotiator_agent.py 🎨.
Good luck negotiating profitable deals! 🏆