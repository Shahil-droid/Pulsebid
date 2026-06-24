from django import forms
from .models import Product, Category


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['title', 'description', 'buy_now_price', 'category', 'image']

        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe condition, age, features...'
            }),
            'title': forms.TextInput(attrs={
                'placeholder': 'e.g., iPhone 12 Pro - Mint Condition'
            }),
            'buy_now_price': forms.NumberInput(attrs={
                'placeholder': 'Enter price in ₹',
                'min': '1',
                'step': '0.01',
            }),
            'category': forms.Select(attrs={
                'style': 'width:100%; padding:12px; background:#0f0f0f; color:white; border:1px solid #333; border-radius:8px;'
            }),
        }