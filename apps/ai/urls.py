from django.urls import path
from .views import (
    ProductDescriptionView,
    ProductSEOView,
    ReviewSummaryView,
    ProductRecommendationView,
    SalesForecastView,
    AIChatSupportView,
    CategoryDescriptionView,
    StoreDescriptionView
)

urlpatterns = [
    path('generate-description/', ProductDescriptionView.as_view(), name='ai_description'),
    path('generate-seo/', ProductSEOView.as_view(), name='ai_seo'),
    path('review-summary/', ReviewSummaryView.as_view(), name='ai_review_summary'),
    path('recommendations/', ProductRecommendationView.as_view(), name='ai_recommendations'),
    path('sales-forecast/', SalesForecastView.as_view(), name='ai_sales_forecast'),
    path('chat/', AIChatSupportView.as_view(), name='ai_chat_support'),
    path('generate-category-description/', CategoryDescriptionView.as_view(), name='ai_category_description'),
    path('generate-store-description/', StoreDescriptionView.as_view(), name='ai_store_description'),
]
