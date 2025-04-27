from flask import Flask, render_template, redirect, url_for, request, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

import os


load_dotenv(dotenv_path=".env", override=True)

print("Environment Variables:")
for key, value in os.environ.items():
    if "DATABASE" in key or "SECRET" in key:
        print(f"{key} = {value}")


app = Flask(__name__)

print("DATABASE_URL ->", os.getenv('DATABASE_URL'))

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)
# MODELLER
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    role = db.Column(db.String, default="user")

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    products = db.relationship('Product', backref="category", lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.String, nullable=False)
    price = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image = db.Column(db.String, nullable=True)
    sales = db.Column(db.Integer, nullable=False, default=0)
    total_earnings = db.Column(db.Float, nullable=False, default=0)
    stocks = db.Column(db.Integer, nullable=False, default=10)
    
    comments = db.relationship('Comment', backref="product", cascade="all, delete-orphan", lazy=True)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    
    user = db.relationship("User", backref="cart_products")
    product = db.relationship("Product", backref="cart_items")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    content = db.Column(db.String(300), nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=5)  # Yeni: Puan ekledim
    user = db.relationship("User", backref="comments", lazy=True)

# ROUTE'LER
products = []

products = [p for p in products if p.get('image')]



yorumlar = {
    'dog.jpeg': [],
    'doga.jpeg': [],
    'deniz.jpeg': [],
    'ist.jpg': [],
    'karakalem1.jpg': [],
    'karakalem2.jpeg': [],
    'karakalem.jpg': [],
    'Mount.jpg': []
}


@app.route('/')
def home():
    products = Product.query.order_by(Product.id.desc()).limit(8).all()  
    return render_template('anasayfa.html', products=products)




@app.route('/giris', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username= request.form.get("username")
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash('Başarıyla giriş yapıldı!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Geçersiz kullanıcı adı veya şifre.', 'danger')
    return render_template('login.html')

@app.route('/kayit', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if not username or not password:
            flash("Kullanıcı adı ve şifre boş olamaz!", "danger")
            return redirect(url_for("register"))
        if User.query.filter_by(username=username).first():
            flash("Bu kullanıcı adı zaten alınmış.", "danger")
            return redirect(url_for("register"))
        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Kayıt başarılı, şimdi giriş yapabilirsin!', 'success')
        return redirect(url_for('login')) 
    return render_template('register.html')

@app.route('/cikis')
def logout():
    session.clear()
    flash('Başarıyla çıkış yapıldı.', 'success')
    return redirect(url_for('home'))


@app.route('/urun/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    comments = Comment.query.filter_by(product_id=product.id).all()
    return render_template('product_detail.html', product=product, comments=comments)

@app.route('/sepet')
def cart():
    if 'user_id' not in session:
        flash("Önce giriş yapmalısınız.", "warning")
        return redirect(url_for('login'))
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    return render_template('cart.html', cart_items=cart_items)

@app.route('/sepete_ekle/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash("Önce giriş yapmalısınız.", "warning")
        return redirect(url_for('login'))
    existing_item = Cart.query.filter_by(user_id=session['user_id'], product_id=product_id).first()
    if existing_item:
        existing_item.quantity += 1
    else:
        cart_item = Cart(user_id=session['user_id'], product_id=product_id, quantity=1)
        db.session.add(cart_item)
    db.session.commit()
    flash("Ürün sepete eklendi.", "success")
    return redirect(url_for('cart'))

@app.route('/yorum_yap/<int:product_id>', methods=['POST'])
def add_comment(product_id):
    if 'user_id' not in session:
        flash("Yorum yapabilmek için giriş yapmalısınız.", "warning")
        return redirect(url_for('login'))
    content = request.form['content']
    rating = request.form.get('rating', 5)
    comment = Comment(user_id=session['user_id'], product_id=product_id, content=content, rating=rating)
    db.session.add(comment)
    db.session.commit()
    flash("Yorum yapıldı!", "success")
    return redirect(url_for('product_detail', product_id=product_id))



@app.cli.command('create_db')
def create_db():
    db.create_all()
    print("Veritabanı oluşturuldu.")

@app.route('/foto/<resim_adi>', methods=['GET', 'POST'])
def foto(resim_adi):
    if request.method == 'POST':
        yorum = request.form['yorum']
        if session.get('username') and yorum:
            yorumlar[resim_adi].append((session['username'], yorum))
    return render_template('foto.html', resim_adi=resim_adi, yorumlar=yorumlar[resim_adi])

from werkzeug.utils import secure_filename

@app.route('/profil')
def profile():
    if 'user_id' not in session:
        flash("Önce giriş yapmalısınız.", "warning")
        return redirect(url_for('login'))
    user_products = Product.query.filter_by(seller_id=session['user_id']).all()
    return render_template('profile.html', user_products=user_products)

@app.route('/urun-ekle', methods=['GET', 'POST'])
def urun_ekle():
    if 'user_id' not in session:
        flash("Ürün ekleyebilmek için giriş yapmalısınız.", "warning")
        return redirect(url_for('login'))

    categories = Category.query.all()  # kategorileri çek

    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        price = request.form.get('price', 0)
        stocks = request.form.get('stocks', 10)
        category_id = request.form.get('category_id', 1)

        file = request.files.get('image')
        filename = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

        if name and price:
            new_product = Product(
                name=name,
                description=description,
                price=float(price),
                category_id=int(category_id),
                seller_id=session['user_id'],
                stocks=int(stocks),
                image=f"uploads/{filename}" if filename else None
            )
            db.session.add(new_product)
            db.session.commit()

            flash("Ürün başarıyla eklendi!", "success")
            return redirect(url_for('profile'))
        else:
            flash("Eksik bilgi girdiniz!", "danger")
    return render_template('urun_ekle.html', categories=categories)



def ensure_categories():
    default_categories = ["Doğa", "Karakalem", "Sulu Boya", "Hayvan"]
    for name in default_categories:
        existing_category = Category.query.filter_by(name=name).first()
        if not existing_category:
            new_category = Category(name=name)
            db.session.add(new_category)
    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        ensure_categories()
    app.run(debug=True)


