import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'savebite.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',  -- 'admin', 'restaurant', 'user'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Restaurants table
    c.execute('''
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            location TEXT,
            phone TEXT,
            cuisine TEXT,
            status TEXT DEFAULT 'active',  -- 'active', 'inactive'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )
    ''')

    # Food items / listings
    c.execute('''
        CREATE TABLE IF NOT EXISTS food_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            original_price REAL NOT NULL,
            discount_percent REAL NOT NULL DEFAULT 0,
            discounted_price REAL NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            expires_at TEXT,
            image_filename TEXT,
            status TEXT DEFAULT 'available',  -- 'available', 'booked', 'expired'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        )
    ''')

    # Bookings table
    c.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            food_item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            total_price REAL NOT NULL,
            status TEXT DEFAULT 'pending',  -- 'pending', 'confirmed', 'cancelled'
            booked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (food_item_id) REFERENCES food_items(id)
        )
    ''')

    # Seed default admin
    from werkzeug.security import generate_password_hash
    c.execute("SELECT id FROM users WHERE email = 'admin@savebite.com'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ('Admin', 'admin@savebite.com', generate_password_hash('admin123'), 'admin')
        )

    conn.commit()
    conn.close()
    print("SaveBite database initialized.")

if __name__ == '__main__':
    init_db()
