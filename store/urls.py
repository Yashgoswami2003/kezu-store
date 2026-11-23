from django.contrib.sitemaps.views import sitemap
from django.contrib.sitemaps import Sitemap
from django.urls import path
from . import views

class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = 'daily'

    def items(self):
        return ['index']

    def location(self, item):
        return '/'

urlpatterns = [
    path('', views.index, name='index'),
    path('health/', views.health_check, name='health_check'),
    path('sitemap.xml', sitemap, {'sitemaps': {'static': StaticViewSitemap}}, name='django.contrib.sitemaps.views.sitemap'),
    path('submit-feedback/', views.submit_feedback, name='submit_feedback'),
    path('feedback/<int:feedback_id>/react/', views.feedback_react, name='feedback_react'),
    path('feedback/<int:feedback_id>/comment/', views.add_feedback_comment, name='add_feedback_comment'),
    path('feedback/comment/<int:comment_id>/delete/', views.delete_feedback_comment, name='delete_feedback_comment'),
    path('feedback/<int:feedback_id>/delete/', views.delete_feedback, name='delete_feedback'),
]