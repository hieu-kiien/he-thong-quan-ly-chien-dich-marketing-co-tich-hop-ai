"""Test cho bộ so sánh phiên bản prompt (Tuần 3 — mục 4 rubric AIA331).

Vì sao có test này
-----------------
`scripts/compare_prompt_variants.py` sinh ra
`docs/PROMPT_VARIANT_COMPARISON.md` — tức là một con số trong báo cáo học thuật
được sinh ra từ code. Nếu script hỏng mà không ai biết, báo cáo vẫn còn nằm đó
và trông rất thuyết phục. Test ở đây bảo đảm:

1. Script chạy được và sinh đủ artifact.
2. Bộ đo thật sự bắt được lỗi (đối chứng âm), chứ không phải luôn trả 0.
3. Báo cáo sinh ra chứa các con số khớp với kết quả tính được — tức báo cáo
   không thể trở thành "văn bản không liên quan gì tới dữ liệu".

Lưu ý: không khẳng định v3 "tốt hơn" v1 trong bất kỳ test nào. Đó là kết quả
đo, và kết quả đo có thể đổi khi prompt đổi.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

#: `tests/` nằm trong `backend/`, nên thư mục gốc repo là hai cấp lên trên.
#: Ghi chú: `settings.BASE_DIR` trong config.py cũng là hai cấp, nhưng ở đây ta
#: cần đường dẫn tới `scripts/` nằm ngoài `backend/` nên phải tự tính.
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = ROOT_DIR / "scripts" / "compare_prompt_variants.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("compare_prompt_variants", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def harness():
    return _load_module()


def test_script_file_exists():
    """File generator phải tồn tại — nếu không, báo cáo đã sinh là đồ trái máy."""
    assert SCRIPT_PATH.exists(), f"Không tìm thấy {SCRIPT_PATH}"


def test_all_three_variants_are_defined_in_prompts_json(harness):
    """Đề bài yêu cầu "ít nhất 3 phiên bản". Harness phải thấy đúng 3."""
    prompts = harness.load_prompts()
    for task_type in harness.STUBS:
        assert task_type in prompts, f"Thiếu tác vụ {task_type} trong prompts.json"
        for variant in ("v1", "v2", "v3"):
            assert variant in prompts[task_type], (
                f"prompts.json[{task_type}] thiếu phiên bản {variant}"
            )


def test_variant_task_matrix_is_complete(harness):
    """Mỗi phiên bản phải được chạy trên đúng 4 tác vụ."""
    prompts = harness.load_prompts()
    for variant in harness.VARIANTS:
        results = harness.evaluate_variant(variant, prompts)
        assert len(results) == len(harness.STUBS), (
            f"{variant}: chạy {len(results)} case, cần {len(harness.STUBS)}"
        )
        assert {r.task for r in results} == set(harness.STUBS)


def test_v3_meets_the_schema_on_every_task(harness):
    """v3 là phiên bản mà hệ thống thực sự chạy (mặc định ở mọi endpoint).

    Nếu một prompt không tạo được output đúng schema thì người dùng nhận 502
    hoặc rơi vào Smart Fallback. Đây là phép kiểm tra hợp đồng quan trọng nhất
    của harness.
    """
    prompts = harness.load_prompts()
    results = harness.evaluate_variant("v3", prompts)
    failing = [r.task for r in results if not r.schema_valid]
    assert not failing, f"v3 không đạt schema ở: {failing}"


def test_v3_covers_all_required_business_fields(harness):
    """v3 phải sinh đủ trường nghiệp vụ bắt buộc cho cả 4 tác vụ."""
    prompts = harness.load_prompts()
    results = harness.evaluate_variant("v3", prompts)
    missing = {r.task: r.missing_required_fields for r in results if r.missing_required_fields}
    assert not missing, f"v3 thiếu trường bắt buộc: {missing}"


def test_banned_keyword_detector_catches_a_real_leak(harness):
    """ĐỐI CHỨNG ÂM: bộ dò từ khóa cấm phải bắt được khi output thật sự rò.

    Không có test này thì "rò từ khóa cấm = 0" trong báo cáo chỉ chứng minh được
    rằng hoặc hệ thống sạch, hoặc bộ đo hỏng — hai khả năng nhìn giống nhau.
    """
    leaked: list = []
    texts: list = []
    harness._collect_text(
        harness.stub_deliberately_leaks_banned_keyword("", harness.BASE_CONTEXT), texts
    )
    haystack = harness._normalize(" ".join(texts))
    leaked = [kw for kw in harness.BANNED_KEYWORDS if harness._normalize(kw) in haystack]

    assert len(leaked) >= 1, (
        "Bộ dò từ khóa cấm KHÔNG bắt được stub rò — mọi kết luận 'rò = 0' trong "
        "báo cáo là vô nghĩa từ thời điểm này."
    )


def test_banned_keyword_detection_ignores_accents(harness):
    """Bộ dò phải bắt được từ khóa dù khác dấu/hoa thường — người dùng Việt hay gõ vậy."""
    haystack = harness._normalize("Săn Mãi Siêu Tốc và SĂN MÃI cả ngày")
    caught = [kw for kw in harness.BANNED_KEYWORDS if harness._normalize(kw) in haystack]
    assert "săn mãi" in caught


def test_placeholder_detector_catches_unfilled_context(harness):
    """ĐỐI CHỨNG ÂM cho bộ dò placeholder.

    `_unfilled_placeholders` là hàm thô, chạy trên chuỗi CHƯA lấp đầy — nên ở đây
    mọi placeholder đều được coi là sót. Bước khác nhau là `_render`, và test
    `test_base_context_fills_every_placeholder_in_every_variant` kiểm tra việc đó
    trên dữ liệu thật của `prompts.json`.
    """
    unfilled = harness._unfilled_placeholders("Xin chào {{campaign_name}}, giá {{khong_ton_tai}}")
    assert "campaign_name" in unfilled
    assert "khong_ton_tai" in unfilled

    # Sau khi render với ngữ cảnh có thật, placeholder đã biết phải biến mất.
    rendered = harness._render("Xin chào {{campaign_name}}", harness.BASE_CONTEXT)
    assert harness._unfilled_placeholders(rendered) == []


def test_base_context_fills_every_placeholder_in_every_variant(harness):
    """Không được còn placeholder sót trong bất kỳ prompt nào.

    Placeholder sót nghĩa là prompt gửi nguyên chữ `{{...}}` tới mô hình — mô hình
    sẽ chế ra chữ đó thành nội dung quảng cáo. Đây là loại lỗi mà mắt thường bỏ sót
    vì nó chỉ xuất hiện ở một biến thể của ngữ cảnh.
    """
    prompts = harness.load_prompts()
    problems: list = []
    for variant in harness.VARIANTS:
        for task_type in harness.STUBS:
            block = prompts.get(task_type, {}).get(variant)
            if not block:
                continue
            for field in ("system", "user"):
                rendered = harness._render(block.get(field, ""), harness.BASE_CONTEXT)
                leftover = harness._unfilled_placeholders(rendered)
                if leftover:
                    problems.append(f"{variant}/{task_type}/{field}: {leftover}")
    assert not problems, "Prompt còn placeholder chưa được lấp đầy:\n  " + "\n  ".join(problems)


def test_harness_is_deterministic(harness):
    """Chạy hai lần phải ra cùng kết quả — nếu không thì báo cáo không tái lập được."""
    prompts = harness.load_prompts()
    first = harness.summarise(harness.evaluate_variant("v3", prompts))
    second = harness.summarise(harness.evaluate_variant("v3", prompts))
    assert first == second


def test_main_writes_both_artifacts(capsys):
    """Chạy script thật phải sinh ra cả báo cáo markdown lẫn artifact JSON."""
    module = _load_module()
    exit_code = module.main()
    assert exit_code == 0

    report = ROOT_DIR / "docs" / "PROMPT_VARIANT_COMPARISON.md"
    artifact = ROOT_DIR / "scripts" / "prompt_variant_results.json"

    assert report.exists(), "Không sinh docs/PROMPT_VARIANT_COMPARISON.md"
    assert artifact.exists(), "Không sinh scripts/prompt_variant_results.json"

    text = report.read_text(encoding="utf-8")
    for heading in (
        "## 1. Phạm vi kết luận",
        "## 2. Bảng so sánh",
        "## 3. Chi tiết theo từng tác vụ",
        "## 4. Cái tiến và cái tụt",
        "## 5. Bộ đo có thật sự bắt được lỗi không?",
        "## 6. Cách tái lập",
        "## 7. Điều chưa làm",
    ):
        assert heading in text, f"Báo cáo thiếu mục: {heading}"

    data = json.loads(artifact.read_text(encoding="utf-8"))
    assert set(data["variants"]) == {"v1", "v2", "v3"}
    assert data["negative_control"]["banned_keyword_detector_works"] is True
    assert data["negative_control"]["placeholder_detector_works"] is True


def test_report_numbers_match_computed_results():
    """Số trong báo cáo phải khớp số tính được — báo cáo không được rời rạc dữ liệu.

    Đây là test quan trọng nhất về mặt liêm chính tài liệu: một báo cáo học thuật
    đẹp mà không bám dữ liệu thì tệ hơn không có báo cáo.
    """
    module = _load_module()
    module.main()

    text = (ROOT_DIR / "docs" / "PROMPT_VARIANT_COMPARISON.md").read_text(encoding="utf-8")
    artifact = json.loads((ROOT_DIR / "scripts" / "prompt_variant_results.json").read_text(encoding="utf-8"))

    for variant in ("v1", "v2", "v3"):
        summary = artifact["variants"][variant]["summary"]
        expected = f"{summary['schema_valid_rate']:.0f}% ({summary['schema_valid']}/{summary['cases']})"
        assert expected in text, (
            f"Báo cáo không chứa số schema_valid_rate của {variant}: mong đợi {expected!r}"
        )

    # Số liệu về bản thân báo cáo cũng phải được kiểm tra.
    assert "KHÔNG" in text, "Báo cáo phải nêu rõ điều mình không chứng minh"
    assert "Điều chưa làm" in text, "Báo cáo phải có mục khoảng trống còn lại"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))