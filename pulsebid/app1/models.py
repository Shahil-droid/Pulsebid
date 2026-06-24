from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.core.validators import MinValueValidator


# 1. User Profile
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_vip = models.BooleanField(default=False)
    reliability_score = models.IntegerField(default=100)

    # Social Fields
    followers = models.ManyToManyField(User, related_name='following', blank=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    # Payment Field (Mandatory for sellers)
    payment_link = models.URLField(blank=True, null=True, help_text="Razorpay or UPI Link")

    def total_followers(self):
        return self.followers.count()

    def adjust_score(self, delta):
        """Safely adjust reliability score within bounds [0, 200]"""
        self.reliability_score = max(0, min(200, self.reliability_score + delta))

    def __str__(self):
        return f"{self.user.username} ({self.total_followers()} followers)"


# 2. Product Categories
class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=10, default='📦')

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return f"{self.icon} {self.name}"


# 3. The Product
class Product(models.Model):
    STATUS_CHOICES = [
        ('FIXED', 'Fixed Price'),
        ('UNLOCKED', 'Auction Unlocked'),
        ('WARMUP', 'Warming Up'),
        ('AUCTION', 'Live Auction'),
        ('SOLD', 'Sold'),
    ]

    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="products")
    title = models.CharField(max_length=200)
    description = models.TextField()

    # Category
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')

    # Image Upload
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)

    # Pricing & State (No negative numbers allowed)
    buy_now_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    current_bid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0.0)])

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='FIXED')

    # Pulse Logic
    interested_users = models.ManyToManyField(User, related_name="interested_products", blank=True)
    interest_threshold = models.IntegerField(default=10)

    # Timers
    auction_start_time = models.DateTimeField(null=True, blank=True)
    auction_end_time = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def get_starting_bid(self):
        """Returns 95% of the Buy Now Price (5% Discount)"""
        if self.buy_now_price:
            return int(float(self.buy_now_price) * 0.95)
        return 0

    def get_interest_count(self):
        return self.interested_users.count()

    def check_threshold(self):
        if self.status == 'FIXED' and self.get_interest_count() >= self.interest_threshold:
            self.status = 'UNLOCKED'
            self.save()
            return True
        return False

    def get_winner(self):
        if self.bids.exists():
            return self.bids.order_by('-amount').first().user
        return None

    def finalize_auction(self):
        """Gamification Logic: Rewards bidders, penalizes fakers"""
        if self.status != 'SOLD':
            self.status = 'SOLD'
            self.save()

            bidders = {bid.user for bid in self.bids.all()}
            interested = set(self.interested_users.all())

            # Reward Bidders (+2)
            for user in bidders:
                profile, _ = Profile.objects.get_or_create(user=user)
                profile.adjust_score(2)
                profile.save()

            # Penalize Fake Interest (-5)
            fake_interest_users = interested - bidders
            for user in fake_interest_users:
                profile, _ = Profile.objects.get_or_create(user=user)
                profile.adjust_score(-5)
                profile.save()

    def __str__(self):
        return self.title


# 4. Bids
class Bid(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="bids")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"₹{self.amount} on {self.product.title} by {self.user.username}"


# 5. Messages (Chat System)
class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inquiries')
    body = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Msg from {self.sender} to {self.recipient}"