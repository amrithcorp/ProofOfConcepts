'''
Exchequer is a python-flask app designed to allow developers
and businesses to create dynamic, speedy, payment forms for 
accepting blockchain assets on the stellar network.

Exchequer is 100% non-custodial and uses existing stellar SDKs.

'''


'''
Left off:
'''

# Import statements and utilized libraries.

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_qrcode import QRcode
import yfinance
import secrets
from datetime import datetime, timedelta
import json
from helper import validate_tx, get_price
import random
import psycopg2
from flask_cors import cross_origin,CORS
# Getting literal and configurable data

sensitive = json.load(open('sensitive.json'))

# Declaring Flask objects.

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = sensitive["dbURI"]
db = SQLAlchemy(app)
CORS(app)
QRcode(app)


# Database Schematics

accepted_assets = db.Table('accepted_assets',
    db.Column('payment_id', db.Integer, db.ForeignKey('payment.id')),
    db.Column('asset_id', db.Integer, db.ForeignKey('asset.id'))
)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    created_by_id = db.Column(db.Integer,db.ForeignKey("account.id"))
    asset_amount = db.Column(db.Float)
    asset_price = db.Column(db.Float)
    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"))
    usd_amount = db.Column(db.Float)
    memo = db.Column(db.String(30))
    lookup = db.Column(db.String(25))
    has_chosen = db.Column(db.Boolean)
    has_conf = db.Column(db.Boolean)
    charge_list = db.Column(db.Text)
    owner_account = db.relationship("Account",foreign_keys=[created_by_id])
    expires = db.Column(db.DateTime)
    chosen_asset = db.relationship('Asset',foreign_keys=[asset_id])
    accepted = db.relationship('Asset',secondary=accepted_assets,backref=db.backref('all_assets',lazy='dynamic'))

class Asset(db.Model): 
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(5))
    issuer = db.Column(db.String(56))
    included_payments = db.relationship('Payment',backref = 'asset')
    icon = db.Column(db.Text)
    sdex = db.Column(db.Boolean)
    note = db.Column(db.Text)


class Account(db.Model): 
    id = db.Column(db.Integer, primary_key = True)
    address = db.Column(db.String(56))
    created_payments = db.relationship('Payment',backref = 'account')
    username = db.Column(db.String(20))
    api_key = db.Column(db.String(30))


# This endpoint creates new transaction objects.

@app.route('/api:<api_key>/create_payment',methods=["GET","POST"])
@cross_origin()
def create_payment(api_key):
    account = Account.query.filter_by(api_key=api_key).first()
    if account == None:
        return "no such api key."
    else:
        payment_req = request.get_json()
        new_query = Payment(
            expires = datetime.now() + timedelta(minutes=payment_req["minutes_to_exp"]),
            usd_amount=payment_req["usd_amount"],
            created_by_id = account.id,
            has_chosen = False,
            lookup = secrets.token_hex(10),
            charge_list = json.dumps(payment_req["charge_list"])
                        )
        for i in payment_req["accepted_assets"]:
            asset = Asset.query.filter_by(ticker=i).first()
            new_query.accepted.append(asset)

        db.session.add(new_query)
        db.session.commit()
        return {"lookup" : f"payment:{new_query.lookup}"}
# This endpoint updates the developer on new events in the transaction

@app.route('/api:<api_key>/lookup:<lookup>')
@cross_origin()
def tx_status(api_key,lookup):
    account = Account.query.filter_by(api_key=api_key).first()
    payment = Payment.query.filter_by(lookup=lookup).first()
    if account.id == payment.created_by_id:
        if not payment.has_chosen:
            return jsonify({
                    "lookup" : lookup,
                    "has_chosen" : False
                })
        else:
            txStat = validate_tx(
                amount=payment.asset_amount,
                memo=payment.memo,
                account=payment.owner_account.address,
                asset=payment.chosen_asset.ticker,
                issuer=payment.chosen_asset.issuer,
                sdex=payment.chosen_asset.sdex,
            ) 
            return jsonify({
                    "lookup" : lookup,
                    "has_chosen" : True,
                    "chosen_asset" : payment.asset,
                    "asset_amount" : payment.asset_amount,
                    "memo" : payment.memo,
                    "asset_price" : payment.asset_price,
                    "usd_amount" : payment.usd_amount,
                    "has_payed" : txStat
                })

# This endpoint allows clients to interact with a more lightweight reponse for DOM updating
           
@app.route('/client_api/txstat/<lookup>')
@cross_origin()
def client_tx_status(lookup):
    payment = Payment.query.filter_by(lookup=lookup).first()
    txStat = validate_tx(
                amount=payment.asset_amount,
                memo=payment.memo,
                account=payment.owner_account.address,
                asset=payment.chosen_asset.ticker,
                issuer=payment.chosen_asset.issuer
            ) 
    return jsonify({"transactionStatus" : txStat})


# This endpoint creates the actual HTML pages that end-users interact with!

@app.route('/payment:<lookup>',methods=["GET","POST"])
def tx_maker(lookup):
    payment = Payment.query.filter_by(lookup=lookup).first()
    account = payment.owner_account
    if not payment.has_chosen:
        if request.method == "GET":
            print(type(payment.charge_list))
            return render_template(
                'assetSelect.html',
                payment = payment,
                account = account,
                chargelis = json.loads(payment.charge_list),
                )
        elif request.method == "POST":
            ticker = request.form["payment-method"]
            asset = Asset.query.filter_by(ticker=ticker).first()
            price = get_price(ticker,asset.sdex,asset.issuer)

            payment.has_chosen = True
            payment.asset_price = price
            payment.asset_amount = round(payment.usd_amount/price,7)
            payment.memo = str(random.randrange(100,999)) + "-" + str(random.randrange(100,999)) + "-" + str(random.randrange(100,999)) + "-" + str(random.randrange(100,999))
            payment.chosen_asset = asset

            db.session.commit()
            return redirect(url_for('tx_maker',lookup=lookup))
    
    elif payment.has_chosen and not payment.has_conf:
        if request.method == "GET":
            return render_template('payConfirm.html',
                    payment=payment,
                    account=payment.owner_account,
                    price = round(payment.asset_price,4),
                    url = f"payment/conf/{lookup}"
                )
    else:
        if request.method == "GET":
            print("=====================")
            #Jan 28, 2022 15:37:25
            x = (payment.expires.strftime("%b %d, %Y %H:%M:%S"))
            print("=====================")
            return render_template(
                'paymentQr.html',
                payment=payment,
                account=account,
                price = round(payment.asset_price,4),
                asset_amount = round(payment.asset_amount),
                exp = x,
                base_url = sensitive['base_url']
            )
        else:
            return redirect(url_for('tx_maker',lookup=lookup))


@app.route('/payment/conf/<lookup>')
def conf_tx(lookup):
    payment = Payment.query.filter_by(lookup=lookup).first()
    if not payment.has_chosen:
        return "Error"
    else:
        payment.has_conf = True
        db.session.commit()
        return redirect(url_for('tx_maker',lookup=lookup))



if __name__ == "__main__":
    app.run(debug=True)