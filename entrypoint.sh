#!/bin/bash

python manage.py makemigrations
python manage.py migrate

# Create superuser script
python manage.py shell << END
from django.contrib.auth.models import User
try:
    User.objects.get(username='admin')
    print('Superuser already exists')
except User.DoesNotExist:
    User.objects.create_superuser('admin', 
                                'admin@admin.com', 
                                '123')
    print('Superuser created successfully')
END

python manage.py runserver 0.0.0.0:8000 &
python manage.py runbot