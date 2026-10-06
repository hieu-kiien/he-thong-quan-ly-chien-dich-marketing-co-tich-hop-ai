"""
Mat khau seed khong duoc ship cung ban build frontend
=====================================================

Vien canh
---------
`frontend/src/pages/LoginPage.tsx` tuong co khoi "chon nhanh tai khoan kiem
thu": ba nut dien san `manager@gmail.com / Manager@123`,
`marketer@gmail.com / Marketer@123`, `approver@gmail.com / Approver@123`.

Yeu cau viet ban (2026-09-24) noi ro: *"Loai bo hoan toan co chec tu dong dang
nhap demo; ... khong con bat ky ma lenh dang nhap tu dong ngam nao"*. Tai khoan
seed van can cho moi truong local/CI, nhung khoi nut nay khong duoc xuat hien o
moi truong that.

Vi sao day la loi bao mat chu khong phai loi UI
----------------------------------------------
Vite **bai bien moi truong vao bundle** luc `npm run build`. Mot chuoi literal
trong file nguon cu the tro thanh JavaScript gui toi moi trinh duyet. Neu khoi
nut luon render, ba mat khau seed nam trong bundle ma moi nguoi dung deu tai
duoc va doc duoc -- ke ca tren production.

Voi vay dieu kien dung khong phai "co nut hay khong", ma la: **nut chi duoc render
khi co du lieu mau cuc bo** (`VITE_ENABLE_OFFLINE_DEMO=true`).

Quy tac cua file nay
--------------------
1. KHONG `pytest.skip`. Neu ai do go khoi nay de "cho gon", test phai DO.
2. KHONG sua duong dan hay ten bien de lam test xanh; neu can, sua ca mo ta
   dieu kien.
3. Test doc **nguyen ban nguon**, khong doc bundle: doi dieu kien o Vite config
   khong lam thoat duoc bo test nay.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOGIN_PAGE = REPO_ROOT / "frontend" / "src" / "pages" / "LoginPage.tsx"
API_SERVICE = REPO_ROOT / "frontend" / "src" / "services" / "api.ts"

# Mat khau seed. Lay tu backend/seed/seed_data.py (resolve_password).
SEED_PASSWORDS = ("Manager@123", "Marketer@123", "Approver@123")
SEED_EMAILS = (
    "manager@gmail.com",
    "marketer@gmail.com",
    "approver@gmail.com",
)


@pytest.fixture(scope="module")
def login_source() -> str:
    assert LOGIN_PAGE.exists(), f"Khong tim thay {LOGIN_PAGE}"
    return LOGIN_PAGE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def api_source() -> str:
    return API_SERVICE.read_text(encoding="utf-8")


def _block_span(source: str, start_marker: str, end_marker: str) -> tuple[int, int]:
    """Tra ve (start, end) cua khoi can bao ve."""
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return start, end


def test_quick_login_block_marked_as_demo_only(login_source):
    """Khoi JSX phai co ghi chu giai thich vi sao khong bat o moi truong."""
    assert "{/* Quick-chips for testing." in login_source, (
        "Khoi quick-login phai giu comment giai thich."
    )
    assert "VITE_ENABLE_OFFLINE_DEMO" in login_source, (
        "Comment phai nhac ten bien bao ve (VITE_ENABLE_OFFLINE_DEMO) de nguoi "
        "sau doc hieu vi sao khoi nay la duy nhat o moi co du lieu mau."
    )


def test_seed_passwords_still_exist_in_source(login_source):
    """Kiem tra co so: khoi quick-login van con dung mat khau seed.

    Neu test nay do, hoac la mat khau da doi, hoac la khoi da bi xoa hoan toan --
    ca hai deu la thay doi can thao loi ro rang chu khong phai de test no.
    """
    for password in SEED_PASSWORDS:
        assert password in login_source, (
            f"{password} khong con trong LoginPage.tsx. Neu da chuyen sang tai "
            "khau lay tu bien moi truong, hay cap nhat SEED_PASSWORDS trong file "
            "test nay de khop voi backend/seed/seed_data.py."
        )


def test_quick_login_block_is_gated_by_offline_demo_flag(login_source):
    """Khoi quick-login phai nam sau dieu kien `showQuickLogin`.

    Day la phep bao ve chinh. Neu khoi kiem tra duoc bo ra khoi JSX, hoac bien
    `showQuickLogin` bi gan gia tri hang, test do.
    """
    # 1. Bien dieu kien phai duoc gan tu co that, khong phan gan truc tiep hang.
    assert "const showQuickLogin = isOfflineDemoEnabled();" in login_source, (
        "`showQuickLogin` phai duoc gan tu `isOfflineDemoEnabled()`. Gan gia tri "
        "hang (vd `const showQuickLogin = true`) se bien ba mat khau seed thanh "
        "hang so trong moi moi truong."
    )

    # 2. Dieu kien phai mo truoc nut dau tien cua khoi quick-login.
    assert "showQuickLogin &&" in login_source, (
        "Khoi quick-login khong con duoc bao ve: khong tim thay dieu kien "
        "`showQuickLogin &&` trong JSX. Hay boc khoi do bang `{showQuickLogin && ("
    )
    gate_index = login_source.index("showQuickLogin &&")
    first_button = login_source.index("handleQuickLogin('manager")
    assert gate_index < first_button, (
        "Dieu kien `showQuickLogin &&` phai nam TRUOC nut quick-login dau tien, "
        f"vi con la nut sau dieu kien (gate={gate_index}, button={first_button})."
    )

    # 3. Va phai nam sau phan dinh nghia cua bien.
    assert gate_index > login_source.index("const showQuickLogin = "), (
        "Dieu kien phai nam sau khai bao bien `showQuickLogin`."
    )

    # 4. Ca khoi phai duoc dong bang ngoac nhon cua dieu kien, va phai dung
    #    TRUOC khi mo footer "Chua co tai khoan?" de khong lam hong JSX.
    footer_index = login_source.index("Chưa có tài khoản?")
    closing = login_source.rindex(")}", first_button, footer_index)
    assert closing > login_source.rindex("handleQuickLogin('approver"), (
        "Khoi quick-login phai duoc dong bang `)}` cua dieu kien, va phai dong "
        "TRUOC khoi footer chuyen sang dang ky."
    )


def test_flag_is_strictly_equal_to_true(api_source):
    """`isOfflineDemoEnabled()` phai so sanh CHAT VOI 'true'.

    Day la hang so bao ve thu hai. `import.meta.env.PROD` luon la true o ban
    production nen khong dung lam dieu kien; neu bien quay ve chuoi rong o moi
    moi truong thi demo bat nham tren production.
    """
    match = re.search(
        r"isOfflineDemoEnabled\s*=\s*\(\)[^;]*?===\s*'([^']*)'", api_source
    )
    assert match, (
        "Khong tim thay phan dinh nghia `isOfflineDemoEnabled`. Neu doi cach xac "
        "dinh bien, sua lai test nay -- va nho dam bao rang mac dinh la TAT."
    )
    assert match.group(1) == "true", (
        f"Dieu kien hien tai la `=== '{match.group(1)}'`. Phai la `'true'`; "
        "moi truong that khong dat bien nay nen mac dinh phai la false."
    )


def test_env_example_documents_the_flag_off_by_default():
    """Bien phai duoc ghi trong `.env.example` va mac dinh la TAT.

    Khong ghi vao `.env.example` nghia la nguoi trien khai se khong biet co the
    bat, va nuoi tinh la nut quick-login la "tinh nang" bat buoc.
    """
    env_example = REPO_ROOT / "backend" / ".env.example"
    candidates = [
        REPO_ROOT / ".env.example",
        REPO_ROOT / "frontend" / ".env.example",
        env_example,
    ]
    existing = [p for p in candidates if p.exists()]
    assert existing, "Khong tim thay .env.example nao de kiem tra."

    found_in = [
        p for p in existing if "VITE_ENABLE_OFFLINE_DEMO" in p.read_text(encoding="utf-8")
    ]
    assert found_in, (
        "Khong tai lieu nao ghi `VITE_ENABLE_OFFLINE_DEMO`. Hay them vao "
        "frontend/.env.example voi gia tri mac dinh `false` va mot dong giai thich."
    )

    for path in found_in:
        for line in path.read_text(encoding="utf-8").splitlines():
            if "VITE_ENABLE_OFFLINE_DEMO" in line and not line.strip().startswith("#"):
                value = line.split("=", 1)[1].strip() if "=" in line else ""
                assert value in ("false", '"false"', "'false'"), (
                    f"{path.name} dat mac dinh VITE_ENABLE_OFFLINE_DEMO={value!r}. "
                    "Phai la `false`: bat mac dinh nghia la mat khau seed co the "
                    "bi render o moi truong chi mot bien la duoc dat."
                )
