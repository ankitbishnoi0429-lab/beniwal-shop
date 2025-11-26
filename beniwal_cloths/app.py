
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import sqlite3, os, json
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
import google.generativeai as genai
from PIL import Image
import io

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'devkey@123secure'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DB = os.path.join(APP_ROOT, 'beniwal.db')

# Admin credentials (configurable via environment)
ADMIN_PHONE = os.environ.get('ADMIN_PHONE', '7900012929')
# Default token is '@' + phone, but can be overridden via env var ADMIN_TOKEN
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', f'@{ADMIN_PHONE}')

# Google Gemini API configuration
try:
    genai.configure(api_key='AIzaSyC-v_gU-X01G2m2B5HGN7k-YZ8N4xvQQwE')
    AI_ENABLED = True
except Exception as e:
    print(f"AI not configured: {e}")
    AI_ENABLED = False

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sellers (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, rating REAL, lat REAL, lon REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY,
        seller_id INTEGER,
        title TEXT,
        price REAL,
        images TEXT,
        videos TEXT,
        description TEXT,
        seller_can_view_buyer_phone INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS product_images (id INTEGER PRIMARY KEY, product_id INTEGER, image_path TEXT, FOREIGN KEY(product_id) REFERENCES products(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY,
        product_id INTEGER,
        buyer_phone TEXT,
        buyer_lat REAL,
        buyer_lon REAL,
        buyer_share_phone INTEGER DEFAULT 1,
        total REAL,
        status TEXT DEFAULT 'pending'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (k TEXT PRIMARY KEY, v TEXT)''')
    conn.commit()
    conn.close()

def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def generate_product_description(title, product_title, image_paths=None):
    """Generate AI-powered product description using Gemini Vision"""
    if not AI_ENABLED:
        return f"Beautiful {title}. High quality product at best price."
    
    try:
        # Start with basic description
        prompt = f"""You are a professional e-commerce product description writer. 
Write a compelling and concise product description for:
Product Title: {product_title}
Category: {title}

The description should be:
- 2-3 sentences maximum
- Highlight key features and benefits
- Use persuasive but honest language
- Include why customers should buy this

Write only the description, no labels or headers."""
        
        # If images are provided, analyze them too
        if image_paths and len(image_paths) > 0:
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Use first image for vision analysis
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_paths[0])
                if os.path.exists(image_path):
                    # Read and encode image
                    with open(image_path, 'rb') as img_file:
                        image_data = img_file.read()
                    
                    from base64 import b64encode
                    image_base64 = b64encode(image_data).decode('utf-8')
                    
                    # Determine image type
                    file_ext = image_paths[0].rsplit('.', 1)[1].lower()
                    mime_types = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp'}
                    mime_type = mime_types.get(file_ext, 'image/jpeg')
                    
                    # Call vision API with image
                    response = model.generate_content([
                        {'text': prompt + "\n\nAlso analyze this product image and enhance the description based on what you see."},
                        {'mime_type': mime_type, 'data': image_base64}
                    ])
                    return response.text.strip()
            except Exception as e:
                print(f"Image analysis failed: {e}")
        
        # Fallback to text-only description
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"AI description generation failed: {e}")
        return f"High quality {title}. Best price guarantee with excellent customer service."


def generate_product_video_stub(title, image_paths=None):
    """Placeholder for AI-generated product video. In production integrate with video-generation API."""
    # Return None to indicate no auto-generated video available
    return None


@app.context_processor
def inject_utilities():
    def tr(key):
        # simple translations
        lang = session.get('lang', 'en')
        strings = {
            'en': {
                'admin': 'Admin',
                'upload_product': 'Upload Product',
                'logout': 'Logout',
                'admin_login': 'Admin Login'
            },
            'hi': {
                'admin': 'एडमिन',
                'upload_product': 'उत्पाद अपलोड करें',
                'logout': 'लॉग आउट',
                'admin_login': 'एडमिन लॉगिन'
            }
        }
        return strings.get(lang, strings['en']).get(key, key)

    # load settings from DB
    try:
        rows = query_db('SELECT k,v FROM settings')
        settings = {r['k']: r['v'] for r in rows}
    except Exception:
        settings = {}

    site_title = settings.get('site_title', "Beniwal Cloths")
    header_color = settings.get('header_color', '#c0392b')
    return dict(tr=tr, site_title=site_title, header_color=header_color, settings=settings)


@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in ('en','hi'):
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

init_db()

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        token = request.form.get('token', '').strip()

        if token == ADMIN_TOKEN:
            session['admin'] = True
            session['admin_user'] = 'admin'
            flash('Admin access granted!', 'success')
            return redirect(url_for('upload'))
        else:
            flash('Invalid token. Use @7900012929', 'error')
    return render_template('admin_login.html')

## Removed quick/forcelogin debug routes for security in production
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))


@app.route('/health')
def health():
    return 'ok', 200

@app.route('/')
def index():
    products = query_db("SELECT p.*, s.name as seller_name, s.rating as seller_rating, s.lat as seller_lat, s.lon as seller_lon FROM products p JOIN sellers s ON p.seller_id = s.id")
    # Parse images for each product
    for product in products:
        try:
            product['images_list'] = json.loads(product['images']) if product['images'] else []
        except:
            product['images_list'] = []
    return render_template('index.html', products=products)

@app.route('/product/<int:pid>')
def product(pid):
    p = query_db("SELECT p.*, s.name as seller_name, s.phone as seller_phone, s.rating as seller_rating, s.lat as seller_lat, s.lon as seller_lon FROM products p JOIN sellers s ON p.seller_id = s.id WHERE p.id = ?", (pid,), one=True)
    if not p:
        return "Product not found", 404
    
    # Parse images from JSON
    try:
        images = json.loads(p['images']) if p['images'] else []
    except:
        images = []
    
    try:
        videos = json.loads(p['videos']) if p.get('videos') else []
    except:
        videos = []

    return render_template('product.html', p=p, images=images, videos=videos)

@app.route('/seller/upload', methods=['GET','POST'])
def upload():
    if not session.get('admin'):
        flash('Please login as admin first', 'error')
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        name = request.form.get('name') or 'Seller'
        phone = request.form.get('phone') or ''
        rating = float(request.form.get('rating') or 5.0)
        lat = float(request.form.get('lat') or 0)
        lon = float(request.form.get('lon') or 0)
        # create seller
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO sellers (name, phone, rating, lat, lon) VALUES (?,?,?,?,?)", (name, phone, rating, lat, lon))
        seller_id = c.lastrowid
        conn.commit()
        # product
        title = request.form.get('title') or 'Untitled'
        category = request.form.get('category') or 'Clothing'
        price = float(request.form.get('price') or 0)
        desc = request.form.get('description') or ''
        
        # Handle multiple images
        image_files = request.files.getlist('images')
        image_paths = []

        for file in image_files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = os.urandom(4).hex()
                filename = f"{timestamp}_{filename}"
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(path)
                image_paths.append(filename)

        # Handle video uploads (optional)
        video_files = request.files.getlist('videos')
        video_paths = []
        for v in video_files:
            if v and v.filename:
                vname = secure_filename(v.filename)
                ts = os.urandom(4).hex()
                vname = f"{ts}_{vname}"
                vpath = os.path.join(app.config['UPLOAD_FOLDER'], vname)
                v.save(vpath)
                video_paths.append(vname)

        # If description empty try AI generation
        if not desc:
            desc = generate_product_description(category, title, image_paths)

        if not image_paths:
            flash('Please upload at least one product image', 'error')
            return redirect(url_for('upload'))
        
        # Seller preference: whether seller can view buyer phone
        seller_view_flag = 1 if request.form.get('seller_view_buyer_phone') == 'on' else 0

        # Save product with multiple image and video references
        images_json = json.dumps(image_paths)
        videos_json = json.dumps(video_paths)
        c.execute("INSERT INTO products (seller_id, title, price, images, videos, description, seller_can_view_buyer_phone) VALUES (?,?,?,?,?,?,?)", (seller_id, title, price, images_json, videos_json, desc, seller_view_flag))
        product_id = c.lastrowid
        conn.commit()
        conn.close()
        
        flash('Product uploaded successfully! AI generated description applied.', 'success')
        return redirect(url_for('index'))
    return render_template('upload.html')

@app.route('/buy/<int:pid>', methods=['GET', 'POST'])
def buy(pid):
    prod = query_db("SELECT * FROM products WHERE id = ?", (pid,), one=True)
    if not prod:
        return "Product not found", 404
    
    if request.method == 'POST':
        buyer_phone = request.form.get('buyer_phone') or ''
        if not buyer_phone:
            flash('Please enter your phone number', 'error')
            return redirect(url_for('product', pid=pid))
        # whether buyer agrees to share phone with seller
        buyer_share = 1 if request.form.get('share_phone') == 'on' else 0
        
        total = float(prod['price'] or 0) + 10  # delivery charge fixed 10
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO orders (product_id, buyer_phone, buyer_lat, buyer_lon, buyer_share_phone, total) VALUES (?,?,?,?,?,?)", (pid, buyer_phone, 0, 0, buyer_share, total))
        order_id = c.lastrowid
        conn.commit()
        conn.close()
        
        seller = query_db("SELECT s.phone FROM sellers s JOIN products p ON p.seller_id = s.id WHERE p.id = ?", (pid,), one=True)
        session['current_order'] = order_id
        session['seller_phone'] = seller['phone'] if seller else 'N/A'
        session['order_product_id'] = pid
        
        return redirect(url_for('confirm_order', order_id=order_id))
    
    # parse images for display
    try:
        images = json.loads(prod['images']) if prod['images'] else []
    except:
        images = []
    return render_template('buy.html', p=prod, images=images)

@app.route('/confirm/<int:order_id>', methods=['GET', 'POST'])
def confirm_order(order_id):
    if request.method == 'POST':
        action = request.form.get('action')
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        
        if action == 'yes':
            c.execute("UPDATE orders SET status='confirmed' WHERE id = ?", (order_id,))
            flash('Order confirmed! Seller will contact you soon.', 'success')
        else:
            c.execute("DELETE FROM orders WHERE id = ?", (order_id,))
            flash('Order cancelled.', 'info')
        
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    
    # GET request - show confirmation page
    order = query_db("SELECT * FROM orders WHERE id = ?", (order_id,), one=True)
    if not order:
        return "Order not found", 404
    
    prod = query_db("SELECT * FROM products WHERE id = ?", (order['product_id'],), one=True)
    seller = query_db("SELECT s.phone FROM sellers s JOIN products p ON p.seller_id = s.id WHERE p.id = ?", (order['product_id'],), one=True)
    
    # determine whether seller should see buyer number: both seller setting and buyer_share must be true
    seller_can_view = bool(prod['seller_can_view_buyer_phone']) and bool(order['buyer_share_phone'])
    return render_template('confirm.html', order=order, prod=prod, seller_phone=seller['phone'] if seller else 'N/A', seller_can_view= seller_can_view)


@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        flash('Please login as admin first', 'error')
        return redirect(url_for('admin_login'))
    products = query_db("SELECT p.*, s.name as seller_name FROM products p JOIN sellers s ON p.seller_id = s.id")
    settings = {r['k']: r['v'] for r in query_db('SELECT k,v FROM settings')}
    return render_template('admin_dashboard.html', products=products, settings=settings)


@app.route('/admin/orders')
def admin_orders():
    if not session.get('admin'):
        flash('Please login as admin first', 'error')
        return redirect(url_for('admin_login'))
    rows = query_db('SELECT o.*, p.title as product_title, p.seller_can_view_buyer_phone as seller_flag FROM orders o JOIN products p ON o.product_id = p.id')
    orders = []
    for r in rows:
        show = bool(r['seller_flag']) and bool(r['buyer_share_phone'])
        orders.append({'id': r['id'], 'product_title': r['product_title'], 'buyer_phone': r['buyer_phone'], 'total': r['total'], 'status': r['status'], 'show_buyer_phone': show})
    return render_template('admin_orders.html', orders=orders)


@app.route('/admin/product/<int:pid>/delete', methods=['POST'])
def admin_delete_product(pid):
    if not session.get('admin'):
        flash('Please login as admin first', 'error')
        return redirect(url_for('admin_login'))
    p = query_db('SELECT * FROM products WHERE id = ?', (pid,), one=True)
    if p:
        # remove images
        try:
            imgs = json.loads(p['images']) if p['images'] else []
            for img in imgs:
                path = os.path.join(app.config['UPLOAD_FOLDER'], img)
                if os.path.exists(path):
                    os.remove(path)
        except Exception:
            pass
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('DELETE FROM products WHERE id = ?', (pid,))
        conn.commit()
        conn.close()
        flash('Product deleted', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/product/<int:pid>/edit', methods=['GET','POST'])
def admin_edit_product(pid):
    if not session.get('admin'):
        flash('Please login as admin first', 'error')
        return redirect(url_for('admin_login'))
    p = query_db('SELECT * FROM products WHERE id = ?', (pid,), one=True)
    if not p:
        flash('Product not found', 'error')
        return redirect(url_for('admin_dashboard'))
    try:
        images = json.loads(p['images']) if p['images'] else []
    except:
        images = []

    if request.method == 'POST':
        title = request.form.get('title') or p['title']
        price = float(request.form.get('price') or p['price'])
        description = request.form.get('description') or p['description']
        seller_view_flag = 1 if request.form.get('seller_view_buyer_phone') == 'on' else 0
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('UPDATE products SET title=?, price=?, description=?, seller_can_view_buyer_phone=? WHERE id=?', (title, price, description, seller_view_flag, pid))
        conn.commit()
        conn.close()
        flash('Product updated', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_edit_product.html', p=p, images=images)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
