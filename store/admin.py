from django.contrib import admin
from .models import Category, Product, Order, Feedback, FeedbackComment


class FeedbackAdminSite(admin.AdminSite):
    site_header = "KEZU & Co. Feedback Desk"
    site_title = "Feedback Admin"
    index_title = "Customer Feedbacks & Comments"

    def has_permission(self, request):
        if not request.user.is_active or not request.user.is_staff:
            return False
        return request.user.is_superuser or request.user.username == "Aksh924"


feedback_admin_site = FeedbackAdminSite(name="feedback_admin")


class FeedbackCommentInline(admin.TabularInline):
    model = FeedbackComment
    extra = 1
    fields = (
        "user",
        "author_name",
        "rating",
        "is_owner_reply",
        "prevent_user_delete",
        "comment_text",
        "created_at",
    )
    readonly_fields = ("created_at",)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer_name",
        "user",
        "fragrance_name",
        "rating",
        "message_preview",
        "owner_reply_status",
        "comments_count",
        "likes_count",
        "dislikes_count",
        "is_public",
        "created_at",
    )
    list_filter = ("rating", "is_public", "created_at")
    search_fields = ("customer_name", "fragrance_name", "message", "owner_reply", "user__username")
    readonly_fields = ("owner_token", "owner_replied_at", "created_at")
    inlines = [FeedbackCommentInline]
    actions = ["make_public", "make_private"]

    @admin.display(description="Feedback Message")
    def message_preview(self, obj):
        text = (obj.message or "").strip()
        return text if len(text) <= 80 else f"{text[:77]}..."

    @admin.display(description="Owner Reply", boolean=True)
    def owner_reply_status(self, obj):
        has_direct_reply = bool((obj.owner_reply or "").strip())
        has_comment_reply = obj.comments.filter(is_owner_reply=True).exists()
        return has_direct_reply or has_comment_reply

    @admin.display(description="Comments")
    def comments_count(self, obj):
        return obj.comments.count()

    @admin.action(description="Mark selected feedbacks as public")
    def make_public(self, request, queryset):
        queryset.update(is_public=True)

    @admin.action(description="Hide selected feedbacks from public feed")
    def make_private(self, request, queryset):
        queryset.update(is_public=False)

    def has_module_permission(self, request):
        return bool(
            request.user.is_active
            and request.user.is_staff
            and (request.user.is_superuser or request.user.username == "Aksh924")
        )

    def has_delete_permission(self, request, obj=None):
        return bool(
            request.user.is_active
            and request.user.is_staff
            and (request.user.is_superuser or request.user.username == "Aksh924")
        )


@admin.register(FeedbackComment)
class FeedbackCommentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "feedback",
        "user",
        "author_name",
        "rating",
        "is_owner_reply",
        "prevent_user_delete",
        "comment_text",
        "created_at",
    )
    list_filter = ("is_owner_reply", "prevent_user_delete", "rating", "created_at")
    search_fields = ("author_name", "comment_text", "feedback__customer_name", "user__username")
    list_editable = ("prevent_user_delete",)
    readonly_fields = ("owner_token", "created_at")
    actions = ["block_user_delete", "allow_user_delete", "mark_as_owner_reply"]

    @admin.action(description="Lock selected comments so users cannot delete them")
    def block_user_delete(self, request, queryset):
        queryset.update(prevent_user_delete=True)

    @admin.action(description="Unlock selected comments for user delete")
    def allow_user_delete(self, request, queryset):
        queryset.update(prevent_user_delete=False)

    @admin.action(description="Mark selected comments as Owner reply")
    def mark_as_owner_reply(self, request, queryset):
        for comment in queryset:
            comment.is_owner_reply = True
            comment.prevent_user_delete = True
            if not comment.author_name or comment.author_name.strip() == "Guest":
                comment.author_name = "Owner"
            comment.save()

    def has_module_permission(self, request):
        return bool(
            request.user.is_active
            and request.user.is_staff
            and (request.user.is_superuser or request.user.username == "Aksh924")
        )

    def has_delete_permission(self, request, obj=None):
        return bool(
            request.user.is_active
            and request.user.is_staff
            and (request.user.is_superuser or request.user.username == "Aksh924")
        )


feedback_admin_site.register(Feedback, FeedbackAdmin)
feedback_admin_site.register(FeedbackComment, FeedbackCommentAdmin)

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Order)