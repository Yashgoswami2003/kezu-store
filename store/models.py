import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=50)  # e.g., Male, Female

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


class Feedback(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='feedbacks',
    )
    customer_name = models.CharField(max_length=100)
    fragrance_name = models.CharField(max_length=120, blank=True)
    rating = models.PositiveSmallIntegerField(default=5)
    message = models.TextField()
    owner_reply = models.TextField(blank=True)
    owner_replied_at = models.DateTimeField(null=True, blank=True)
    likes_count = models.PositiveIntegerField(default=0)
    dislikes_count = models.PositiveIntegerField(default=0)
    owner_token = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.owner_reply and self.owner_reply.strip() and not self.owner_replied_at:
            self.owner_replied_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Feedback {self.id} - {self.customer_name}"


class FeedbackComment(models.Model):
    feedback = models.ForeignKey(Feedback, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='feedback_comments',
    )
    author_name = models.CharField(max_length=100, default="Guest")
    rating = models.PositiveSmallIntegerField(default=5)
    is_owner_reply = models.BooleanField(default=False)
    prevent_user_delete = models.BooleanField(default=False)
    comment_text = models.TextField()
    owner_token = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.is_owner_reply:
            self.prevent_user_delete = True
            if not self.author_name or self.author_name.strip() == "Guest":
                self.author_name = "Owner"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Comment {self.id} on Feedback {self.feedback_id}"