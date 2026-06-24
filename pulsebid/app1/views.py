from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse, Http404
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse_lazy, reverse
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, DeleteView
from django.db.models import Q
from .models import Product, Bid, Profile, Message, Category
from .forms import ProductForm


# --- CONTEXT PROCESSOR FOR UNREAD COUNT ---
def unread_count_context(request):
    """Returns unread message count for the navigation badge."""
    if request.user.is_authenticated:
        count = Message.objects.filter(recipient=request.user, is_read=False).count()
        return {'unread_msg_count': count}
    return {'unread_msg_count': 0}


# --- 1. HOME & DISCOVERY ---
class ProductListView(ListView):
    model = Product
    template_name = 'app1/index.html'
    context_object_name = 'products'
    ordering = ['-id']

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.exclude(status='SOLD')
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

        cat = self.request.GET.get('cat')
        if cat:
            qs = qs.filter(category__id=cat)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = Category.objects.all()
        ctx['selected_cat'] = self.request.GET.get('cat', '')

        if u_q := self.request.GET.get('user_q'):
            ctx['user_results'] = User.objects.filter(username__icontains=u_q)
            ctx['user_search_term'] = u_q
        return ctx


class LiveAuctionsView(ListView):
    model = Product
    template_name = 'app1/live_auctions.html'
    context_object_name = 'products'

    def get_queryset(self):
        return Product.objects.filter(
            Q(status='AUCTION') | Q(status='WARMUP')
        ).order_by('auction_end_time')


class VIPDropsView(ListView):
    model = Product
    template_name = 'app1/vip_drops.html'
    context_object_name = 'products'

    def get_queryset(self):
        return Product.objects.filter(
            seller__profile__is_vip=True
        ).exclude(status__in=['SOLD', 'AUCTION', 'WARMUP']).order_by('-id')


# --- 2. AUTHENTICATION ---
class CustomSignupView(CreateView):
    form_class = UserCreationForm
    template_name = 'app1/signup.html'
    success_url = reverse_lazy('app1:index')

    def form_valid(self, form):
        user = form.save()
        Profile.objects.get_or_create(user=user)
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(self.request, user)
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'redirect_url': str(self.success_url)})
        return redirect(self.success_url)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        return super().form_invalid(form)


class CustomLoginView(LoginView):
    template_name = 'app1/login.html'

    def get_success_url(self):
        return self.request.POST.get('next') or self.request.GET.get('next') or reverse_lazy('app1:index')


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('app1:index')


# --- 3. PROFILE & FOLLOW ---
class ProfileDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'app1/profile.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        username = self.kwargs.get('username') or self.request.user.username

        user = User.objects.filter(username=username).first()
        if not user:
            user = self.request.user  # Fallback

        profile, _ = Profile.objects.get_or_create(user=user)

        # Won auctions
        won_products = []
        sold_products = Product.objects.filter(status='SOLD')
        for p in sold_products:
            winner = p.get_winner()
            if winner == user:
                won_products.append(p)

        ctx.update({
            'profile_user': user,
            'profile': profile,
            'my_products': Product.objects.filter(seller=user),
            'my_bids': Bid.objects.filter(user=user).order_by('-timestamp')[:5],
            'won_products': won_products,
            'is_following': profile.followers.filter(id=self.request.user.id).exists()
        })
        return ctx


class FollowToggleView(LoginRequiredMixin, View):
    def post(self, request, user_id):
        target_user = User.objects.filter(pk=user_id).first()
        if not target_user or request.user == target_user:
            return redirect('app1:index')

        profile, _ = Profile.objects.get_or_create(user=target_user)
        if profile.followers.filter(id=request.user.id).exists():
            profile.followers.remove(request.user)
        else:
            profile.followers.add(request.user)

        profile.is_vip = profile.total_followers() >= 1000
        profile.save()
        return redirect('app1:view_profile', username=target_user.username)


class ProfileEditView(LoginRequiredMixin, View):
    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return render(request, 'app1/edit_profile.html', {'user': request.user, 'profile': profile})

    def post(self, request):
        u = request.user
        p, _ = Profile.objects.get_or_create(user=u)

        # BUG FIX: use .get() with fallback to existing value instead of None
        u.first_name = request.POST.get('first_name', u.first_name) or u.first_name
        u.last_name = request.POST.get('last_name', u.last_name) or u.last_name
        u.email = request.POST.get('email', u.email) or u.email
        u.save()

        link = request.POST.get('payment_link')
        if link:
            p.payment_link = link
        if 'profile_pic' in request.FILES:
            p.profile_pic = request.FILES['profile_pic']
        p.save()
        return redirect('app1:view_profile', username=u.username)


