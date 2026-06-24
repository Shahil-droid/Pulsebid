import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pulsebid.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from app1.models import Category

cats = [
    ('Electronics', '📱'),
    ('Fashion', '👗'),
    ('Sports', '⚽'),
    ('Books', '📚'),
    ('Art', '🎨'),
    ('Gaming', '🎮'),
    ('Home', '🏠'),
    ('Other', '📦'),
]

for name, icon in cats:
    obj, created = Category.objects.get_or_create(name=name, defaults={'icon': icon})
    status = 'Created' if created else 'Exists'
    print(f"  {status}: {icon} {name}")

print(f"\nTotal categories: {Category.objects.count()}")
