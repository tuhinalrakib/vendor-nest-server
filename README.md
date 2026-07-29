<div align="center">

# 🛒 VendorNest — Multi-Vendor E-Commerce SaaS Backend API

  <p><b>Powerful, Scalable & Secure Multi-Vendor E-Commerce Backend Engine built with Django REST Framework</b></p>

  [![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
  [![DRF](https://img.shields.io/badge/Django_REST_Framework-3.17-red?style=for-the-badge&logo=django&logoColor=white)](https://www.django-rest-framework.org/)
  [![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon_DB-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech/)
  [![Google Gemini AI](https://img.shields.io/badge/Google_Gemini_AI-Integrated-8E75B2?style=for-the-badge&logo=google-gemini&logoColor=white)](https://ai.google.dev/)
  [![Render](https://img.shields.io/badge/Render-Deployed-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com/)

</div>

---

## 📌 Project Overview

**VendorNest API** is the robust core backend engine powering the VendorNest Multi-Vendor E-Commerce SaaS Platform. Built using **Django 6.0** and **Django REST Framework (DRF)**, it provides enterprise-grade REST APIs for multi-tenant vendor management, AI-assisted seller automation, product catalog management, split-order processing, secure payments (Stripe & Wise), Cloudinary media management, and automated notifications (Email/SMS).

---

## ✨ Key Features

### 🔐 Authentication & Access Control
- **JWT Authentication**: Secure stateless token authentication via `djangorestframework-simplejwt`.
- **Role-Based Access Control (RBAC)**: Fine-grained permissions for `Admin`, `Seller/Vendor`, and `Customer`.
- **Google OAuth 2.0 Integration**: One-click social login via Google Sign-In.

### 🤖 AI-Powered E-Commerce Automation
- **Google Gemini AI Integration**: Automated product description generation, SEO tag suggestions, and AI seller assistant.

### 🛍️ Vendor & Catalog Management
- **Multi-Vendor Architecture**: Isolated vendor storefronts, store profile configuration, and seller onboarding workflows.
- **Advanced Product Catalog**: Categories, subcategories, stock inventory tracking, dynamic variants, and attribute options.
- **Cloud Media Uploads**: Fast image & asset management powered by **Cloudinary**.

### 📦 Order, Shipping & Payments
- **Multi-Seller Order Splitting**: Automatic order item separation and status tracking across multiple vendors in a single checkout.
- **Payment & Automated Payouts**: Integrated with **Stripe** for payment processing and **Wise API Sandbox** for vendor payouts.
- **Shipping Engine**: Dynamic shipping method calculation and cost assignment.
- **Coupons & Discounts**: Fixed-amount and percentage-based promotional codes.

### 📧 Notifications, SMS & Asynchronous Queue
- **Email Service**: Dual configuration support for **Resend** and **Brevo (Sendinblue)**.
- **SMS Messaging**: Instant SMS notifications sent via **Twilio**.
- **Task Queue & Caching**: **Celery** background worker setup backed by **Redis**.

### 📖 Interactive API Documentation
- **Swagger UI & ReDoc**: Auto-generated interactive API specification powered by `drf-yasg`.

---

## 🛠️ Tech Stack & Dependencies

| Component | Technology |
| :--- | :--- |
| **Backend Framework** | Django 6.0 + Django REST Framework 3.17 |
| **Language** | Python 3.11+ |
| **Database** | PostgreSQL (Neon Cloud / Production) or SQLite (Dev) |
| **Authentication** | SimpleJWT + Google OAuth 2.0 |
| **Media Storage** | Cloudinary (`django-cloudinary-storage`) |
| **AI Integration** | Google Generative AI (`google-generativeai` / Gemini) |
| **Payment Gateway** | Stripe SDK + Wise API Sandbox |
| **Notifications** | Resend API / Brevo API + Twilio SMS |
| **Background Tasks** | Celery + Redis |
| **WSGI Server** | Gunicorn |
| **Static Files** | WhiteNoise |
| **API Documentation** | OpenAPI 2.0 / Swagger via `drf-yasg` |
| **Deployment Target** | Render / Railway / Docker |

---

## 📂 Project Structure

```gfm
vendor-nest-server/
├── apps/
│   ├── ai/            # Google Gemini AI services & automation endpoints
│   ├── categories/    # Product categories & subcategory management
│   ├── coupons/       # Discount codes & promotional rules engine
│   ├── dashboard/     # Admin & Vendor analytical data endpoints
│   ├── notifications/ # Email (Resend/Brevo) & Twilio SMS notification engine
│   ├── orders/        # Order management, cart & checkout logic
│   ├── payments/      # Stripe payment processing & transaction handlers
│   ├── products/      # Product catalog, inventory & variation management
│   ├── seller/        # Vendor profile onboarding, settings & Wise payouts
│   ├── shipping/      # Delivery methods & shipping cost rules
│   └── users/         # User auth, JWT, Google OAuth & RBAC rules
├── config/            # Django Project Settings
│   ├── settings/
│   │   ├── base.py       # Core configuration & installed apps
│   │   ├── local.py      # Local development settings (SQLite)
│   │   └── production.py # Production settings (PostgreSQL, CORS, Security)
│   ├── urls.py           # Master API URL Router & Swagger endpoints
│   ├── wsgi.py           # WSGI application entrypoint
│   └── celery.py         # Celery task queue configuration
├── services/          # External integrations (Cloudinary, AI, Wise, etc.)
├── build.sh           # Automated deployment script for Render
├── Dockerfile         # Production Docker container image definition
├── docker-compose.yml # Multi-container Docker orchestration (DB, Redis, Django, Celery)
├── .env.docker.example # Environment variable template for Docker deployment
├── manage.py          # Django Administrative CLI
├── requirements.txt   # Python Dependencies
└── README.md          # Project Documentation
```

---

## 🚀 Quick Start (Local Setup)

### 1. Prerequisites
- **Python**: 3.11 or higher
- **Git**
- Virtual environment tool (`venv` or `uv`)

### 2. Clone the Repository
```bash
git clone https://github.com/your-username/vendor-nest-server.git
cd vendor-nest-server
```

### 3. Create & Activate Virtual Environment
```bash
# On Windows
python -m venv .venv
.venv\Scripts\activate

# On macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Setup Environment Variables
Create a `.env` file in the root directory:

```env
# Django Core Settings
DJANGO_SECRET_KEY=your-super-secret-key-here
DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
BACKEND_URL=http://127.0.0.1:8000
FRONTEND_URL=http://localhost:3000

# Cloudinary Credentials
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Database (Neon PostgreSQL or leave blank for local SQLite)
DB_NAME=neondb
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_neon_db_host
DB_PORT=5432

# Google AI (Gemini) API Key
GEMINI_API_KEY=your_gemini_api_key

# Google OAuth 2.0
GOOGLE_CLIENT_ID=your_google_client_id

# Stripe & Wise Configuration
STRIPE_SECRET_KEY=your_stripe_secret_key
WISE_API_TOKEN=your_wise_token
WISE_PROFILE_ID=your_wise_profile_id

# Email & SMS Service Keys
RESEND_API_KEY=your_resend_key
BREVO_API_KEY=your_brevo_key
DEFAULT_FROM_EMAIL=onboarding@resend.dev
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_number

# Redis Configuration (For Celery/Cache)
REDIS_URL=redis://localhost:6379/0
```

### 6. Run Database Migrations
```bash
python manage.py migrate
```

### 7. Create Superuser (Admin Account)
```bash
python manage.py createsuperuser
```

### 8. Start Development Server
```bash
python manage.py runserver
```
The server will run at: `http://127.0.0.1:8000/`

---

## 📚 API Documentation (Swagger)

Interactive API documentation is generated automatically. Access it when the server is running:

- **Swagger UI**: [https://vendor-nest-server.onrender.com/swagger/](https://vendor-nest-server.onrender.com/swagger/)

---

## 🌐 Deployment Guide (Render)

This backend repository is configured for deployment on **Render**.

### Render Setup Checklist:
1. **Service Type**: Web Service (Python)
2. **Build Command**: `./build.sh`
3. **Start Command**: `gunicorn config.wsgi:application`
4. **Environment Variables**:
   - `DJANGO_SETTINGS_MODULE` = `config.settings.production`
   - `DJANGO_SECRET_KEY` = `<secure-secret-key>`
   - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` (Neon PostgreSQL)
   - `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
   - `GEMINI_API_KEY`, `STRIPE_SECRET_KEY`, `RESEND_API_KEY`

---

## 📄 License

This project is licensed under the **MIT License**.

---

<div align="center">
  <sub>Built with ❤️ for the <b>VendorNest</b> Multi-Vendor SaaS Ecosystem</sub>
</div>
