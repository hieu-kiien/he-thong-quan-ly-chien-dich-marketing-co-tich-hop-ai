from django.contrib import messages
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import CategoryForm
from .models import Category


class CategoryListView(ListView):
    model = Category
    template_name = "categories/category_list.html"
    context_object_name = "categories"
    paginate_by = 10

    allowed_sort_fields = {
        "code": "code",
        "name": "name",
        "status": "status",
        "created_at": "created_at",
        "product_count": "product_count",
    }

    def get_paginate_by(self, queryset):
        per_page = self.request.GET.get("per_page", self.paginate_by)
        try:
            per_page = int(per_page)
        except (TypeError, ValueError):
            return self.paginate_by
        return per_page if per_page in [5, 10, 20, 50] else self.paginate_by

    def get_queryset(self):
        queryset = Category.objects.annotate(product_count=Count("products"))
        query = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()

        if query:
            queryset = queryset.filter(
                Q(code__icontains=query)
                | Q(name__icontains=query)
                | Q(description__icontains=query)
            )
        if status in Category.CategoryStatus.values:
            queryset = queryset.filter(status=status)

        sort = self.request.GET.get("sort", "name")
        direction = self.request.GET.get("dir", "asc")
        sort_field = self.allowed_sort_fields.get(sort, "name")
        if direction == "desc":
            sort_field = f"-{sort_field}"
        return queryset.order_by(sort_field, "id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Quản lý Nhóm sản phẩm",
                "query": self.request.GET.get("q", ""),
                "selected_status": self.request.GET.get("status", ""),
                "status_choices": Category.CategoryStatus.choices,
                "per_page": str(self.get_paginate_by(self.object_list)),
                "sort": self.request.GET.get("sort", "name"),
                "direction": self.request.GET.get("dir", "asc"),
                "total_count": Category.objects.count(),
                "active_count": Category.objects.filter(
                    status=Category.CategoryStatus.ACTIVE
                ).count(),
            }
        )
        return context


class CategoryDetailView(DetailView):
    model = Category
    template_name = "categories/category_detail.html"
    context_object_name = "category"

    def get_queryset(self):
        return Category.objects.annotate(product_count=Count("products"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Chi tiết nhóm sản phẩm"
        return context


class CategoryCreateView(CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "categories/category_form.html"
    success_url = reverse_lazy("categories:category_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Thêm nhóm sản phẩm"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Đã thêm nhóm sản phẩm thành công.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Vui lòng kiểm tra lại các trường bị lỗi.")
        return super().form_invalid(form)


class CategoryUpdateView(UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "categories/category_form.html"
    success_url = reverse_lazy("categories:category_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Sửa nhóm sản phẩm"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Đã cập nhật nhóm sản phẩm.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Vui lòng kiểm tra lại các trường bị lỗi.")
        return super().form_invalid(form)


class CategoryDeleteView(DeleteView):
    model = Category
    template_name = "categories/category_confirm_delete.html"
    context_object_name = "category"
    success_url = reverse_lazy("categories:category_list")

    def get_queryset(self):
        return Category.objects.annotate(product_count=Count("products"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Xóa nhóm sản phẩm"
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "Không thể xóa nhóm đang chứa sản phẩm. Hãy chuyển sản phẩm sang nhóm khác trước.",
            )
            return redirect("categories:category_detail", pk=self.object.pk)
        messages.success(self.request, "Đã xóa nhóm sản phẩm.")
        return response
