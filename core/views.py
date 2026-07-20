from django.http import JsonResponse

# Create your views here.
def home(request):
    return JsonResponse({
        "message": "Vendor-Nest Server API is running 🚀"
    })