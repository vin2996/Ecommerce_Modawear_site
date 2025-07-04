from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

PRODUCT_FILE = os.path.join('data', 'products.json')
CATEGORY_FILE = os.path.join('data', 'categories.json')
PURCHASES_FILE = os.path.join('data', 'purchases.json')
USERS_FILE = os.path.join('data', 'users.json')  # NEW: Users file path

def load_products():
    if not os.path.exists(PRODUCT_FILE):
        return []
    with open(PRODUCT_FILE, 'r') as f:
        return json.load(f)

def save_products(products):
    with open(PRODUCT_FILE, 'w') as f:
        json.dump(products, f, indent=4)

def load_categories():
    if not os.path.exists(CATEGORY_FILE):
        return []
    try:
        with open(CATEGORY_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def load_purchases():
    if not os.path.exists(PURCHASES_FILE):
        return []
    try:
        with open(PURCHASES_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_purchases(purchases):
    with open(PURCHASES_FILE, 'w') as f:
        json.dump(purchases, f, indent=4)

# NEW: Load users from file
def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

# NEW: Save users to file
def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

@app.route('/')
def index():
    search_query = request.args.get('q', '').strip().lower()  # ✅ FIXED KEY: should be 'q'
    products = load_products()
    categories = load_categories()

    if search_query:
        filtered_products = [p for p in products if search_query in p['name'].lower()]
    else:
        filtered_products = products

    return render_template('index.html', products=filtered_products, categories=categories, search_query=search_query)

@app.route('/products')
def product_list():
    products = load_products()
    return render_template('products.html', products=products)

@app.route('/product/<int:product_id>', methods=['GET'])
def view_product(product_id):
    products = load_products()
    product = next((p for p in products if p['id'] == product_id), None)
    if product:
        return render_template('view_product.html', product=product)
    return "Product not found", 404

@app.route('/cart')
def cart():
    if 'cart' not in session:
        session['cart'] = []
    cart_ids = session['cart']
    products = load_products()
    cart_products = [p for p in products if p['id'] in cart_ids]
    return render_template('cart.html', cart=cart_products)

@app.route('/add_to_cart/<int:product_id>', methods=['GET'])
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = []
    if product_id not in session['cart']:
        session['cart'].append(product_id)
        session.modified = True
    return redirect(url_for('cart'))

@app.route('/buy_now/<int:product_id>', methods=['GET', 'POST'])
def buy_now(product_id):
    products = load_products()
    product = next((p for p in products if p['id'] == product_id), None)
    if not product:
        return "Product not found", 404

    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        contact = request.form.get('contact')
        total = int(product['price']) + 50

        purchases = load_purchases()
        purchases.append({
            'items': [product],
            'name': name,
            'address': address,
            'contact': contact,
            'total': total
        })
        save_purchases(purchases)

        return render_template('order_confirmation.html', cart=[product], name=name, address=address, contact=contact, total=total)

    return render_template('checkout.html', cart=[product])

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        image = request.files.get('image')

        if not name or not price or not image:
            return "Missing fields", 400

        filename = secure_filename(image.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(image_path)

        products = load_products()
        new_product = {
            'id': len(products) + 1,
            'name': name,
            'price': int(price),
            'image': f'uploads/{filename}'
        }
        products.append(new_product)
        save_products(products)

        return redirect(url_for('index'))

    return render_template('add_product.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Check admin hardcoded login
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            session['username'] = 'admin'
            return redirect(url_for('index'))
        else:
            # Check users file for registered users
            users = load_users()
            user = next((u for u in users if u['username'] == username and u['password'] == password), None)
            if user:
                session['logged_in'] = True
                session['username'] = username
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'cart' not in session or not session['cart']:
        return redirect(url_for('cart'))

    name = request.form.get('name')
    address = request.form.get('address')
    contact = request.form.get('contact')

    products = load_products()
    cart_ids = session['cart']
    cart_products = [p for p in products if p['id'] in cart_ids]
    total = sum(int(p['price']) for p in cart_products) + 50

    session['cart'] = []
    session.modified = True

    purchases = load_purchases()
    purchases.append({
        'items': cart_products,
        'name': name,
        'address': address,
        'contact': contact,
        'total': total
    })
    save_purchases(purchases)

    return render_template('order_confirmation.html', cart=cart_products, name=name, address=address, contact=contact, total=total)

@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

@app.route('/add_category', methods=['GET', 'POST'])
def add_category():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if not os.path.exists(CATEGORY_FILE):
        with open(CATEGORY_FILE, 'w') as f:
            json.dump([], f)

    if request.method == 'POST':
        name = request.form.get('name')
        image = request.files.get('image')

        if not name or not image:
            return "Missing name or image", 400

        filename = secure_filename(image.filename)
        image_path = os.path.join('static', 'categories', filename)
        image.save(image_path)

        with open(CATEGORY_FILE, 'r') as f:
            try:
                categories = json.load(f)
            except json.JSONDecodeError:
                categories = []

        new_category = {
            'name': name,
            'image': f'categories/{filename}'
        }
        categories.append(new_category)

        with open(CATEGORY_FILE, 'w') as f:
            json.dump(categories, f, indent=4)

        return redirect(url_for('index'))

    return render_template('add_category.html')

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if 'cart' not in session or not session['cart']:
        return redirect(url_for('cart'))

    products = load_products()
    cart_ids = session['cart']
    cart_products = [p for p in products if p['id'] in cart_ids]

    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        contact = request.form.get('contact')
        total = sum(int(p['price']) for p in cart_products) + 50

        session['cart'] = []
        session.modified = True

        purchases = load_purchases()
        purchases.append({
            'items': cart_products,
            'name': name,
            'address': address,
            'contact': contact,
            'total': total
        })
        save_purchases(purchases)

        return render_template('order_confirmation.html', cart=cart_products, name=name, address=address, contact=contact, total=total)

    return render_template('checkout.html', cart=cart_products)

@app.route('/checkout_single/<int:product_id>', methods=['GET', 'POST'])
def checkout_single(product_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    products = load_products()
    product = next((p for p in products if p['id'] == product_id), None)
    if not product:
        return "Product not found", 404

    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        contact = request.form.get('contact')
        total = int(product['price']) + 50

        purchases = load_purchases()
        purchases.append({
            'items': [product],
            'name': name,
            'address': address,
            'contact': contact,
            'total': total
        })
        save_purchases(purchases)

        return render_template('order_confirmation.html', cart=[product], name=name, address=address, contact=contact, total=total)

    return render_template('checkout.html', cart=[product])

@app.route('/my_purchases')
def my_purchases():
    purchases = load_purchases()
    return render_template('my_purchases.html', purchases=purchases)

# ✅ NEW ROUTE (Added for Cancel Button)
@app.route('/cancel_purchase/<int:purchase_index>', methods=['POST'])
def cancel_purchase(purchase_index):
    purchases = load_purchases()
    if 0 <= purchase_index < len(purchases):
        purchases.pop(purchase_index)
        save_purchases(purchases)
    return redirect(url_for('my_purchases'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        confirm_password = request.form.get('confirm_password').strip()

        if not username or not password or not confirm_password:
            return render_template('register.html', error='Please fill in all fields.')

        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match.')

        users = load_users()
        # Check if username exists
        if any(user['username'] == username for user in users):
            return render_template('register.html', error='Username already taken.')

        # Add new user
        users.append({
            'username': username,
            'password': password  # For production, hash this!
        })
        save_users(users)

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(debug=True)
