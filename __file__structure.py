"""
 * backend/
│
├── config/
│   ├── settings/
│   │     ├── base.py
│   │     ├── local.py
│   │     ├── production.py
│   │     └── __init__.py
│   │
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── celery.py
│
├── apps/
│
│   ├── authentication/
│   │      ├── models.py
│   │      ├── serializers.py
│   │      ├── views.py
│   │      ├── urls.py
│   │      ├── permissions.py
│   │      ├── services.py
│   │      └── tests.py
│
│   ├── users/
│   │
│   ├── sellers/
│   │
│   ├── categories/
│   │
│   ├── brands/
│   │
│   ├── products/
│   │
│   ├── product_images/
│   │
│   ├── inventory/
│   │
│   ├── cart/
│   │
│   ├── wishlist/
│   │
│   ├── coupons/
│   │
│   ├── checkout/
│   │
│   ├── orders/
│   │
│   ├── payments/
│   │
│   ├── shipping/
│   │
│   ├── reviews/
│   │
│   ├── notifications/
│   │
│   ├── analytics/
│   │
│   ├── ai/
│   │
│   └── dashboard/
│
├── common/
│   ├── permissions.py
│   ├── pagination.py
│   ├── utils.py
│   ├── constants.py
│   ├── validators.py
│   ├── exceptions.py
│   ├── middleware.py
│   └── responses.py
│
├── services/
│   ├── cloudinary_service.py
│   ├── stripe_service.py
│   ├── email_service.py
│   ├── redis_service.py
│   ├── ai_service.py
│   └── jwt_service.py
│
├── media/
│
├── static/
│
├── templates/
│
├── requirements.txt
├── manage.py
├── Dockerfile
├── docker-compose.yml
├── .env
└── README.md
"""