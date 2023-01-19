#This is a high-level wrapper, allowing for dynamic interactions with blockchains regardless of token.
from stellar_sdk import Keypair,Server,TransactionBuilder,Network,Account,server,exceptions
from bitcash import Key
import requests
import secrets
from web3 import Web3
from secrets import token_bytes
from coincurve import PublicKey
from sha3 import keccak_256
import json
#ended at Crypto.new() with bnb addition.
import web3
js = (open("keys.txt","r").readlines())
js = json.loads((open("keys.txt","r").readlines())[0])
class Base_account:
    def __init__(self,ticker):
        self.ticker = ticker
        if self.ticker == "XLM":
            self.key = js["stellar_lumen_key"]
            self.address = js["stellar_lumen_addr"]
            self.fee = 0.000001
        elif self.ticker == "BCH":
            self.key = js["bitcoincash_key"]
            self.address = js["bitcoincash_addr"]
            self.fee = 0.000000021 * 300
        elif self.ticker == "USDC":
            self.key = js["usdc_key"]
            self.address = js["usdc_addr"]
            self.fee = 0
        elif self.ticker == "BNB":
            self.key = js["bnb_key"]
            self.address = js["bnb_addr"]
            self.w3 = Web3(Web3.HTTPProvider("https://bsc-dataseed1.binance.org:443"))
            self.bscankey = js["bscan_key"]
        else:
            self.key = None
    def balance(self):
        if self.ticker == "XLM":
            url = "https://horizon.stellar.org/accounts/GBMXIVJN7LAS27U3QW5NFCCDRDLQGJKLJZSU77IP6LJ5ARFRPEYUNW7B"
            a = float(requests.get(url).json()["balances"][1]["balance"])
            return {
                "confirmed" : a-1.5,
                "unconfirmed" : 0
            }
        elif self.ticker == "BCH":
            url = f"https://rest.bch.actorforth.org/v2/address/details/{self.address}"
            req = requests.get(url).json()
            confbal = req["balance"]
            unconfbal = req["unconfirmedBalance"]
            return {
                "confirmed" : confbal,
                "unconfirmed" : unconfbal
            }
        elif self.ticker == "USDC":
            url = "https://horizon.stellar.org/accounts/GBMXIVJN7LAS27U3QW5NFCCDRDLQGJKLJZSU77IP6LJ5ARFRPEYUNW7B"
            a = float(requests.get(url).json()["balances"][0]["balance"])
            return {
                "confirmed" : a,
                "unconfirmed" : 0
            }
        elif self.ticker == "BNB":
            url = f"https://api.bscscan.com/api?module=account&action=balance&address={self.address}&apikey={self.bscankey}"
            bal = int(requests.get(url).json()["result"])
            return {"confirmed" : self.w3.fromWei(bal,'ether'), "unconfirmed" : 0}
    def transact(self,recepient,amount):
        if self.ticker == "XLM":
            keypair = Keypair.from_secret(self.key)  
            server = Server(horizon_url="https://horizon.stellar.org")
            source_account = server.load_account(keypair.public_key)
            base_fee=server.fetch_base_fee()
            transaction = (
                TransactionBuilder(
                    source_account = source_account,
                    network_passphrase = Network.PUBLIC_NETWORK_PASSPHRASE,
                    base_fee=base_fee

                )
                .append_payment_op(
                    destination = recepient,
                    asset_code = "XLM",
                    amount = f"{round(amount, 7)}"
                )
                .build()
            )
            transaction.sign(keypair)
            response = server.submit_transaction(transaction)
            return response

        elif self.ticker == "USDC":
            keypair = Keypair.from_secret(self.key)  
            server = Server(horizon_url="https://horizon.stellar.org")
            source_account = server.load_account(keypair.public_key)
            base_fee=server.fetch_base_fee()
            transaction = (
                TransactionBuilder(
                    source_account = source_account,
                    network_passphrase = Network.PUBLIC_NETWORK_PASSPHRASE,
                    base_fee=base_fee

                )
                .append_payment_op(
                    destination = recepient,
                    asset_code = "USDC",
                    amount = f"{round(amount, 7)}",
                    asset_issuer="GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN"
                )
                .build()
            )
            transaction.sign(keypair)
            response = server.submit_transaction(transaction)
            return response
        if self.ticker == "BCH":
            if recepient.startswith("bitcoincash:") == False:
                recepient = f"bitcoincash:{recepient}"
            else:
                recepient = recepient
            ac = Key(self.key)
            output = [(recepient,amount,'bch')]
            tx = ac.send(output,unspents=ac.get_unspents())
            return tx
        elif self.ticker == "BNB":
            nonce = self.w3.eth.getTransactionCount(self.address)
            tx = {
                "nonce" : nonce,
                "to" : recepient,
                "value" : self.w3.toWei(amount,'ether'),
                "gas" : 21000,
                "gasPrice": self.w3.toWei('5','gwei')
            }
            signed_tx = self.w3.eth.account.sign_transaction(tx,self.key)
            sent_tx = self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
            return self.w3.toHex(sent_tx)


