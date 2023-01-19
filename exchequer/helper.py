import yfinance
import requests
import json

def get_price(ticker,sdex,issuer):
    if not sdex:
        if ticker == "USDC":
            return 1.00
        else:
            dat = yfinance.Ticker(f"{ticker}-USD").history(period="1d")["Close"][0]
            return dat
    else:
        url = f"https://api.stellar.expert/explorer/public/asset/{ticker}-{issuer}"
        req = requests.get(url).json()
        price_xlm = req["price"]
        return price_xlm*get_price("XLM",False,None)
        

def validate_tx(amount,asset,account,memo,issuer):
    asset_id = ""
    if asset == "XLM":
        asset_id = "XLM"
    else:
        asset_id = asset+"-"+issuer+"-" + "1"
    url = f"https://api.stellar.expert/explorer/public/payments?asset={asset_id}&memo={memo}&account={account}"
    resp = requests.get(url).json()
    transaction_status = False
    if len(resp["_embedded"]["records"]) == 1 and float(resp["_embedded"]["records"][0]["amount"]) == amount:
        transaction_status = True
    return transaction_status
