# Single Agent Approach (with Extended Thinking)

Duration: 118.57s
Cost: $0.1805

# Product Catalog System - Complete Implementation

## Project Structure

```
product-catalog/
├── backend/
│   ├── app.py
│   ├── models.py
│   ├── config.py
│   ├── recommendations.py
│   ├── requirements.txt
│   └── uploads/
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── index.tsx
│   │   ├── api/
│   │   │   └── client.ts
│   │   ├── components/
│   │   │   ├── ProductList.tsx
│   │   │   ├── ProductDetail.tsx
│   │   │   ├── Cart.tsx
│   │   │   ├── SearchFilters.tsx
│   │   │   └── admin/
│   │   │       ├── AdminDashboard.tsx
│   │   │       ├── ProductForm.tsx
│   │   │       └── ProductTable.tsx
│   │   └── types/
│   │       └── index.ts
└── README.md
```

## Backend Implementation

### requirements.txt

```txt
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-CORS==4.0.0
psycopg2-binary==2.9.9
Pillow==10.1.0
python-dotenv==1.0.0
werkzeug==3.0.1
```

### backend/config.py

```python
import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:postgres@localhost:5432/product_catalog'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
```

### backend/models.py

```python
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Index

db = SQLAlchemy()

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    products = db.relationship('Product', backref='category', lazy=True)
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat()
        }


class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    image_url = db.Column(db.String(500))
    rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    inventory = db.relationship('Inventory', backref='product', uselist=False, cascade='all, delete-orphan')
    viewing_history = db.relationship('ViewingHistory', backref='product', cascade='all, delete-orphan')
    
    # Indexes
    __table_args__ = (
        Index('idx_product_category', 'category_id'),
        Index('idx_product_price', 'price'),
        Index('idx_product_rating', 'rating'),
    )
    
    def to_dict(self, include_inventory=False):
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price),
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'image_url': self.image_url,
            'rating': self.rating,
            'rating_count': self.rating_count,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_inventory and self.inventory:
            data['inventory'] = self.inventory.to_dict()
        
        return data


class Inventory(db.Model):
    __tablename__ = 'inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), unique=True, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    reserved = db.Column(db.Integer, default=0)
    last_restocked = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'reserved': self.reserved,
            'available': self.quantity - self.reserved,
            'last_restocked': self.last_restocked.isoformat()
        }


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    viewing_history = db.relationship('ViewingHistory', backref='user', cascade='all, delete-orphan')
    cart_items = db.relationship('CartItem', backref='user', cascade='all, delete-orphan')


class ViewingHistory(db.Model):
    __tablename__ = 'viewing_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_viewing_user_product', 'user_id', 'product_id'),
        Index('idx_viewing_time', 'viewed_at'),
    )


class CartItem(db.Model):
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    product = db.relationship('Product')
    
    def to_dict(self):
        return {
            'id': self.id,
            'product': self.product.to_dict(include_inventory=True),
            'quantity': self.quantity,
            'added_at': self.added_at.isoformat()
        }
```

### backend/recommendations.py

