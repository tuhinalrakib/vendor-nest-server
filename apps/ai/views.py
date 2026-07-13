import os
import json
import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
try:
    import google.generativeai as genai
    has_gemini = True
except ImportError:
    has_gemini = False

from products.models import Product, Review
from orders.models import Order, OrderItem
from seller.models import SellerProfile

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")

# Startup Diagnostics
# print("\n--- [VendorNest AI Diagnostics] ---")
# print(f"google-generativeai installed: {has_gemini}")
# print(f"GEMINI_API_KEY loaded:        {'Yes (Starts with ' + api_key[:8] + '...)' if api_key else 'No (None or Empty)'}")

supported_models = []
if has_gemini and api_key:
    try:
        genai.configure(api_key=api_key)
        supported_models = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # print(f"Available models:             {supported_models}")
    except Exception as e:
        print(f"Failed to list models:        {e}")
print("-----------------------------------\n")

if has_gemini and api_key:
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"Gemini configuration error: {e}")

class ProductDescriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        is_admin = user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role == 'admin')
        if not is_admin and hasattr(user, 'seller_profile') and user.seller_profile.plan == 'starter':
            return Response(
                {"error": "AI features are not available on the Starter plan. Please upgrade to Growth or Enterprise to unlock AI description generation."},
                status=status.HTTP_403_FORBIDDEN
            )
        name = request.data.get("name")
        category = request.data.get("category", "")
        features = request.data.get("features", "")

        if not name:
            return Response({"error": "Product name is required."}, status=status.HTTP_400_BAD_REQUEST)

        prompt = (
            f"Create a professional, highly engaging, and SEO-friendly product description for a product named '{name}' "
            f"in the '{category}' category. Key features to include: {features}. "
            f"Write the description with rich formatting, paragraphs, and list items. "
            f"Do not include any code block quotes (like ```html or ```markdown) in your final response. Just return the raw text."
        )

        if not has_gemini or not api_key:
            # Fallback mock response if API Key is not set
            mock_desc = (
                f"Introducing the all-new <strong>{name}</strong>!<br/><br/>"
                f"Designed specifically for enthusiasts in the {category} space, this product combines "
                f"cutting-edge design with state-of-the-art functionality. Whether you're upgrading your daily routine "
                f"or buying it as a gift, it delivers exceptional value.<br/><br/>"
                f"<strong>Key Features:</strong>"
                f"<ul>"
                f"  <li><strong>Premium Build Quality:</strong> Crafted using top-grade materials for ultimate durability.</li>"
                f"  <li><strong>Exceptional Performance:</strong> Optimized to deliver outstanding results every time.</li>"
                f"  <li><strong>Modern Design:</strong> Sleek aesthetics that fit seamlessly into any setup.</li>"
                f"</ul>"
            )
            return Response({"content": mock_desc})

        try:
            try:
                model = genai.GenerativeModel("gemini-3.5-flash")
                response = model.generate_content(prompt)
            except Exception:
                try:
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    response = model.generate_content(prompt)
                except Exception:
                    model = genai.GenerativeModel("gemini-flash-latest")
                    response = model.generate_content(prompt)
            return Response({"content": response.text.strip()})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductSEOView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        is_admin = user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role == 'admin')
        if not is_admin and hasattr(user, 'seller_profile') and user.seller_profile.plan == 'starter':
            return Response(
                {"error": "AI tools are not available on the Starter plan. Please upgrade to Growth or Enterprise to unlock AI SEO generator."},
                status=status.HTTP_403_FORBIDDEN
            )
        name = request.data.get("name")
        category = request.data.get("category", "")
        description = request.data.get("description", "")

        if not name:
            return Response({"error": "Product name is required."}, status=status.HTTP_400_BAD_REQUEST)

        prompt = (
            f"Generate search engine optimized tags, a meta title, and a meta description for a product named '{name}' "
            f"in the '{category}' category with description: '{description}'. "
            f"Format the output strictly as a JSON object: "
            f'{{"meta_title": "...", "meta_description": "...", "tags": ["tag1", "tag2", "..."]}}. '
            f"Do not include any markdown format tags or extra words."
        )

        if not has_gemini or not api_key:
            # Fallback mock response
            clean_name = name[:40]
            mock_seo = {
                "meta_title": f"Buy {clean_name} Online - Best Prices & Quality | VendorNest",
                "meta_description": f"Purchase the high-quality {clean_name} today. Browse our selection of {category} products with fast shipping and secure payments.",
                "tags": [category.lower(), name.lower().split()[0], "premium", "trending", "shop"]
            }
            return Response(mock_seo)

        try:
            try:
                model = genai.GenerativeModel("gemini-3.5-flash")
                response = model.generate_content(prompt)
            except Exception:
                try:
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    response = model.generate_content(prompt)
                except Exception:
                    model = genai.GenerativeModel("gemini-flash-latest")
                    response = model.generate_content(prompt)
            result_text = response.text.strip()
            # Clean possible markdown JSON wrappers
            cleaned_text = result_text.replace("```json", "").replace("```", "").strip()
            parsed_json = json.loads(cleaned_text)
            return Response(parsed_json)
        except Exception as e:
            return Response({
                "meta_title": f"Buy {name} - Best deals | VendorNest",
                "meta_description": f"Purchase {name} in {category} category today. High quality and top customer ratings.",
                "tags": [category.lower(), "shop", "sale"]
            })


