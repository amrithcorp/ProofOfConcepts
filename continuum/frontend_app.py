from flask import Flask,redirect,url_for,render_template,request,jsonify
from flask_sqlalchemy import SQLAlchemy
import secrets

from sqlalchemy.orm import backref

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
    amount = db.Column(db.Float)
    has_settled = db.Column(db.Boolean)
    command = db.Column(db.Text)
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



@app.route('/')
def index():
    return redirect(url_for('create_account'))

@app.route('/create_account',methods=["GET","POST"])
def create_account():
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        email = request.form["email_f"]
        password = request.form["password_f"]
        new_query = Issuer(
            email = email, 
            password = password,
            api_key = secrets.token_urlsafe(60),
            public_auth = secrets.token_urlsafe(60),
            private_auth = secrets.token_urlsafe(60)
            )
        db.session.add(new_query)
        db.session.commit()
        return "created_account"

@app.route('/login',methods=["GET","POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        email = request.form["email_f"]
        password = request.form["password_f"]
        new_query = Issuer.query.filter_by(email = email, password = password).first()
        # return jsonify(request.form)
        return redirect(url_for('dashboard',apikey=new_query.api_key))

@app.route('/dashboard/continuum:<apikey>')
def dashboard(apikey):
    user = Issuer.query.filter_by(api_key = apikey).first()
    return render_template(
        'dashboard.html',
        apikey = apikey,
        email = user.email,
        public_auth = user.public_auth,
        secret_auth = user.private_auth,
        a = user.owner,
        b = user.made,
    ) 


@app.route('/dashboard/continuum:<apikey>/<asset_secret>')
def asset_t(apikey,asset_secret):
    user = Issuer.query.filter_by(api_key = apikey).first()
    asset = Asset.query.filter_by(owner_id = user.id,secret_code = asset_secret).first()
    return render_template(
        'transaction.html',
        b = asset.transactions,
    )

    
@app.route('/create_asset/continuum:<apikey>',methods=["GET","POST"])
def create_asset(apikey):
    user = Issuer.query.filter_by(api_key = apikey).first()
    if request.method == "GET":
        return render_template('asset_form.html')
    else:
        a = request.form
        new_asset = Asset(
            name = a["name"],
            ticker = a["ticker"],
            supply = a["supply"],
            step = 2,
            owner_id = user.id,
            tier = a["tier"],
            dep_balance = 5000,
            public_code = secrets.token_urlsafe(15),
            secret_code = secrets.token_urlsafe(15)
        )
        db.session.add(new_asset)
        db.session.commit()
        return f"created asset {new_asset.ticker}, with owner: {new_asset.issuer.email}"


@app.route('/create_created_account/continuum:<apikey>',methods=["GET","POST"])
def created_acc(apikey):
    user = Issuer.query.filter_by(api_key = apikey).first()
    if request.method == "GET":
        return render_template('custodial.html')
    else:
        asset = Asset.query.filter_by(secret_code = request.form["asset"]).first()
        new_acc = Created(
            email = request.form["email"],
            asset_balance = request.form["balance"],
            asset_id = asset.id,
            secret = secrets.token_hex(15),
            issued_by_id = user.id,
        )
        db.session.add(new_acc)
        db.session.commit()
        return f"created account {new_acc.secret} with email: {new_acc.email} for asset: {new_acc.asset.ticker}."



@app.route('/get_info/continuum:<apikey>/<secret>')
def get_info(apikey,secret):
    created_account = Created.query.filter_by(secret = secret).first()
    api_client = Issuer.query.filter_by(api_key = apikey).first()
    if api_client.id == created_account.issued_by_id:
        return f"authorized to view {created_account.email}, they have {created_account.asset_balance} {created_account.asset.ticker}"
    else:
        return "not authenticated to view this user."


@app.route('/transact/continuum:<apikey>',methods = ["GET","POST"])
def transact(apikey):
    if request.method == "GET":    
        return render_template('transact.html')
    elif request.method == "POST":
        from_user = Created.query.filter_by(secret = request.form["from"]).first()
        to_user = Created.query.filter_by(secret = request.form["to"]).first()
        asset = Asset.query.filter_by(secret_code = request.form["asset"]).first()
        if (from_user.asset.ticker,to_user.asset.ticker) == (asset.ticker,asset.ticker):
            amount = round(float(request.form["amount"]),asset.step)
            new_transaction = Transaction(
                asset_id = asset.id,
                from_id = from_user.id,
                to_id = to_user.id,
                amount = amount,
                has_settled = True,
                command = None,
                fee_charged = 5,
                memo = request.form["memo"]
            )
            db.session.add(new_transaction)
            db.session.commit()
            return f"sending {amount} {asset.name} from {from_user.email} to {to_user.email}"
        else:
            return "multiple asset secrets do not match"
if __name__ == "__main__":
    app.run(port=5001,debug=True)