```python
from models import ViewingHistory, Product, db
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from collections import defaultdict

class RecommendationEngine:
    
    @staticmethod
    def get_recommendations(user_id, limit=10):
        """
        Generate product recommendations based on:
        1. Collaborative filtering (users who viewed similar products)
        2. Category-based recommendations
        3. Popular products
        """
        
        recommendations = []
        
        # Get user's viewing history (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        user_viewed = db.session.query(ViewingHistory.product_id)\
            .filter(and_(
                ViewingHistory.user_id == user_id,
                ViewingHistory.viewed_at >= thirty_days_ago
            ))\
            .distinct()\
            .all()
        
        user_viewed_ids = [p[0] for p in user_viewed]
        
        if not user_viewed_ids:
            # No history, return popular products
            return RecommendationEngine._get_popular_products(limit)
        
        # Collaborative filtering: Find users who viewed similar products
        similar_users = db.session.query(ViewingHistory.user_id)\
            .filter(and_(
                ViewingHistory.product_id.in_(user_viewed_ids),
                ViewingHistory.user_id != user_id
            ))\
            .distinct()\
            .limit(100)\
            .all()
        
        similar_user_ids = [u[0] for u in similar_users]
        
        if similar_user_ids:
            # Get products viewed by similar users
            collaborative_products = db.session.query(
                ViewingHistory.product_id,
                func.count(ViewingHistory.id).label('view_count')
            )\
            .filter(and_(
                ViewingHistory.user_id.in_(similar_user_ids),
                ViewingHistory.product_id.notin_(user_viewed_ids),
                ViewingHistory.viewed_at >= thirty_days_ago
            ))\
            .group_by(ViewingHistory.product_id)\
            .order_by(func.count(ViewingHistory.id).desc())\
            .limit(limit)\
            .all()
            
            recommendations.extend([p[0] for p in collaborative_products])
        
        # Category-based recommendations
        if len(recommendations) < limit:
            user_categories = db.session.query(Product.category_id)\
                .filter(Product.id.in_(user_viewed_ids))\
                .distinct()\
                .all()
            
            category_ids = [c[0] for c in user_categories]
            
            if category_ids:
                category_products = db.session.query(Product.id)\
                    .filter(and_(
                        Product.category_id.in_(category_ids),
                        Product.id.notin_(user_viewed_ids),
                        Product.id.notin_(recommendations),
                        Product.is_active == True
                    ))\
                    .order_by(Product.rating.desc())\
                    .limit(limit - len(recommendations))\
                    .all()
                
                recommendations.extend([p[0] for p in category_products])
        
        # Fill remaining with popular products
        if len(recommendations) < limit:
            popular = RecommendationEngine._get_popular_products(
                limit - len(recommendations),
                exclude_ids=user_viewed_ids + recommendations
            )
            recommendations.extend(popular)
        
        # Fetch full product details
        products = Product.query.filter(Product.id.in_(recommendations[:limit])).all()
        
        # Maintain order based on recommendation score
        product_dict = {p.id: p for p in products}
        ordered_products = [product_dict[pid] for pid in recommendations if pid in product_dict]
        
        return [p.to_dict(include_inventory=True) for p in ordered_products]
    
    @staticmethod
    def _get_popular_products(limit, exclude_ids=None):
        """Get popular products based on rating and view count"""
        query = db.session.query(Product.id)\
            .filter(Product.is_active == True)
        
        if exclude_ids:
            query = query.filter(Product.id.notin_(exclude_ids))
        
        products = query.order_by(
            Product.rating.desc(),
            Product.rating_count.desc()
        ).limit(limit).all()
        
        return [p[0] for p in products]
```

### backend/app.py

