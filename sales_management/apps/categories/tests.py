from django.test import TestCase
from django.urls import reverse

from .models import Category


class CategoryCRUDTests(TestCase):
    def test_list_view_renders_categories(self):
        Category.objects.create(code="CAT-001", name="Đồ uống")

        response = self.client.get(reverse("categories:category_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Đồ uống")

    def test_create_category(self):
        response = self.client.post(
            reverse("categories:category_create"),
            {
                "code": "cat-002",
                "name": "Thực phẩm",
                "description": "Nhóm hàng thực phẩm",
                "status": Category.CategoryStatus.ACTIVE,
            },
        )

        self.assertRedirects(response, reverse("categories:category_list"))
        self.assertTrue(Category.objects.filter(code="CAT-002").exists())

    def test_update_category(self):
        category = Category.objects.create(code="CAT-003", name="Cũ")

        response = self.client.post(
            reverse("categories:category_update", kwargs={"pk": category.pk}),
            {
                "code": "CAT-003",
                "name": "Tên mới",
                "description": "",
                "status": Category.CategoryStatus.INACTIVE,
            },
        )

        self.assertRedirects(response, reverse("categories:category_list"))
        category.refresh_from_db()
        self.assertEqual(category.name, "Tên mới")
        self.assertEqual(category.status, Category.CategoryStatus.INACTIVE)

    def test_delete_category(self):
        category = Category.objects.create(code="CAT-004", name="Xóa")

        response = self.client.post(
            reverse("categories:category_delete", kwargs={"pk": category.pk})
        )

        self.assertRedirects(response, reverse("categories:category_list"))
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())
