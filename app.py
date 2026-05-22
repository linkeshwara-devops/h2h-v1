# app.py - Complete Harvest2Hotel Backend
import os
import uuid
import json
import decimal
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'harvest2hotel-secret-key-2024'
CORS(app, supports_credentials=True)

# Database configuration - SQLite for development
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///harvest2hotel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==================== MODELS ====================

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    business_name = db.Column(db.String(100))
    city = db.Column(db.String(50))
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'phone': self.phone,
            'user_type': self.user_type,
            'full_name': self.full_name,
            'business_name': self.business_name,
            'city': self.city,
            'is_verified': self.is_verified
        }

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    quantity_available = db.Column(db.Numeric(10, 2), nullable=False)
    unit = db.Column(db.String(20), default='kg')
    price_per_unit = db.Column(db.Numeric(10, 2), nullable=False)
    organic_certified = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    farmer = db.relationship('User', backref='products')
    
    def to_dict(self):
        return {
            'id': self.id,
            'farmer_id': self.farmer_id,
            'farmer_name': self.farmer.business_name or self.farmer.full_name if self.farmer else None,
            'name': self.name,
            'category': self.category,
            'quantity_available': float(self.quantity_available),
            'unit': self.unit,
            'price_per_unit': float(self.price_per_unit),
            'organic_certified': self.organic_certified,
            'description': self.description,
            'is_active': self.is_active
        }

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    hotel_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(30), default='pending')
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    delivery_address = db.Column(db.Text, nullable=False)
    delivery_date = db.Column(db.String(50))
    payment_status = db.Column(db.String(30), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    farmer = db.relationship('User', foreign_keys=[farmer_id], backref='farmer_orders')
    hotel = db.relationship('User', foreign_keys=[hotel_id], backref='hotel_orders')
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def generate_order_number(self):
        return f"H2H{datetime.utcnow().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'farmer_name': self.farmer.business_name or self.farmer.full_name if self.farmer else None,
            'hotel_name': self.hotel.business_name or self.hotel.full_name if self.hotel else None,
            'status': self.status,
            'total_amount': float(self.total_amount),
            'delivery_address': self.delivery_address,
            'delivery_date': self.delivery_date,
            'payment_status': self.payment_status,
            'items': [item.to_dict() for item in self.items],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    price_per_unit = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    
    product = db.relationship('Product')
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product.name if self.product else None,
            'quantity': float(self.quantity),
            'price_per_unit': float(self.price_per_unit),
            'subtotal': float(self.subtotal)
        }

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    frequency = db.Column(db.String(30), nullable=False)
    next_delivery = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    
    user = db.relationship('User', backref='subscriptions')
    product = db.relationship('Product')
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product.name if self.product else None,
            'farmer_name': self.product.farmer.business_name if self.product and self.product.farmer else None,
            'quantity': float(self.quantity),
            'frequency': self.frequency,
            'next_delivery': self.next_delivery,
            'is_active': self.is_active
        }

# ==================== AUTHENTICATION ====================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        user = User.query.get(session['user_id'])
        if not user:
            session.clear()
            return jsonify({'error': 'User not found'}), 401
        return f(user=user, *args, **kwargs)
    return decorated_function

# ==================== ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard.html')
def dashboard():
    if 'user_id' not in session:
        return render_template('index.html')
    return render_template('dashboard.html')