```python
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from config import Config
from models import db, Category, Product, Inventory, User, ViewingHistory, CartItem
from recommendations import RecommendationEngine
import os
from PIL import Image
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

db.init_app(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_or_create_user(session_id):
    """Get or create user based on session ID"""
    user = User.query.filter_by(session_id=session_id).first()
    if not user:
        user = User(session_id=session_id)
        db.session.add(user)
        db.session.commit()
    return user

# ============= CATEGORY ENDPOINTS =============

@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    return jsonify([c.to_dict() for c in categories])

@app.route('/api/categories', methods=['POST'])
def create_category():
    data = request.json
    category = Category(
        name=data['name'],
        description=data.get('description'),
        parent_id=data.get('parent_id')
    )
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201

# ============= PRODUCT ENDPOINTS =============

@app.route('/api/products', methods=['GET'])
def get_products():
    """Get products with filters and search"""
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Build query
    query = Product.query.filter_by(is_active=True)
    
    # Search
    search = request.args.get('search')
    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f'%{search}%'),
                Product.description.ilike(f'%{search}%')
            )
        )
    
    # Category filter
    category_id = request.args.get('category_id', type=int)
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    # Price range filter
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    # Rating filter
    min_rating = request.args.get('min_rating', type=float)
    if min_rating is not None:
        query = query.filter(Product.rating >= min_rating)
    
    # Sorting
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    if sort_by == 'price':
        query = query.order_by(Product.price.desc() if sort_order == 'desc' else Product.price.asc())
    elif sort_by == 'rating':
        query = query.order_by(Product.rating.desc() if sort_order == 'desc' else Product.rating.asc())
    elif sort_by == 'name':
        query = query.order_by(Product.name.desc() if sort_order == 'desc' else Product.name.asc())
    else:
        query = query.order_by(Product.created_at.desc() if sort_order == 'desc' else Product.created_at.asc())
    
    # Execute pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'products': [p.to_dict(include_inventory=True) for p in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
        'per_page': per_page
    })

@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Get single product by ID"""
    product = Product.query.get_or_404(product_id)
    
    # Track viewing history
    session_id = request.headers.get('X-Session-ID')
    if session_id:
        user = get_or_create_user(session_id)
        viewing = ViewingHistory(user_id=user.id, product_id=product_id)
        db.session.add(viewing)
        db.session.commit()
    
    return jsonify(product.to_dict(include_inventory=True))

@app.route('/api/admin/products', methods=['GET'])
def admin_get_products():
    """Get all products for admin (including inactive)"""
    products = Product.query.order_by(Product.created_at.desc()).all()
    return jsonify([p.to_dict(include_inventory=True) for p in products])

@app.route('/api/admin/products', methods=['POST'])
def create_product():
    """Create new product"""
    data = request.json
    
    product = Product(
        name=data['name'],
        description=data.get('description'),
        price=data['price'],
        category_id=data['category_id'],
        image_url=data.get('image_url'),
        rating=data.get('rating', 0.0),
        rating_count=data.get('rating_count', 0),
        is_active=data.get('is_active', True)
    )
    
    db.session.add(product)
    db.session.flush()  # Get product ID
    
    # Create inventory
    inventory = Inventory(
        product_id=product.id,
        quantity=data.get('quantity', 0)
    )
    db.session.add(inventory)
    db.session.commit()
    
    return jsonify(product.to_dict(include_inventory=True)), 201

@app.route('/api/admin/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Update product"""
    product = Product.query.get_or_404(product_id)
    data = request.json
    
    product.name = data.get('name', product.name)
    product.description = data.get('description', product.description)
    product.price = data.get('price', product.price)
    product.category_id = data.get('category_id', product.category_id)
    product.image_url = data.get('image_url', product.image_url)
    product.rating = data.get('rating', product.rating)
    product.rating_count = data.get('rating_count', product.rating_count)
    product.is_active = data.get('is_active', product.is_active)
    product.updated_at = datetime.utcnow()
    
    # Update inventory if provided
    if 'quantity' in data:
        if product.inventory:
            product.inventory.quantity = data['quantity']
            product.inventory.last_restocked = datetime.utcnow()
        else:
            inventory = Inventory(product_id=product.id, quantity=data['quantity'])
            db.session.add(inventory)
    
    db.session.commit()
    return jsonify(product.to_dict(include_inventory=True))

@app.route('/api/admin/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Delete product"""
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return '', 204

# ============= IMAGE UPLOAD =============

@app.route('/api/upload', methods=['POST'])
def upload_image():
    """Upload product image"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to avoid conflicts
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{int(datetime.utcnow().timestamp())}{ext}"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Resize and optimize image
        image = Image.open(file)
        image.thumbnail((800, 800), Image.Resampling.LANCZOS)
        image.save(filepath, optimize=True, quality=85)
        
        return jsonify({'url': f'/api/uploads/{filename}'}), 201
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/api/uploads/<filename>')
def get_upload(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ============= RECOMMENDATIONS =============

@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    """Get product recommendations for user"""
    session_id = request.headers.get('X-Session-ID')
    
    if not session_id:
        # Return popular products if no session
        products = Product.query.filter_by(is_active=True)\
            .order_by(Product.rating.desc())\
            .limit(10)\
            .all()
        return jsonify([p.to_dict(include_inventory=True) for p in products])
    
    user = get_or_create_user(session_id)
    recommendations = RecommendationEngine.get_recommendations(user.id, limit=10)
    
    return jsonify(recommendations)

# ============= CART ENDPOINTS =============

@app.route('/api/cart', methods=['GET'])
def get_cart():
    """Get user's cart"""
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        return jsonify({'error': 'Session ID required'}), 400
    
    user = get_or_create_user(session_id)
    cart_items = CartItem.query.filter_by(user_id=user.id).all()
    
    return jsonify({
        'items': [item.to_dict() for item in cart_items],
        'total': sum(float(item.product.price) * item.quantity for item in cart_items)
    })

@app.route('/api/cart', methods=['POST'])
def add_to_cart():
    """Add item to cart"""
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        return jsonify({'error': 'Session ID required'}), 400
    
    data = request.json
    user = get_or_create_user(session_id)
    
    # Check if item already in cart
    cart_item = CartItem.query.filter_by(
        user_id=user.id,
        product_id=data['product_id']
    ).first()
    
    if cart_item:
        cart_item.quantity += data.get('quantity', 1)
    else:
        cart_item = CartItem(
            user_id=user.id,
            product_id=data['product_id'],
            quantity=data.get('quantity', 1)
        )
        db.session.add(cart_item)
    
    db.session.commit()
    return jsonify(cart_item.to_dict()), 201

@app.route('/api/cart/<int:item_id>', methods=['PUT'])
def update_cart_item(item_id):
    """Update cart item quantity"""
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        return jsonify({'error': 'Session ID required'}), 400
    
    user = get_or_create_user(session_id)
    cart_item = CartItem.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    
    data = request.json
    cart_item.quantity = data['quantity']
    
    db.session.commit()
    return jsonify(cart_item.to_dict())

@app.route('/api/cart/<int:item_id>', methods=['DELETE'])
def remove_from_cart(item_id):
    """Remove item from cart"""
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        return jsonify({'error': 'Session ID required'}), 400
    
    user = get_or_create_user(session_id)
    cart_item = CartItem.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    
    db.session.delete(cart_item)
    db.session.commit()
    return '', 204

# ============= DATABASE INITIALIZATION =============

@app.route('/api/init-db', methods=['POST'])
def init_db():
    """Initialize database with sample data"""
    db.drop_all()
    db.create_all()
    
    # Create categories
    electronics = Category(name='Electronics', description='Electronic devices and accessories')
    clothing = Category(name='Clothing', description='Apparel and fashion')
    books = Category(name='Books', description='Books and literature')
    home = Category(name='Home & Garden', description='Home and garden products')
    
    db.session.add_all([electronics, clothing, books, home])
    db.session.commit()
    
    # Create sample products
    products_data = [
        {
            'name': 'Wireless Headphones',
            'description': 'High-quality wireless headphones with noise cancellation',
            'price': 99.99,
            'category_id': electronics.id,
            'rating': 4.5,
            'rating_count': 150,
            'quantity': 50
        },
        {
            'name': 'Smartphone',
            'description': 'Latest smartphone with advanced features',
            'price': 699.99,
            'category_id': electronics.id,
            'rating': 4.7,
            'rating_count': 320,
            'quantity': 30
        },
        {
            'name': 'Laptop',
            'description': 'Powerful laptop for work and entertainment',
            'price': 1299.99,
            'category_id': electronics.id,
            'rating': 4.6,
            'rating_count': 210,
            'quantity': 20
        },
        {
            'name': 'Cotton T-Shirt',
            'description': 'Comfortable cotton t-shirt',
            'price': 19.99,
            'category_id': clothing.id,
            'rating': 4.2,
            'rating_count': 89,
            'quantity': 200
        },
        {
            'name': 'Jeans',
            'description': 'Classic denim jeans',
            'price': 49.99,
            'category_id': clothing.id,
            'rating': 4.3,
            'rating_count': 156,
            'quantity': 150
        },
        {
            'name': 'Winter Jacket',
            'description': 'Warm winter jacket',
            'price': 129.99,
            'category_id': clothing.id,
            'rating': 4.8,
            'rating_count': 95,
            'quantity': 75
        },
        {
            'name': 'Python Programming Guide',
            'description': 'Complete guide to Python programming',
            'price': 39.99,
            'category_id': books.id,
            'rating': 4.9,
            'rating_count': 412,
            'quantity': 100
        },
        {
            'name': 'Science Fiction Novel',
            'description': 'Bestselling science fiction novel',
            'price': 14.99,
            'category_id': books.id,
            'rating': 4.4,
            'rating_count': 267,
            'quantity': 180
        },
        {
            'name': 'Coffee Maker',
            'description': 'Automatic coffee maker',
            'price': 79.99,
            'category_id': home.id,
            'rating': 4.1,
            'rating_count': 134,
            'quantity': 60
        },
        {
            'name': 'Garden Tools Set',
            'description': 'Complete set of garden tools',
            'price': 59.99,
            'category_id': home.id,
            'rating': 4.5,
            'rating_count': 78,
            'quantity': 90
        }
    ]
    
    for product_data in products_data:
        quantity = product_data.pop('quantity')
        product = Product(**product_data)
        db.session.add(product)
        db.session.flush()
        
        inventory = Inventory(product_id=product.id, quantity=quantity)
        db.session.add(inventory)
    
    db.session.commit()
    
    return jsonify({'message': 'Database initialized successfully'}), 201

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
```

