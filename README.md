# ClearanceHub – Shop Closing Sale System

A mini web project built with Python Flask + SQLite + HTML/CSS/JS.

## Features
- **3 Roles**: Admin, Shop Owner, User
- Login & Registration with role selection
- Shop Owner: Register shop, upload items with images and discounts
- User: Browse deals by name/location, book items, cancel pending bookings
- Admin: Monitor all users, shops, and listings; toggle shop status

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the App
```bash
python app.py
```

Open your browser at: **http://localhost:5000**

### 3. Default Admin Login
- **Email**: `admin@clearancehub.com`
- **Password**: `admin123`

## Folder Structure
```
savebite/
├── app.py                  # Flask application (all routes)
├── database.py             # DB schema & initialization
├── requirements.txt
├── clearancehub.db         # SQLite DB (auto-created)
├── static/
│   ├── css/style.css       # Global design system
│   ├── js/main.js          # JS utilities
│   └── uploads/            # Uploaded item images
└── templates/
    ├── base.html           # Shared layout
    ├── index.html          # Landing page
    ├── login.html
    ├── register.html
    ├── admin/
    │   ├── dashboard.html
    │   ├── users.html
    │   ├── shops.html
    │   └── listings.html
    ├── owner/
    │   ├── dashboard.html
    │   ├── register_shop.html
    │   ├── add_item.html
    │   ├── my_items.html
    │   └── bookings.html
    └── user/
        ├── dashboard.html
        ├── browse.html
        ├── bookings.html
        └── book_item.html
```

## User Roles

| Role       | Capabilities |
|------------|-------------|
| **Admin**  | View/delete users, toggle shops, remove listings |
| **Owner**  | Register shop, add/delete items, confirm bookings |
| **User**   | Browse deals, book items, cancel pending bookings |