# --- 4. SELLING & MANAGEMENT ---
class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'app1/product_form.html'
    success_url = reverse_lazy('app1:index')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        profile, _ = Profile.objects.get_or_create(user=request.user)
        if not profile.payment_link:
            base_url = reverse('app1:edit_profile')
            return redirect(f"{base_url}?seller_mode=true")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.seller = self.request.user
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        form.instance.status = 'UNLOCKED' if profile.is_vip else 'FIXED'
        return super().form_valid(form)


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'app1/product_form.html'
    pk_url_kwarg = 'product_id'

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user)

    def get_success_url(self):
        return reverse('app1:product_detail', kwargs={'product_id': self.object.id})


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    model = Product
    template_name = 'app1/product_confirm_delete.html'
    success_url = reverse_lazy('app1:index')
    pk_url_kwarg = 'product_id'

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user)


# --- 5. BUYING FLOW ---
class CheckoutView(LoginRequiredMixin, View):
    def get(self, request, product_id):
        product = Product.objects.filter(pk=product_id).first()
        if not product or product.status != 'FIXED':
            return redirect('app1:index')

        # BUG FIX: Seller can't buy own product
        if request.user == product.seller:
            return redirect('app1:product_detail', product_id=product.id)

        # Security: Buyer must be interested to proceed
        if request.user not in product.interested_users.all():
            return redirect('app1:product_detail', product_id=product.id)

        return render(request, 'app1/checkout.html', {'product': product})


class PaymentSuccessView(LoginRequiredMixin, View):
    def post(self, request, product_id):
        product = Product.objects.filter(pk=product_id).first()
        if not product or product.status != 'FIXED':
            return redirect('app1:index')

        # BUG FIX: Seller can't buy own product
        if request.user == product.seller:
            return redirect('app1:product_detail', product_id=product.id)

        product.status = 'SOLD'
        product.current_bid = product.buy_now_price
        product.save()

        Bid.objects.create(user=request.user, product=product, amount=product.buy_now_price)
        return render(request, 'app1/payment_success.html', {'product': product})


class FakeGatewayView(LoginRequiredMixin, View):
    def get(self, request, product_id):
        product = Product.objects.filter(pk=product_id).first()
        if not product:
            return redirect('app1:index')
        return render(request, 'app1/fake_gateway.html', {'product': product})


# --- 6. MESSAGING ---
class SendEnquiryView(LoginRequiredMixin, View):
    def post(self, request, product_id):
        product = Product.objects.filter(pk=product_id).first()
        # BUG FIX: check product is not None before accessing product.id
        if not product:
            return redirect('app1:index')
        if request.user not in product.interested_users.all():
            return redirect('app1:product_detail', product_id=product.id)

        if msg := request.POST.get('message'):
            Message.objects.create(
                sender=request.user,
                recipient=product.seller,
                product=product,
                body=msg
            )
        return redirect('app1:product_detail', product_id=product.id)


class InboxView(LoginRequiredMixin, TemplateView):
    template_name = 'app1/inbox.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        msgs = Message.objects.filter(
            Q(sender=self.request.user) | Q(recipient=self.request.user)
        ).select_related('product', 'sender', 'recipient').order_by('-timestamp')

        convos = {}
        for m in msgs:
            other = m.recipient if m.sender == self.request.user else m.sender
            key = f"{m.product.id}_{other.id}"
            if key not in convos:
                convos[key] = {
                    'product': m.product,
                    'other_user': other,
                    'last_message': m
                }
        ctx['conversations'] = convos.values()
        return ctx


class ChatDetailView(LoginRequiredMixin, View):
    def get(self, request, product_id, other_user_id):
        product = Product.objects.filter(pk=product_id).first()
        other = User.objects.filter(pk=other_user_id).first()
        if not product or not other:
            return redirect('app1:inbox')

        msgs = Message.objects.filter(product=product).filter(
            (Q(sender=request.user) & Q(recipient=other)) |
            (Q(sender=other) & Q(recipient=request.user))
        ).order_by('timestamp')

        msgs.filter(recipient=request.user).update(is_read=True)
        return render(request, 'app1/chat.html', {
            'product': product,
            'messages': msgs,
            'other_user': other
        })

    def post(self, request, product_id, other_user_id):
        product = Product.objects.filter(pk=product_id).first()
        other = User.objects.filter(pk=other_user_id).first()
        if product and other and (body := request.POST.get('body')):
            Message.objects.create(
                sender=request.user,
                recipient=other,
                product=product,
                body=body
            )
        return redirect('app1:chat_detail', product_id=product_id, other_user_id=other_user_id)


# --- 7. AUCTION LOGIC ---
class ProductDetailView(DetailView):
    model = Product
    template_name = 'app1/product_detail.html'
    context_object_name = 'product'
    pk_url_kwarg = 'product_id'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        now = timezone.now()

        # 1. Warmup -> Auction
        if obj.status == 'WARMUP' and obj.auction_start_time and now >= obj.auction_start_time:
            obj.status = 'AUCTION'
            obj.save()
            return obj

        # 2. Auction -> Sold (Auto-Finalize)
        if obj.status == 'AUCTION' and obj.auction_end_time and now > obj.auction_end_time:
            obj.finalize_auction()

        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Add bid history (last 10 bids)
        ctx['bid_history'] = self.object.bids.order_by('-timestamp')[:10]
        return ctx


