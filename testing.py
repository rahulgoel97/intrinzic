import requests

def get_financials(ticker):
    # 1. Setup headers (Required by SEC)
    headers = {'User-Agent': "Rahul Goel rahulgol97@gmail.com"}
    
    # 2. Get CIK mapping
    ticker = ticker.upper()
    mapping_url = "https://www.sec.gov/files/company_tickers.json"
    mapping_res = requests.get(mapping_url, headers=headers).json()
    
    cik = None
    for entry in mapping_res.values():
        if entry['ticker'] == ticker:
            cik = str(entry['cik_str']).zfill(10)
            company_name = entry['title']
            break
            
    if not cik:
        return "Ticker not found."

    # 3. Get Company Facts (The financial data)
    facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    facts_res = requests.get(facts_url, headers=headers).json()
    
    # Path to the data: us-gaap -> Concept -> units -> USD
    # Note: Revenue tags can vary (e.g., 'Revenues' or 'RevenueFromContractWithCustomerExcluding轉CostOfSales')
    # We will try the most common GAAP tags
    data_points = {
        "Revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingVat"],
        "OpIncome": ["OperatingIncomeLoss"]
    }
    
    results = {"Annual": {}, "Quarterly": {}}

    for label, tags in data_points.items():
        for tag in tags:
            if tag in facts_res['facts']['us-gaap']:
                series = facts_res['facts']['us-gaap'][tag]['units']['USD']
                
                # Filter for most recent 10-K (Annual) and 10-Q (Quarterly)
                annuals = [f for f in series if f['form'] == '10-K']
                quarters = [f for f in series if f['form'] == '10-Q']
                
                if annuals:
                    results["Annual"][label] = annuals[-1]['val']
                if quarters:
                    results["Quarterly"][label] = quarters[-1]['val']
                break

    # 4. Final Output Formatting
    output = (
        f"Company Name: {company_name}, Ticker: {ticker}\n"
        f"--- Most Recent Year (Annual) ---\n"
        f"Revenue: ${results['Annual'].get('Revenue', 0):,.0f}\n"
        f"Operating Income: ${results['Annual'].get('OpIncome', 0):,.0f}\n"
        f"--- Most Recent Quarter ---\n"
        f"Revenue: ${results['Quarterly'].get('Revenue', 0):,.0f}\n"
        f"Operating Income: ${results['Quarterly'].get('OpIncome', 0):,.0f}"
    )
    
    return output

import requests
import pandas as pd

def get_financials_by_cik(cik):
    # Ensure CIK is 10 digits with leading zeros
    cik_padded = str(cik).zfill(10)
    
    # SEC requires a descriptive User-Agent
    headers = {
        'User-Agent': "Rahul Goel (rahulgol97@gmail.com)",
        'Accept-Encoding': 'gzip, deflate'
    }

    # API Endpoint for all company facts
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return f"Error fetching data: {e}"

    # Get Company Name from the metadata
    company_name = data.get('entityName', 'Unknown')
    
    # Financial concepts we want (GAAP tags)
    # Note: Revenue tags vary by industry; we check common ones
    concepts = {
        "Revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingVat", "SalesRevenueNet"],
        "OpIncome": ["OperatingIncomeLoss"]
    }

    results = {"Annual": {}, "Quarterly": {}}

    for label, tags in concepts.items():
        found = False
        for tag in tags:
            if tag in data['facts']['us-gaap']:
                series = data['facts']['us-gaap'][tag]['units']['USD']
                
                # Filter for 10-K (Annual) and 10-Q (Quarterly)
                annuals = [f for f in series if f['form'] == '10-K']
                quarters = [f for f in series if f['form'] == '10-Q']
                
                if annuals:
                    results["Annual"][label] = annuals[-1]['val']
                if quarters:
                    results["Quarterly"][label] = quarters[-1]['val']
                
                found = True
                break # Stop searching tags once one is found
        
        if not found:
            results["Annual"][label] = "N/A"
            results["Quarterly"][label] = "N/A"

    return (
        f"Company Name: {company_name}, CIK: {cik_padded}\n"
        f"--- Most Recent Year (10-K) ---\n"
        f"Revenue: {results['Annual'].get('Revenue'):,}\n"
        f"Operating Income: {results['Annual'].get('OpIncome'):,}\n"
        f"--- Most Recent Quarter (10-Q) ---\n"
        f"Revenue: {results['Quarterly'].get('Revenue'):,}\n"
        f"Operating Income: {results['Quarterly'].get('OpIncome'):,}"
    )


def get_cik_for_ticker(ticker):
    ticker = ticker.upper()
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {'User-Agent': "Rahul Goel rahulgol97@gmail.com"}
    response = requests.get(url, headers=headers)
    ticker_data = response.json()
    

    # The JSON is formatted as {"0": {"cik_str": 68505, "ticker": "MSI", "title": "Motorola Solutions, Inc."}, ...}
    for item in ticker_data.values():
        if item['ticker'] == ticker:
            # Crucial: The SEC API requires a 10-digit CIK with leading zeros
            return str(item['cik_str']).zfill(10)
    
    return None


# Test it
ticker_name = input("Please enter a ticker: ")
cik = get_cik_for_ticker(ticker_name)
print("CIK: ", cik)
get_financials_by_cik(cik)
