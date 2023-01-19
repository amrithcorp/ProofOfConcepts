from flask import Flask, json,redirect,url_for,render_template,request,jsonify
from flask_sqlalchemy import SQLAlchemy
import secrets
import datetime

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///db.db'

db = SQLAlchemy(app)

class Issuer(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.Text)
    password = db.Column(db.String(45))
    api_key = db.Column(db.String(64))
    public_auth = db.Column(db.String(64))
    private_auth =  db.Column(db.String(64))
    owner = db.relationship('Asset',backref ='issuer')
    made = db.relationship('Created',backref ='issuer')

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(30))
    ticker = db.Column(db.String(5))
    created_when = db.Column(db.DateTime,default = datetime.datetime.utcnow())
    supply = db.Column(db.Float)
    step = db.Column(db.Integer)
    public_code = db.Column(db.String(15))
    secret_code = db.Column(db.String(15))
    owner_id = db.Column(db.Integer, db.ForeignKey("issuer.id"))
    tier = db.Column(db.Integer)
    dep_balance = db.Column(db.Float,default=100.00)
    transactions = db.relationship('Transaction',backref="Asset")

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key = True)    
    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"))
    from_id= db.Column(db.Integer, db.ForeignKey("created.id"))
    to_id= db.Column(db.Integer, db.ForeignKey("created.id"))
    time = db.Column(db.DateTime,default = datetime.datetime.utcnow())
    lookup = db.Column(db.String(32))
    amount = db.Column(db.Float)
    has_settled = db.Column(db.Boolean)
    fee_charged = db.Column(db.Float)
    memo = db.Column(db.String(20))
    asset = db.relationship("Asset",foreign_keys=[asset_id])
    from_acc = db.relationship("Created",foreign_keys=[from_id])
    to_acc = db.relationship("Created",foreign_keys=[to_id])

