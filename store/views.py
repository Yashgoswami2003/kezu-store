from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.utils import timezone
from .models import Product, Category, Feedback, FeedbackComment
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.core.cache import cache
import json
import os
import urllib.request
import urllib.parse
import uuid


def _has_owner_privilege(request, data=None):
    if request.user.is_authenticated and (
        request.user.is_staff
        or request.user.is_superuser
        or getattr(request.user, 'username', '') == 'Aksh924'
    ):
        return True
    configured_secret = getattr(settings, 'FEEDBACK_OWNER_SECRET', '') or os.environ.get('FEEDBACK_OWNER_SECRET', '')
    provided_secret = ''
    if isinstance(data, dict):
        provided_secret = (data.get('owner_secret') or data.get('owner_key') or '').strip()
    if not provided_secret:
        provided_secret = (request.headers.get('X-Owner-Secret') or '').strip()
    if configured_secret and provided_secret and provided_secret == configured_secret:
        return True
    return False


def _is_feedback_author(request, feedback_obj, provided_token=''):
    if request.user.is_authenticated and getattr(feedback_obj, 'user_id', None) == request.user.id:
        return True
    if _is_valid_uuid(provided_token) and str(feedback_obj.owner_token) == provided_token:
        return True
    return False


def _is_comment_author(request, comment_obj, provided_token=''):
    if request.user.is_authenticated and getattr(comment_obj, 'user_id', None) == request.user.id:
        return True
    if _is_valid_uuid(provided_token) and str(comment_obj.owner_token) == provided_token:
        return True
    return False


def _notify_owner_whatsapp(feedback_obj):
    webhook_url = getattr(settings, 'OWNER_WHATSAPP_WEBHOOK_URL', '') or os.environ.get('OWNER_WHATSAPP_WEBHOOK_URL', '')
    owner_phone = getattr(settings, 'OWNER_WHATSAPP_NUMBER', '') or os.environ.get('OWNER_WHATSAPP_NUMBER', '')
    if not webhook_url and not owner_phone:
        return

    fragrance_part = f"\nFragrance: {feedback_obj.fragrance_name}" if feedback_obj.fragrance_name else ""
    alert_text = (
        f"New Feedback on KEZU & Co.\n"
        f"Name: {feedback_obj.customer_name}\n"
        f"Rating: {feedback_obj.rating}/5"
        f"{fragrance_part}\n"
        f"Message: {feedback_obj.message}"
    )

    try:
        if webhook_url:
            payload = json.dumps({
                'phone': owner_phone,
                'message': alert_text,
                'feedback_id': feedback_obj.id,
            }).encode('utf-8')
            req = urllib.request.Request(
                webhook_url,
                data=payload,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=4):
                pass
        elif owner_phone:
            # Optional CallMeBot / SMS-WhatsApp gateway pattern if OWNER_WHATSAPP_API_TEMPLATE is set
            api_template = getattr(settings, 'OWNER_WHATSAPP_API_TEMPLATE', '') or os.environ.get('OWNER_WHATSAPP_API_TEMPLATE', '')
            if api_template:
                target_url = api_template.format(
                    phone=urllib.parse.quote(owner_phone),
                    text=urllib.parse.quote(alert_text),
                )
                with urllib.request.urlopen(target_url, timeout=4):
                    pass
    except Exception:
        # WhatsApp notification failure should never block feedback creation
        pass


def _serialize_comment(comment_obj):
    return {
        'id': comment_obj.id,
        'author_name': 'Owner' if comment_obj.is_owner_reply else comment_obj.author_name,
        'rating': getattr(comment_obj, 'rating', 5),
        'is_owner_reply': comment_obj.is_owner_reply,
        'prevent_user_delete': bool(getattr(comment_obj, 'prevent_user_delete', False)),
        'comment_text': comment_obj.comment_text,
        'owner_token': str(comment_obj.owner_token),
        'created_at': timezone.localtime(comment_obj.created_at).strftime('%d %b %Y, %I:%M %p'),
    }


def _serialize_feedback(feedback_obj):
    comments_qs = feedback_obj.comments.order_by('created_at')
    return {
        'id': feedback_obj.id,
        'customer_name': feedback_obj.customer_name,
        'fragrance_name': feedback_obj.fragrance_name,
        'rating': feedback_obj.rating,
        'message': feedback_obj.message,
        'owner_reply': getattr(feedback_obj, 'owner_reply', '') or '',
        'owner_replied_at': (
            timezone.localtime(feedback_obj.owner_replied_at).strftime('%d %b %Y, %I:%M %p')
            if getattr(feedback_obj, 'owner_replied_at', None)
            else ''
        ),
        'likes_count': feedback_obj.likes_count,
        'dislikes_count': feedback_obj.dislikes_count,
        'owner_token': str(feedback_obj.owner_token),
        'is_public': feedback_obj.is_public,
        'created_at': timezone.localtime(feedback_obj.created_at).strftime('%d %b %Y, %I:%M %p'),
        'comments': [_serialize_comment(c) for c in comments_qs],
    }


def _parse_request_data(request):
    if request.content_type and 'application/json' in request.content_type:
        return json.loads(request.body.decode('utf-8') or '{}')
    return request.POST


def _is_valid_uuid(value):
    if not value:
        return False
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