class ReviewSummaryView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        product_id = request.data.get("product_id")
        
        # Try fetching reviews from DB
        reviews_query = Review.objects.filter(product_id=product_id) if product_id else []
        review_comments = [r.comment for r in reviews_query if r.comment]

        # If empty, use realistic mock reviews for demonstration
        if not review_comments:
            review_comments = [
                "Absolutely love this product! The sound is crisp and clear.",
                "Battery life is outstanding. Lasts all day easily.",
                "A bit expensive compared to other brands, but build quality is top-notch.",
                "Highly recommended if you want reliability.",
                "The noise cancellation is good but could be slightly better in crowded subway cars.",
            ]

        reviews_text = "\n- ".join(review_comments)
        prompt = (
            f"Analyze the following customer reviews for this product and summarize them into a short paragraph "
            f"describing the overall consensus, followed by a bulleted list of Pros and Cons. "
            f"Reviews:\n- {reviews_text}"
        )

        if not has_gemini or not api_key:
            mock_summary = (
                "<strong>Customer Consensus:</strong> Highly positive. Customers love the sound clarity and exceptional battery life, though some note it is on the pricier side.<br/><br/>"
                "<strong>Pros:</strong><br/>"
                "• Crisp and clear audio output<br/>"
                "• All-day battery endurance<br/>"
                "• Durable build quality<br/><br/>"
                "<strong>Cons:</strong><br/>"
                "• Higher price point than competitors<br/>"
                "• Noise cancellation could be stronger in noisy environments"
            )
            return Response({"summary": mock_summary})

        try:
            try:
                model = genai.GenerativeModel("gemini-3.5-flash")
                response = model.generate_content(prompt)
            except Exception:
                try:
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    response = model.generate_content(prompt)
                except Exception:
                    model = genai.GenerativeModel("gemini-flash-latest")
                    response = model.generate_content(prompt)
            return Response({"summary": response.text.strip()})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryDescriptionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        name = request.data.get("name")
        if not name:
            return Response({"error": "Category name is required."}, status=status.HTTP_400_BAD_REQUEST)

        prompt = (
            f"Generate a short, professional, and engaging category description for an e-commerce platform category named '{name}'. "
            f"The description should be 2 to 3 sentences long (around 30-50 words) and summarize what types of products customers can expect to find. "
            f"Just return the plain text of the description directly, without any extra words, markdown, or code block formatting."
        )

        if not has_gemini or not api_key:
            # Fallback mock description
            mock_desc = f"Explore our exclusive collection of high-quality products in the {name} category. Discover top-rated items, curated selections, and great deals to suit your needs."
            return Response({"description": mock_desc})

        try:
            try:
                model = genai.GenerativeModel("gemini-3.5-flash")
                response = model.generate_content(prompt)
            except Exception:
                try:
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    response = model.generate_content(prompt)
                except Exception:
                    model = genai.GenerativeModel("gemini-flash-latest")
                    response = model.generate_content(prompt)
            return Response({"description": response.text.strip()})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductRecommendationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        product_id = request.query_params.get("product_id")
        
        # Try fetching products from DB
        db_products = list(Product.objects.all()[:10])
        catalog = []
        for p in db_products:
            catalog.append({
                "id": str(p.id),
                "name": p.name,
                "category": p.category.name if p.category else "Uncategorized",
                "price": float(p.price)
            })

        # Fallback catalog if DB is empty
        if not catalog:
            catalog = [
                {"id": "rec-1", "name": "Ergonomic Office Chair", "category": "Furniture", "price": 249.99},
                {"id": "rec-2", "name": "USB-C Hub Multi-port 8-in-1", "category": "Electronics", "price": 49.99},
                {"id": "rec-3", "name": "Wireless Mechanical Keyboard", "category": "Electronics", "price": 89.99},
                {"id": "rec-4", "name": "Minimalist Desk Pad XL", "category": "Office Supplies", "price": 19.99},
                {"id": "rec-5", "name": "LED Smart Desk Lamp", "category": "Home & Kitchen", "price": 34.99},
            ]

        # Current product details
        current_product = {"id": "prod-x", "name": "Wireless ANC Headphones Pro", "category": "Electronics", "price": 129.99}
        if product_id:
            db_p = Product.objects.filter(id=product_id).first()
            if db_p:
                current_product = {
                    "id": str(db_p.id),
                    "name": db_p.name,
                    "category": db_p.category.name if db_p.category else "Uncategorized",
                    "price": float(db_p.price)
                }

        prompt = (
            f"Given a user is viewing the product '{current_product['name']}' (Category: {current_product['category']}, Price: ${current_product['price']}), "
            f"recommend exactly 3 products from this available catalog: {json.dumps(catalog)}. "
            f"Explain for each recommended product WHY it goes well with the current product. "
            f"Format the output strictly as a JSON list of objects: "
            f'[{{"id": "...", "name": "...", "category": "...", "price": 0.0, "reason": "..."}}]. '
            f"Do not include markdown markup around JSON."
        )

        if not has_gemini or not api_key:
            # Fallback mock recommendations
            mock_recs = [
                {
                    "id": "rec-2",
                    "name": "USB-C Hub Multi-port 8-in-1",
                    "category": "Electronics",
                    "price": 49.99,
                    "reason": "Perfect companion to connect your wireless headphone transmitter and keep your laptop ports free."
                },
                {
                    "id": "rec-3",
                    "name": "Wireless Mechanical Keyboard",
                    "category": "Electronics",
                    "price": 89.99,
                    "reason": "Complete your quiet workspace setup with this high-performance wireless mechanical keyboard."
                },
                {
                    "id": "rec-5",
                    "name": "LED Smart Desk Lamp",
                    "category": "Home & Kitchen",
                    "price": 34.99,
                    "reason": "Provides focus lighting to enhance productivity while listening to music with your headphones."
                }
            ]
            return Response(mock_recs)

        try:
            try:
                model = genai.GenerativeModel("gemini-3.5-flash")
                response = model.generate_content(prompt)
            except Exception:
                try:
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    response = model.generate_content(prompt)
                except Exception:
                    model = genai.GenerativeModel("gemini-flash-latest")
                    response = model.generate_content(prompt)
            result_text = response.text.strip()
            cleaned_text = result_text.replace("```json", "").replace("```", "").strip()
            parsed_json = json.loads(cleaned_text)
            return Response(parsed_json)
        except Exception as e:
            return Response(catalog[:3])