# Auth Routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    if User.query.filter_by(phone=data['phone']).first():
        return jsonify({'error': 'Phone already registered'}), 400
    
    user = User(
        email=data['email'],
        phone=data['phone'],
        user_type=data['user_type'],
        full_name=data['full_name'],
        business_name=data.get('business_name'),
        city=data.get('city')
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'Registration successful', 'user': user.to_dict()}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    user = User.query.filter_by(email=data['email']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    session['user_id'] = user.id
    session['user_type'] = user.user_type
    
    return jsonify({'message': 'Login successful', 'user': user.to_dict()})

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'})

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user(user):
    return jsonify({'user': user.to_dict()})

# Product Routes
@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.filter_by(is_active=True).order_by(Product.created_at.desc()).all()
    return jsonify({'products': [p.to_dict() for p in products]})

@app.route('/api/products/farmer', methods=['GET'])
@login_required
def get_farmer_products(user):
    if user.user_type != 'farmer':
        return jsonify({'error': 'Only farmers can access'}), 403
    products = Product.query.filter_by(farmer_id=user.id).all()
    return jsonify({'products': [p.to_dict() for p in products]})

@app.route('/api/products', methods=['POST'])
@login_required
def create_product(user):
    if user.user_type != 'farmer':
        return jsonify({'error': 'Only farmers can add products'}), 403
    
    data = request.get_json()
    product = Product(
        farmer_id=user.id,
        name=data['name'],
        category=data['category'],
        quantity_available=data['quantity_available'],
        unit=data.get('unit', 'kg'),
        price_per_unit=data['price_per_unit'],
        organic_certified=data.get('organic_certified', False),
        description=data.get('description')
    )
    
    db.session.add(product)
    db.session.commit()
    
    return jsonify({'product': product.to_dict(), 'message': 'Product added successfully'}), 201

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@login_required
def delete_product(user, product_id):
    product = Product.query.get_or_404(product_id)
    if product.farmer_id != user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    product.is_active = False
    db.session.commit()
    
    return jsonify({'message': 'Product deleted successfully'})

# Order Routes
@app.route('/api/orders', methods=['GET'])
@login_required
def get_orders(user):
    if user.user_type == 'farmer':
        orders = Order.query.filter_by(farmer_id=user.id).order_by(Order.created_at.desc()).all()
    elif user.user_type == 'hotel':
        orders = Order.query.filter_by(hotel_id=user.id).order_by(Order.created_at.desc()).all()
    else:
        orders = Order.query.order_by(Order.created_at.desc()).all()
    
    return jsonify({'orders': [o.to_dict() for o in orders]})

@app.route('/api/orders', methods=['POST'])
@login_required
def create_order(user):
    if user.user_type != 'hotel':
        return jsonify({'error': 'Only hotels can place orders'}), 403
    
    data = request.get_json()
    total_amount = 0
    items_data = []
    
    for item in data['items']:
        product = Product.query.get(item['product_id'])
        if not product or not product.is_active:
            return jsonify({'error': f'Product not available'}), 400
        if product.quantity_available < item['quantity']:
            return jsonify({'error': f'Insufficient quantity for {product.name}'}), 400
        
        subtotal = float(product.price_per_unit) * float(item['quantity'])
        total_amount += subtotal
        
        items_data.append({
            'product_id': product.id,
            'quantity': item['quantity'],
            'price_per_unit': float(product.price_per_unit),
            'subtotal': subtotal
        })
        
        # Update inventory
        product.quantity_available -= item['quantity']
    
    order = Order(
        order_number=Order.generate_order_number(Order),
        farmer_id=data['farmer_id'],
        hotel_id=user.id,
        total_amount=total_amount,
        delivery_address=data['delivery_address'],
        delivery_date=data.get('delivery_date')
    )
    
    db.session.add(order)
    db.session.flush()
    
    for item_data in items_data:
        order_item = OrderItem(order_id=order.id, **item_data)
        db.session.add(order_item)
    
    db.session.commit()
    
    return jsonify({'order': order.to_dict(), 'message': 'Order placed successfully'}), 201

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
@login_required
def update_order_status(user, order_id):
    order = Order.query.get_or_404(order_id)
    
    if user.user_type == 'farmer' and order.farmer_id != user.id:
        return jsonify({'error': 'Permission denied'}), 403
    if user.user_type == 'hotel' and order.hotel_id != user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.get_json()
    order.status = data.get('status', order.status)
    db.session.commit()
    
    return jsonify({'message': 'Order status updated', 'order': order.to_dict()})

# Subscription Routes
@app.route('/api/subscriptions', methods=['GET'])
@login_required
def get_subscriptions(user):
    if user.user_type != 'hotel':
        return jsonify({'error': 'Only hotels can have subscriptions'}), 403
    
    subscriptions = Subscription.query.filter_by(user_id=user.id, is_active=True).all()
    return jsonify({'subscriptions': [s.to_dict() for s in subscriptions]})

@app.route('/api/subscriptions', methods=['POST'])
@login_required
def create_subscription(user):
    if user.user_type != 'hotel':
        return jsonify({'error': 'Only hotels can create subscriptions'}), 403
    
    data = request.get_json()
    subscription = Subscription(
        user_id=user.id,
        product_id=data['product_id'],
        quantity=data['quantity'],
        frequency=data['frequency'],
        next_delivery=data.get('next_delivery')
    )
    
    db.session.add(subscription)
    db.session.commit()
    
    return jsonify({'subscription': subscription.to_dict(), 'message': 'Subscription created'}), 201

# Marketplace Stats
@app.route('/api/marketplace/stats', methods=['GET'])
def get_stats():
    total_farmers = User.query.filter_by(user_type='farmer').count()
    total_hotels = User.query.filter_by(user_type='hotel').count()
    active_products = Product.query.filter_by(is_active=True).count()
    total_orders = Order.query.count()
    
    return jsonify({
        'total_farmers': total_farmers,
        'total_hotels': total_hotels,
        'active_products': active_products,
        'total_orders': total_orders
    })

@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = [
        {'id': 'vegetable', 'name': 'Vegetables', 'icon': '🥬'},
        {'id': 'fruit', 'name': 'Fruits', 'icon': '🍎'},
        {'id': 'grain', 'name': 'Grains', 'icon': '🌾'},
        {'id': 'dairy', 'name': 'Dairy', 'icon': '🥛'},
        {'id': 'spice', 'name': 'Spices', 'icon': '🌶️'}
    ]
    return jsonify({'categories': categories})

# Create tables
with app.app_context():
    db.create_all()
    
    # Create demo farmer if not exists
    if not User.query.filter_by(email='farmer@example.com').first():
        farmer = User(
            email='farmer@example.com',
            phone='9876543210',
            user_type='farmer',
            full_name='Demo Farmer',
            business_name='Green Fields Farm',
            city='Pune'
        )
        farmer.set_password('farmer123')
        db.session.add(farmer)
    
    # Create demo hotel if not exists
    if not User.query.filter_by(email='hotel@example.com').first():
        hotel = User(
            email='hotel@example.com',
            phone='9876543211',
            user_type='hotel',
            full_name='Demo Hotel',
            business_name='Grand Hotel',
            city='Mumbai'
        )
        hotel.set_password('hotel123')
        db.session.add(hotel)
    
    # Create demo products
    if Product.query.count() == 0:
        farmer = User.query.filter_by(email='farmer@example.com').first()
        if farmer:
            products = [
                Product(farmer_id=farmer.id, name='Organic Tomatoes', category='vegetable', quantity_available=500, price_per_unit=40, organic_certified=True),
                Product(farmer_id=farmer.id, name='Fresh Spinach', category='vegetable', quantity_available=300, price_per_unit=30, organic_certified=True),
                Product(farmer_id=farmer.id, name='Basmati Rice', category='grain', quantity_available=1000, price_per_unit=80),
                Product(farmer_id=farmer.id, name='Farm Fresh Potatoes', category='vegetable', quantity_available=800, price_per_unit=25),
                Product(farmer_id=farmer.id, name='Organic Apples', category='fruit', quantity_available=200, price_per_unit=120, organic_certified=True)
            ]
            for p in products:
                db.session.add(p)
    
    db.session.commit()

# ==================== RUN APP ====================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)