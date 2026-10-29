from django.shortcuts import render
from .models import Product, Category
from django.http import HttpResponse

def index(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    return render(request, 'index.html', {'products': products, 'categories': categories})

def health_check(request):
    return HttpResponse("OK")