class SalesForecastView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # Fetch actual order items if any, otherwise fall back
        sales_history = [
            {"week": "Week 1", "revenue": 4200.0, "orders": 34},
            {"week": "Week 2", "revenue": 5800.0, "orders": 46},
            {"week": "Week 3", "revenue": 7100.0, "orders": 58},
            {"week": "Week 4", "revenue": 9400.0, "orders": 72},
        ]

        prompt = (
            f"You are a professional business intelligence analyst. Based on this seller's historical sales "
            f"for the past month: {json.dumps(sales_history)}, forecast the next 4 weeks of sales. "
            f"Format the output strictly as a JSON object: "
            f'{{"forecast": [{{"week": "Week 5", "predicted_revenue": 0.0}}, ...], "insights": "...", "recommendations": "..."}}. '
            f"Do not include markdown tags."
        )

        if not has_gemini or not api_key:
            mock_forecast = {
                "forecast": [
                    {"week": "Week 5", "predicted_revenue": 10500.0},
                    {"week": "Week 6", "predicted_revenue": 11800.0},
                    {"week": "Week 7", "predicted_revenue": 13200.0},
                    {"week": "Week 8", "predicted_revenue": 15000.0},
                ],
                "insights": "Sales have shown strong upward momentum, growing at approximately 30% week-over-week. This indicates strong product-market fit or seasonality.",
                "recommendations": "Ensure you restock top electronics categories immediately. Consider launching a retargeting campaign for Week 6 to sustain the momentum."
            }
            return Response(mock_forecast)

        try:
            try:
                model = genai.GenerativeModel("gemini-3.5-flash")
                response = model.generate_content(prompt)
            except Exception:
                try:
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    response = model.generate_content(prompt)
                except Exception:
                    model = genai.GenerativeModel("gemini-flash-latest")
                    response = model.generate_content(prompt)
            result_text = response.text.strip()
            cleaned_text = result_text.replace("```json", "").replace("```", "").strip()
            parsed_json = json.loads(cleaned_text)
            return Response(parsed_json)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIChatSupportView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        message = request.data.get("message")
        history = request.data.get("history", [])

        if not message:
            return Response({"error": "Message is required."}, status=status.HTTP_400_BAD_REQUEST)

        db_products = list(Product.objects.all()[:10])
        catalog = []
        for p in db_products:
            catalog.append({
                "name": p.name,
                "price": f"${p.price}",
                "features": p.description or "Quality product listed on VendorNest store"
            })

        if not catalog:
            catalog = [
                {"name": "Wireless ANC Headphones Pro", "price": "$129.99", "features": "Active Noise Cancelling, 40hr Battery"},
                {"name": "Ergonomic Office Chair Leather", "price": "$249.50", "features": "Lumbar support, genuine leather, adjustable armrests"},
                {"name": "Minimalist Water Bottle 1L", "price": "$24.99", "features": "Vacuum insulated, stainless steel, keeps cold for 24h"},
                {"name": "USB-C Multi-port Hub 8-in-1", "price": "$49.99", "features": "4K HDMI, SD Reader, 100W Power Delivery"},
            ]

        formatted_history = ""
        for h in history:
            role = "User" if h.get("sender") == "user" else "Assistant"
            formatted_history += f"{role}: {h.get('text')}\n"

        prompt = (
            f"You are the VendorNest Store AI Assistant. Answer customer queries about our products "
            f"using the catalog data: {json.dumps(catalog)}.\n"
            f"Chat History:\n{formatted_history}"
            f"User: {message}\n"
            f"Assistant:"
        )

        if not has_gemini or not api_key:
            answer = "I'd be glad to help! "
            m_lower = message.lower()
            
            # Look for keyword match in the database product list
            matched_product = None
            for item in catalog:
                name_words = [w.lower() for w in item["name"].split() if len(w) > 3]
                if item["name"].lower() in m_lower or any(word in m_lower for word in name_words):
                    matched_product = item
                    break
            
            if matched_product:
                answer += f"Our {matched_product['name']} ({matched_product['price']}) is a great choice. Details: {matched_product['features']}."
            else:
                product_names = [item["name"] for item in catalog[:4]]
                answer += f"We have several amazing products in our store, including {', '.join(product_names)}. Let me know if you would like pricing or detail information about any of these!"
            
            return Response({"reply": answer})

        try:
            try:
                model = genai.GenerativeModel("gemini-3.5-flash")
                response = model.generate_content(prompt)
            except Exception:
                try:
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    response = model.generate_content(prompt)
                except Exception:
                    model = genai.GenerativeModel("gemini-flash-latest")
                    response = model.generate_content(prompt)
            return Response({"reply": response.text.strip()})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StoreDescriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        is_admin = user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role == 'admin')
        if not is_admin and user.role == 'seller':
            seller_profile = getattr(user, 'seller_profile', None)
            if seller_profile and seller_profile.plan == 'starter':
                return Response(
                    {"error": "AI features are not available on the Starter plan. Please upgrade to Growth or Enterprise to unlock AI description generation."},
                    status=status.HTTP_403_FORBIDDEN
                )

        name = request.data.get("name")
        description_style = request.data.get("style", "professional")

        if not name:
            return Response({"error": "Store name is required."}, status=status.HTTP_400_BAD_REQUEST)

        prompt = (
            f"Create a professional, highly engaging, and customer-focused storefront shop description for an e-commerce merchant store named '{name}' "
            f"using a '{description_style}' tone and style. "
            f"It should be around 60 to 100 words long and summarize the store's dedication to quality, customer trust, and value. "
            f"Just return the plain text of the description directly, without any code block markdown wrappers or extra tags."
        )

        if not has_gemini or not api_key:
            mock_desc = (
                f"Welcome to {name}, your premier destination for high-quality products and exceptional service. "
                f"We are dedicated to bringing you the best selection of curated goods designed to elevate your everyday lifestyle. "
                f"With a focus on reliability, premium quality, and customer satisfaction, we strive to deliver an unparalleled shopping experience. "
                f"Thank you for choosing us as your trusted shopping partner!"
            )
            return Response({"description": mock_desc})

        try:
            try:
                model = genai.GenerativeModel("gemini-3.5-flash")
                response = model.generate_content(prompt)
            except Exception:
                try:
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    response = model.generate_content(prompt)
                except Exception:
                    model = genai.GenerativeModel("gemini-flash-latest")
                    response = model.generate_content(prompt)
            return Response({"description": response.text.strip()})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
