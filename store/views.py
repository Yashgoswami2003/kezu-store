from django.shortcuts import render
from .models import Product, Category, Feedback
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.core.cache import cache
import json

def index(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    return render(request, 'index.html', {'products': products, 'categories': categories})

def health_check(request):
    return HttpResponse("OK")

def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or 'unknown'

def _is_rate_limited(ip_addr, limit=5, window_seconds=60):
    cache_key = f"feedback_rate:{ip_addr}"
    current_count = cache.get(cache_key)
    if current_count is None:
        cache.set(cache_key, 1, timeout=window_seconds)
        return False
    if current_count >= limit:
        return True
    try:
        cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, current_count + 1, timeout=window_seconds)
    return False

@require_POST
def submit_feedback(request):
    try:
        client_ip = _get_client_ip(request)
        if _is_rate_limited(client_ip, limit=5, window_seconds=60):
            return JsonResponse(
                {'success': False, 'error': 'Too many feedback requests. Please try again after a minute.'},
                status=429
            )

        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST

        customer_name = (data.get('customer_name') or data.get('name') or '').strip()
        fragrance_name = (data.get('fragrance_name') or data.get('fragrance') or '').strip()
        message = (data.get('message') or data.get('feedback') or '').strip()
        raw_rating = data.get('rating', 5)

        try:
            rating = int(raw_rating)
            if rating < 1 or rating > 5:
                rating = 5
        except (TypeError, ValueError):
            rating = 5

        if not customer_name or not message:
            return JsonResponse(
                {'success': False, 'error': 'Please enter your name and feedback message.'},
                status=400
            )

        feedback_obj = Feedback.objects.create(
            customer_name=customer_name,
            fragrance_name=fragrance_name,
            rating=rating,
            message=message,
        )

        # Yahan baad mein chaho toh backend se client ke WhatsApp API/webhook par bhi bhej sakte ho
        # bina user ke browser ko redirect kiye.

        return JsonResponse({
            'success': True,
            'id': feedback_obj.id,
            'message': 'Thank you for your feedback!'
        })

    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'error': 'Invalid request payload.'},
            status=400
        )
    except Exception:
        return JsonResponse(
            {'success': False, 'error': 'Something went wrong while saving feedback.'},
            status=500
        )