## Frontend Implementation

### package.json

```json
{
  "name": "product-catalog-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.2",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "typescript": "^5.3.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "devDependencies": {
    "react-scripts": "5.0.1"
  },
  "eslintConfig": {
    "extends": [
      "react-app"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}
```

### tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "jsx": "react-jsx",
    "module": "ESNext",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "allowJs": true,
    "noEmit": true,
    "isolatedModules": true,
    "allowSyntheticDefaultImports": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "strict": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

### frontend/src/types/index.ts

```typescript
export interface Category {
  id: number;
  name: string;
  description: string;
  parent_id: number | null;
  created_at: string;
}

export interface Inventory {
  id: number;
  product_id: number;
  quantity: number;
  reserved: number;
  available: number;
  last_restocked: string;
}

export interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  category_id: number;
  category_name: string;
  image_url: string | null;
  rating: number;
  rating_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  inventory?: Inventory;
}

export interface CartItem {
  id: number;
  product: Product;
  quantity: number;
  added_at: string;
}

export interface Cart {
  items: CartItem[];
  total: number;
}

export interface ProductsResponse {
  products: Product[];
  total: number;
  pages: number;
  current_page: number;
  per_page: number;
}

export interface SearchFilters {
  search?: string;
  category_id?: number;
  min_price?: number;
  max_price?: number;
  min_rating?: number;
  sort_by?: 'price' | 'rating' | 'name' | 'created_at';
  sort_order?: 'asc' | 'desc';
  page?: number;
  per_page?: number;
}
```

