"""
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
├── manage.py          # Django Administrative CLI
├── requirements.txt   # Python Dependencies
└── README.md          # Project Documentation
"""