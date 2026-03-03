import asyncio
import httpx
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
import os

# Import your existing system components
from Services.app.storage import DataStorage, PATHS
from Services.app.supabase_store import SupabaseConfig
from Services.app.domain.models import PriceCache
from Services.app.logger import log_event

# --- CONFIGURATION ---
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
MAX_CONCURRENT_REQUESTS = 10  # Don't hammer the server too hard

async def fetch_symbol_data(client: httpx.AsyncClient, symbol: str) -> Dict:
    """Asynchronously fetches and parses a single symbol from Merolagani."""
    url = f"https://merolagani.com/CompanyDetail.aspx?symbol={symbol}"
    
    # Initialize with default "Safe" values
    result = {
        "Symbol": symbol,
        "LTP": 0.0,
        "Change": 0.0,
        "High52": 0.0,
        "Low52": 0.0,
        "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        response = await client.get(url, timeout=15.0)
        if response.status_code != 200:
            return result

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Parse LTP (Price)
        price_tag = soup.select_one("#ctl00_ContentPlaceHolder1_CompanyDetail1_lblMarketPrice")
        if price_tag:
            result['LTP'] = float(price_tag.text.strip().replace(",", ""))

        # 2. Parse Other Details from the Info Table
        rows = soup.find_all('tr')
        for row in rows:
            text = row.get_text()
            
            # Extract % Change
            if "% Change" in text:
                tds = row.find_all('td')
                if tds:
                    try:
                        # Extract part before '(' e.g. "5.20 (1.2%)" -> "5.20"
                        val = tds[0].text.strip().split('(')[0].replace(",", "")
                        result['Change'] = float(val)
                    except: pass
            
            # Extract 52 Week Range
            if "52 Weeks High - Low" in text:
                tds = row.find_all('td')
                if tds:
                    range_text = tds[-1].text.strip().replace(",", "")
                    if "-" in range_text:
                        parts = range_text.split("-")
                        result['High52'] = float(parts[0].strip())
                        result['Low52'] = float(parts[1].strip())
        
        return result

    except Exception as e:
        print(f"⚠️ Failed to fetch {symbol}: {e}")
        return result


async def _get_market_data_async(symbols: List[str]) -> Dict[str, Dict[str, float]]:
    limits = httpx.Limits(max_connections=MAX_CONCURRENT_REQUESTS)
    async with httpx.AsyncClient(headers={'User-Agent': USER_AGENT}, limits=limits) as client:
        tasks = [fetch_symbol_data(client, s) for s in symbols]
        rows = await asyncio.gather(*tasks)

    out: Dict[str, Dict[str, float]] = {}
    for r in rows:
        sym = str(r.get("Symbol", "")).upper().strip()
        if not sym:
            continue
        out[sym] = {
            "price": float(r.get("LTP", 0.0) or 0.0),
            "change": float(r.get("Change", 0.0) or 0.0),
            "high": float(r.get("High52", 0.0) or 0.0),
            "low": float(r.get("Low52", 0.0) or 0.0),
        }
    return out


def get_market_data(symbols: List[str]) -> Dict[str, Dict[str, float]]:
    """Synchronous wrapper used by Streamlit tabs."""
    clean_symbols = [str(s).upper().strip() for s in symbols if str(s).strip()]
    if not clean_symbols:
        return {}
    try:
        return asyncio.run(_get_market_data_async(clean_symbols))
    except RuntimeError:
        # Safe fallback when an event loop is already running.
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_get_market_data_async(clean_symbols))
        finally:
            loop.close()

async def run_market_update():
    """Main Orchestrator for the Scraper."""
    print(f"🚀 Starting Market Update at {datetime.now()}")
    
    # 1. Setup Storage (Detect if running in GitHub or Local)
    # Using environment variables for GitHub Actions compatibility
    url = os.getenv("SUPABASE_URL") or "YOUR_FALLBACK_URL"
    key = os.getenv("SUPABASE_KEY") or "YOUR_FALLBACK_KEY"
    
    storage = DataStorage(
        supabase_config=SupabaseConfig(url=url, key=key),
        local_root=os.getcwd()
    )

    # 2. Get the list of symbols to track
    # We pull this from your existing holdings so you never have to manually update the list
    holdings = storage.get_holdings()
    symbols_to_track = holdings['Symbol'].unique().tolist()
    
    if not symbols_to_track:
        print("ℹ️ No symbols found in holdings. Scraping default watch list.")
        symbols_to_track = ["NABIL", "UPPER", "HRL", "HDL", "NICA"]

    # 3. Fetch data concurrently
    limits = httpx.Limits(max_connections=MAX_CONCURRENT_REQUESTS)