### frontend/src/api/client.ts

```typescript
import axios from 'axios';
import { Product, ProductsResponse, Category, Cart, CartItem, SearchFilters } from '../types';

const API_BASE_URL = 'http://localhost:5000/api';

// Generate or get session ID
const getSessionId = (): string => {
  let sessionId = localStorage.getItem('sessionId');
  if (!sessionId) {
    sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem('sessionId', sessionId);
  }
  return sessionId;
};

// Create axios instance with session ID header
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add session ID to all requests
apiClient.interceptors.request.use((config) => {
  config.headers['X-Session-ID'] = getSessionId();
  return config;
});

// Products API
export const productsApi = {
  getAll: (filters?: SearchFilters): Promise<ProductsResponse> => 
    apiClient.get('/products', { params: filters }).then(res => res.data),
  
  getById: (id: number): Promise<Product> => 
    apiClient.get(`/products/${id}`).then(res => res.data),
  
  getRecommendations: (): Promise<Product[]> => 
    apiClient.get('/recommendations').then(res => res.data),
};

// Admin Products API
export const adminProductsApi = {
  getAll: (): Promise<Product[]> => 
    apiClient.get('/admin/products').then(res => res.data),
  
  create: (product: Partial<Product>): Promise<Product> => 
    apiClient.post('/admin/products', product).then(res => res.data),
  
  update: (id: number, product: Partial<Product>): Promise<Product> => 
    apiClient.put(`/admin/products/${id}`, product).then(res => res.data),
  
  delete: (id: number): Promise<void> => 
    apiClient.delete(`/admin/products/${id}`).then(res => res.data),
};

// Categories API
export const categoriesApi = {
  getAll: (): Promise<Category[]> => 
    apiClient.get('/categories').then(res => res.data),
  
  create: (category: Partial<Category>): Promise<Category> => 
    apiClient.post('/categories', category).then(res => res.data),
};

// Cart API
export const cartApi = {
  get: (): Promise<Cart> => 
    apiClient.get('/cart').then(res => res.data),
  
  add: (productId: number, quantity: number = 1): Promise<CartItem> => 
    apiClient.post('/cart', { product_id: productId, quantity }).then(res => res.data),
  
  update: (itemId: number, quantity: number): Promise<CartItem> => 
    apiClient.put(`/cart/${itemId}`, { quantity }).then(res => res.data),
  
  remove: (itemId: number): Promise<void> => 
    apiClient.delete(`/cart/${itemId}`).then(res => res.data),
};

// Upload API
export const uploadApi = {
  uploadImage: (file: File): Promise<{ url: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(res => res.data);
  },
};

// Database initialization
export const dbApi = {
  initialize: (): Promise<{ message: string }> => 
    apiClient.post('/init-db').then(res => res.data),
};
```

