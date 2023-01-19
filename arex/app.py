import secrets
import psycopg2
from flask import Flask,request,redirect,render_template,url_for
from flask_sqlalchemy import SQLAlchemy
from flask_qrcode import QRcode
import datetime
import yfinance as yf
from crypto import Base_account,Crypto
import qrcode

app = Flask(__name__)

db = SQLAlchemy(app)
QRcode(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "--database_url--"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

class Offer(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    original_crypto = db.Column(db.String(10))
    converted_crypto = db.Column(db.String(10))
    refund_address = db.Column(db.String(256))
    send_to_address = db.Column(db.String(256))
    time = db.Column(db.DateTime,default = datetime.datetime.utcnow())
    lookup = db.Column(db.Text)
    amount_original = db.Column(db.Float)
    amount_converted = db.Column(db.Float)
    system_key = db.Column(db.String(256))
    server_received = db.Column(db.Boolean,default=False)
    server_confirmed = db.Column(db.Boolean,default=False)
    server_sent = db.Column(db.Boolean,default=False)

def get_current_price(symbol):
    ticker = yf.Ticker(symbol)
    todays_data = ticker.history(period='1d')
    return todays_data['Close'][0]
def rate(converted,original):
    con_price = get_current_price(f"{converted}-USD")
    ori_price = get_current_price(f"{original}-USD")
    rate = (ori_price/con_price)
    return rate

@app.route('/',methods=["GET","POST"])
def table():
    return redirect(url_for('index'))

@app.route('/pool',methods=["GET","POST"])
def index():
    if request.method == "GET":
        return render_template(
            'pool.html',
             bch_price = round(get_current_price("BCH-USD"),2),
            xlm_price = round(get_current_price("XLM-USD"),4),
            bch_bal = Base_account("BCH").balance()["confirmed"],
            xlm_bal = (Base_account("XLM").balance()["confirmed"]) - 1.5,
            usdc_bal = Base_account("USDC").balance()["confirmed"],
            bnb_price = round(get_current_price("BNB-USD"),2),
            bnb_bal = float(Base_account("BNB").balance()["confirmed"]),
            bch_address = Base_account("BCH").address,
            bnb_address = Base_account("BNB").address,
            xlm_address = Base_account("XLM").address,
            usdc_address = Base_account("USDC").address,
                )
    elif request.method == "POST":
        converted_crypto = request.form["converted_crypto"]
        original_crypto = request.form["original_crypto"]
        refund_address = request.form["refund_address"]
        send_to_address = request.form["send_to_address"]
        amount = request.form["amount"]
        r = (float(rate(converted_crypto,original_crypto)))
        if Base_account(converted_crypto).balance()["confirmed"] <= r*float(amount):
            return f"Not enough {converted_crypto} in our reserves" 
        if converted_crypto == "" or original_crypto == "" or refund_address == "" or send_to_address == "" or amount == "":
            return "atleast one field was not filled."
        new_query = Offer(
            lookup=secrets.token_hex(20),
            converted_crypto = converted_crypto,
            original_crypto = original_crypto,
            refund_address = refund_address,
            send_to_address = send_to_address,
            amount_original = float(amount),
            amount_converted = float(amount) *r, 
            system_key = Crypto(original_crypto).new().syskey
        )
        db.session.add(new_query)
        db.session.commit()
        return redirect(url_for('transaction',lookup=new_query.lookup))

@app.route('/transaction/<lookup>')
def transaction(lookup):
    a = Offer.query.filter_by(lookup=lookup).first()
    time_now = datetime.datetime.utcnow()
    i = False
    has_memo = False
    memo = None
    if datetime.datetime.utcnow() >= a.time + datetime.timedelta(minutes = 15):
        i = True
    else:
        i = False    
    if a.original_crypto == "XLM" or a.original_crypto == "USDC":
        has_memo = True
        memo = a.system_key
    else:
        has_memo = False
    account = Crypto(a.original_crypto).init(a.system_key)
    bal = account.balance()
    if float(bal["confirmed"]) >= a.amount_original and a.server_received == False:
        a.server_received = True
        db.session.commit() 
    if bal["unconfirmed"] == 0 and a.server_received == True:
        a.server_confirmed = True
        db.session.commit()
    if (a.server_received,a.server_confirmed) == (True,True) and a.server_sent == False:
        Base_account(a.converted_crypto).transact(recepient=a.send_to_address,amount=a.amount_converted)
        a.server_sent = True
        db.session.commit()
    if a.server_sent == True and bal["confirmed"] > 0 and a.original_crypto == "BCH":
        temporary_account = Crypto("BCH").init(a.system_key).sweep("bitcoincash:qz8v7kkv7pa2zqqjn8q82gp6xw3hdk0dtqfdg9vtga")
    if a.server_sent == True and bal["confirmed"] > 0 and a.original_crypto == "BNB":
        temporary_account = Crypto("BNB").init(a.system_key)
        temporary_account.sweep("0xfBe1B4e1b5F63e55029Fa1F74A008A92fF6B7299")
    url1 = f"img/{a.original_crypto}.png"
    url2 = f"img/{a.converted_crypto}.png"
    return render_template(
        'transaction.html',
        id = lookup,
        original_crypto = a.original_crypto,
        converted_crypto = a.converted_crypto,
        rate = a.amount_original/a.amount_converted,
        amount_converted = a.amount_converted,
        time_now = time_now,
        time = a.time,
        expiry = a.time + datetime.timedelta(minutes = 15),
        is_expired = i,
        refund_address = a.refund_address,
        send_to = a.send_to_address,
        amount_original = a.amount_original,
        original_account_address = account.address,
        original_account_balance = bal["confirmed"],
        has_memo = has_memo,
        memo = memo,
        confirmed_bal = bal["confirmed"]-bal["unconfirmed"],
        unconfirmed_bal = bal["unconfirmed"],
        is_recv = a.server_received,
        is_conf = a.server_confirmed,
        is_sent = a.server_sent,
        url1=url1,
        url2=url2
        
    )

if __name__ == "__main__":
    app.run(debug=True)
