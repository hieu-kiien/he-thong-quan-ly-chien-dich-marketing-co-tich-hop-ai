from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("products/", include("apps.products.urls")),
    path("categories/", include("apps.categories.urls")),
    path("customers/", include("apps.customers.urls")),
    path("suppliers/", include("apps.suppliers.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("sales/", include("apps.sales.urls")),
    path("purchases/", include("apps.purchases.urls")),
    path("reports/", include("apps.reports.urls")),
    path("knowledge/", include("apps.knowledge.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
