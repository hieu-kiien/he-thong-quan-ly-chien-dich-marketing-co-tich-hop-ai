from django import forms

from .models import Category


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["code", "name", "description", "status"]
        labels = {
            "code": "Mã nhóm",
            "name": "Tên nhóm",
            "description": "Mô tả",
            "status": "Trạng thái",
        }
        help_texts = {
            "code": "Dùng chữ, số hoặc dấu gạch ngang. Ví dụ: CAT-001.",
            "description": "Mô tả ngắn giúp nhân viên nhận biết nhóm sản phẩm.",
        }
        widgets = {
            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "VD: CAT-001",
                    "autocomplete": "off",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "VD: Đồ uống",
                    "autocomplete": "off",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Nhập mô tả nhóm sản phẩm",
                }
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper()

    def clean_name(self):
        return self.cleaned_data["name"].strip()