class Created(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    issued_by_id = db.Column(db.Integer, db.ForeignKey("issuer.id"))
    email = db.Column(db.Text)
    asset_balance = db.Column(db.Float)
    secret = db.Column(db.String(15))
    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"))
    asset = db.relationship('Asset',backref="created")
    created_when = db.Column(db.DateTime,default = datetime.datetime.utcnow())


@app.route('/')
def index():
    return redirect(url_for('dashboard',api_key = "amriths_api_key"))


@app.route('/api/v1/continuum:<api_key>/dashboard')
def dashboard(api_key):
    query = Issuer.query.filter_by(api_key=api_key).first()        
    resp = {
        "email" : query.email,
        "api_key" : f"continuum:{query.api_key}",
        "public_auth" : query.public_auth,
        "private_auth" : query.private_auth,
        "assets" : [],
        "created_accounts" : [],
    }
    for i in query.made:
        user_info = {
            "email" : i.email,
            "balance" : i.asset_balance,
            "secret" : i.secret,
            "asset" : i.asset.ticker
        }
        resp["created_accounts"].append(user_info)
    for i in query.owner:
        asset_info = {
            "asset_secret" : i.secret_code,
            "supply" : round(float(i.supply),i.step),
            "name" : i.name,
            "step" : i.step,
            "public_code" : i.public_code,
            "tier" : i.tier,
            "ticker" : i.ticker,
            "secret" : i.secret_code
        }
        resp["assets"].append(asset_info)
    return jsonify(resp)


@app.route('/api/v1/continuum:<api_key>/create_asset',methods=["POST"])
def create_asset(api_key):
    user = Issuer.query.filter_by(api_key=api_key).first()
    a = request.get_json()
    check_name = Asset.query.filter_by(owner_id = user.id, name = a["name"]).first()
    check_ticker = Asset.query.filter_by(owner_id = user.id, ticker = a["ticker"]).first()
    if check_ticker == None and check_name == None:
        new_asset = Asset(
            name = a["name"],
            ticker = a["ticker"],
            supply = a["supply"],
            step = a["step"],
            owner_id = user.id,
            tier = a["tier"],
            dep_balance = 5000,
            public_code = secrets.token_urlsafe(15),
            secret_code = secrets.token_urlsafe(15)
            )    
        db.session.add(new_asset)
        db.session.commit()
        return jsonify({
            "error":False,
            "asset_secret":new_asset.secret_code,
            "public_code":new_asset.public_code,
            "asset_name":new_asset.name,
            "created_utc":new_asset.created_when
        })
    else:
        return jsonify({
            "error":True,
            "error_msg":"one or more of your assets has this name or ticker"
        })

@app.route('/api/v1/continuum:<api_key>/asset_info/<asset_secret>',methods=["GET"])
def asset_info(api_key,asset_secret):
    user = Issuer.query.filter_by(api_key=api_key).first()
    asset = Asset.query.filter_by(secret_code=asset_secret,owner_id=user.id).first()
    return jsonify({
        "secret":asset.secret_code,
        "name":asset.name,
        "ticker":asset.ticker,
        "supply":asset.supply,
        "step":asset.step,
        "tier":asset.tier
    })


@app.route('/api/v1/continuum:<api_key>/create_account',methods=["POST","GET"])
def create_account(api_key):
    a = request.get_json()
    user = Issuer.query.filter_by(api_key=api_key).first()
    asset = Asset.query.filter_by(secret_code = a["asset_secret"]).first()
    check = Created.query.filter_by(email=a["email"],asset_id=asset.id).first()
    if check == None:
        balance = a["balance"]
        email = a["email"]
        new_account = Created(
            email = email,
            asset_balance = balance,
            asset_id = asset.id,
            secret = secrets.token_hex(15),
            issued_by_id = user.id,
        )
        db.session.add(new_account)
        db.session.commit()
        return jsonify({
            "error":False,
            "account_secret":new_account.secret,
            "asset":new_account.asset.ticker,
            "email":new_account.email,
            "created_utc":new_account.created_when
        })
    else:
        return jsonify({
             "error":True,
            "error_msg":"there is already an account in this asset with this email!"
       })

@app.route('/api/v1/continuum:<api_key>/transaction',methods=["POST","GET"])
def transact(api_key):
    custodian = Issuer.query.filter_by(api_key=api_key).first()
    a = request.get_json()
    asset = Asset.query.filter_by(secret_code=a["asset_secret"]).first()
    from_account = Created.query.filter_by(secret=a["from_secret"],asset_id=asset.id).first()
    to_account = Created.query.filter_by(secret=a["to_secret"],asset_id=asset.id).first()
    amount=round(a["amount"],asset.step)
    if amount > from_account.asset_balance:
        return jsonify({
            "error":True,
            "error_msg":"not enough funds in original account."
        })
    has_settled=False
    if asset.tier == 1 or asset.tier == 2:
        has_settled = True
    from_account.asset_balance = from_account.asset_balance - amount
    to_account.asset_balance = to_account.asset_balance + amount
    transaction = Transaction(
        asset_id=asset.id,
        from_id=from_account.id,
        to_id=to_account.id,
        amount=amount,
        memo = a["memo"],
        lookup = secrets.token_urlsafe(30),
        has_settled=has_settled,
        fee_charged = 5
    )
    db.session.add(transaction)
    db.session.commit()
    return jsonify({
        "error":False,
        "transaction":transaction.lookup,
        "time":transaction.time      
    })

@app.route('/api/v1/continuum:<api_key>/get_user_by_email/asset:<asset_secret>/email:<email>',methods=["GET"])
def get_account_by_email(api_key,asset_secret,email):
    user = Issuer.query.filter_by(api_key=api_key).first()
    asset = Asset.query.filter_by(secret_code = asset_secret).first()
    account = Created.query.filter_by(email = email, asset_id = asset.id, issued_by_id = user.id).first()
    if account == None:
        return jsonify({"exists":False})
    else:
        return jsonify({
            "exists": True,
            "asset":account.asset.secret_code,
            "email":email,
            "balance":account.asset_balance,
        })

@app.route('/api/v1/continuum:<api_key>/get_transaction_by_lookup/<transaction_id>')
def get_transaction_by_lookup(api_key,transaction_id):
    user = Issuer.query.filter_by(api_key=api_key).first()
    transaction = Transaction.query.filter_by(lookup=transaction_id).first()
    if transaction.asset.owner_id == user.id:
        from_secret = transaction.from_acc.secret
        to_secret = transaction.to_acc.secret
        return jsonify({
            "asset_secret":transaction.asset.secret_code,
            "amount": transaction.amount,
            "lookup":transaction_id,
            "from_secret":from_secret,
            "to_secret":to_secret,
            "fee":transaction.fee_charged,
            "memo":transaction.memo
        })

        
if __name__ == "__main__":
    app.run(debug=True)
