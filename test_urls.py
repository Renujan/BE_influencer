import os
import sys
import django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from django.urls import get_resolver
resolver = get_resolver()
for url in resolver.url_patterns:
    print(url)
