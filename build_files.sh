#!/usr/bin/env bash
echo "Building VendorNest on Vercel..."
python3 -m pip install -r requirements.txt
python3 manage.py collectstatic --no-input --clear
echo "Static files collected successfully!"
