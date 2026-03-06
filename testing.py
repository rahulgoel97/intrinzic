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
    cik_padded = str(cik).zfill(10)
    headers = {
        "User-Agent": "Rahul Goel (rahulgol97@gmail.com)",
        "Accept-Encoding": "gzip, deflate"
    }
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return f"Error fetching data: {e}"

    company_name = data.get("entityName", "Unknown")
    facts = data.get("facts", {}).get("us-gaap", {})

    revenue_tags = [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingVat",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet"
    ]
    op_income_tag = "OperatingIncomeLoss"

    results = {
        "Annual": {},
        "Quarterly": {}
    }

    def extract_max_per_period(series, period_type):
        records = {}
        for entry in series:
            if "segment" in entry:
                continue
            val = entry.get("val")
            if val is None or val <= 0:
                continue
            if period_type == "Annual":
                period_key = entry.get("fy")
            else:
                period_key = entry.get("end")
            if period_key not in records or val > records[period_key]["val"]:
                records[period_key] = {
                    "val": val,
                    "form": entry.get("form"),
                    "fy": entry.get("fy"),
                    "fp": entry.get("fp"),
                    "end": entry.get("end"),
                    "tag": entry.get("concept", "")
                }
        sorted_keys = sorted(records.keys())
        return [records[k] for k in sorted_keys]

    # Revenue
    for tag in revenue_tags:
        if tag not in facts:
            continue
        units = facts[tag].get("units", {})
        if "USD" not in units:
            continue
        series = units["USD"]
        ann = extract_max_per_period(series, "Annual")
        qtr = extract_max_per_period(series, "Quarterly")
        for r in ann:
            fy = r["fy"]
            if fy not in results["Annual"] or r["val"] > results["Annual"][fy]["val"]:
                results["Annual"][fy] = r
        for r in qtr:
            end = r["end"]
            if end not in results["Quarterly"] or r["val"] > results["Quarterly"][end]["val"]:
                results["Quarterly"][end] = r

    # Operating Income
    if op_income_tag in facts:
        units = facts[op_income_tag].get("units", {})
        if "USD" in units:
            series = units["USD"]
            ann = extract_max_per_period(series, "Annual")
            qtr = extract_max_per_period(series, "Quarterly")
            for r in ann:
                fy = r["fy"]
                if fy not in results["Annual"] or r["val"] > results["Annual"][fy]["val"]:
                    results["Annual"][fy] = r
            for r in qtr:
                end = r["end"]
                if end not in results["Quarterly"] or r["val"] > results["Quarterly"][end]["val"]:
                    results["Quarterly"][end] = r

    # Convert cumulative quarterly to per-quarter
    quarterly_sorted = sorted(results["Quarterly"].values(), key=lambda x: x["end"])
    per_quarter = []
    prev_val = {}
    for r in quarterly_sorted:
        fy = r["fy"]
        if fy not in prev_val:
            actual = r["val"]
        else:
            actual = r["val"] - prev_val[fy]
        prev_val[fy] = r["val"]
        r_copy = r.copy()
        r_copy["val"] = actual
        per_quarter.append(r_copy)

    annual_list = [results["Annual"][k] for k in sorted(results["Annual"])]
    quarterly_list = per_quarter

    # Print
    print("CIK:", cik_padded)
    print("Company:", company_name)
    print("Annual Revenue & Operating Income (max per fiscal year):")
    for r in annual_list:
        print(r)
    print("\nQuarterly Revenue & Operating Income (per quarter):")
    for r in quarterly_list:
        print(r)

    return {
        "Company": company_name,
        "CIK": cik_padded,
        "Annual": annual_list,
        "Quarterly": quarterly_list
    }




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
ticker_name = input("Please enter a ticker name: ")
cik = get_cik_for_ticker(ticker_name)
print("CIK: ", cik)
get_financials_by_cik(cik)
