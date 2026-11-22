from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.http import HttpResponse
from .urls import SECRET_ADMIN_SLUG


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or 'unknown'


def _send_login_alert(ip_addr, attempts, path):
    recipient = getattr(settings, 'ALERT_EMAIL_TO', '')
    if not recipient:
        return
    try:
        send_mail(
            subject='[Z++ Alert] Multiple Failed Admin Login Attempts',
            message=(
                f'Alert: {attempts} failed login attempts detected on admin login.\n'
                f'IP Address: {ip_addr}\n'
                f'Path: {path}'
            ),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None) or recipient,
            recipient_list=[recipient],
            fail_silently=True,
        )
    except Exception:
        pass


class AdminLoginProtectionMiddleware:
    """
    Blocks repeated brute-force login attempts on the secret admin login URL
    and sends an email alert after more than 3 failed attempts.
    """
    ALERT_AFTER_ATTEMPTS = 3
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_SECONDS = 900  # 15 minutes

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        login_path = f'/{SECRET_ADMIN_SLUG}/login/'
        is_login_post = request.method == 'POST' and request.path.rstrip('/') == login_path.rstrip('/')

        if is_login_post:
            ip_addr = _get_client_ip(request)
            lock_key = f'admin_login_lock:{ip_addr}'
            fail_key = f'admin_login_fail:{ip_addr}'
            alert_key = f'admin_login_alert_sent:{ip_addr}'

            if cache.get(lock_key):
                return HttpResponse(
                    'Too many failed login attempts. Try again after 15 minutes.',
                    status=429,
                    content_type='text/plain',
                )

            response = self.get_response(request)

            if response.status_code in (301, 302):
                cache.delete(fail_key)
                cache.delete(lock_key)
                cache.delete(alert_key)
            else:
                fails = cache.get(fail_key, 0) + 1

                if fails > self.ALERT_AFTER_ATTEMPTS and not cache.get(alert_key):
                    _send_login_alert(ip_addr, fails, request.path)
                    cache.set(alert_key, True, timeout=self.LOCKOUT_SECONDS)

                if fails >= self.MAX_FAILED_ATTEMPTS:
                    cache.set(lock_key, True, timeout=self.LOCKOUT_SECONDS)
                    cache.delete(fail_key)
                else:
                    cache.set(fail_key, fails, timeout=self.LOCKOUT_SECONDS)

            return response

        return self.get_response(request)