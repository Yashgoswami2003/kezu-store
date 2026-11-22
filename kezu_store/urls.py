"""
URL configuration for kezu_store project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
1. Add an import:  from my_app import views
2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
1. Add an import:  from other_app.views import Home
2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
1. Import the include() function: from django.urls import include, path
2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

SECRET_ADMIN_SLUG = 'kz-ops-9f4k2x'

def blocked_admin_decoy(request, rest=''):
    ua = (request.META.get('HTTP_USER_AGENT') or '').lower()
    is_browser = any(k in ua for k in ('mozilla', 'chrome', 'safari', 'edge', 'opera'))

    if not is_browser:
        return HttpResponse("0x00", status=404, content_type="text/plain; charset=utf-8")

    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>⚠ 0xERR_VOID</title>
<style>
  html, body {
    margin: 0; padding: 0; height: 100%;
    background: #070709; color: #ff2a4b;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    display: flex; align-items: center; justify-content: center; text-align: center;
  }
  .box { border: 1px solid #ff2a4b44; padding: 28px 36px; background: #11070b; }
  .sym { font-size: 42px; letter-spacing: 6px; margin-bottom: 10px; }
  .code { font-size: 14px; color: #ff8a9b; letter-spacing: 2px; }
  .timer { margin-top: 16px; font-size: 13px; color: #9ca3af; }
  body.purged { background: #000; }
  body.purged .box { display: none; }
</style>
</head>
<body>
  <div class="box">
    <div class="sym">☠ [ 0x4F-NULL // ⊘ ] ☠</div>
    <div class="code">SIGNAL_SEVERED :: NO_ROUTE_ARTIFACT</div>
    <div class="timer">WINDOW PURGE IN <span id="sec">60</span>s</div>
  </div>
  <script>
    let left = 60;
    const el = document.getElementById('sec');
    const iv = setInterval(() => {
      left -= 1;
      if (el) el.textContent = Math.max(0, left);
      if (left <= 0) {
        clearInterval(iv);
        document.body.classList.add('purged');
        try { window.close(); } catch (e) {}
      }
    }, 1000);
  </script>
</body>
</html>"""
    return HttpResponse(html, status=404, content_type="text/html; charset=utf-8")

urlpatterns = [
    path('admin/', blocked_admin_decoy),
    path('admin/<path:rest>', blocked_admin_decoy),
    path(f'{SECRET_ADMIN_SLUG}/', admin.site.urls),
    path('', include('store.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)