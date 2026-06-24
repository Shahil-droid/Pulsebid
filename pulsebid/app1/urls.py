from django.urls import path
from . import views

app_name = 'app1'

urlpatterns = [
    # --- Home & Discovery ---
    path('', views.ProductListView.as_view(), name='index'),
    path('live/', views.LiveAuctionsView.as_view(), name='live_auctions'),
    path('drops/', views.VIPDropsView.as_view(), name='vip_drops'),
    
    # --- Authentication ---
    path('signup/', views.CustomSignupView.as_view(), name='signup'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    
    # --- Profile & Selling ---
    path('profile/<str:username>/', views.ProfileDetailView.as_view(), name='view_profile'),
    path('profile/edit/me/', views.ProfileEditView.as_view(), name='edit_profile'),
    path('profile/follow/<int:user_id>/', views.FollowToggleView.as_view(), name='follow_toggle'),
    path('sell/', views.ProductCreateView.as_view(), name='create_product'),

    # --- Product Management (Edit/Delete) ---
    path('product/<int:product_id>/edit/', views.ProductUpdateView.as_view(), name='product_edit'),
    path('product/<int:product_id>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),

    # --- Product Actions (Auction Logic) ---
    path('product/<int:product_id>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('product/<int:product_id>/interest/', views.ToggleInterestView.as_view(), name='toggle_interest'),
    path('product/<int:product_id>/start_warmup/', views.StartWarmupView.as_view(), name='start_warmup'),
    path('product/<int:product_id>/keep_fixed/', views.KeepFixedPriceView.as_view(), name='keep_fixed'),
    path('product/<int:product_id>/bid/', views.PlaceBidView.as_view(), name='place_bid'),
    
    # --- Messaging & Buying ---
    path('product/<int:product_id>/enquire/', views.SendEnquiryView.as_view(), name='send_enquiry'),
    path('inbox/', views.InboxView.as_view(), name='inbox'),
    path('inbox/<int:product_id>/<int:other_user_id>/', views.ChatDetailView.as_view(), name='chat_detail'),

    # --- Payment (Checkout Flow) ---
    path('buy/<int:product_id>/checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('buy/<int:product_id>/process/', views.PaymentSuccessView.as_view(), name='payment_success'),

    path('product/<int:product_id>/force_end/', views.ForceEndAuctionView.as_view(), name='force_end'),
]