class ToggleInterestView(LoginRequiredMixin, View):
    """BUG FIX: Changed from GET to POST to properly handle state mutation."""

    def post(self, request, *args, **kwargs):
        product = Product.objects.filter(pk=kwargs.get('product_id')).first()
        if not product:
            return JsonResponse({'status': 'error', 'message': 'Product not found'})

        # Seller can't express interest on own product
        if request.user == product.seller:
            return JsonResponse({'status': 'error', 'message': 'Cannot express interest on your own product.'})

        profile, _ = Profile.objects.get_or_create(user=request.user)
        if profile.reliability_score < 50:
            return JsonResponse({'status': 'error', 'message': 'Low reliability score. Minimum 50 required.'})

        if request.user in product.interested_users.all():
            product.interested_users.remove(request.user)
            added = False
        else:
            product.interested_users.add(request.user)
            added = True

        unlocked = product.check_threshold()
        return JsonResponse({
            'status': 'success',
            'count': product.get_interest_count(),
            'added': added,
            'unlocked': unlocked
        })


# --- UPDATED: StartWarmupView with Scheduling ---
class StartWarmupView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        product = Product.objects.filter(pk=kwargs.get('product_id')).first()

        if not product or request.user != product.seller:
            return redirect('app1:product_detail', product_id=kwargs.get('product_id'))

        custom_start_time = request.POST.get('start_time')

        if product.status == 'UNLOCKED':
            # 5% Discount
            current_price_float = float(product.buy_now_price)
            discounted_price = int(current_price_float * 0.95)
            product.current_bid = discounted_price

            # Schedule Logic
            if custom_start_time:
                try:
                    start_dt = timezone.datetime.fromisoformat(custom_start_time)
                    if timezone.is_naive(start_dt):
                        start_dt = timezone.make_aware(start_dt)
                    product.auction_start_time = start_dt
                    product.auction_end_time = start_dt + timedelta(hours=1)
                except ValueError:
                    pass  # Fallback to default if invalid

            if not product.auction_start_time:  # Default
                product.auction_start_time = timezone.now() + timedelta(minutes=30)
                product.auction_end_time = product.auction_start_time + timedelta(hours=1)

            product.status = 'WARMUP'
            product.save()

        return redirect('app1:product_detail', product_id=product.id)


class KeepFixedPriceView(LoginRequiredMixin, View):
    """BUG FIX: Changed from GET to POST to properly handle state mutation."""

    def post(self, request, *args, **kwargs):
        product = Product.objects.filter(pk=kwargs.get('product_id')).first()
        if not product:
            return redirect('app1:index')
        if request.user != product.seller:
            return redirect('app1:product_detail', product_id=product.id)

        if product.status == 'UNLOCKED':
            product.status = 'FIXED'
            product.interested_users.clear()
            product.save()
        return redirect('app1:product_detail', product_id=product.id)


class ForceEndAuctionView(LoginRequiredMixin, View):
    def post(self, request, product_id):
        product = Product.objects.filter(pk=product_id).first()
        if not product or request.user != product.seller:
            return redirect('app1:index')

        product.finalize_auction()
        return redirect('app1:product_detail', product_id=product.id)


class PlaceBidView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        product = Product.objects.filter(pk=kwargs.get('product_id')).first()
        if not product:
            return JsonResponse({'status': 'fail', 'message': 'Not found'})

        if product.status != 'AUCTION':
            return JsonResponse({'status': 'fail', 'message': 'Auction is not active'})

        # BUG FIX: Seller can't bid on own product
        if request.user == product.seller:
            return JsonResponse({'status': 'fail', 'message': 'Cannot bid on your own product'})

        # BUG FIX: Proper exception types instead of bare except
        try:
            amount = float(request.POST.get('amount', 0))
        except (TypeError, ValueError):
            return JsonResponse({'status': 'fail', 'message': 'Invalid amount'})

        if amount <= 0:
            return JsonResponse({'status': 'fail', 'message': 'Amount must be positive'})

        # BUG FIX: null check on auction_end_time before arithmetic
        extended = False
        if product.auction_end_time:
            time_remaining = product.auction_end_time - timezone.now()
            if time_remaining < timedelta(seconds=60):
                product.auction_end_time += timedelta(seconds=60)
                product.save()
                extended = True

        if amount > float(product.current_bid):
            product.current_bid = amount
            product.save()
            Bid.objects.create(user=request.user, product=product, amount=amount)
            return JsonResponse({
                'status': 'success',
                'new_price': float(amount),
                'extended': extended
            })
        return JsonResponse({'status': 'fail', 'message': f'Bid must be higher than ₹{product.current_bid}'})