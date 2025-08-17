import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import random
import time

# Updated working URLs for scraping commodity prices from commodityonline.com
COMMODITY_URLS = {
    "Cardamom": "https://www.commodityonline.com/mandiprices/cardamoms/kerala",
    "Turmeric": "https://www.commodityonline.com/mandiprices/turmeric",
    "Mango": "https://www.commodityonline.com/mandiprices/mango",
    "Potato": "https://www.commodityonline.com/mandiprices/potato",
    "Coffee": "https://www.commodityonline.com/mandiprices/state/karnataka",
    "Coconut": "https://www.commodityonline.com/mandiprices/coconut/uttrakhand/dehradoon"
}

OUTPUT_FILE = r"C:\\Users\\aravi\\Music\\ai_negotiator\\data\\negotiation_market_data.csv"

def get_headers():
    """Generate random headers to mimic a real browser."""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5.2 Safari/605.1.15"
    ]
    return {
        "User-Agent": random.choice(user_agents),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

def initialize_csv():
    """Initialize CSV with headers if missing or empty."""
    if not os.path.exists(OUTPUT_FILE) or os.path.getsize(OUTPUT_FILE) == 0:
        empty_df = pd.DataFrame(columns=[
            "Date", "Product", "Variety", "State", "District", "Market",
            "Min Price (Rs/quintal)", "Max Price (Rs/quintal)"
        ])
        empty_df.to_csv(OUTPUT_FILE, index=False)
        print(f"📄 Initialized empty CSV at: {OUTPUT_FILE}")

def generate_dummy_data(product: str) -> list:
    """Fallback dummy data with realistic price ranges."""
    markets = ["Mumbai", "Chennai", "Kolkata", "Delhi", "Bengaluru", "Ahmedabad"]
    states = ["Maharashtra", "Tamil Nadu", "West Bengal", "Delhi", "Karnataka", "Gujarat"]
    
    product_price_ranges = {
        "Mango": (4000, 7000),
        "Coffee": (10000, 15000),
        "Turmeric": (8000, 12000),
        "Cardamom": (20000, 30000),
        "Potato": (1500, 2500),
        "Coconut": (2000, 5000)
    }
    
    varieties = {
        "Mango": ["Alphonso", "Badami", "Kesar"],
        "Coffee": ["Arabica", "Robusta", "Chicory Blend"],
        "Turmeric": ["Salem", "Erode", "Sangli"],
        "Cardamom": ["Green", "Black", "Mixed Grade"],
        "Potato": ["Jyoti", "Kufri"],
        "Coconut": ["Fresh", "Desiccated"]
    }

    data = []
    for _ in range(3):
        price_low_base, price_high_base = product_price_ranges.get(product, (3000, 6000))
        price_low = random.randint(price_low_base, int(price_high_base * 0.9))
        price_high = price_low + random.randint(50, int(price_high_base * 0.1))
        
        row = {
            "Date": datetime.today().strftime('%Y-%m-%d'),
            "Product": product,
            "Variety": random.choice(varieties.get(product, ["Standard"])),
            "State": random.choice(states),
            "District": "N/A",
            "Market": random.choice(markets),
            "Min Price (Rs/quintal)": price_low,
            "Max Price (Rs/quintal)": price_high
        }
        data.append(row)
    print(f"⚠️ Using dummy data for {product} due to scraping failure.")
    return data

def scrape_prices(product: str, url: str, retries: int = 3) -> list:
    """Scrape prices from commodityonline.com with retries and fallback."""
    attempt = 0
    while attempt < retries:
        try:
            headers = get_headers()
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Different parsing logic depending on product and page structure

            # For Cardamom and Coconut (Kerala / Dehradoon)
            if product == "Cardamom" and "cardamoms/kerala" in url:
                table = soup.find("table", class_="table")
                data = []
                if table:
                    for tr in table.find_all("tr")[1:]:
                        tds = tr.find_all("td")
                        if len(tds) >= 4:
                            row = {
                                "Date": datetime.today().strftime('%Y-%m-%d'),
                                "Product": "Cardamom",
                                "Variety": "N/A",
                                "State": "Kerala",
                                "District": "N/A",
                                "Market": tds[0].text.strip(),
                                "Min Price (Rs/quintal)": tds[2].text.strip().replace("Rs ", "").replace("/ Kg", "").strip(),
                                "Max Price (Rs/quintal)": tds[1].text.strip().replace("Rs ", "").replace("/ Kg", "").strip()
                            }
                            data.append(row)
                    if data:
                        return data

            if product == "Coconut" and "coconut/uttrakhand/dehradoon" in url:
                # Coconut prices on specific page
                summary_section = soup.find("div", class_="market-price-summary")
                data = []
                if summary_section:
                    avg_price_text = summary_section.find("li", class_="mb-1").find("p").text.strip()
                    prices = [float(s) for s in avg_price_text.split() if s.replace('.', '', 1).isdigit()]
                    if prices:
                        row = {
                            "Date": datetime.today().strftime('%Y-%m-%d'),
                            "Product": "Coconut",
                            "Variety": "N/A",
                            "State": "Uttrakhand",
                            "District": "Dehradoon",
                            "Market": "Dehradoon",
                            "Min Price (Rs/quintal)": prices[1],
                            "Max Price (Rs/quintal)": prices[0]
                        }
                        data.append(row)
                        return data

            # For Coffee (Karnataka) with different table class
            if product == "Coffee" and "state/karnataka" in url:
                table = soup.find("table", class_="table table-list")
                data = []
                if table:
                    tbody = table.find("tbody")
                    if tbody:
                        for tr in tbody.find_all("tr"):
                            tds = tr.find_all("td")
                            if len(tds) >= 8:
                                row = {
                                    "Date": tds[1].text.strip(),
                                    "Product": tds[0].text.strip(),
                                    "Variety": "N/A",
                                    "State": "Karnataka",
                                    "District": tds[2].text.strip(),
                                    "Market": tds[3].text.strip(),
                                    "Min Price (Rs/quintal)": tds[6].text.strip().replace("₹ ", "").replace("/ Quintal", ""),
                                    "Max Price (Rs/quintal)": tds[8].text.strip().replace("₹ ", "").replace("/ Quintal", "")
                                }
                                if row["Product"].lower() == "coffee":
                                    data.append(row)
                        if data:
                            return data

            # For Turmeric, Mango, Potato — generic commodityonline.com tables
            # These pages have tables with class 'table table-bordered table-striped'
            table = soup.find("table", class_="table table-bordered table-striped")
            data = []
            if table:
                for tr in table.find_all("tr")[1:]:
                    tds = tr.find_all("td")
                    if len(tds) >= 7:
                        # Structure: Market | Variety | Min | Max | ...
                        # Date and state/district may not be explicitly present; we assign today and N/A for these
                        min_price = tds[4].text.strip().replace("₹ ", "").replace("/ Quintal", "").replace(",", "")
                        max_price = tds[5].text.strip().replace("₹ ", "").replace("/ Quintal", "").replace(",", "")
                        row = {
                            "Date": datetime.today().strftime('%Y-%m-%d'),
                            "Product": product,
                            "Variety": tds[1].text.strip() if len(tds) > 1 else "N/A",
                            "State": "N/A",
                            "District": "N/A",
                            "Market": tds[0].text.strip(),
                            "Min Price (Rs/quintal)": min_price,
                            "Max Price (Rs/quintal)": max_price
                        }
                        data.append(row)
                if data:
                    return data

            print(f"⚠️ No valid data found for {product} on this attempt. Retrying...")
            attempt += 1
            time.sleep(random.uniform(5, 10))

        except requests.RequestException as e:
            attempt += 1
            print(f"❌ Attempt {attempt}/{retries} failed for {product}: {e}")
            time.sleep(random.uniform(5, 10))
            if attempt == retries:
                print(f"❌ Max retries reached for {product}. Falling back to dummy data.")
                return generate_dummy_data(product)

    return generate_dummy_data(product)

def save_to_csv(new_data: list):
    """Save scraped data to CSV without duplicates."""
    df_new = pd.DataFrame(new_data)
    initialize_csv()

    try:
        df_existing = pd.read_csv(OUTPUT_FILE)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True).drop_duplicates()
    except pd.errors.EmptyDataError:
        print("⚠️ CSV file was empty. Starting fresh.")
        df_combined = df_new

    df_combined.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Updated: {OUTPUT_FILE} with {len(df_combined)} rows.")

def fetch_all():
    """Fetch prices for all commodities and save to CSV."""
    all_prices = []
    for product, url in COMMODITY_URLS.items():
        print(f"🔍 Scraping {product} prices...")
        prices = scrape_prices(product, url)
        all_prices.extend(prices)
        time.sleep(random.uniform(1, 2))  # polite delay
    save_to_csv(all_prices)

def fetch_and_return_df():
    """Fetch all and return DataFrame."""
    fetch_all()
    return pd.read_csv(OUTPUT_FILE)

if __name__ == "__main__":
    fetch_all()
