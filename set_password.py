import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraping_platform.settings')
django.setup()

from django.contrib.auth.models import User

user = User.objects.get(username='admin')
user.set_password('admin123')
user.save()
print("Password set to 'admin123' for user 'admin'")
