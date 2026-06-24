from django.contrib import admin
from .models import Product, Bid, Profile, Message, Category


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'reliability_score', 'is_vip', 'total_followers')


class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'status', 'category', 'current_bid', 'get_interest_count', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('title', 'description')


class BidAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'amount', 'timestamp')
    list_filter = ('timestamp',)


class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'product', 'timestamp', 'is_read')
    list_filter = ('is_read', 'timestamp')


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')


admin.site.register(Product, ProductAdmin)
admin.site.register(Bid, BidAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(Category, CategoryAdmin)