def index(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    feedbacks_qs = Feedback.objects.filter(is_public=True).prefetch_related('comments').order_by('-created_at')
    feedbacks_data = [_serialize_feedback(fb) for fb in feedbacks_qs]
    is_owner_session = bool(
        request.user.is_authenticated
        and (
            request.user.is_staff
            or request.user.is_superuser
            or getattr(request.user, 'username', '') == 'Aksh924'
        )
    )
    return render(request, 'index.html', {
        'products': products,
        'categories': categories,
        'feedbacks': feedbacks_qs,
        'feedbacks_json': json.dumps(feedbacks_data),
        'is_owner_session': is_owner_session,
    })


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

        data = _parse_request_data(request)

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
            user=request.user if request.user.is_authenticated else None,
            customer_name=customer_name,
            fragrance_name=fragrance_name,
            rating=rating,
            message=message,
            is_public=True,
        )

        # Backend se owner ke WhatsApp webhook/API par alert bhejna (bina browser redirect ke)
        _notify_owner_whatsapp(feedback_obj)

        return JsonResponse({
            'success': True,
            'id': feedback_obj.id,
            'owner_token': str(feedback_obj.owner_token),
            'feedback': _serialize_feedback(feedback_obj),
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


@require_POST
def feedback_react(request, feedback_id):
    try:
        feedback_obj = get_object_or_404(Feedback, id=feedback_id, is_public=True)
        data = _parse_request_data(request)
        action = (data.get('action') or '').strip().lower()
        previous_action = (data.get('previous_action') or '').strip().lower()

        if action not in ('like', 'dislike', 'clear'):
            return JsonResponse({'success': False, 'error': 'Invalid reaction action.'}, status=400)

        if previous_action == 'like' and feedback_obj.likes_count > 0:
            feedback_obj.likes_count -= 1
        elif previous_action == 'dislike' and feedback_obj.dislikes_count > 0:
            feedback_obj.dislikes_count -= 1

        if action == 'like':
            feedback_obj.likes_count += 1
        elif action == 'dislike':
            feedback_obj.dislikes_count += 1

        feedback_obj.save(update_fields=['likes_count', 'dislikes_count'])

        return JsonResponse({
            'success': True,
            'id': feedback_obj.id,
            'likes_count': feedback_obj.likes_count,
            'dislikes_count': feedback_obj.dislikes_count,
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request payload.'}, status=400)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Could not update reaction.'}, status=500)


@require_POST
def add_feedback_comment(request, feedback_id):
    try:
        feedback_obj = get_object_or_404(Feedback, id=feedback_id, is_public=True)
        data = _parse_request_data(request)

        raw_author = (data.get('author_name') or data.get('name') or 'Guest').strip() or 'Guest'
        comment_text = (data.get('comment_text') or data.get('comment') or '').strip()
        raw_rating = data.get('rating', 5)
        try:
            comment_rating = int(raw_rating)
            if comment_rating < 1 or comment_rating > 5:
                comment_rating = 5
        except (TypeError, ValueError):
            comment_rating = 5

        requested_owner = bool(data.get('is_owner_reply', False))
        is_owner_reply = requested_owner and _has_owner_privilege(request, data)
        author_name = 'Owner' if is_owner_reply else raw_author

        if not comment_text:
            return JsonResponse({'success': False, 'error': 'Please enter a comment.'}, status=400)

        comment_obj = FeedbackComment.objects.create(
            feedback=feedback_obj,
            user=request.user if request.user.is_authenticated else None,
            author_name=author_name,
            rating=comment_rating,
            is_owner_reply=is_owner_reply,
            prevent_user_delete=is_owner_reply,
            comment_text=comment_text,
        )

        if is_owner_reply and bool(data.get('update_feedback_reply', False)):
            feedback_obj.owner_reply = comment_text
            feedback_obj.owner_replied_at = timezone.now()
            feedback_obj.save(update_fields=['owner_reply', 'owner_replied_at'])

        return JsonResponse({
            'success': True,
            'comment': _serialize_comment(comment_obj),
            'feedback': _serialize_feedback(feedback_obj),
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request payload.'}, status=400)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Could not add comment.'}, status=500)


@require_POST
def delete_feedback_comment(request, comment_id):
    try:
        comment_obj = get_object_or_404(FeedbackComment, id=comment_id)
        data = _parse_request_data(request)
        provided_token = (data.get('owner_token') or request.headers.get('X-Owner-Token') or '').strip()
        is_store_owner = _has_owner_privilege(request, data)

        if not is_store_owner and getattr(comment_obj, 'prevent_user_delete', False):
            return JsonResponse(
                {'success': False, 'error': 'Users are not allowed to delete this comment.'},
                status=403
            )

        if not is_store_owner and not _is_comment_author(request, comment_obj, provided_token):
            return JsonResponse(
                {'success': False, 'error': 'You are not allowed to delete this comment.'},
                status=403
            )

        comment_obj.delete()
        return JsonResponse({'success': True, 'deleted_id': comment_id})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request payload.'}, status=400)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Could not delete comment.'}, status=500)


@require_POST
def delete_feedback(request, feedback_id):
    try:
        feedback_obj = get_object_or_404(Feedback, id=feedback_id)
        data = _parse_request_data(request)
        provided_token = (data.get('owner_token') or request.headers.get('X-Owner-Token') or '').strip()
        is_store_owner = _has_owner_privilege(request, data)

        if not is_store_owner and not _is_feedback_author(request, feedback_obj, provided_token):
            return JsonResponse(
                {'success': False, 'error': 'Only the owner or the user who created this feedback can delete it.'},
                status=403
            )

        feedback_obj.delete()
        return JsonResponse({'success': True, 'deleted_id': feedback_id})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request payload.'}, status=400)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Could not delete feedback.'}, status=500)