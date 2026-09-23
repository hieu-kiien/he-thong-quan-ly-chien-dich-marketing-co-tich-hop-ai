import time
import json
import hashlib
import re
from typing import Dict, Any, Optional
import httpx
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import AILog
from app.services.ai.prompt_engine import prompt_engine

class AIService:
    def __init__(self):
        self._base_url = None
        self._api_key = None
        self._model = None
        self._timeout = None
        self._max_retries = None
        self._fallback_enabled = None

    @property
    def base_url(self) -> str:
        return self._base_url if self._base_url is not None else settings.AI_BASE_URL.rstrip("/")

    @base_url.setter
    def base_url(self, val: str):
        self._base_url = val

    @property
    def api_key(self) -> str:
        return self._api_key if self._api_key is not None else settings.AI_API_KEY

    @api_key.setter
    def api_key(self, val: str):
        self._api_key = val

    @property
    def model(self) -> str:
        return self._model if self._model is not None else settings.AI_MODEL

    @model.setter
    def model(self, val: str):
        self._model = val

    @property
    def timeout(self) -> int:
        return self._timeout if self._timeout is not None else settings.AI_TIMEOUT_SECONDS

    @timeout.setter
    def timeout(self, val: int):
        self._timeout = val

    @property
    def max_retries(self) -> int:
        return self._max_retries if self._max_retries is not None else settings.AI_MAX_RETRIES

    @max_retries.setter
    def max_retries(self, val: int):
        self._max_retries = val

    @property
    def fallback_enabled(self) -> bool:
        return self._fallback_enabled if self._fallback_enabled is not None else settings.AI_ENABLE_FALLBACK

    @fallback_enabled.setter
    def fallback_enabled(self, val: bool):
        self._fallback_enabled = val

    def _clean_json_response(self, text: str) -> Dict[str, Any]:
        """Làm sạch markdown code block (```json ... ```) để parse an toàn"""
        clean_text = text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_text)
        if match:
            clean_text = match.group(1).strip()
        return json.loads(clean_text)

    def _validate_task_output(self, task_code: str, data: Dict[str, Any], prompt_version: str):
        """Kiểm tra schema cấu trúc kết quả từ AI provider trước khi chấp nhận"""
        from app.schemas.schemas import AIIdeaResponse, AIDraftResponse, AISummaryResponse
        test_payload = {
            **data,
            "model_used": self.model,
            "prompt_version": prompt_version,
            "task_type": task_code
        }
        if task_code == "IDEA":
            AIIdeaResponse.model_validate(test_payload)
        elif task_code == "DRAFT":
            AIDraftResponse.model_validate(test_payload)
        elif task_code == "SUMMARY":
            AISummaryResponse.model_validate(test_payload)

    def _call_provider_with_retry(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "MarketFlow AI",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
        }

        url = f"{self.base_url}/chat/completions"

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["choices"][0]["message"]["content"]
                    elif resp.status_code == 429:
                        time.sleep(1.0 * (attempt + 1))
                        continue
                    else:
                        raise RuntimeError(f"AI Provider trả về lỗi HTTP {resp.status_code}: {resp.text}")
            except httpx.TimeoutException:
                last_error = "TIMEOUT"
            except Exception as e:
                last_error = str(e)

        raise RuntimeError(last_error or "Không thể kết nối AI Provider")

    def _generate_fallback(self, task_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Tự động sinh kết quả chuẩn nghiệp vụ khi provider chưa có key hoặc bị gián đoạn"""
        camp_name = context.get("campaign_name", "Chiến dịch Mùa Hè")
        prod_name = context.get("product_name", "Sản phẩm")
        usp = context.get("product_usp", "Chất lượng vượt trội")
        channel = context.get("channel_name", "Facebook")

        if task_type in ["idea_generation", "IDEA"]:
            return {
                "ideas": [
                    {
                        "id": 1,
                        "angle": "Tập trung vào lợi ích cốt lõi",
                        "headline": f"Khám phá sự khác biệt cùng {prod_name}",
                        "concept": f"Nhấn mạnh đặc tính {usp} giúp giải quyết nỗi đau khách hàng.",
                        "target_emotion": "Tò mò, hy vọng"
                    },
                    {
                        "id": 2,
                        "angle": "Câu chuyện thực tế (Storytelling)",
                        "headline": f"Một ngày thay đổi nhờ {prod_name}",
                        "concept": "Chia sẻ hành trình của khách hàng từ khi gặp khó khăn đến khi trải nghiệm sản phẩm.",
                        "target_emotion": "Đồng cảm, tin tưởng"
                    },
                    {
                        "id": 3,
                        "angle": "Bắt trend và phong cách trẻ trung",
                        "headline": f"Gen Z nói gì về {prod_name}?",
                        "concept": f"Sử dụng ngôn ngữ trendy trên kênh {channel} kết hợp visual bắt mắt.",
                        "target_emotion": "Hào hứng, sôi nổi"
                    },
                    {
                        "id": 4,
                        "angle": "So sánh trước và sau (Before/After)",
                        "headline": f"Trước và sau khi biết đến {usp}",
                        "concept": "Minh họa sự tiện lợi và khác biệt rõ rệt khi ứng dụng giải pháp.",
                        "target_emotion": "Thuyết phục"
                    },
                    {
                        "id": 5,
                        "angle": "Lời khuyên từ chuyên gia",
                        "headline": f"Bí quyết tối ưu hiệu quả cùng {prod_name}",
                        "concept": "Đưa ra 3 mẹo thực chiến hữu ích và lồng ghép sản phẩm tự nhiên.",
                        "target_emotion": "Tôn trọng, chuyên nghiệp"
                    }
                ],
                "warnings": ["Dữ liệu được tạo từ chế độ Smart Fallback (mạng ngoại vi không khả dụng)."],
                "assumptions": ["Giả định đối tượng khách hàng mục tiêu thuộc độ tuổi 18-35."]
            }
        elif task_type in ["content_draft", "DRAFT"]:
            selected_idea = context.get("selected_idea", "Ý tưởng nổi bật")
            return {
                "title": f"🔥 Đột phá trải nghiệm cùng {prod_name}!",
                "body": f"Bạn đang tìm kiếm giải pháp với tiêu chí {usp}?\n\n{selected_idea}\n\nĐừng bỏ lỡ cơ hội nâng tầm trải nghiệm của bạn ngay hôm nay cùng chúng tôi!\n\n#Marketing #{channel.replace(' ', '')} #{prod_name.replace(' ', '')}",
                "cta": "👉 Nhắn tin ngay để nhận tư vấn chi tiết!",
                "warnings": ["Bản nháp cần được nhân viên biên tập trước khi gửi Manager duyệt."],
                "assumptions": ["Sản phẩm đang sẵn sàng cung ứng trên thị trường."]
            }
        elif task_type in ["performance_summary", "SUMMARY"]:
            total_views = context.get("total_views", 0)
            total_clicks = context.get("total_clicks", 0)
            ctr = context.get("ctr", 0.0)
            roi = context.get("roi", 0.0)
            return {
                "executive_summary": f"Chiến dịch '{camp_name}' ghi nhận tổng cộng {total_views} lượt xem và {total_clicks} lượt click, đạt CTR {ctr}%.",
                "strengths": [
                    f"Kênh đạt tỷ lệ nhấp chuột tốt ({ctr}%), cho thấy nội dung hấp dẫn người xem.",
                    f"Tỷ suất sinh lời ROI ước tính {roi}% phản ánh hiệu quả ngân sách tích cực."
                ],
                "weaknesses": [
                    "Tỷ lệ chuyển đổi ở một số khung giờ chưa đồng đều.",
                    "Chi phí trung bình trên mỗi click (CPC) có xu hướng tăng nhẹ vào cuối tuần."
                ],
                "recommendations": [
                    "Tập trung ngân sách vào các bài viết có tương tác cao nhất.",
                    "Thử nghiệm A/B Testing tiêu đề mới để hạ giá thành mỗi click.",
                    "Lập lịch đăng bài vào khung giờ vàng (11h30 - 13h00 và 20h00 - 22h00)."
                ],
                "warnings": ["Số liệu phân tích dựa trên báo cáo hiện có trong CSDL."]
            }
        return {}

    def execute_task(
        self,
        db: Session,
        user_id: int,
        campaign_id: Optional[int],
        task_type: str, # 'idea_generation', 'content_draft', 'performance_summary'
        task_code: str, # 'IDEA', 'DRAFT', 'SUMMARY'
        prompt_version: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        start_time = time.time()
        system_prompt, user_prompt = prompt_engine.get_prompt(task_type, prompt_version, context)
        
        input_hash = hashlib.sha256((system_prompt + user_prompt).encode("utf-8")).hexdigest()

        result_status = "SUCCESS"
        error_code = None
        output_data = {}

        # Nếu không có API Key và bật Fallback -> Dùng Fallback trực tiếp
        if (not self.api_key or self.api_key.strip() == "") and self.fallback_enabled:
            output_data = self._generate_fallback(task_type, context)
            latency_ms = int((time.time() - start_time) * 1000)
            model_used = f"{self.model} (Fallback Mock)"
        else:
            try:
                raw_response = self._call_provider_with_retry(system_prompt, user_prompt)
                try:
                    output_data = self._clean_json_response(raw_response)
                    # BUG-BE-08: Kiểm tra tính hợp lệ của schema kết quả AI
                    self._validate_task_output(task_code, output_data, prompt_version)
                    latency_ms = int((time.time() - start_time) * 1000)
                    model_used = self.model
                except (json.JSONDecodeError, ValidationError) as schema_err:
                    result_status = "SCHEMA_ERROR"
                    error_code = "ERR_INVALID_SCHEMA" if isinstance(schema_err, ValidationError) else "ERR_INVALID_JSON"
                    if self.fallback_enabled:
                        output_data = self._generate_fallback(task_type, context)
                        msg = "Mô hình AI trả về sai cấu trúc schema; đã tự động kích hoạt chế độ Smart Fallback." if isinstance(schema_err, ValidationError) else "Model trả về sai JSON, hệ thống tự động bẫy lỗi và sinh dữ liệu dự phòng an toàn."
                        output_data.setdefault("warnings", []).append(msg)
                        model_used = f"{self.model} (Auto-recovered)"
                        latency_ms = int((time.time() - start_time) * 1000)
                    else:
                        latency_ms = int((time.time() - start_time) * 1000)
                        self._log_call(db, user_id, campaign_id, task_code, self.model, prompt_version, input_hash, None, result_status, error_code, latency_ms)
                        raise schema_err
            except Exception as e:
                if result_status != "SCHEMA_ERROR":
                    err_str = str(e)
                    if "TIMEOUT" in err_str:
                        result_status = "TIMEOUT"
                        error_code = "ERR_AI_TIMEOUT"
                    else:
                        result_status = "PROVIDER_ERROR"
                        error_code = "ERR_PROVIDER"

                    if self.fallback_enabled:
                        output_data = self._generate_fallback(task_type, context)
                        output_data.setdefault("warnings", []).append(f"Lỗi AI ({err_str}), đã kích hoạt chế độ dự phòng an toàn.")
                        latency_ms = int((time.time() - start_time) * 1000)
                        model_used = f"{self.model} (Failover Fallback)"
                    else:
                        latency_ms = int((time.time() - start_time) * 1000)
                        self._log_call(db, user_id, campaign_id, task_code, self.model, prompt_version, input_hash, None, result_status, error_code, latency_ms)
                        raise e

        # Ghi log vào bảng ai_logs
        self._log_call(
            db=db,
            user_id=user_id,
            campaign_id=campaign_id,
            task_type=task_code,
            model=model_used,
            prompt_version=prompt_version,
            input_hash=input_hash,
            output_json=json.dumps(output_data, ensure_ascii=False),
            result_status=result_status,
            error_code=error_code,
            latency_ms=latency_ms
        )

        output_data["model_used"] = model_used
        output_data["prompt_version"] = prompt_version
        output_data["task_type"] = task_code
        return output_data

    def _log_call(
        self,
        db: Session,
        user_id: int,
        campaign_id: Optional[int],
        task_type: str,
        model: str,
        prompt_version: str,
        input_hash: str,
        output_json: Optional[str],
        result_status: str,
        error_code: Optional[str],
        latency_ms: int
    ):
        try:
            log_entry = AILog(
                user_id=user_id,
                campaign_id=campaign_id,
                task_type=task_type,
                provider=settings.AI_PROVIDER,
                model=model,
                prompt_version=prompt_version,
                input_hash=input_hash,
                output_json=output_json,
                result_status=result_status,
                error_code=error_code,
                latency_ms=latency_ms
            )
            db.add(log_entry)
            db.commit()
        except Exception:
            db.rollback()

ai_service = AIService()
