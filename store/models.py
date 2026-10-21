from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=50) # e.g., Male, Female

    def __str__(self):
        return self.name

class Product(models.Model):
    title = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='products/')
    scent_notes = models.CharField(max_length=200, blank=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.title

class Order(models.Model):
    customer_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} - {self.customer_name}"