### frontend/src/components/SearchFilters.tsx

```typescript
import React, { useState, useEffect } from 'react';
import { Category, SearchFilters } from '../types';
import { categoriesApi } from '../api/client';

interface SearchFiltersProps {
  onFilterChange: (filters: SearchFilters) => void;
  initialFilters?: SearchFilters;
}

const SearchFiltersComponent: React.FC<SearchFiltersProps> = ({ 
  onFilterChange, 
  initialFilters = {} 
}) => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [filters, setFilters] = useState<SearchFilters>(initialFilters);

  useEffect(() => {
    categoriesApi.getAll().then(setCategories).catch(console.error);
  }, []);

  const handleFilterChange = (key: keyof SearchFilters, value: any) => {
    const newFilters = { ...filters, [key]: value || undefined };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>Filters</h3>
      
      <div style={styles.filterGroup}>
        <label style={styles.label}>Search</label>
        <input
          type="text"
          placeholder="Search products..."
          value={filters.search || ''}
          onChange={(e) => handleFilterChange('search', e.target.value)}
          style={styles.input}
        />
      </div>

      <div style={styles.filterGroup}>
        <label style={styles.label}>Category</label>
        <select
          value={filters.category_id || ''}
          onChange={(e) => handleFilterChange('category_id', e.target.value ? Number(e.target.value) : undefined)}
          style={styles.select}
        >
          <option value="">All Categories</option>
          {categories.map(cat => (
            <option key={cat.id} value={cat.id}>{cat.name}</option>
          ))}
        </select>
      </div>

      <div style={styles.filterGroup}>
        <label style={styles.label}>Price Range</label>
        <div style={styles.priceInputs}>
          <input
            type="number"
            placeholder="Min"
            value={filters.min_price || ''}
            onChange={(e) => handleFilterChange('min_price', e.target.value ? Number(e.target.value) : undefined)}
            style={styles.priceInput}
          />
          <span style={styles.priceSeparator}>-</span>
          <input
            type="number"
            placeholder="Max"
            value={filters.max_price || ''}
            onChange={(e) => handleFilterChange('max_price', e.target.value ? Number(e.target.value) : undefined)}
            style={styles.priceInput}
          />
        </div>
      </div>

      <div style={styles.filterGroup}>
        <label style={styles.label}>Minimum Rating</label>
        <select
          value={filters.min_rating || ''}
          onChange={(e) => handleFilterChange('min_rating', e.target.value ? Number(e.target.value) : undefined)}
          style={styles.select}
        >
          <option value="">Any Rating</option>
          <option value="4">4+ Stars</option>
          <option value="3">3+ Stars</option>
          <option value="2">2+ Stars</option>
        </select>
      </div>

      <div style={styles.filterGroup}>
        <label style={styles.label}>Sort By</label>
        <select
          value={filters.sort_by || 'created_at'}
          onChange={(e) => handleFilterChange('sort_by', e.target.value)}
          style={styles.select}
        >
          <option value="created_at">Newest</option>
          <option value="price">Price</option>
          <option value="rating">Rating</option>
          <option value="name">Name</option>
        </select>
      </div>

      <div style={styles.filterGroup}>
        <label style={styles.label}>Order</label>
        <select
          value={filters.sort_order || 'desc'}
          onChange={(e) => handleFilterChange('sort_order', e.target.value as 'asc' | 'desc')}
          style={styles.select}
        >
          <option value="desc">Descending</option>
          <option value="asc">Ascending</option>
        </select>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    backgroundColor: '#f8f9fa',
    padding: '20px',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  title: {
    marginTop: 0,
    marginBottom: '15px',
    fontSize: '18px',
    fontWeight: 'bold',
  },
  filterGroup: {
    marginBottom: '15px',
  },
  label: {
    display: 'block',
    marginBottom: '5px',
    fontWeight: '500',
    fontSize: '14px',
  },
  input: {
    width: '100%',
    padding: '8px',
    borderRadius: '4px',
    border: '1px solid #ddd',
    fontSize: '14px',
    boxSizing: 'border-box',
  },
  select: {
    width: '100%',
    padding: '8px',
    borderRadius: '4px',
    border: '1px solid #ddd',
    fontSize: '14px',
    boxSizing: 'border-box',
  },
  priceInputs: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  priceInput: {
    flex: 1,
    padding: '8px',
    borderRadius: '4px',
    border: '1px solid #ddd',
    fontSize: '14px',
  },
  priceSeparator: {
    color: '#666',
  },
};

export default SearchFiltersComponent;
```

### frontend/src/components/ProductList.tsx

```typescript
import React, { useState, useEffect } from 'react';
import { Product, SearchFilters, ProductsResponse } from '../types';
import { productsApi, cartApi } from '../api/client';
import { Link } from 'react-router-dom';
import SearchFiltersComponent from './SearchFilters';

const ProductList: React.FC = () => {
  const [data, setData] = useState<ProductsResponse | null>(null);
  const [recommendations, setRecommendations] = useState<Product[]>([]);
  const [filters, setFilters] = useState<SearchFilters>({ page: 1, per_page: 12 });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadProducts();
    loadRecommendations();
  }, [filters]);

  const loadProducts = async () => {
    setLoading(true);
    try {
      const response = await productsApi.getAll(filters);
      setData(response);
    } catch (error) {
      console.error('Error loading products:', error);
    }
    setLoading(false);