class Crypto:
    def __init__(self,ticker):
        self.ticker = ticker
        self.init.ticker = self.ticker
        self.new.ticker = self.ticker
    class init:
        def __init__(self,syskey):
            if self.ticker == "XLM":
                self.memo = syskey
                self.address = Base_account("XLM").address
            elif self.ticker == "BCH":
                self.syskey = syskey
                self.address = Key(syskey).address
            if self.ticker == "USDC":
                self.memo = syskey
                self.address = Base_account("USDC").address
            if self.ticker == "BNB":
                self.w3 = Web3(Web3.HTTPProvider("https://bsc-dataseed1.binance.org:443"))
                pk_bytes = bytes.fromhex(syskey)
                public_key = PublicKey.from_valid_secret(pk_bytes).format(compressed=False)[1:]
                addr = keccak_256(public_key).digest()[-20:]
                self.syskey = syskey
                self.address = self.w3.toChecksumAddress((f"0x{addr.hex()}"))
                self.bscankey = "5JSJ8ITBTJBT7QT8AYUF5P5F7C8I9C6G3B"
        def balance(self):
            if self.ticker == "XLM":
                account_address = "GBMXIVJN7LAS27U3QW5NFCCDRDLQGJKLJZSU77IP6LJ5ARFRPEYUNW7B"
                url = f"https://api.stellar.expert/explorer/public/payments?asset=XLM&memo={self.memo}&account={account_address}"
                req = requests.get(url).json()["_embedded"]["records"]
                if req == []:
                    return {"confirmed" : 0, "unconfirmed" : 0}
                else:
                    bal = req[0]["amount"]
                print(bal)
                return {"confirmed" : float(bal), "unconfirmed" : 0}
            elif self.ticker == "BCH":
                k = Key(self.syskey)
                url = f"https://rest.bch.actorforth.org/v2/address/details/{k.address}"
                req = requests.get(url).json()
                confbal = req["balance"]
                unconfbal = req["unconfirmedBalance"]

                return {
                "confirmed" : confbal,
                "unconfirmed" : unconfbal
            }
            elif self.ticker == "USDC":
                url = f"https://api.stellar.expert/explorer/public/payments?asset=USDC-GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN-1&memo={self.memo}&account={self.address}"
                req = requests.get(url).json()["_embedded"]["records"]
                if req == []:
                    return {"confirmed" : 0, "unconfirmed" : 0}
                else:
                    bal = req[0]["amount"]  
                    return {"confirmed" : float(bal), "unconfirmed" : 0}
            elif self.ticker == "BNB":
                url = f"https://api.bscscan.com/api?module=account&action=balance&address={self.address}&apikey={self.bscankey}"
                bal = int(requests.get(url).json()["result"])
                return {"confirmed" : self.w3.fromWei(bal,'ether'), "unconfirmed" : 0}
        def sweep(self,recipient):
            if self.ticker == "BCH":
                a = Key(self.syskey)
                tx = a.send([],fee=1,unspents=a.get_unspents(),leftover=recipient)
                return tx
            if self.ticker == "BNB":
                    pk = self.syskey
                    nonce = self.w3.eth.getTransactionCount(self.address)
                    fee = self.w3.toWei('5','gwei') * 21000
                    bal = (self.w3.eth.get_balance(self.address))
                    final_amount = bal-fee
                    tx = {
                        "nonce" : nonce,
                        "to" : recipient,
                        "value" : final_amount,
                        "gas" : 21000,
                        "gasPrice": self.w3.toWei('5','gwei')
                    }
                    print("====================")
                    print(pk)
                    print("====================")

                    signed_tx = self.w3.eth.account.sign_transaction(tx,pk)
                    sent_tx = self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
                    return self.w3.toHex(sent_tx)
              
        
    class new:
        def __init__(self):
            if self.ticker == "XLM":
                memo = secrets.token_hex(12)
                self.syskey = memo
                self.memo = memo
                self.address = Base_account("XLM").address
            elif self.ticker == "USDC":
                memo = secrets.token_hex(12)
                self.syskey = memo
                self.memo = memo
                self.address = Base_account("USDC").address
            elif self.ticker == "BCH":
                ac = Key()
                self.syskey = ac.to_wif()
                self.address = ac.address
            elif self.ticker == "BNB":
                self.w3 = Web3(Web3.HTTPProvider("https://bsc-dataseed1.binance.org:443"))
                private_key = keccak_256(token_bytes(32)).digest()
                public_key = PublicKey.from_valid_secret(private_key).format(compressed=False)[1:]
                addr = keccak_256(public_key).digest()[-20:]
                self.syskey = private_key.hex()
                self.address = f"0x{addr.hex()}"
                self.bscankey = "5JSJ8ITBTJBT7QT8AYUF5P5F7C8I9C6G3B"

        def balance(self):
            if self.ticker == "XLM":
                account_address = "GBMXIVJN7LAS27U3QW5NFCCDRDLQGJKLJZSU77IP6LJ5ARFRPEYUNW7B"
                url = f"https://api.stellar.expert/explorer/public/payments?asset=XLM&memo={self.memo}&account={account_address}"
                req = requests.get(url).json()["_embedded"]["records"]
                if req == []:
                    return {"confirmed" : 0, "unconfirmed" : 0}
                else:
                    bal = req[0]["amount"]
                print(bal)
                return {"confirmed" : float(bal), "unconfirmed" : 0}
            elif self.ticker == "BCH":
                k = Key(self.syskey)
                url = f"https://rest.bch.actorforth.org/v2/address/details/{k.address}"
                req = requests.get(url).json()
                confbal = req["balance"]
                unconfbal = req["unconfirmedBalance"]

                return {
                "confirmed" : confbal,
                "unconfirmed" : unconfbal
            }
            elif self.ticker == "USDC":
                url = f"https://api.stellar.expert/explorer/public/payments?asset=USDC-GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN-1&memo={self.memo}&account={self.address}"
                req = requests.get(url).json()["_embedded"]["records"]
                if req == []:
                    return {"confirmed" : 0, "unconfirmed" : 0}
                else:
                    bal = req[0]["amount"]  
                    return {"confirmed" : float(bal), "unconfirmed" : 0}
            elif self.ticker == "BNB":
                url = f"https://api.bscscan.com/api?module=account&action=balance&address={self.address}&apikey={self.bscankey}"
                bal = requests.get(url).json()["result"]
                print("==============================")
                print(bal)
                print("==============================")
                return {"confirmed" : bal, "unconfirmed" : 0}

print(Base_account("BNB").balance())