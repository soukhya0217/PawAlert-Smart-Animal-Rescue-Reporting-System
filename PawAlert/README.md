# 🐾 PawAlert — Street Animal Help Platform

A full-stack web platform to report injured or abandoned street animals and connect them with nearby volunteers, NGOs, and veterinarians.

\---

## 🗂 Project Structure

```
PawAlert/
├── backend/
│   ├── app.py              ← Flask REST API
│   ├── requirements.txt    ← Python packages
│   ├── .env.example        ← Environment variable template
│   └── .env                ← Your actual config (auto-created by start.bat)
├── frontend/
│   ├── style.css           ← Shared CSS for all pages
│   ├── login.html          ← Customer Login \& Register
│   ├── admin-login.html    ← Admin Login
│   ├── index.html          ← Main App (Report, Dashboard, Volunteer, Contact)
│   └── admin.html          ← Admin Panel (Manage Reports \& Volunteers)
├── start.bat               ← One-click setup \& launcher (Windows)
└── README.md               ← This file
```

\---

## ⚡ Quick Start (Windows)

1. Install the prerequisites (see below)
2. Double-click **`start.bat`**
3. The browser will open automatically at `frontend/login.html`

\---

## 📋 Prerequisites

### 1\. Python 3.8+

Download from https://www.python.org/downloads/  
**Important:** Check ✅ "Add Python to PATH" during installation.

Verify: `python --version`

### 2\. MongoDB Community Server

Download from https://www.mongodb.com/try/download/community  
Install and run as a **Windows Service** (recommended — it starts automatically).

Verify: `mongod --version`

### 3\. pip (comes with Python)

Verify: `pip --version`

\---

## 🔧 Manual Setup (if start.bat doesn't work)

```bash
# 1. Install Python packages
pip install -r backend/requirements.txt

# 2. Copy environment file
copy backend\\.env.example backend\\.env

# 3. Start MongoDB (if not running as a service)
mongod --dbpath data/db

# 4. Start the backend
cd backend
python app.py

# 5. Open frontend/login.html in your browser
```

\---

## 🔑 Default Credentials

|Role|Username|Password|
|-|-|-|
|Admin|`admin`|`Admin@123`|
|User|Register a new account on the Login page||

To change admin credentials, edit `backend/.env`:

```
ADMIN\_USERNAME=admin
ADMIN\_PASSWORD=Admin@123
```

\---

## 🌐 API Endpoints

|Method|Endpoint|Auth|Description|
|-|-|-|-|
|GET|/api/health|None|Health check|
|POST|/api/auth/register|None|Register new user|
|POST|/api/auth/login|None|User login|
|POST|/api/auth/admin-login|None|Admin login|
|GET|/api/reports|None|Get all reports|
|POST|/api/reports|User JWT|Create new report|
|PUT|/api/reports/:id|Admin JWT|Update report|
|DELETE|/api/reports/:id|Admin JWT|Delete report|
|GET|/api/my-reports|User JWT|Get user's own reports|
|GET|/api/volunteers|None|Get all volunteers|
|POST|/api/volunteers|None|Register as volunteer|
|DELETE|/api/volunteers/:id|Admin JWT|Remove volunteer|
|GET|/api/admin/stats|Admin JWT|Get dashboard stats|

\---

## ✅ Validation Rules

* **Phone number**: Exactly 10 digits, numbers only
* **Password**: Minimum 6 characters
* **Email**: Must contain @ and a domain
* **Animal types**: Dog, Cat, Cow, Bird, Other
* **Help types**: Rescue, Medical, Food

\---

## 🔒 Security

* Passwords are hashed using **bcrypt** (never stored in plain text)
* Sessions managed with **JWT tokens** (7-day expiry for users, 8-hour for admin)
* All protected routes verify the JWT before processing
* Admin routes require `is\_admin: true` in the token

\---

## 🚀 Deploying to Production

For production deployment:

1. Set a strong `SECRET\_KEY` in `.env`
2. Use a production WSGI server: `gunicorn -w 4 app:app`
3. Use MongoDB Atlas (cloud) instead of localhost
4. Serve frontend via Nginx or a static host (Netlify, Vercel)
5. Add Google Maps API key for live location pins
6. Integrate an email service (e.g., SendGrid) for rescue alerts

\---

## 🆘 Emergency Helplines (India)

|Organisation|Contact|
|-|-|
|Animal Welfare Board (All India)|1800-180-5236|
|CUPA — Bengaluru|+91 98450 99817|
|BSPCA — Mumbai|+91 22 2417 6086|
|Friendicoes — Delhi|+91 11 2634 6622|
|Blue Cross — Chennai|+91 44 2235 1001|

\---

## 🛠 Tech Stack

|Layer|Technology|
|-|-|
|Frontend|HTML5, CSS3, Vanilla JS|
|Backend|Python 3, Flask|
|Database|MongoDB (via PyMongo)|
|Auth|JWT + bcrypt|
|Dev Tools|python-dotenv, flask-cors|

\---

Built with ❤️ for street animals across India.

