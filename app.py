from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from werkzeug.security import generate_password_hash, check_password_hash
import re

from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-only-change-me')

# 🗄️ Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/upload'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

from flask_mail import Mail, Message

app.config['MAIL_SERVER'] = 'smtp.gmail.com'       # Replace with your SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

mail = Mail(app)

# 👤 User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)

# 📱 Product Model (Mobile Accessories)
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(300), nullable=True)
    category = db.Column(db.String(100), nullable=False)

# 🛒 Purchase Model
from datetime import datetime, timedelta

class Booking(db.Model):  # keeping name Booking for DB compatibility
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    mobile_number = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(300), nullable=False)
    price = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    payment_details = db.Column(db.String(300), nullable=True)

    # 🆕 New columns
    order_date_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    delivery_date_time = db.Column(
        db.DateTime,
        default=lambda: datetime.utcnow() + timedelta(days=7),
        nullable=False
    )


# 🔨 Initialize Database (Run once)
with app.app_context():
    db.create_all()


# 🏠 Home Page
@app.route('/')
def home_page():
    return render_template('home.html')

# 📝 Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return render_template('signup.html')

        if len(password) < 6:
            flash("Password must be at least 6 characters long!", "error")
            return render_template('signup.html')

        if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
            flash("Username must be 3-20 characters long and contain only letters, numbers, and underscores.", "error")
            return render_template('signup.html')

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Invalid email address!", "error")
            return render_template('signup.html')

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash("Username or email already exists!", "error")
            return render_template('signup.html')

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Signup successful! Please login.", "success")
            return redirect(url_for('login'))
        except Exception:
            db.session.rollback()
            flash("An error occurred while creating your account. Please try again.", "error")

    return render_template('signup.html')

# 🚪 Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        # 🛠 Admin Login
        if username == os.getenv('ADMIN_USERNAME', 'admin') and password == os.getenv('ADMIN_PASSWORD', ''):
            session['username'] = "admin"
            flash("Admin login successful!", "success")
            return redirect(url_for('admin_dashboard'))

        # 🔍 User Login
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash(f"Login successful! Welcome back, {username}!", "success")
            return redirect(url_for('products_page'))

        flash("Incorrect username or password!", "error")
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/my_orders')
def my_orders():
    if 'user_id' not in session:
        flash("Please login to view your orders.", "error")
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Fetch orders for this user only
    orders = db.session.query(
        Booking.id,
        Product.name,
        Booking.price,
        Booking.payment_method,
        Booking.order_date_time,
        Booking.delivery_date_time
    ).join(Product, Booking.product_id == Product.id) \
     .filter(Booking.user_id == user_id) \
     .all()

    return render_template("my_orders.html", orders=orders)

# 📱 Products
@app.route('/products')
def products_page():
    products = Product.query.all()
    return render_template('products.html', products=products)

# 🛒 Purchase Page
from datetime import datetime, timedelta

@app.route('/booking/<int:product_id>', methods=['GET', 'POST'])
def booking_page(product_id):
    if 'user_id' not in session:
        flash("Please login to purchase a product!", "error")
        return redirect(url_for('login'))

    product = Product.query.get_or_404(product_id)
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        booking = Booking(
            product_id=product.id,
            user_id=user.id,
            full_name=request.form['full_name'].strip(),
            mobile_number=request.form['mobile_number'].strip(),
            email=user.email,  # logged-in user's email
            address=request.form['address'].strip(),
            price=float(request.form['price'].strip()),
            payment_method=request.form['payment_method'].strip(),
            payment_details=request.form.get('payment_details', '').strip(),
            order_date_time=datetime.utcnow(),
            delivery_date_time=datetime.utcnow() + timedelta(days=7)
        )
        db.session.add(booking)
        db.session.commit()

        # Send HTML email confirmation
        try:
            msg = Message(
                subject="Booking Confirmation",
                recipients=[user.email]
            )
            
            # HTML email content
            msg.html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2 style="color:#2E86C1;">Booking Confirmation</h2>
                <p>Hello <strong>{booking.full_name}</strong>,</p>
                <p>Your booking for <strong>{product.name}</strong> has been successfully placed!</p>
                
                <h3>Order Details:</h3>
                <table style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px;">Product</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{product.name}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px;">Price</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">${booking.price:.2f}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px;">Payment Method</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{booking.payment_method}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px;">Delivery Date</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{booking.delivery_date_time.strftime('%Y-%m-%d')}</td>
                    </tr>
                </table>

                <p>Shipping Address:</p>
                <p>{booking.address}</p>

                <p>Thank you for shopping with us!</p>
                <p>Best regards,<br>Your Company Name</p>
            </body>
            </html>
            """
            mail.send(msg)
        except Exception as e:
            print("Email sending failed:", e)
            flash("Booking successful, but email could not be sent.", "warning")
        else:
            flash("Booking successful! A confirmation email has been sent.", "success")

        return redirect(url_for('products_page'))

    return render_template('booking.html', product=product, user=user)


# 🚪 Logout
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

# ⚙️ Admin Dashboard
@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'username' not in session or session['username'] != 'admin':
        flash("Unauthorized access! Admins only.", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        product_id = request.form.get('product_id')
        name = request.form.get('name').strip()
        price = request.form.get('price').strip()
        category = request.form.get('category').strip()
        image_file = request.files.get('image')

        if not name or not price or not category:
            flash("All fields are required!", "error")
            return redirect(url_for('admin_dashboard'))

        try:
            price = float(price)
        except ValueError:
            flash("Invalid price format!", "error")
            return redirect(url_for('admin_dashboard'))

        image_filename = None
        if image_file and image_file.filename != '':
            image_filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image_file.save(image_path)

        if product_id:  # Update
            product = Product.query.get(product_id)
            if product:
                product.name = name
                product.price = price
                product.category = category
                if image_filename:
                    product.image = image_filename
                db.session.commit()
                flash("Product updated successfully!", "success")
            else:
                flash("Product not found!", "error")
        else:  # Add New
            new_product = Product(
                name=name,
                price=price,
                category=category,
                image=image_filename if image_file else None
            )
            db.session.add(new_product)
            db.session.commit()
            flash("Product added successfully!", "success")

        return redirect(url_for('admin_dashboard'))

    # ✅ Delete Product
    delete_id = request.args.get('delete_id')
    if delete_id:
        product = Product.query.get(delete_id)
        if product:
            db.session.delete(product)
            db.session.commit()
            flash("Product deleted successfully!", "success")
        else:
            flash("Product not found!", "error")
        return redirect(url_for('admin_dashboard'))

    # ✅ Get Data
    products = Product.query.all()
    users = User.query.all()
    

    bookings = db.session.query(
    Booking.id,
    Booking.full_name,
    User.username,
    Product.name,
    Booking.price,
    Booking.payment_method,
    Booking.order_date_time,
    Booking.delivery_date_time
).join(User, Booking.user_id == User.id) \
 .join(Product, Booking.product_id == Product.id) \
 .all()




    return render_template(
        'admin_dashboard.html',
        products=products,
        users=users,
        bookings=bookings,
        product_count=len(products),
        user_count=len(users),
        booking_count=len(bookings)
    )

# 📄 Info Pages
@app.route('/about')
def about_page():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact_page():
    if request.method == 'POST':
        flash("Thanks for reaching out! We'll get back to you soon.", "success")
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True)
