from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import get_db, init_db
from functools import wraps

app = Flask(__name__)
app.secret_key = 'savebite_secret_key_2024'

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ── Decorators ──────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('Access denied.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ── Public Routes ───────────────────────────────────────────────────────────

@app.route('/')
def index():
    db = get_db()
    featured = db.execute('''
        SELECT f.*, r.name AS restaurant_name, r.location, r.cuisine
        FROM food_items f JOIN restaurants r ON f.restaurant_id = r.id
        WHERE f.status = 'available' AND r.status = 'active'
        ORDER BY f.discount_percent DESC LIMIT 8
    ''').fetchall()
    db.close()
    return render_template('index.html', featured=featured)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name  = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        role  = request.form.get('role', 'user')
        if role not in ('user', 'restaurant'):
            role = 'user'
        db = get_db()
        if db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone():
            db.close()
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        db.execute('INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)',
                   (name, email, generate_password_hash(password), role))
        db.commit(); db.close()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        db.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['name']    = user['name']
            session['role']    = user['role']
            flash(f"Welcome back, {user['name']}!", 'success')
            return redirect(url_for({
                'admin':      'admin_dashboard',
                'restaurant': 'restaurant_dashboard',
                'user':       'user_dashboard'
            }[user['role']]))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/browse')
def browse():
    search   = request.args.get('q', '')
    location = request.args.get('location', '')
    db = get_db()
    query  = '''SELECT f.*, r.name AS restaurant_name, r.location, r.cuisine
                FROM food_items f JOIN restaurants r ON f.restaurant_id = r.id
                WHERE f.status = 'available' AND r.status = 'active' '''
    params = []
    if search:
        query  += " AND (f.name LIKE ? OR f.description LIKE ?)"
        params += [f'%{search}%', f'%{search}%']
    if location:
        query  += " AND r.location LIKE ?"
        params.append(f'%{location}%')
    query += " ORDER BY f.discount_percent DESC"
    items = db.execute(query, params).fetchall()
    db.close()
    return render_template('user/browse.html', items=items, search=search, location=location)

# ── User Routes ─────────────────────────────────────────────────────────────

@app.route('/user/dashboard')
@login_required
@role_required('user')
def user_dashboard():
    db = get_db()
    bookings = db.execute('''
        SELECT b.*, f.name AS food_name, f.image_filename, f.discounted_price,
               r.name AS restaurant_name
        FROM bookings b
        JOIN food_items f ON b.food_item_id = f.id
        JOIN restaurants r ON f.restaurant_id = r.id
        WHERE b.user_id = ? ORDER BY b.booked_at DESC
    ''', (session['user_id'],)).fetchall()
    db.close()
    return render_template('user/dashboard.html', bookings=bookings)

@app.route('/user/book/<int:item_id>', methods=['GET', 'POST'])
@login_required
@role_required('user')
def book_item(item_id):
    db = get_db()
    item = db.execute('''
        SELECT f.*, r.name AS restaurant_name, r.location, r.phone
        FROM food_items f JOIN restaurants r ON f.restaurant_id = r.id
        WHERE f.id=? AND f.status='available'
    ''', (item_id,)).fetchone()
    if not item:
        db.close()
        flash('Item not available.', 'danger')
        return redirect(url_for('browse'))
    if request.method == 'POST':
        qty   = max(1, min(int(request.form.get('quantity', 1)), item['quantity']))
        total = round(item['discounted_price'] * qty, 2)
        db.execute('INSERT INTO bookings (user_id,food_item_id,quantity,total_price) VALUES (?,?,?,?)',
                   (session['user_id'], item_id, qty, total))
        new_qty    = item['quantity'] - qty
        new_status = 'available' if new_qty > 0 else 'booked'
        db.execute('UPDATE food_items SET quantity=?,status=? WHERE id=?', (new_qty, new_status, item_id))
        db.commit(); db.close()
        flash('Food booked successfully!', 'success')
        return redirect(url_for('user_bookings'))
    db.close()
    return render_template('user/book_item.html', item=item)

@app.route('/user/bookings')
@login_required
@role_required('user')
def user_bookings():
    db = get_db()
    bookings = db.execute('''
        SELECT b.*, f.name AS food_name, f.image_filename, f.discounted_price,
               r.name AS restaurant_name, r.location
        FROM bookings b
        JOIN food_items f ON b.food_item_id = f.id
        JOIN restaurants r ON f.restaurant_id = r.id
        WHERE b.user_id=? ORDER BY b.booked_at DESC
    ''', (session['user_id'],)).fetchall()
    db.close()
    return render_template('user/bookings.html', bookings=bookings)

@app.route('/user/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
@role_required('user')
def cancel_booking(booking_id):
    db = get_db()
    b = db.execute('SELECT * FROM bookings WHERE id=? AND user_id=?',
                   (booking_id, session['user_id'])).fetchone()
    if b and b['status'] == 'pending':
        db.execute("UPDATE bookings SET status='cancelled' WHERE id=?", (booking_id,))
        item = db.execute('SELECT * FROM food_items WHERE id=?', (b['food_item_id'],)).fetchone()
        db.execute("UPDATE food_items SET quantity=?,status='available' WHERE id=?",
                   (item['quantity'] + b['quantity'], b['food_item_id']))
        db.commit()
        flash('Booking cancelled.', 'info')
    db.close()
    return redirect(url_for('user_bookings'))

# ── Restaurant Routes ────────────────────────────────────────────────────────

@app.route('/restaurant/dashboard')
@login_required
@role_required('restaurant')
def restaurant_dashboard():
    db = get_db()
    restaurant = db.execute('SELECT * FROM restaurants WHERE owner_id=?', (session['user_id'],)).fetchone()
    stats = {}
    if restaurant:
        rid = restaurant['id']
        stats['total']    = db.execute('SELECT COUNT(*) FROM food_items WHERE restaurant_id=?', (rid,)).fetchone()[0]
        stats['available']= db.execute("SELECT COUNT(*) FROM food_items WHERE restaurant_id=? AND status='available'", (rid,)).fetchone()[0]
        stats['booked']   = db.execute("SELECT COUNT(*) FROM food_items WHERE restaurant_id=? AND status='booked'", (rid,)).fetchone()[0]
        stats['bookings'] = db.execute('''SELECT COUNT(*) FROM bookings b JOIN food_items f ON b.food_item_id=f.id WHERE f.restaurant_id=?''', (rid,)).fetchone()[0]
    db.close()
    return render_template('restaurant/dashboard.html', restaurant=restaurant, stats=stats)

@app.route('/restaurant/register', methods=['GET', 'POST'])
@login_required
@role_required('restaurant')
def register_restaurant():
    db = get_db()
    if db.execute('SELECT id FROM restaurants WHERE owner_id=?', (session['user_id'],)).fetchone():
        db.close()
        flash('You already have a restaurant registered.', 'info')
        return redirect(url_for('restaurant_dashboard'))
    if request.method == 'POST':
        db.execute('INSERT INTO restaurants (owner_id,name,description,location,phone,cuisine) VALUES (?,?,?,?,?,?)',
                   (session['user_id'], request.form['name'].strip(),
                    request.form.get('description','').strip(),
                    request.form.get('location','').strip(),
                    request.form.get('phone','').strip(),
                    request.form.get('cuisine','').strip()))
        db.commit(); db.close()
        flash('Restaurant registered!', 'success')
        return redirect(url_for('restaurant_dashboard'))
    db.close()
    return render_template('restaurant/register.html')

@app.route('/restaurant/add_food', methods=['GET', 'POST'])
@login_required
@role_required('restaurant')
def add_food():
    db = get_db()
    restaurant = db.execute('SELECT * FROM restaurants WHERE owner_id=?', (session['user_id'],)).fetchone()
    if not restaurant:
        db.close()
        flash('Please register your restaurant first.', 'warning')
        return redirect(url_for('register_restaurant'))
    if request.method == 'POST':
        orig    = float(request.form['original_price'])
        disc    = float(request.form['discount_percent'])
        dp      = round(orig * (1 - disc / 100), 2)
        qty     = int(request.form.get('quantity', 1))
        expires = request.form.get('expires_at', '').strip() or None
        img_fn  = None
        if 'image' in request.files:
            f = request.files['image']
            if f and f.filename and allowed_file(f.filename):
                img_fn = secure_filename(f.filename)
                f.save(os.path.join(app.config['UPLOAD_FOLDER'], img_fn))
        db.execute('''INSERT INTO food_items
            (restaurant_id,name,description,original_price,discount_percent,discounted_price,quantity,expires_at,image_filename)
            VALUES (?,?,?,?,?,?,?,?,?)''',
            (restaurant['id'], request.form['name'].strip(),
             request.form.get('description','').strip(),
             orig, disc, dp, qty, expires, img_fn))
        db.commit(); db.close()
        flash('Food item added!', 'success')
        return redirect(url_for('restaurant_items'))
    db.close()
    return render_template('restaurant/add_food.html', restaurant=restaurant)

@app.route('/restaurant/items')
@login_required
@role_required('restaurant')
def restaurant_items():
    db = get_db()
    restaurant = db.execute('SELECT * FROM restaurants WHERE owner_id=?', (session['user_id'],)).fetchone()
    items = []
    if restaurant:
        items = db.execute('SELECT * FROM food_items WHERE restaurant_id=? ORDER BY created_at DESC', (restaurant['id'],)).fetchall()
    db.close()
    return render_template('restaurant/my_items.html', items=items, restaurant=restaurant)

@app.route('/restaurant/delete_item/<int:item_id>', methods=['POST'])
@login_required
@role_required('restaurant')
def delete_food(item_id):
    db = get_db()
    r = db.execute('SELECT * FROM restaurants WHERE owner_id=?', (session['user_id'],)).fetchone()
    if r:
        db.execute('DELETE FROM food_items WHERE id=? AND restaurant_id=?', (item_id, r['id']))
        db.commit()
        flash('Item removed.', 'info')
    db.close()
    return redirect(url_for('restaurant_items'))

@app.route('/restaurant/bookings')
@login_required
@role_required('restaurant')
def restaurant_bookings():
    db = get_db()
    r = db.execute('SELECT * FROM restaurants WHERE owner_id=?', (session['user_id'],)).fetchone()
    bookings = []
    if r:
        bookings = db.execute('''
            SELECT b.*, f.name AS food_name, u.name AS user_name, u.email AS user_email, f.discounted_price
            FROM bookings b JOIN food_items f ON b.food_item_id=f.id JOIN users u ON b.user_id=u.id
            WHERE f.restaurant_id=? ORDER BY b.booked_at DESC
        ''', (r['id'],)).fetchall()
    db.close()
    return render_template('restaurant/bookings.html', bookings=bookings, restaurant=r)

@app.route('/restaurant/confirm/<int:booking_id>', methods=['POST'])
@login_required
@role_required('restaurant')
def confirm_booking(booking_id):
    db = get_db()
    db.execute("UPDATE bookings SET status='confirmed' WHERE id=?", (booking_id,))
    db.commit(); db.close()
    flash('Booking confirmed!', 'success')
    return redirect(url_for('restaurant_bookings'))

# ── Admin Routes ─────────────────────────────────────────────────────────────

@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    db = get_db()
    stats = {
        'users':       db.execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0],
        'restaurants': db.execute("SELECT COUNT(*) FROM restaurants").fetchone()[0],
        'food_items':  db.execute("SELECT COUNT(*) FROM food_items").fetchone()[0],
        'bookings':    db.execute("SELECT COUNT(*) FROM bookings").fetchone()[0],
        'active':      db.execute("SELECT COUNT(*) FROM restaurants WHERE status='active'").fetchone()[0],
        'waste_saved': db.execute("SELECT COALESCE(SUM(total_price),0) FROM bookings WHERE status!='cancelled'").fetchone()[0],
    }
    recent = db.execute('''
        SELECT b.*, f.name AS food_name, u.name AS user_name, r.name AS restaurant_name
        FROM bookings b JOIN food_items f ON b.food_item_id=f.id
        JOIN users u ON b.user_id=u.id JOIN restaurants r ON f.restaurant_id=r.id
        ORDER BY b.booked_at DESC LIMIT 6
    ''').fetchall()
    db.close()
    return render_template('admin/dashboard.html', stats=stats, recent=recent)

@app.route('/admin/users')
@login_required
@role_required('admin')
def admin_users():
    db = get_db()
    users = db.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    db.close()
    return render_template('admin/users.html', users=users)

@app.route('/admin/delete_user/<int:uid>', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_user(uid):
    db = get_db()
    db.execute('DELETE FROM users WHERE id=?', (uid,))
    db.commit(); db.close()
    flash('User deleted.', 'info')
    return redirect(url_for('admin_users'))

@app.route('/admin/restaurants')
@login_required
@role_required('admin')
def admin_restaurants():
    db = get_db()
    restaurants = db.execute('''
        SELECT r.*, u.name AS owner_name, u.email AS owner_email
        FROM restaurants r JOIN users u ON r.owner_id=u.id ORDER BY r.created_at DESC
    ''').fetchall()
    db.close()
    return render_template('admin/restaurants.html', restaurants=restaurants)

@app.route('/admin/toggle_restaurant/<int:rid>', methods=['POST'])
@login_required
@role_required('admin')
def toggle_restaurant(rid):
    db = get_db()
    r = db.execute('SELECT status FROM restaurants WHERE id=?', (rid,)).fetchone()
    if r:
        new = 'inactive' if r['status'] == 'active' else 'active'
        db.execute('UPDATE restaurants SET status=? WHERE id=?', (new, rid))
        db.commit()
    db.close()
    return redirect(url_for('admin_restaurants'))

@app.route('/admin/listings')
@login_required
@role_required('admin')
def admin_listings():
    db = get_db()
    items = db.execute('''
        SELECT f.*, r.name AS restaurant_name, r.location
        FROM food_items f JOIN restaurants r ON f.restaurant_id=r.id ORDER BY f.created_at DESC
    ''').fetchall()
    db.close()
    return render_template('admin/listings.html', items=items)

@app.route('/admin/delete_item/<int:item_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_item(item_id):
    db = get_db()
    db.execute('DELETE FROM food_items WHERE id=?', (item_id,))
    db.commit(); db.close()
    flash('Item removed.', 'info')
    return redirect(url_for('admin_listings'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
