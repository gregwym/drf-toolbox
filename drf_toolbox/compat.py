try:
    from django_pg import models
    django_pgfields_installed = True
except ImportError:
    from django.db import models
    django_pgfields_installed = False
