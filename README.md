# Mobile Accessories Shop

A Flask web application for browsing mobile accessories, user signup/login, product booking, order history, and an admin product dashboard.

## Features
- User signup and login
- Product listing
- Booking / checkout flow
- Order history
- Admin dashboard for product management
- Email booking confirmation (SMTP configuration required)

## Setup (Windows)

1. Install Python 3.10+.
2. Open this project folder in VS Code.
3. In the terminal run:

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

4. Set environment variables in your terminal (or create a local `.env` and load it with a dotenv package if you choose to add one):

```bat
set SECRET_KEY=replace-with-a-long-random-secret
set ADMIN_USERNAME=admin
set ADMIN_PASSWORD=replace-with-a-strong-admin-password
set MAIL_USERNAME=your-email@gmail.com
set MAIL_PASSWORD=your-gmail-app-password
set MAIL_DEFAULT_SENDER=your-email@gmail.com
```

5. Run:

```bat
python app.py
```

Open http://127.0.0.1:5000

## Important
- Never commit email app passwords, secret keys, or real customer database files.
- The database is created locally when the app runs.
- Configure the environment variables before using admin login or email functionality.
