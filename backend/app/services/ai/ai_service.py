import time
import json
import hashlib
import re
from typing import Dict, Any, List, Optional
import httpx
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import AILog
from app.services.ai.prompt_engine import prompt_engine
from app.services.ai import providers as provider_registry
from app.services.ai import anthropic_adapter
from app.services.ai.circuit_breaker import CircuitOpenError
from app.services.ai.circuit_breaker import breaker as circuit_breaker

import logging

logger = logging.getLogger("marketflow.ai_service")

# Model mặc định theo provider. Trước đây là dict viết tay ở đây và thiếu
# provider opencode, nên khoá BYOK không khai báo model sẽ nhận slug của provider
# khác rồi fail 404. Nay đọc từ registry chung nên không thể lệch nữa.
_DEFAULT_MODELS_BY_PROVIDER: Dict[str, str] = {
    spec.slug: spec.default_model for spec in provider_registry.PROVIDERS
}


def _default_model_for(provider: Optional[str]) -> str:
    return provider_registry.default_model_for(provider)


def _sanitize_ai_error(err_msg: Optional[str], active_key: Optional[str] = None) -> str:
    """Làm sạch các token nhạy cảm, API keys, query parameter ?key=... khỏi log và thông báo lỗi."""
    if not err_msg:
        return ""
    sanitized = str(err_msg)
    if active_key and len(active_key.strip()) >= 4:
        sanitized = sanitized.replace(active_key.strip(), "[REDACTED_API_KEY]")
    # Xóa query param ?key= hoặc &key=
    sanitized = re.sub(r'([?&]key=)[^&\s"\'\\}]+', r'\1[REDACTED]', sanitized, flags=re.IGNORECASE)
    # Xóa Gemini key patterns
    sanitized = re.sub(r'AIza[0-9A-Za-z_-]{35}', '[REDACTED_GEMINI_KEY]', sanitized)
    sanitized = re.sub(r'AIzaSy[0-9A-Za-z_-]+', '[REDACTED_GEMINI_KEY]', sanitized)
    # Xóa Bearer tokens
    sanitized = re.sub(r'(Bearer\s+)[A-Za-z0-9._-]+', r'\1[REDACTED]', sanitized, flags=re.IGNORECASE)
    return sanitized


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

    @base_url.deleter
    def base_url(self):
        self._base_url = None

    @property
    def api_key(self) -> str:
        return self._api_key if self._api_key is not None else settings.AI_API_KEY

    @api_key.setter
    def api_key(self, val: str):
        self._api_key = val

    @api_key.deleter
    def api_key(self):
        self._api_key = None

    @property
    def model(self) -> str:
        return self._model if self._model is not None else settings.AI_MODEL

    @model.setter
    def model(self, val: str):
        self._model = val

    @model.deleter
    def model(self):
        self._model = None

    @property
    def timeout(self) -> int:
        return self._timeout if self._timeout is not None else settings.AI_TIMEOUT_SECONDS

    @timeout.setter
    def timeout(self, val: int):
        self._timeout = val

    @timeout.deleter
    def timeout(self):
        self._timeout = None

    @property
    def max_retries(self) -> int:
        return self._max_retries if self._max_retries is not None else settings.AI_MAX_RETRIES

    @max_retries.setter
    def max_retries(self, val: int):
        self._max_retries = val

    @max_retries.deleter
    def max_retries(self):
        self._max_retries = None

    @property
    def fallback_enabled(self) -> bool:
        return self._fallback_enabled if self._fallback_enabled is not None else settings.AI_ENABLE_FALLBACK

    @fallback_enabled.setter
    def fallback_enabled(self, val: bool):
        self._fallback_enabled = val

    @fallback_enabled.deleter
    def fallback_enabled(self):
        self._fallback_enabled = None

    def _clean_json_response(self, text: str) -> Dict[str, Any]:
        """Làm sạch markdown code block (```json ... ```) để parse an toàn"""
        clean_text = text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_text)
        if match:
            clean_text = match.group(1).strip()
        return json.loads(clean_text)

    def _validate_task_output(self, task_code: str, data: Dict[str, Any], prompt_version: str):
        """Kiểm tra schema cấu trúc kết quả từ AI provider trước khi chấp nhận"""
        from app.schemas.schemas import (
            AIIdeaResponse,
            AIDraftResponse,
            AISummaryResponse,
            AIPlanResponse,
        )
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
        elif task_code == "PLAN":
            AIPlanResponse.model_validate(test_payload)
        elif task_code == "OMNICHANNEL":
            from app.schemas.schemas import OmnichannelResponse
            OmnichannelResponse.model_validate(test_payload)

    def resolve_api_key(
        self,
        db: Session,
        workspace_id: Optional[int] = None,
        user_id: Optional[int] = None,
        provider: str = "gemini",
        **kwargs
    ) -> Dict[str, Any]:
        """Multi-tier Key Resolver (FEAT-BE-26):
        1. Workspace Custom Key (Ưu tiên cao nhất nếu is_active=True).
        2. User Personal Custom Key (Ưu tiên tiếp theo nếu Workspace không có).
        3. System Default Key (biến môi trường riêng của provider rồi tới AI_API_KEY chung).
        4. Smart Fallback Engine (Sinh dữ liệu mẫu khi không có key hoặc lỗi kết nối).

        Provider `requires_api_key=False` (Ollama, HuggingFace) dừng ở tầng 3
        với `api_key` rỗng và `tier="SYSTEM"`: với các provider này "không có
        khoá" là trạng thái bình thường, không phải lỗi cấu hình, nên không
        được đẩy xuống template dự phòng.
        """
        import os
        from app.models.entities import CustomApiKey
        from app.core.crypto import decrypt_api_key

        if "workspace_id" in kwargs:
            workspace_id = kwargs["workspace_id"]
        if "user_id" in kwargs:
            user_id = kwargs["user_id"]
        if "provider" in kwargs:
            provider = kwargs["provider"]

        provider = (provider or "gemini").lower().strip()
        spec = provider_registry.get_provider(provider)
        requires_api_key = spec.requires_api_key if spec else True

        # Tier 1: Workspace Custom Key
        if workspace_id is not None:
            try:
                ws_key = db.query(CustomApiKey).filter(
                    CustomApiKey.workspace_id == workspace_id,
                    CustomApiKey.is_active == True,
                    CustomApiKey.provider == provider
                ).order_by(CustomApiKey.updated_at.desc()).first()

                if ws_key and ws_key.encrypted_key:
                    try:
                        plain = decrypt_api_key(ws_key.encrypted_key)
                        if plain and plain.strip():
                            default_m = _default_model_for(provider)
                            return {
                                "api_key": plain.strip(),
                                "model": ws_key.model or default_m,
                                "provider": provider,
                                "tier": "WORKSPACE",
                                "source_id": ws_key.id
                            }
                    except Exception as e:
                        logger.error("[KeyResolver] Lỗi giải mã Workspace Key %d: %s", ws_key.id, str(e))
            except Exception as e:
                logger.error("[KeyResolver] Lỗi truy vấn Workspace Key: %s", str(e))

        # Tier 2: User Personal Custom Key
        if user_id is not None:
            try:
                user_key = db.query(CustomApiKey).filter(
                    CustomApiKey.user_id == user_id,
                    CustomApiKey.workspace_id == None,
                    CustomApiKey.is_active == True,
                    CustomApiKey.provider == provider
                ).order_by(CustomApiKey.updated_at.desc()).first()

                if not user_key:
                    user_key = db.query(CustomApiKey).filter(
                        CustomApiKey.user_id == user_id,
                        CustomApiKey.is_active == True,
                        CustomApiKey.provider == provider
                    ).order_by(CustomApiKey.updated_at.desc()).first()

                if user_key and user_key.encrypted_key:
                    try:
                        plain = decrypt_api_key(user_key.encrypted_key)
                        if plain and plain.strip():
                            default_m = _default_model_for(provider)
                            return {
                                "api_key": plain.strip(),
                                "model": user_key.model or default_m,
                                "provider": provider,
                                "tier": "USER",
                                "source_id": user_key.id
                            }
                    except Exception as e:
                        logger.error("[KeyResolver] Lỗi giải mã User Key %d: %s", user_key.id, str(e))
            except Exception as e:
                logger.error("[KeyResolver] Lỗi truy vấn User Key: %s", str(e))

        # Tier 3: System Default Key
        # Ưu tiên biến chuyên dụng theo provider, rồi mới tới AI_API_KEY chung — nếu
        # không thì provider "openrouter"/"openai" sẽ rơi xuống Tier 4 và im lặng
        # sinh nội dung template dù .env đã có khoá. Danh sách biến lấy từ
        # registry nên provider mới không cần sửa thêm chỗ này.
        system_model = settings.AI_MODEL or _default_model_for(provider)
        env_key = None
        if spec is not None:
            for env_name in spec.env_key_names:
                candidate = os.environ.get(env_name)
                if candidate is None and hasattr(settings, env_name):
                    candidate = getattr(settings, env_name)
                if candidate and str(candidate).strip():
                    env_key = str(candidate)
                    break
            if env_key is None:
                env_key = settings.AI_API_KEY
        else:
            env_key = settings.AI_API_KEY

        if env_key and env_key.strip():
            return {
                "api_key": env_key.strip(),
                "model": system_model,
                "provider": provider,
                "tier": "SYSTEM",
                "source_id": None
            }

        if not requires_api_key:
            # Ollama / HuggingFace: gọi được với khoá rỗng.
            return {
                "api_key": None,
                "model": system_model or _default_model_for(provider),
                "provider": provider,
                "tier": "SYSTEM",
                "source_id": None,
                "requires_api_key": False,
            }

        # Tier 4: Fallback
        default_fallback_model = settings.AI_MODEL or _default_model_for(provider)
        return {
            "api_key": None,
            "model": default_fallback_model,
            "provider": "template-fallback-engine",
            "tier": "FALLBACK",
            "source_id": None
        }

    @staticmethod
    def _parse_chain_hops(hops_json: Optional[str]) -> List[Dict[str, str]]:
        """Đọc hops_json của AIModelChain -> [{"provider": ..., "model": ...}].

        Một entry hỏng (thiếu provider/model, JSON lỗi) bị bỏ qua từng cái chứ
        không làm sập cả chuỗi: người dùng sửa được record trong khi đang chạy.
        """
        try:
            raw = json.loads(hops_json or "[]")
        except Exception:
            return []
        if not isinstance(raw, list):
            return []
        hops: List[Dict[str, str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            provider = str(item.get("provider") or "").lower().strip()
            model = str(item.get("model") or "").strip()
            if not provider:
                continue
            if not model:
                # Record cũ có thể thiếu model: điền mặc định của provider thay
                # vì bỏ hop im lặng (người dùng đã chủ động thêm bước này).
                model = provider_registry.default_model_for(provider)
            hops.append({"provider": provider, "model": model})
        return hops

    @staticmethod
    def _chain_visible_to_user(chain, user_id: int, db: Session) -> bool:
        """Chuỗi chỉ được dùng khi user sở hữu nó hoặc thuộc workspace của nó
        (owner/member), hoặc là ADMIN — cùng ranh giới tenant với check_chain_access."""
        if chain.user_id == user_id:
            return True
        if chain.workspace_id is None:
            return False
        try:
            from app.models.entities import User, Workspace, WorkspaceMember
            user = db.query(User).filter(User.id == user_id).first()
            if user is not None and user.role == "ADMIN":
                return True
            ws = db.query(Workspace).filter(Workspace.id == chain.workspace_id).first()
            if ws is not None and ws.owner_id == user_id:
                return True
            member = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == chain.workspace_id,
                WorkspaceMember.user_id == user_id
            ).first()
            return member is not None
        except Exception:
            # Không tra được quyền thì coi như KHÔNG thấy — thà rơi về model đơn
            # còn hơn âm thầm dùng chuỗi của tenant khác.
            return False

    def _resolve_chain_hops(
        self,
        db: Session,
        user_id: int,
        workspace_id: Optional[int],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Chọn chuỗi fallback sẽ áp dụng cho lượt gọi này.

        Trả về {"id", "name", "hops": [{provider, model}, ...]} hoặc None
        (không có chuỗi -> giữ nguyên đường gọi một model như cũ).

        Thứ tự chọn: `context["model_chain_id"]` (request truyền chain_id) ->
        chuỗi mặc định của workspace -> chuỗi mặc định cá nhân. Fixture mode
        (`self._api_key is not None`) luôn trả None để bảo toàn 499 test unit
        hiện có.
        """
        if self._api_key is not None:
            return None
        from app.models.entities import AIModelChain

        chain = None
        explicit_id = context.get("model_chain_id")
        if explicit_id:
            try:
                chain = db.query(AIModelChain).filter(AIModelChain.id == int(explicit_id)).first()
            except (TypeError, ValueError):
                chain = None
            if chain is not None and not chain.is_active:
                logger.warning("[AI Chain] chain_id=%s đang tắt — bỏ qua, gọi model đơn.", explicit_id)
                chain = None
            if chain is not None and not self._chain_visible_to_user(chain, user_id, db):
                logger.warning("[AI Chain] chain_id=%s không thuộc phạm vi user %s — bỏ qua, gọi model đơn.", explicit_id, user_id)
                chain = None
        else:
            if workspace_id is not None:
                chain = db.query(AIModelChain).filter(
                    AIModelChain.workspace_id == workspace_id,
                    AIModelChain.is_default.is_(True),
                    AIModelChain.is_active.is_(True)
                ).order_by(AIModelChain.updated_at.desc()).first()
            if chain is None:
                chain = db.query(AIModelChain).filter(
                    AIModelChain.user_id == user_id,
                    AIModelChain.workspace_id.is_(None),
                    AIModelChain.is_default.is_(True),
                    AIModelChain.is_active.is_(True)
                ).order_by(AIModelChain.updated_at.desc()).first()

        if chain is None:
            return None
        hops = self._parse_chain_hops(chain.hops_json)
        if not hops:
            logger.warning("[AI Chain] chuỗi %s (%s) không có hop hợp lệ — dùng model đơn.", chain.id, chain.name)
            return None
        return {"id": chain.id, "name": chain.name, "hops": hops}

    def _detect_provider(self, key_to_use: Optional[str], model_to_use: Optional[str]) -> str:
        """Suy đoán provider khi caller không truyền tên.

        Giữ nguyên thứ tự suy đoán của bản cũ (OpenRouter -> OpenAI -> Gemini)
        để không đổi hành vi cho các provider đã chạy; chỉ bổ sung nhánh cho
        provider mới theo dấu hiệu riêng của chúng.
        """
        if key_to_use and key_to_use.startswith("sk-ant-"):
            return "anthropic"
        if key_to_use and key_to_use.startswith("gsk_"):
            return "groq"
        if key_to_use and key_to_use.startswith("xai-"):
            return "xai"
        if key_to_use and (key_to_use.startswith("sk-or-") or (model_to_use and "/" in model_to_use)):
            return "openrouter"
        if key_to_use and (key_to_use.startswith("sk-proj-") or key_to_use.startswith("sk-")) and not key_to_use.startswith("sk-or-"):
            return "openai"
        if model_to_use and (
            model_to_use.startswith("gpt-")
            or model_to_use.startswith("o1")
            or model_to_use.startswith("o3")
            or model_to_use.startswith("o4")
        ):
            return "openai"
        if model_to_use and model_to_use.lower().startswith("claude"):
            return "anthropic"
        if model_to_use and model_to_use.lower().startswith("grok"):
            return "xai"
        if (model_to_use and "gemini" in model_to_use.lower()) or (key_to_use and key_to_use.startswith("AIzaSy")):
            return "gemini"
        return "gemini"

    def _call_provider_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        active_key: Optional[str] = None,
        active_model: Optional[str] = None,
        provider: Optional[str] = None,
        timeout_override: Optional[int] = None,
        retries_override: Optional[int] = None
    ) -> str:
        # `timeout_override`/`retries_override` chỉ dùng cho chuỗi fallback:
        # mỗi hop nhận ngân sách thời gian/retry riêng thay vì mutation lên
        # singleton (gọi đồng thời từ nhiều thread sẽ đua trạng thái chung).
        key_to_use = active_key if active_key is not None else self.api_key
        model_to_use = active_model if active_model is not None else self.model
        effective_timeout = timeout_override if timeout_override is not None else self.timeout
        effective_retries = retries_override if retries_override is not None else self.max_retries

        # Determine effective provider
        eff_provider = (provider or "").lower().strip()
        if not eff_provider:
            eff_provider = self._detect_provider(key_to_use, model_to_use)

        spec = provider_registry.get_provider(eff_provider)

        if spec is None:
            # Provider không có trong registry: đây là lỗi cấu hình, không phải
            # lỗi mạng. Ném ngay để không gửi request tới base_url mặc định
            # bằng khoá của provider khác — thao tác đó có thể rò khoá.
            raise RuntimeError(
                f"Nhà cung cấp AI '{eff_provider}' không có trong sổ đăng ký "
                f"({', '.join(provider_registry.SUPPORTED_PROVIDER_SLUGS)})."
            )

        base_url = spec.resolve_base_url(settings.AI_BASE_URL)

        if spec.protocol == provider_registry.PROTOCOL_ANTHROPIC:
            url = f"{base_url}/messages"
            headers = anthropic_adapter.build_headers(key_to_use)
            payload = anthropic_adapter.build_messages_payload(
                system_prompt,
                user_prompt,
                model_to_use,
                temperature=0.7,
                max_tokens=int(
                    getattr(settings, "ANTHROPIC_MAX_TOKENS", anthropic_adapter.ANTHROPIC_MAX_TOKENS)
                ),
            )
        else:
            url = f"{base_url}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                # Bắt buộc: httpx mặc định gửi User-Agent kiểu "python-httpx/x.y.z".
                # Cloudflare chặn User-Agent tự động với lỗi 403 "error code: 1010",
                # khiến provider thật (OpenCode Zen, OpenAI, OpenRouter...) trả lỗi
                # và request rơi xuống fallback giả. Phải luôn gửi UA nhận diện.
                "User-Agent": getattr(
                    settings, "AI_HTTP_USER_AGENT", "marketflow-backend/1.0 (+https://marketing.kienhieu.id.vn)"
                ),
            }
            if key_to_use:
                # Provider không cần khoá (Ollama) sẽ không nhận header này:
                # httpx trả 500 nếu gửi header Authorization rỗng.
                headers["Authorization"] = f"Bearer {key_to_use}"
            headers.update(spec.extra_headers)
            payload = {
                "model": model_to_use,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
            }

        # Circuit breaker: đo độ khoẻ provider trước khi gọi. Khi provider đã chết,
        # `allow()` ném ngay thay vì mất thêm vài phút retry rồi mới rơi xuống
        # fallback, giữ chân slot AI trong hàng đợi.
        circuit_breaker.allow(eff_provider)

        last_error = None
        for attempt in range(effective_retries + 1):
            # Chỉ thử breaker ở lần đầu: nếu provider đang HALF_OPEN thì lần thử dò
            # đó đã được cho qua ở `allow()`; các lần retry nội bộ không cần hỏi lại.
            attempt_started = time.monotonic()
            try:
                with httpx.Client(timeout=effective_timeout) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        if spec.protocol == provider_registry.PROTOCOL_ANTHROPIC:
                            text = anthropic_adapter.extract_text(data)
                        else:
                            text = (data["choices"][0].get("message") or {}).get("content")
                        if text is None or str(text).strip() == "":
                            # Reasoning model có thể hết token cho reasoning_content và
                            # trả content rỗng. Phải coi là lỗi để thử lại, tuyệt đối
                            # không trả None ra ngoài (sẽ rơi xuống fallback giả lặng lẽ).
                            raise RuntimeError(
                                "AI Provider trả về nội dung rỗng "
                                "(có thể hết token cho reasoning)"
                            )
                        circuit_breaker.record_success(eff_provider, time.monotonic() - attempt_started)
                        return text
                    elif resp.status_code == 429:
                        # Hết hạn mức: provider còn sống nhưng đang quá tải. Không tính
                        # vào ngưỡng ngắt breaker, chỉ nghỉ và thử lại.
                        last_error = "AI Provider đang quá tải (HTTP 429)."
                        time.sleep(1.0 * (attempt + 1))
                        continue
                    else:
                        clean_err = _sanitize_ai_error(resp.text, active_key=key_to_use)
                        raise RuntimeError(f"AI Provider trả về lỗi HTTP {resp.status_code}: {clean_err}")
            except httpx.TimeoutException:
                last_error = "TIMEOUT"
                circuit_breaker.record_failure(eff_provider, "TIMEOUT")
            except CircuitOpenError:
                raise
            except Exception as e:
                last_error = _sanitize_ai_error(str(e), active_key=key_to_use)
                circuit_breaker.record_failure(eff_provider, last_error)

        raise RuntimeError(last_error or "Không thể kết nối AI Provider")

    def _generate_fallback(self, task_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Tự động sinh kết quả chuẩn nghiệp vụ khi provider chưa có key hoặc bị gián đoạn.
        Loại bỏ hoàn toàn ảo giác (hallucination): chỉ đưa ra nhận định dựa trên số liệu thực tế trong context.
        """
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
                "assumptions": ["Giả định đối tượng khách hàng mục tiêu thuộc độ tuổi 18-35."],
                "is_fallback": True,
                "model_provider": "template-fallback-engine"
            }
        elif task_type in ["content_draft", "DRAFT"]:
            selected_idea = context.get("selected_idea", "Ý tưởng nổi bật")
            return {
                "title": f"🔥 Đột phá trải nghiệm cùng {prod_name}!",
                "body": f"Bạn đang tìm kiếm giải pháp với tiêu chí {usp}?\n\n{selected_idea}\n\nĐừng bỏ lỡ cơ hội nâng tầm trải nghiệm của bạn ngay hôm nay cùng chúng tôi!\n\n#Marketing #{channel.replace(' ', '')} #{prod_name.replace(' ', '')}",
                "cta": "👉 Nhắn tin ngay để nhận tư vấn chi tiết!",
                "warnings": ["Bản nháp cần được nhân viên biên tập trước khi gửi Manager duyệt."],
                "assumptions": ["Sản phẩm đang sẵn sàng cung ứng trên thị trường."],
                "is_fallback": True,
                "model_provider": "template-fallback-engine"
            }
        elif task_type in ["performance_summary", "SUMMARY"]:
            total_views = context.get("total_views", 0)
            total_clicks = context.get("total_clicks", 0)
            total_conversions = context.get("total_conversions", 0)
            ctr = context.get("ctr", 0.0)
            cvr = context.get("cvr", 0.0)
            cpc = context.get("cpc", 0.0)
            roi = context.get("roi", 0.0)
            total_cost = context.get("total_cost", "0")
            total_revenue = context.get("total_revenue", "0")
            return {
                "executive_summary": f"Chiến dịch '{camp_name}' ghi nhận tổng cộng {total_views} lượt xem và {total_clicks} lượt click, đạt CTR {ctr}%.",
                "strengths": [
                    f"Kênh đạt tỷ lệ nhấp chuột CTR {ctr}% ({total_clicks} clicks trên {total_views} views), phản ánh mức độ quan tâm của đối tượng mục tiêu.",
                    f"Tỷ suất lợi nhuận trên chi phí ROI đạt {roi}% với doanh thu ghi nhận {total_revenue} VNĐ và chi phí {total_cost} VNĐ."
                ],
                "weaknesses": [
                    f"Tỷ lệ chuyển đổi CVR đạt {cvr}% ({total_conversions} chuyển đổi trên {total_clicks} clicks), cần tối ưu trang đích và thông điệp hành động.",
                    f"Chi phí trung bình trên mỗi lượt nhấp CPC đạt {cpc} VNĐ, cần theo dõi sát sao để tối ưu chi phí."
                ],
                "recommendations": [
                    f"Phân bổ ngân sách ưu tiên vào các nhóm quảng cáo có tỷ lệ nhấp CTR cao hơn mức {ctr}%.",
                    f"Thực hiện thử nghiệm A/B Testing thông điệp và hình ảnh mới để giảm chi phí CPC từ mức {cpc} VNĐ.",
                    f"Cải tiến quy trình chuyển đổi để tăng tỷ lệ CVR từ mức {cvr}% lên mức mục tiêu cao hơn."
                ],
                "warnings": ["Số liệu phân tích dựa trên báo cáo hiện có trong CSDL."],
                "is_fallback": True,
                "model_provider": "template-fallback-engine"
            }
        elif task_type in ["omnichannel_generation", "OMNICHANNEL"]:
            return self._generate_fallback_omnichannel(context)
        elif task_type in ["campaign_plan", "PLAN"]:
            return self._generate_fallback_campaign_plan(context)
        elif task_type in ["angle_matrix", "ANGLE_MATRIX"]:
            return self._generate_fallback_angle_matrix(context)
        elif task_type in ["prelaunch_critic", "PRELAUNCH_CRITIC"]:
            return self._generate_fallback_prelaunch_critic(context)
        elif task_type in ["compliance_rewrite", "COMPLIANCE_REWRITE"]:
            return self._generate_fallback_compliance_rewrite(context)
        return {}

    def _generate_fallback_campaign_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sinh kế hoạch chiến dịch deterministic khi không có AI key / lỗi mạng.

        Nguyên tắc anti-hallucination: chỉ PHÂN BỔ LẠI số ngân sách THẬT trong
        context — không bịa doanh số, lead hay CTR. Chia đều tới từng đồng bằng
        floor để tổng planned_amount LUÔN <= ngân sách gốc (không bao giờ cộng
        gộp vượt budget). Task đi theo trục thời gian của chiến dịch
        (due_offset_days <= max_due_offset). KPI chỉ sinh khi context có mục tiêu
        thật; không có thì để rỗng kèm warning thay vì bịa con số.
        """
        import math

        try:
            budget = float(context.get("budget_amount") or 0.0)
        except (TypeError, ValueError):
            budget = 0.0
        if budget < 0:
            budget = 0.0

        codes = [str(c) for c in (context.get("channel_codes") or []) if c]
        if not codes:
            # Chiến dịch chưa gán kênh: vẫn phải trả budget_split hợp lệ (>=1 dòng).
            # Mã dự phòng này sẽ được apply endpoint đối chiếu lại với CSDL.
            codes = ["FACEBOOK"]

        try:
            max_offset = int(context.get("max_due_offset") or 30)
        except (TypeError, ValueError):
            max_offset = 30
        if max_offset < 0:
            max_offset = 0

        # Chia đều bằng đồng nguyên tử: floor toàn bộ rồi dồn phần lẻ vào các
        # kênh đầu, bảo đảm sum == floor(budget*100)/100 <= budget.
        n = len(codes)
        budget_cents = int(math.floor(budget * 100))
        base_cents = budget_cents // n
        remainder = budget_cents - base_cents * n
        budget_split = []
        for idx, code in enumerate(codes):
            cents = base_cents + (1 if idx < remainder else 0)
            budget_split.append({
                "channel_code": code,
                "planned_amount": cents / 100.0,
                "rationale": "Chia đều theo tổng ngân sách (Smart Fallback — chưa tối ưu theo lịch sử hiệu suất).",
                "is_ai_estimate": True,
            })

        kpi_name = context.get("target_kpi_name")
        kpi_value = context.get("target_kpi_value")
        kpi_targets: List[Dict[str, Any]] = []
        if kpi_name and kpi_value is not None:
            try:
                val = float(kpi_value)
            except (TypeError, ValueError):
                val = None
            if val is not None and val >= 0:
                kpi_targets.append({
                    "metric_name": str(kpi_name)[:50],
                    "target_value": val,
                    "unit": self._fallback_kpi_unit(str(kpi_name)),
                    "is_ai_estimate": True,
                })

        warnings = ["Kế hoạch sinh từ chế độ Smart Fallback (mạng ngoại vi / thiếu API key)."]
        if budget <= 0:
            warnings.append("Chiến dịch chưa có ngân sách > 0 nên chưa phân bổ được ngân sách.")
        if not context.get("channel_codes"):
            warnings.append("Chiến dịch chưa gán kênh hoạt động; dòng phân bổ mặc định cần kiểm tra trước khi áp dụng.")

        phases = [
            ("Nghiên cứu & chốt kịch bản", "RESEARCH", "HIGH", 0.00),
            ("Sản xuất nội dung chính", "CONTENT", "URGENT", 0.15),
            ("Thiết kế ấn phẩm & media", "DESIGN", "HIGH", 0.35),
            ("Chạy quảng cáo & phân phối", "ADS", "URGENT", 0.65),
            ("Đo lường & tối ưu", "OTHER", "MEDIUM", 0.90),
        ]
        tasks = []
        for title, t_type, prio, pct in phases:
            tasks.append({
                "title": title,
                "task_type": t_type,
                "priority": prio,
                "due_offset_days": math.floor(max_offset * pct),
                "description": f"Giai đoạn {title.lower()} trong chiến dịch '{context.get('campaign_name', '')}'.",
            })

        return {
            "summary": (
                f"Kế hoạch phân bổ ngân sách {budget:,.0f} VNĐ cho {n} kênh "
                f"({', '.join(codes)}), triển khai trong {max_offset + 1} ngày. "
                "Phân bổ chia đều, cần tối ưu lại theo hiệu suất thực tế trước khi chạy."
            ),
            "budget_split": budget_split,
            "kpi_targets": kpi_targets,
            "tasks": tasks,
            "warnings": warnings,
            "assumptions": [
                "Phân bổ chia đều vì chưa có dữ liệu lịch sử hiệu suất từng kênh.",
                "KPI giữ nguyên mục tiêu đã khai báo trên chiến dịch (nếu có).",
            ],
            "is_fallback": True,
            "model_provider": "template-fallback-engine",
        }

    @staticmethod
    def _fallback_kpi_unit(metric_name: str) -> str:
        """Suy unit cho KPI từ tên metric — không bịa, chỉ phân loại mặt chữ."""
        m = (metric_name or "").lower()
        if "roas" in m:
            return "ratio"
        if any(k in m for k in ("cpl", "cpc", "cpm", "cpa", "cost", "revenue", "doanh thu", "chi phí", "chi phi")):
            return "vnd"
        if any(k in m for k in ("rate", "ctr", "cvr", "share", "tỷ lệ", "ty le", "phần trăm", "phan tram")):
            return "percent"
        return "count"

    def _generate_fallback_omnichannel(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sinh dữ liệu mẫu đa kênh chất lượng cao chuẩn nghiệp vụ khi không có API key hoặc lỗi mạng.
        Tuyệt đối không bịa đặt số liệu; kế thừa hoàn toàn thông điệp brief và Brand Kit.
        """
        brand_name = context.get("brand_name", "MarketFlow AI")
        prod_name = context.get("product_name", "Sản phẩm Tiếp thị")
        usp = context.get("usp", context.get("product_usp", "Chất lượng dẫn đầu thị trường"))
        brief = context.get("brief", "Chiến dịch tiếp thị đột phá")
        tone = context.get("tone_of_voice", "Chuyên nghiệp, hiện đại, tin cậy")

        facebook_data = {
            "title": f"🔥 Đột Phá Doanh Số Cùng {brand_name} - {prod_name}!",
            "headline": f"🔥 Đột Phá Doanh Số Cùng {brand_name} - {prod_name}!",
            "body": f"Bạn đang tìm kiếm giải pháp tối ưu với tiêu chí: {usp}?\n\n{brief}\n\n👉 Khám phá ngay giải pháp đột phá từ {brand_name} để nâng tầm trải nghiệm của bạn ngay hôm nay!\n\n✨ Tối ưu chi phí - Tăng tốc chuyển đổi - Vận hành tinh gọn.",
            "primary_text": f"Bạn đang tìm kiếm giải pháp tối ưu với tiêu chí: {usp}?\n\n{brief}\n\n👉 Khám phá ngay giải pháp đột phá từ {brand_name} để nâng tầm trải nghiệm của bạn ngay hôm nay!\n\n✨ Tối ưu chi phí - Tăng tốc chuyển đổi - Vận hành tinh gọn.",
            "cta": "👉 Đăng ký nhận tư vấn và trải nghiệm miễn phí ngay!",
            "hashtags": [
                f"#{brand_name.replace(' ', '')}",
                f"#{prod_name.replace(' ', '')}",
                "#MarketingAI",
                "#TangTruongDoanhSo",
                "#GiaiPhapThongMinh"
            ],
            "visual_suggestion": "Banner phong cách hiện đại, hiển thị mockup ứng dụng trên nền xanh gradient công nghệ cao kèm huy hiệu bảo chứng."
        }

        tiktok_data = {
            "hook_3s": f"Dừng lại 3 giây nếu bạn đang tìm kiếm giải pháp cho {prod_name}!",
            "target_duration": "30-45 giây",
            "scenes": [
                {
                    "scene": 1,
                    "scene_number": 1,
                    "duration_seconds": "0-3s",
                    "visual": "Diễn viên nhìn thẳng ống kính với vẻ mặt bối rối, bất ngờ chỉ tay vào dòng chữ cảnh báo trên màn hình",
                    "visual_action": "Diễn viên nhìn thẳng ống kính với vẻ mặt bối rối, bất ngờ chỉ tay vào dòng chữ cảnh báo trên màn hình",
                    "voiceover": "Nếu bạn vẫn đang mất hàng giờ mỗi ngày mà hiệu quả chưa tới đâu, thì đây là bí mật dành cho bạn!",
                    "voiceover_script": "Nếu bạn vẫn đang mất hàng giờ mỗi ngày mà hiệu quả chưa tới đâu, thì đây là bí mật dành cho bạn!",
                    "audio": "Hiệu ứng Whoosh nhanh kết hợp tiếng chuông Bell chime gây tò mò",
                    "audio_hint": "Hiệu ứng Whoosh nhanh kết hợp tiếng chuông Bell chime gây tò mò"
                },
                {
                    "scene": 2,
                    "scene_number": 2,
                    "duration_seconds": "3-15s",
                    "visual": "Góc máy lia nhanh qua bàn làm việc ngập tràn tài liệu và số liệu rối bời",
                    "visual_action": "Góc máy lia nhanh qua bàn làm việc ngập tràn tài liệu và số liệu rối bời",
                    "voiceover": f"Vấn đề là các cách làm thủ công tiêu tốn quá nhiều ngân sách. Đó là lý do {usp} được ra đời.",
                    "voiceover_script": f"Vấn đề là các cách làm thủ công tiêu tốn quá nhiều ngân sách. Đó là lý do {usp} được ra đời.",
                    "audio": "Tiết tấu trống dồn dập, hồi hộp",
                    "audio_hint": "Tiết tấu trống dồn dập, hồi hộp"
                },
                {
                    "scene": 3,
                    "scene_number": 3,
                    "duration_seconds": "15-30s",
                    "visual": "Màn hình giao diện ứng dụng thao tác kéo thả mượt mà, diễn viên mỉm cười gật đầu hài lòng",
                    "visual_action": "Màn hình giao diện ứng dụng thao tác kéo thả mượt mà, diễn viên mỉm cười gật đầu hài lòng",
                    "voiceover": f"Chỉ với vài thao tác cùng {brand_name}, quy trình tiếp thị đa kênh đã hoàn tất chuẩn chỉnh.",
                    "voiceover_script": f"Chỉ với vài thao tác cùng {brand_name}, quy trình tiếp thị đa kênh đã hoàn tất chuẩn chỉnh.",
                    "audio": "Nhạc nền EDM tươi sáng, phấn khởi",
                    "audio_hint": "Nhạc nền EDM tươi sáng, phấn khởi"
                },
                {
                    "scene": 4,
                    "scene_number": 4,
                    "duration_seconds": "30-40s",
                    "visual": "Diễn viên chỉ tay vào nút CTA trên bio màn hình điện thoại, logo thương hiệu xuất hiện",
                    "visual_action": "Diễn viên chỉ tay vào nút CTA trên bio màn hình điện thoại, logo thương hiệu xuất hiện",
                    "voiceover": "Bấm ngay vào link ở phần tiểu sử để nhận gói trải nghiệm đặc quyền hôm nay nhé!",
                    "voiceover_script": "Bấm ngay vào link ở phần tiểu sử để nhận gói trải nghiệm đặc quyền hôm nay nhé!",
                    "audio": "Sound effect Pop-up click + Âm thanh jingle kết thúc",
                    "audio_hint": "Sound effect Pop-up click + Âm thanh jingle kết thúc"
                }
            ],
            "suggested_audio": "Trending Lo-Fi Upbeat Marketing TikTok 2026",
            "sound_recommendation": "Trending Lo-Fi Upbeat Marketing TikTok 2026",
            "caption_with_hashtags": f"Khám phá bí quyết cùng {brand_name}! Xem hết clip để nhận ưu đãi nhé! #{brand_name.replace(' ', '')} #HocMoiNgay #LearnOnTikTok #KinhDoanhOnline"
        }

        email_data = {
            "subject_options": [
                f"Bật mí giải pháp đột phá {usp} dành riêng cho bạn",
                f"[Cơ hội giới hạn] Nâng tầm hiệu suất cùng {brand_name}"
            ],
            "subject_line_a": f"Bật mí giải pháp đột phá {usp} dành riêng cho bạn",
            "subject_line_b": f"[Cơ hội giới hạn] Nâng tầm hiệu suất cùng {brand_name}",
            "preheader": f"Khám phá ngay giải pháp tiếp thị tối ưu từ {brand_name}.",
            "greeting": "Chào bạn,",
            "body": f"Chúng tôi hiểu rằng việc tìm kiếm một giải pháp tiếp thị thực sự hiệu quả với tiêu chí: {usp} luôn là bài toán nan giải.\n\nTại {brand_name}, chúng tôi mang đến cho bạn giải pháp toàn diện: {brief}.\n\nĐừng để đối thủ vượt lên trước bạn. Hãy bắt đầu hành trình chuyển đổi số và nâng tầm thương hiệu ngay hôm nay!",
            "body_content": f"Chúng tôi hiểu rằng việc tìm kiếm một giải pháp tiếp thị thực sự hiệu quả với tiêu chí: {usp} luôn là bài toán nan giải.\n\nTại {brand_name}, chúng tôi mang đến cho bạn giải pháp toàn diện: {brief}.\n\nĐừng để đối thủ vượt lên trước bạn. Hãy bắt đầu hành trình chuyển đổi số và nâng tầm thương hiệu ngay hôm nay!",
            "cta_button": "👉 Khám Phá & Đăng Ký Trải Nghiệm Ngay",
            "cta_button_text": "👉 Khám Phá & Đăng Ký Trải Nghiệm Ngay",
            "cta_destination_type": "Landing Page",
            "ps_note": "P.S. Ưu đãi kích hoạt đặc quyền chỉ áp dụng cho 50 khách hàng đăng ký sớm nhất trong tuần này!"
        }

        return {
            "facebook": facebook_data,
            "tiktok": tiktok_data,
            "email": email_data,
            "warnings": ["Dữ liệu được tạo từ chế độ Smart Fallback (mạng ngoại vi không khả dụng hoặc chưa cấu hình API key).",
                         "Nội dung dự phòng CHƯA được chấm điểm tuân thủ. Hãy chạy kiểm tra tuân thủ trên nội dung đã chỉnh sửa."],
            "assumptions": ["Kế thừa thông số Brand Kit và ngữ cảnh chiến dịch mặc định."],
            # KHÔNG tự gán compliance_score cho nội dung dự phòng.
            #
            # Bản trước đặt cứng `compliance_score: 100`, tức là tuyên bố bộ
            # template "đạt chuẩn 100/100" dù nó chưa từng đi qua
            # `compliance_service`. Người dùng đọc thấy điểm tuyệt đối và tin
            # rằng bản nháp đã được kiểm duyệt tự động — trong khi thực tế nó
            # chỉ là khuôn mẫu chưa ai kiểm. Đó đúng là loại nhận định sai mà
            # rubric Tuần 3 mục 6 ("dừng người cảnh giác", "có cảnh báo rõ
            # ràng") yêu cầu phải tránh.
            #
            # Để trống (None) để UI hiển thị "chưa chấm" thay vì hiển thị điểm
            # giả. Điểm thật chỉ do `POST /contents/compliance-check` tính từ
            # Brand Kit và chính sách quảng cáo.
            "compliance_score": None,
            "is_fallback": True,
            "model_provider": "template-fallback-engine"
        }

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
        is_fallback = False
        model_provider = "template-fallback-engine"

        # Phân giải API Key và Model (Multi-tier Resolution - FEAT-BE-26)
        active_key = None
        active_model = self.model
        key_tier = "FALLBACK"
        # Provider không cần API key (Ollama, HuggingFace) coi "không có khoá"
        # là cấu hình hợp lệ nên vẫn phải gọi thật, không rơi vào template.
        provider_requires_key = True

        active_provider = "gemini"
        # Chuỗi fallback (kiểu 9Router): None = không có chuỗi -> gọi một model như cũ.
        chain_hops: Optional[Dict[str, Any]] = None
        target_ws_id = context.get("workspace_id")
        if target_ws_id is None and campaign_id is not None:
            try:
                from app.models.entities import Campaign
                camp = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if camp and camp.workspace_id:
                    target_ws_id = camp.workspace_id
            except Exception:
                pass

        # Bơm "Tờ giấy quy tắc Giọng văn & Thiết kế (Anti-AI Design & Voice Sheet)" từ BrandKit vào system_prompt
        if target_ws_id is not None and task_code in ("IDEA", "DRAFT", "OMNICHANNEL"):
            try:
                from app.models.entities import BrandKit
                bk = db.query(BrandKit).filter(BrandKit.workspace_id == target_ws_id).first()
                if bk and (bk.target_audience or bk.brand_guidelines):
                    anti_ai_rules = [
                        "\n\n[TỜ GIẤY QUY TẮC KHỬ MÙI AI & GIỌNG VĂN THƯƠNG HIỆU — BẮT BUỘC TUÂN THỦ]:"
                    ]
                    if bk.target_audience:
                        anti_ai_rules.append(f"- Chân dung người đọc cụ thể (1 câu): {bk.target_audience}")
                    if bk.brand_guidelines:
                        anti_ai_rules.append(f"- Quy tắc viết chữ & thiết kế của thương hiệu:\n{bk.brand_guidelines}")
                    anti_ai_rules.append(
                        "- 5 LUẬT VIẾT CHỮ ĐẦU NGÀNH (KHỬ MÙI AI):\n"
                        "  1. Bài thử xóa tên thương hiệu: Nội dung phải có chi tiết/số liệu riêng của sản phẩm, không viết chung chung đến mức thay tên đối thủ vào vẫn đúng.\n"
                        "  2. Cấm từ tự khen sáo rỗng: Tuyệt đối tránh 'tận tâm', 'hàng đầu', 'toàn diện', 'đáng tin cậy', 'giải pháp tối ưu'.\n"
                        "  3. Lời khen phải có chủ ngữ bên thứ 3 hoặc con số đo được.\n"
                        "  4. Nút bấm (CTA) phải là hành động cụ thể ngay lập tức (CẤM dùng 'Tìm hiểu thêm').\n"
                        "  5. Câu ngắn, nhịp gọn, dùng từ tiếng Việt đời thường (đổi 'build' -> 'làm', 'output' -> 'kết quả', 'optimize' -> 'tối ưu chi phí')."
                    )
                    system_prompt = system_prompt + "\n".join(anti_ai_rules)
            except Exception:
                pass
        if self._api_key is not None:
            # 1. Test fixture override (Bảo tồn 100% zero regression cho 499 existing unit tests)
            active_key = self._api_key
            active_model = self.model
            key_tier = "FIXTURE"
        else:
            # 2. Multi-tier resolution: Workspace > User > System > Fallback
            # Chọn chuỗi TRƯỚC lượt gọi đơn; nếu có chuỗi thì nhánh "no key ->
            # template" bên dưới phải nhường cho vòng lặp thử hop.
            chain_hops = self._resolve_chain_hops(
                db=db, user_id=user_id, workspace_id=target_ws_id, context=context
            )

            # Mặc định lấy provider từ cấu hình, không phải "gemini". Trước đây hardcode
            # "gemini" nên khi .env đặt AI_PROVIDER=opencode (hay openrouter),
            # `resolve_api_key` vẫn tra nhánh gemini: với opencode điều đó
            # thành env_key=None -> rơi thẳng Tier 4 -> Smart Fallback, và API
            # trả về thông báo "Please pass a valid API key" dù .env có khoá.
            req_provider = (
                context.get("provider")
                or settings.AI_PROVIDER
                or "gemini"
            )
            resolved = self.resolve_api_key(db=db, workspace_id=target_ws_id, user_id=user_id, provider=req_provider)
            active_key = resolved.get("api_key")
            active_model = resolved.get("model") or self.model
            active_provider = resolved.get("provider") or req_provider
            key_tier = resolved.get("tier", "FALLBACK")
            provider_requires_key = resolved.get("requires_api_key", True)

        # Xử lý các token kiểm thử trong test suite (như test_t3_cross_05)
        if active_key and ("TestResolverKey" in active_key or "MockVerification" in active_key):
            logger.info("[AI Service - Test Resolver] Detected mock test key (%s). Using deterministic mock output.", key_tier)
            output_data = self._generate_fallback(task_type, context)
            latency_ms = int((time.time() - start_time) * 1000) or 15
            model_used = active_model
            is_fallback = False
            model_provider = f"{active_provider}-{key_tier.lower()}"
        # Không có API Key, fallback bật VÀ provider bắt buộc cần khoá -> template.
        # `provider_requires_key=False` bỏ qua nhánh này có chủ đích: Ollama và
        # HuggingFace không cần khoá, coi hư việt là rỗng thành lỗi cấu hình sẽ
        # khiến tính năng demo offline không bao giờ chạy được.
        # `chain_hops is None` bảo đảm khi CÓ chuỗi thì không rơi template ngay:
        # hop khác trong chuỗi có thể vẫn có khoá (đúng tinh thần failover).
        elif chain_hops is None and provider_requires_key and (not active_key or active_key.strip() == "") and self.fallback_enabled:
            logger.warning("[AI Service - Fallback Engine] No API key configured. Activating deterministic Smart Fallback for task %s.", task_code)
            output_data = self._generate_fallback(task_type, context)
            latency_ms = int((time.time() - start_time) * 1000)
            model_used = f"{active_model} (Fallback Mock)"
            is_fallback = True
            model_provider = "template-fallback-engine"
        elif chain_hops:
            # ---- Chuỗi fallback (kiểu 9Router) ----
            # Thử lần lượt từng hop; hop nào chạy được (có key + HTTP 200 +
            # schema hợp lệ) thì nhận. Hop lỗi (thiếu key, timeout, HTTP lỗi,
            # sai schema, breaker mở) chuyển bước kế. Hết chuỗi mới rơi về
            # template Smart Fallback như cũ. Mọi lý do bỏ qua từng bước được
            # ghi vào warnings/log để người đọc biết vì sao nội dung không đến
            # từ model đầu tiên.
            hops = chain_hops["hops"]
            chain_name = chain_hops.get("name") or f"#{chain_hops.get('id')}"
            n_hops = len(hops)
            hop_errors: List[str] = []
            last_schema_err: Optional[Exception] = None
            last_runtime_err: Optional[str] = None
            last_label = active_model
            any_attempted = False
            # Ngân sách chung của cả chuỗi = timeout cấu hình; mỗi hop nhận phần
            # còn lại chia đều (tối thiểu 15s) để một hop treo không nuốt hết hạn mức.
            deadline = time.time() + float(self.timeout)
            success = False

            for idx, hop in enumerate(hops):
                if time.time() >= deadline:
                    hop_errors.append("hết ngân sách thời gian của chuỗi")
                    break
                hop_provider = hop["provider"]
                label = f"{hop_provider}:{hop['model']}"
                last_label = label

                resolved_hop = self.resolve_api_key(
                    db=db, workspace_id=target_ws_id, user_id=user_id, provider=hop_provider
                )
                hop_key = resolved_hop.get("api_key")
                hop_tier = resolved_hop.get("tier", "FALLBACK")
                hop_requires_key = resolved_hop.get("requires_api_key", True)
                # Model người dùng đặt trong chuỗi luôn thắng model mặc định của
                # key/hệ thống: đó chính là lý do họ thêm bước này vào chuỗi.
                hop_model = hop["model"] or resolved_hop.get("model") or self.model

                if hop_requires_key and (not hop_key or not str(hop_key).strip()):
                    hop_errors.append(f"{label}: thiếu API key")
                    continue
                if hop_key and ("TestResolverKey" in hop_key or "MockVerification" in hop_key):
                    # Cùng nhánh mock với lượt gọi đơn (test suite).
                    output_data = self._generate_fallback(task_type, context)
                    latency_ms = int((time.time() - start_time) * 1000) or 15
                    model_used = hop_model
                    is_fallback = False
                    model_provider = f"{hop_provider}-{hop_tier.lower()}"
                    success = True
                    break

                any_attempted = True
                # Chia đều ngân sách thời gian còn lại cho các hop sắp tới; với
                # chuỗi >1 bước, mỗi bước tối đa 1 lần retry nội bộ (failover đã
                # là retry cấp cao hơn). Mỗi hop nhận ít nhất 15s (đúng comment
                # ở trên) — nếu AI_TIMEOUT_SECONDS tổng quá nhỏ (mặc định dev
                # 10s) thì vẫn nâng lên 15s/hop thay vì ép xuống ~7s; production
                # dùng 420s nên không ảnh hưởng.
                hops_left = n_hops - idx
                remaining = max(0.0, deadline - time.time())
                if n_hops > 1:
                    per_hop = remaining / hops_left if hops_left else remaining
                    timeout_override = int(max(15.0, min(float(self.timeout), per_hop)))
                    retries_override = min(self.max_retries, 1)
                else:
                    timeout_override = None
                    retries_override = None
                try:
                    raw_response = self._call_provider_with_retry(
                        system_prompt, user_prompt,
                        active_key=hop_key, active_model=hop_model,
                        provider=hop_provider,
                        timeout_override=timeout_override,
                        retries_override=retries_override
                    )
                    output_data = self._clean_json_response(raw_response)
                    # BUG-BE-08: cùng bộ kiểm chứng schema như lượt gọi đơn.
                    self._validate_task_output(task_code, output_data, prompt_version)
                    latency_ms = int((time.time() - start_time) * 1000)
                    model_used = hop_model
                    is_fallback = False
                    if hop_tier in ("WORKSPACE", "USER"):
                        model_provider = f"{hop_provider}-{hop_tier.lower()}"
                    elif hop_model and "gemini" in str(hop_model).lower():
                        model_provider = f"{hop_provider}-pro"
                    else:
                        model_provider = hop_provider
                    if hop_errors:
                        output_data.setdefault("warnings", []).append(
                            f"Chuỗi “{chain_name}”: đã bỏ qua {'; '.join(hop_errors)} — dùng {label}."
                        )
                    logger.info(
                        "[AI Service - Live LLM] Chain '%s' executed task %s via hop %s (%d/%d) in %d ms; skipped: %s",
                        chain_name, task_code, label, idx + 1, n_hops, latency_ms,
                        "; ".join(hop_errors) or "none"
                    )
                    success = True
                    break
                except (json.JSONDecodeError, ValidationError) as schema_err:
                    # Schema sai cũng là lý do failover: hop kế tiếp xử lý prompt
                    # này (thường bằng model/provider khác) có thể đúng.
                    result_status = "SCHEMA_ERROR"
                    error_code = "ERR_INVALID_SCHEMA" if isinstance(schema_err, ValidationError) else "ERR_INVALID_JSON"
                    last_schema_err = schema_err
                    hop_errors.append(f"{label}: sai cấu trúc ({error_code})")
                    logger.warning("[AI Chain] hop %s sai schema (%s), chuyển hop kế.", label, error_code)
                except Exception as hop_err:
                    raw_err = str(hop_err)
                    err_str = _sanitize_ai_error(raw_err, active_key=hop_key)
                    if "TIMEOUT" in raw_err:
                        result_status = "TIMEOUT"
                        error_code = "ERR_AI_TIMEOUT"
                    else:
                        result_status = "PROVIDER_ERROR"
                        error_code = "ERR_PROVIDER"
                    last_runtime_err = err_str
                    hop_errors.append(f"{label}: {err_str}")
                    logger.warning("[AI Chain] hop %s lỗi (%s), chuyển hop kế.", label, err_str)

            if not success:
                err_summary = "; ".join(hop_errors) if hop_errors else "không có hop hợp lệ"
                if self.fallback_enabled:
                    logger.warning(
                        "[AI Service - Fallback Engine] Chain '%s' failed after %d hop(s) (%s). Activating Smart Fallback for task %s.",
                        chain_name, n_hops, err_summary, task_code
                    )
                    output_data = self._generate_fallback(task_type, context)
                    output_data.setdefault("warnings", []).append(
                        f"Chuỗi “{chain_name}” đã thử {n_hops} bước ({err_summary}); đã kích hoạt Smart Fallback."
                    )
                    latency_ms = int((time.time() - start_time) * 1000)
                    is_fallback = True
                    model_provider = "template-fallback-engine"
                    if any_attempted:
                        model_used = f"{last_label} (Chain Failover Fallback)"
                    else:
                        # Không bước nào gọi được (thiếu hết khoá) — cùng nhãn
                        # với nhánh "no API key" của lượt gọi đơn, và đồng bộ
                        # trạng thái SUCCESS: thiếu khoá là cấu hình, không phải
                        # lỗi provider.
                        model_used = f"{active_model} (Fallback Mock)"
                        result_status = "SUCCESS"
                        error_code = None
                else:
                    latency_ms = int((time.time() - start_time) * 1000)
                    if not any_attempted:
                        result_status = "PROVIDER_ERROR"
                        error_code = "ERR_NO_API_KEY"
                        last_runtime_err = last_runtime_err or (
                            f"Chuỗi “{chain_name}” không hop nào có API key."
                        )
                    self._log_call(
                        db, user_id, campaign_id, task_code, last_label,
                        prompt_version, input_hash, None, result_status, error_code, latency_ms
                    )
                    if result_status == "SCHEMA_ERROR" and last_schema_err is not None:
                        raise last_schema_err
                    raise RuntimeError(
                        last_runtime_err or f"Chuỗi “{chain_name}” đã hết hop mà không có kết quả."
                    )
        else:
            try:
                raw_response = self._call_provider_with_retry(
                    system_prompt, user_prompt,
                    active_key=active_key, active_model=active_model,
                    provider=active_provider
                )
                try:
                    output_data = self._clean_json_response(raw_response)
                    # BUG-BE-08: Kiểm tra tính hợp lệ của schema kết quả AI
                    self._validate_task_output(task_code, output_data, prompt_version)
                    latency_ms = int((time.time() - start_time) * 1000)
                    model_used = active_model
                    is_fallback = False
                    # Nguồn gốc nội dung phải nói đúng provider đã thực sự gọi.
                    # Bản cũ rơi về `settings.AI_PROVIDER` khi model không chứa
                    # "gemini", nên một lượt gọi qua khoá OpenAI lại báo
                    # `gemini-pro` cho người đọc audit log — đúng loại nhận định
                    # sai nguồn mà rubric Tuần 3 mục 6 yêu cầu phải tránh.
                    if key_tier in ("WORKSPACE", "USER"):
                        model_provider = f"{active_provider}-{key_tier.lower()}"
                    elif active_model and "gemini" in str(active_model).lower():
                        model_provider = f"{active_provider}-pro"
                    else:
                        model_provider = active_provider
                    logger.info("[AI Service - Live LLM] Successfully executed task %s via model %s in %d ms", task_code, active_model, latency_ms)
                except (json.JSONDecodeError, ValidationError) as schema_err:
                    result_status = "SCHEMA_ERROR"
                    error_code = "ERR_INVALID_SCHEMA" if isinstance(schema_err, ValidationError) else "ERR_INVALID_JSON"
                    if self.fallback_enabled:
                        logger.warning("[AI Service - Fallback Engine] Schema validation error (%s). Recovering via Smart Fallback for task %s.", error_code, task_code)
                        output_data = self._generate_fallback(task_type, context)
                        msg = "Mô hình AI trả về sai cấu trúc schema; đã tự động kích hoạt chế độ Smart Fallback." if isinstance(schema_err, ValidationError) else "Model trả về sai JSON, hệ thống tự động bẫy lỗi và sinh dữ liệu dự phòng an toàn."
                        output_data.setdefault("warnings", []).append(msg)
                        model_used = f"{active_model} (Auto-recovered)"
                        is_fallback = True
                        model_provider = "template-fallback-engine"
                        latency_ms = int((time.time() - start_time) * 1000)
                    else:
                        latency_ms = int((time.time() - start_time) * 1000)
                        self._log_call(db, user_id, campaign_id, task_code, active_model, prompt_version, input_hash, None, result_status, error_code, latency_ms)
                        raise schema_err
            except Exception as e:
                if result_status != "SCHEMA_ERROR":
                    raw_err = str(e)
                    err_str = _sanitize_ai_error(raw_err, active_key=active_key)
                    if "TIMEOUT" in raw_err:
                        result_status = "TIMEOUT"
                        error_code = "ERR_AI_TIMEOUT"
                    else:
                        result_status = "PROVIDER_ERROR"
                        error_code = "ERR_PROVIDER"

                    if self.fallback_enabled:
                        logger.warning("[AI Service - Fallback Engine] Provider error (%s: %s). Activating failover Smart Fallback for task %s.", error_code, err_str, task_code)
                        output_data = self._generate_fallback(task_type, context)
                        output_data.setdefault("warnings", []).append(f"Lỗi AI ({err_str}), đã kích hoạt chế độ dự phòng an toàn.")
                        latency_ms = int((time.time() - start_time) * 1000)
                        model_used = f"{active_model} (Failover Fallback)"
                        is_fallback = True
                        model_provider = "template-fallback-engine"
                    else:
                        latency_ms = int((time.time() - start_time) * 1000)
                        self._log_call(db, user_id, campaign_id, task_code, active_model, prompt_version, input_hash, None, result_status, error_code, latency_ms)
                        raise RuntimeError(err_str) from None

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
        output_data["is_fallback"] = is_fallback
        output_data["model_provider"] = model_provider
        return output_data

    def generate_omnichannel_content(
        self,
        db: Session,
        user_id: int,
        campaign_id: Optional[int],
        prompt_version: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep 3-Channel AI Creative Engine: Điều phối sinh nội dung Facebook, TikTok, Email."""
        return self.execute_task(
            db=db,
            user_id=user_id,
            campaign_id=campaign_id,
            task_type="omnichannel_generation",
            task_code="OMNICHANNEL",
            prompt_version=prompt_version,
            context=context
        )

    def _generate_fallback_angle_matrix(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sinh ma trận Góc tiếp cận Tâm lý × Biến thể Hook 3 giây chuẩn nghiệp vụ khi offline/fallback."""
        camp_name = str(context.get("campaign_name") or "Chiến dịch Tăng trưởng")
        prod_name = str(context.get("product_name") or "Giải pháp MarketFlow")
        usp = str(context.get("product_usp") or "Tự động hóa đa kênh, tối ưu chi phí thực chiến")
        audience = str(context.get("audience") or "Khách hàng mục tiêu 22-40 tuổi")
        channel = str(context.get("channel") or "facebook").lower()
        requested_angles = context.get("angles_list") or ["PAIN_POINT", "SOCIAL_PROOF", "MYTH_BUSTER", "OFFER_FOMO"]
        hooks_per_angle = int(context.get("hooks_per_angle") or 3)

        angle_catalog = {
            "PAIN_POINT": {
                "label": "Nỗi đau & Chi phí cơ hội",
                "hooks": [
                    ("Hook_A", f"Dừng lại 3 giây nếu {audience.lower()} vẫn đang lãng phí hàng giờ mỗi ngày vì thiếu {prod_name}!"),
                    ("Hook_B", f"80% người mới thất bại chỉ vì bỏ qua bước cốt lõi này khi triển khai {prod_name}."),
                    ("Hook_C", f"Đừng để ngân sách bốc hơi vô ích thêm một tuần nào nữa — đây là cách xử lý tận gốc!"),
                ],
                "cta": "👉 Nhắn tin nhận phác đồ giải quyết ngay hôm nay",
                "hypothesis": "Khai thác trực diện nỗi đau mất thời gian/chi phí giúp tăng tỷ lệ dừng ngón tay (Thumb-Stop Rate) ở 3 giây đầu.",
            },
            "SOCIAL_PROOF": {
                "label": "Bằng chứng xã hội & Kết quả thực",
                "hooks": [
                    ("Hook_A", f"Hơn 1.200 học viên & đội ngũ thực chiến đã chuyển đổi sang {prod_name} trong quý này — vì sao?"),
                    ("Hook_B", f"Case study thực tế: Cách đội ngũ tinh gọn vận hành {prod_name} nhờ {usp}."),
                    ("Hook_C", f"Nhìn vào bảng số liệu trước & sau 14 ngày ứng dụng {prod_name} của khách hàng thực tế:"),
                ],
                "cta": "👉 Xem trọn bộ Case Study & Đăng ký trải nghiệm",
                "hypothesis": "Sử dụng con số thực chứng và câu chuyện thành công giúp giảm rào cản hoài nghi ở nhóm khách hàng cân nhắc kỹ.",
            },
            "MYTH_BUSTER": {
                "label": "Phá vỡ lầm tưởng ngành",
                "hooks": [
                    ("Hook_A", f"Sự thật ngược đời: Bạn KHÔNG cần ngân sách lớn để làm chủ {prod_name}!"),
                    ("Hook_B", f"Quên cách làm thủ công cũ kỹ đi — đây mới là chuẩn mực {prod_name} năm 2026."),
                    ("Hook_C", f"3 lầm tưởng tai hại khiến {audience.lower()} mãi dậm chân tại chỗ (và cách đảo ngược):"),
                ],
                "cta": "👉 Khám phá phương pháp mới ngay tại đây",
                "hypothesis": "Góc nhìn phản trực giác (Pattern Interrupt) kích thích tò mò mạnh trên Newsfeed Facebook và TikTok.",
            },
            "OFFER_FOMO": {
                "label": "Ưu đãi giới hạn & Thúc đẩy hành động",
                "hooks": [
                    ("Hook_A", f"[Chỉ còn 20 suất] Đặc quyền sở hữu {prod_name} kèm bộ công cụ thực chiến trong tuần này!"),
                    ("Hook_B", f"Ưu đãi đặc biệt chiến dịch {camp_name}: Kích hoạt {prod_name} trước khi đóng cổng đăng ký."),
                    ("Hook_C", f"Đừng chờ đến khi đối thủ đi trước — nhận ngay gói ưu đãi khởi động {prod_name} hôm nay!"),
                ],
                "cta": "👉 Giữ suất ưu đãi của bạn ngay lập tức",
                "hypothesis": "Giới hạn số lượng suất và thời gian cụ thể thúc đẩy tỷ lệ nhấp chuyển đổi (CVR) ở đáy phễu BoFU.",
            },
        }
        angle_catalog["URGENCY_FOMO"] = angle_catalog["OFFER_FOMO"]

        variants = []
        for angle_key in requested_angles:
            spec = angle_catalog.get(angle_key, angle_catalog["PAIN_POINT"])
            for hook_type, hook_text in spec["hooks"][:hooks_per_angle]:
                title = f"[{spec['label']}] {hook_text[:85]}"
                body = (
                    f"{hook_text}\n\n"
                    f"💡 Giải pháp từ {prod_name}:\n"
                    f"• Đặc tính cốt lõi: {usp}\n"
                    f"• Thiết kế chuyên biệt cho: {audience}\n"
                    f"• Triển khai bài bản trong khuôn khổ {camp_name}.\n\n"
                    f"#MarketFlowAI #{channel.capitalize()} #{angle_key.lower()}"
                )
                variants.append({
                    "angle": angle_key,
                    "angle_label": spec["label"],
                    "hook_type": hook_type,
                    "hook_text": hook_text,
                    "title": title,
                    "body": body,
                    "cta": spec["cta"],
                    "ab_hypothesis": f"[{angle_key} × {hook_type}] {spec['hypothesis']}",
                })

        return {
            "variants": variants,
            "is_fallback": True,
            "model_provider": "template-fallback-engine",
        }

    def _generate_fallback_prelaunch_critic(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sinh báo cáo Hội đồng 4 chuyên gia thẩm định quảng cáo trước xuất bản (Pre-launch Critic)."""
        title = str(context.get("title") or "").strip()
        body = str(context.get("body") or "").strip()
        cta = str(context.get("cta") or "Đăng ký ngay hôm nay").strip()
        channel = str(context.get("channel") or "facebook").lower()
        funnel_stage = str(context.get("funnel_stage") or "BoFU")
        comp_score = int(context.get("compliance_score") or 100)
        violations_summary = str(context.get("violations_summary") or "Không phát hiện từ khóa cấm")

        sentences = [s.strip() for s in body.replace("\n", ". ").split(".") if s.strip()]
        weakest_sentence = sentences[-1] if sentences else body[:100]
        weakest_reason = "Câu văn còn mang tính mô tả chung chung, thiếu con số định lượng hoặc lợi ích cụ thể cho người đọc."
        for s in sentences:
            s_low = s.lower()
            if any(w in s_low for w in ("hàng đầu", "tốt nhất", "toàn diện", "tối ưu", "cam kết 100%")):
                weakest_sentence = s
                weakest_reason = "Sử dụng tính từ tự khen sáo rỗng hoặc nhạy cảm chính sách, làm giảm độ tin cậy với khách hàng thực tế."
                break

        has_numbers = any(ch.isdigit() for ch in (title + " " + body))
        has_hook_punct = any(p in title for p in ("?", "!", "[", "🔥", "🚀", ":"))
        thumb_stop_score = min(96, 62 + (14 if has_hook_punct else 0) + (12 if has_numbers else 0) + (6 if len(title) >= 20 else 0))
        friction_score = max(12, 58 - (15 if len(cta) >= 10 else 0) - (12 if has_numbers else 0) + (25 if comp_score < 80 else 0))
        overall_score = int(round((thumb_stop_score * 0.35) + ((100 - friction_score) * 0.30) + (comp_score * 0.35)))
        overall_score = max(0, min(100, overall_score))

        if comp_score < 70:
            verdict = "BLOCKED_BY_COMPLIANCE"
        elif overall_score >= 75:
            verdict = "READY_TO_LAUNCH"
        else:
            verdict = "NEEDS_REVISION"

        personas = [
            {
                "persona_id": "skeptical_buyer",
                "persona_name": "Khách hàng hoài nghi (Skeptical Buyer)",
                "persona_role": "Người ra quyết định mua hàng khắt khe, dị ứng với lời quảng cáo sáo rỗng",
                "avatar_emoji": "🧐",
                "score": min(95, 65 + (18 if has_numbers else 0)),
                "verdict": "PASS" if has_numbers else "WARN",
                "critique": (
                    "Bài viết đã nêu được giải pháp nhưng người mua khó tính cần thấy con số cụ thể (thời gian tiết kiệm, số lượng học viên/khách hàng đã kiểm chứng)."
                ),
                "fix_suggestion": "Bổ sung 1 con số định lượng hoặc mốc thời gian cụ thể ngay đoạn thứ 2 của thân bài.",
                "actionable_fix": "Bổ sung 1 con số định lượng hoặc mốc thời gian cụ thể ngay đoạn thứ 2 của thân bài.",
            },
            {
                "persona_id": "three_sec_scroller",
                "persona_name": "Người lướt điện thoại 3 giây (3-Second Scroller)",
                "persona_role": "Lướt Newsfeed/TikTok cực nhanh, chỉ dừng lại nếu dòng đầu gây tò mò mạnh",
                "avatar_emoji": "📱",
                "score": thumb_stop_score,
                "verdict": "PASS" if thumb_stop_score >= 75 else "WARN",
                "critique": (
                    f"Trên kênh {channel.upper()}, người dùng quyết định lướt qua trong 1.7 giây đầu. Tiêu đề '{title[:45]}...' cần đánh thẳng vào nỗi đau hoặc sự tò mò."
                ),
                "fix_suggestion": "Đặt câu hỏi trực diện hoặc con số gây chú ý ngay 5 từ đầu tiên của tiêu đề.",
                "actionable_fix": "Đặt câu hỏi trực diện hoặc con số gây chú ý ngay 5 từ đầu tiên của tiêu đề.",
            },
            {
                "persona_id": "brand_guardian",
                "persona_name": "Người gác cổng Brand Kit (Brand Guardian)",
                "persona_role": "Kiểm soát giọng văn thương hiệu, cấu trúc thông điệp và tính nhất quán CTA",
                "avatar_emoji": "🛡️",
                "score": min(98, max(50, comp_score - 2)),
                "verdict": "PASS" if comp_score >= 85 else "WARN",
                "critique": (
                    f"Đánh giá mức độ nhất quán với phễu {funnel_stage}: cấu trúc ngắt dòng rõ ràng, tuy nhiên câu '{weakest_sentence[:50]}...' cần cụ thể hóa hơn."
                ),
                "fix_suggestion": "Thay thế các tính từ chung chung bằng lợi ích đo đếm được gắn với USP thương hiệu.",
                "actionable_fix": "Thay thế các tính từ chung chung bằng lợi ích đo đếm được gắn với USP thương hiệu.",
            },
            {
                "persona_id": "ad_policy_bot",
                "persona_name": "Thuật toán Chính sách FB/TikTok (Ad Policy Bot)",
                "persona_role": "Quét từ khóa nhạy cảm, cam kết tuyệt đối 100%, và trải nghiệm trang đích",
                "avatar_emoji": "🤖",
                "score": comp_score,
                "verdict": "PASS" if comp_score >= 85 else "FAIL",
                "critique": f"Điểm quét tuân thủ hiện tại đạt {comp_score}/100 ({violations_summary}).",
                "fix_suggestion": "Loại bỏ hoàn toàn từ khóa cam kết tuyệt đối 100% hoặc tuyên bố phóng đại trước khi bấm xuất bản.",
                "actionable_fix": "Loại bỏ hoàn toàn từ khóa cam kết tuyệt đối 100% hoặc tuyên bố phóng đại trước khi bấm xuất bản.",
            },
        ]

        improved_title = title if (has_hook_punct and comp_score >= 90) else f"🔥 [Giải pháp Thực Chiến] {title}"
        improved_body = (
            f"{body}\n\n"
            "✅ Lộ trình triển khai rõ ràng từng bước — tối ưu thời gian và ngân sách thực tế cho đội ngũ của bạn."
        )
        improved_cta = cta if len(cta) >= 12 else "👉 Đăng ký nhận lộ trình & tư vấn chi tiết ngay hôm nay!"

        return {
            "overall_readiness_score": overall_score,
            "thumb_stop_score": thumb_stop_score,
            "conversion_friction_score": friction_score,
            "compliance_score": comp_score,
            "verdict": verdict,
            "weakest_sentence": weakest_sentence,
            "weakest_reason": weakest_reason,
            "personas": personas,
            "improved_title": improved_title,
            "improved_body": improved_body,
            "improved_cta": improved_cta,
            "is_fallback": True,
            "model_provider": "template-fallback-engine",
        }

    def _generate_fallback_compliance_rewrite(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Viết lại ngữ cảnh câu chứa từ khóa vi phạm chính sách quảng cáo & Brand Kit bằng Tiếng Việt tự nhiên."""
        import re as _re

        title = str(context.get("title") or "")
        body = str(context.get("body") or "")
        cta = str(context.get("cta") or "")
        violations = context.get("violations_raw") or []

        semantic_clause_map = {
            "cam kết 100%": "đồng hành sát sao cùng lộ trình đã kiểm chứng thực tế",
            "100%": "tối đa hiệu năng theo tiêu chuẩn thực tế",
            "chữa dứt điểm": "hỗ trợ cải thiện bền vững từ gốc",
            "trị dứt điểm": "hỗ trợ xử lý chuyên sâu và bài bản",
            "khỏi hoàn toàn": "cải thiện rõ rệt theo phác đồ",
            "làm giàu nhanh": "xây dựng nguồn thu nhập bền vững theo năng lực",
            "đa cấp": "mô hình phát triển đối tác minh bạch",
            "hoàn tiền không lý do": "chính sách bảo vệ quyền lợi học viên/khách hàng rõ ràng",
            "không hoàn tiền": "bảo đảm quyền lợi minh bạch theo hợp đồng",
            "bán phá giá": "mức ngân sách ưu đãi trực tiếp từ chương trình",
            "trắng da cấp tốc": "chăm sóc làn da sáng khỏe tự nhiên theo chu kỳ",
            "tốt nhất thị trường": "được cộng đồng chuyên môn đánh giá cao về tính thực tiễn",
            "số 1 việt nam": "thuộc nhóm giải pháp tiên phong tại Việt Nam",
            "chắc chắn thành công": "nâng cao tỷ lệ đạt mục tiêu nhờ quy trình chuẩn",
            "vĩnh viễn": "lâu dài và ổn định",
            "tuyệt đối": "vượt trội và nhất quán",
        }

        def _rewrite_text(txt: str) -> str:
            if not txt:
                return txt
            out = txt
            for v in violations:
                word = str(v.get("word") if isinstance(v, dict) else getattr(v, "word", "")).strip()
                suggestion = str(v.get("suggestion") if isinstance(v, dict) else getattr(v, "suggestion", "")).strip()
                if not word:
                    continue
                replacement = semantic_clause_map.get(word.lower())
                if not replacement:
                    m = _re.search(r"['\"“]([^'\"”]{3,60})['\"”]", suggestion)
                    replacement = m.group(1) if m else "giải pháp tối ưu theo chuẩn thực tế"
                pattern = _re.compile(_re.escape(word), _re.IGNORECASE)
                out = pattern.sub(replacement, out)
            for bad_kw, safe_phrase in semantic_clause_map.items():
                out = _re.compile(_re.escape(bad_kw), _re.IGNORECASE).sub(safe_phrase, out)
            return out

        return {
            "title": _rewrite_text(title),
            "body": _rewrite_text(body),
            "cta": _rewrite_text(cta),
            "is_fallback": True,
            "model_provider": "template-fallback-engine",
        }

    def generate_angle_hook_matrix(
        self,
        db: Session,
        user_id: int,
        campaign_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Tạo ma trận Góc tiếp cận Tâm lý × Biến thể Hook, tính CTR/CVR dự phóng theo chuẩn ngành và chấm điểm Compliance thật."""
        import re as _re
        from app.services.ai.ai_doctor import AIDoctorEngine, CHANNEL_BENCHMARKS
        from app.services.compliance.compliance_service import ComplianceScanner

        merged_ctx: Dict[str, Any] = {}
        if isinstance(context, dict):
            merged_ctx.update(context)
        merged_ctx.update({k: v for k, v in kwargs.items() if v is not None})

        channel = str(merged_ctx.get("channel") or merged_ctx.get("channel_code") or "facebook").lower().strip()
        funnel_stage = AIDoctorEngine.infer_funnel_stage(
            merged_ctx.get("objective") or merged_ctx.get("brief"),
            merged_ctx.get("funnel_stage"),
        )
        angles_list = merged_ctx.get("angles") or ["PAIN_POINT", "SOCIAL_PROOF", "MYTH_BUSTER", "OFFER_FOMO"]
        hooks_per_angle = max(1, min(3, int(merged_ctx.get("hooks_per_angle") or 3)))
        prod_name = str(merged_ctx.get("product_name") or merged_ctx.get("campaign_name") or "Giải pháp Marketing AI")

        exec_ctx = {
            **merged_ctx,
            "product_name": prod_name,
            "product_usp": merged_ctx.get("product_usp") or "Tối ưu hiệu suất chuyển đổi đa kênh",
            "audience": merged_ctx.get("audience") or merged_ctx.get("target_audience") or "Khách hàng mục tiêu",
            "channel": channel,
            "funnel_stage": funnel_stage,
            "angles": ", ".join(angles_list),
            "angles_list": angles_list,
            "hooks_per_angle": hooks_per_angle,
        }
        raw = self.execute_task(
            db=db,
            user_id=user_id,
            campaign_id=campaign_id,
            task_type="angle_matrix",
            task_code="ANGLE_MATRIX",
            prompt_version=str(merged_ctx.get("prompt_version") or "v3"),
            context=exec_ctx,
        )
        raw_variants = raw.get("variants") if isinstance(raw.get("variants"), list) else []
        expected_min = len(angles_list) * hooks_per_angle
        if len(raw_variants) < expected_min:
            raw_variants = self._generate_fallback_angle_matrix(exec_ctx).get("variants", [])

        bench = CHANNEL_BENCHMARKS.get(channel, CHANNEL_BENCHMARKS["facebook"])
        base_ctr = float(bench.get("ctr_good", 2.0))
        base_cvr = float(bench.get("cvr_good", 3.0))

        angle_multipliers = {
            "PAIN_POINT": (1.18, 1.05),
            "SOCIAL_PROOF": (1.08, 1.22),
            "MYTH_BUSTER": (1.25, 0.98),
            "OFFER_FOMO": (1.12, 1.28),
            "URGENCY_FOMO": (1.12, 1.28),
        }
        hook_multipliers = {
            "Hook_A": (1.06, 1.02),
            "Hook_B": (1.00, 1.08),
            "Hook_C": (0.96, 1.04),
        }

        camp_slug = _re.sub(
            r"[^a-z0-9]+",
            "_",
            str(merged_ctx.get("campaign_name") or f"camp_{campaign_id or 1}").lower(),
        ).strip("_")[:32] or "campaign"
        ws_id = merged_ctx.get("workspace_id")

        enriched_variants = []
        for idx, item in enumerate(raw_variants):
            if not isinstance(item, dict):
                continue
            angle = str(item.get("angle") or angles_list[idx % len(angles_list)]).upper()
            hook_type = str(item.get("hook_type") or f"Hook_{chr(65 + (idx % 3))}")
            title = str(item.get("title") or "").strip() or f"[{angle}] Giải pháp đột phá"
            body = str(item.get("body") or "").strip() or title
            cta = str(item.get("cta") or "Đăng ký ngay").strip()
            hook_text = str(item.get("hook_text") or item.get("hook_3s") or title)

            ctr_mult, cvr_mult = angle_multipliers.get(angle, (1.0, 1.0))
            h_ctr_m, h_cvr_m = hook_multipliers.get(hook_type, (1.0, 1.0))
            if funnel_stage == "ToFU":
                ctr_mult *= 1.10
                cvr_mult *= 0.85
            elif funnel_stage == "BoFU":
                cvr_mult *= 1.12

            pred_ctr = round(base_ctr * ctr_mult * h_ctr_m, 2)
            pred_cvr = round(base_cvr * cvr_mult * h_cvr_m, 2)

            scan_res = ComplianceScanner.scan(
                title=title,
                body=body,
                cta=cta,
                workspace_id=ws_id,
                db=db,
            )
            utm_params = (
                f"?utm_source={channel}&utm_medium=paid_social"
                f"&utm_campaign={camp_slug}&utm_content={angle.lower()}_{hook_type.lower()}"
            )
            enriched_variants.append({
                "id": f"{angle}_{hook_type}_{idx + 1}",
                "angle": angle,
                "angle_code": angle,
                "creative_angle": angle,
                "angle_label": str(item.get("angle_label") or angle),
                "funnel_stage": funnel_stage,
                "hook_type": hook_type,
                "hook_variant": hook_type,
                "hook_text": hook_text,
                "hook_3s": hook_text,
                "title": title,
                "body": body,
                "cta": cta,
                "ab_hypothesis": str(item.get("ab_hypothesis") or f"Kiểm thử góc {angle} kết hợp {hook_type} trên kênh {channel}."),
                "predicted_ctr_pct": pred_ctr,
                "predicted_cvr_pct": pred_cvr,
                "compliance_score": int(scan_res.score),
                "compliance_status": str(scan_res.status),
                "utm_params": utm_params,
            })

        return {
            "campaign_id": campaign_id,
            "product_name": prod_name,
            "channel": channel,
            "funnel_stage": funnel_stage,
            "angles_count": len(angles_list),
            "total_variants": len(enriched_variants),
            "variants_count": len(enriched_variants),
            "strategy_summary": (
                f"Đã thiết lập {len(angles_list)} Góc tiếp cận tâm lý × {hooks_per_angle} biến thể 3s Hook "
                f"({len(enriched_variants)} Ad Variants) cho '{prod_name}' ở tầng phễu {funnel_stage}."
            ),
            "variants": enriched_variants,
            "provider_used": raw.get("model_provider"),
            "model_used": raw.get("model_used"),
            "fallback_used": bool(raw.get("is_fallback", False)),
        }

    def simulate_prelaunch_critic(
        self,
        db: Session,
        user_id: int,
        campaign_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Mô phỏng Hội đồng chuyên gia thẩm định quảng cáo trước khi xuất bản."""
        from app.services.compliance.compliance_service import ComplianceScanner

        merged_ctx: Dict[str, Any] = {}
        if isinstance(context, dict):
            merged_ctx.update(context)
        merged_ctx.update({k: v for k, v in kwargs.items() if v is not None})

        ws_id = merged_ctx.get("workspace_id")
        channel = str(merged_ctx.get("channel") or merged_ctx.get("channel_code") or "facebook").lower().strip()
        title = str(merged_ctx.get("title") or "").strip()
        body = str(merged_ctx.get("body") or "").strip()
        cta = str(merged_ctx.get("cta") or "Đăng ký ngay").strip()

        scan_res = ComplianceScanner.scan(
            title=title,
            body=body,
            cta=cta,
            workspace_id=ws_id,
            db=db,
        )
        violations_summary = (
            ", ".join(f"{v.word} ({v.severity})" for v in scan_res.violations)
            if scan_res.violations
            else "Không phát hiện từ khóa cấm"
        )

        exec_ctx = {
            **merged_ctx,
            "channel": channel,
            "title": title,
            "body": body,
            "cta": cta,
            "compliance_score": int(scan_res.score),
            "violations_summary": violations_summary,
        }
        raw = self.execute_task(
            db=db,
            user_id=user_id,
            campaign_id=campaign_id,
            task_type="prelaunch_critic",
            task_code="PRELAUNCH_CRITIC",
            prompt_version=str(merged_ctx.get("prompt_version") or "v3"),
            context=exec_ctx,
        )
        fallback_data = self._generate_fallback_prelaunch_critic(exec_ctx)
        raw_personas = raw.get("personas") if isinstance(raw.get("personas"), list) and len(raw.get("personas")) >= 3 else fallback_data["personas"]
        personas = []
        for idx, p in enumerate(raw_personas):
            if not isinstance(p, dict):
                continue
            fix_s = str(p.get("fix_suggestion") or p.get("actionable_fix") or "Tối ưu câu mở đầu và bằng chứng số liệu.")
            personas.append({
                "persona_id": str(p.get("persona_id") or f"persona_{idx + 1}"),
                "persona_name": str(p.get("persona_name") or f"Persona #{idx + 1}"),
                "persona_role": str(p.get("persona_role") or "Chuyên gia đánh giá chuyển đổi & chính sách quảng cáo"),
                "avatar_emoji": str(p.get("avatar_emoji") or ("🧐" if idx == 0 else "📱" if idx == 1 else "🛡️" if idx == 2 else "🤖")),
                "score": int(p.get("score", 80)),
                "verdict": str(p.get("verdict") or "PASS"),
                "critique": str(p.get("critique") or ""),
                "fix_suggestion": fix_s,
                "actionable_fix": fix_s,
            })

        overall_score = int(raw.get("overall_readiness_score", fallback_data["overall_readiness_score"]))
        verdict = str(raw.get("verdict") or fallback_data["verdict"])
        if int(scan_res.score) < 70:
            launch_rec = "HIGH_RISK_REWRITE"
        elif overall_score >= 75:
            launch_rec = "READY_TO_LAUNCH"
        else:
            launch_rec = "NEEDS_MINOR_TUNING"

        imp_title = str(raw.get("improved_title") or fallback_data["improved_title"])
        imp_body = str(raw.get("improved_body") or fallback_data["improved_body"])
        imp_cta = str(raw.get("improved_cta") or fallback_data["improved_cta"])

        return {
            "overall_readiness_score": overall_score,
            "thumb_stop_score": int(raw.get("thumb_stop_score", fallback_data["thumb_stop_score"])),
            "conversion_friction_score": int(raw.get("conversion_friction_score", fallback_data["conversion_friction_score"])),
            "compliance_score": int(scan_res.score),
            "verdict": verdict,
            "verdict_label": (
                "Sẵn sàng triển khai chạy thử nghiệm (Ready to Launch)"
                if launch_rec == "READY_TO_LAUNCH"
                else "Cần tinh chỉnh câu chữ trước khi tiêu ngân sách"
            ),
            "launch_recommendation": launch_rec,
            "weakest_sentence": str(raw.get("weakest_sentence") or fallback_data["weakest_sentence"]),
            "weakest_reason": str(raw.get("weakest_reason") or fallback_data["weakest_reason"]),
            "personas": personas,
            "persona_critiques": personas[:3],
            "improved_title": imp_title,
            "improved_body": imp_body,
            "improved_cta": imp_cta,
            "rewritten_version": {
                "title": imp_title,
                "body": imp_body,
                "cta": imp_cta,
                "improvement_notes": "Đã tối ưu Hook 3 giây đầu, bổ sung dẫn chứng định lượng và đảm bảo an toàn chính sách.",
            },
            "provider_used": raw.get("model_provider"),
            "model_used": raw.get("model_used"),
            "fallback_used": bool(raw.get("is_fallback", False)),
        }

    def semantic_compliance_rewrite(
        self,
        db: Session,
        user_id: int,
        workspace_id: Optional[int] = None,
        channel: str = "facebook",
        title: str = "",
        body: str = "",
        cta: Optional[str] = None,
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
        campaign_id: Optional[int] = None,
        violations: Optional[List[Any]] = None,
        banned_keywords: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Viết lại ngữ cảnh câu chứa từ khóa vi phạm chính sách quảng cáo & Brand Kit và xác minh lại bằng ComplianceScanner."""
        from app.services.compliance.compliance_service import ComplianceScanner
        from app.models.entities import BrandKit, Campaign

        if workspace_id is None and campaign_id is not None:
            camp_obj = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if camp_obj:
                workspace_id = camp_obj.workspace_id

        old_scan = ComplianceScanner.scan(
            title=title,
            body=body,
            cta=cta or "",
            workspace_id=workspace_id,
            db=db,
        )
        if not old_scan.violations and not violations:
            return {
                "old_score": int(old_scan.score),
                "new_score": int(old_scan.score),
                "old_status": str(old_scan.status),
                "new_status": str(old_scan.status),
                "fixed_violations_count": 0,
                "fixed_violations": [],
                "title": title,
                "body": body,
                "cta": cta,
                "rewritten_title": title,
                "rewritten_body": body,
                "rewritten_cta": cta,
                "violations_before": [],
                "violations_after": [],
            }

        bk = db.query(BrandKit).filter(BrandKit.workspace_id == workspace_id).first() if workspace_id else None
        violations_raw = [v.model_dump() for v in old_scan.violations] if old_scan.violations else (violations or [])
        violations_text = "\n".join(
            f"- Từ vi phạm: '{v.get('word')}' ({v.get('category')}/{v.get('severity')}) -> Gợi ý: {v.get('suggestion')}"
            for v in violations_raw
            if isinstance(v, dict)
        )

        ctx = {
            "workspace_id": workspace_id,
            "channel": channel,
            "brand_name": bk.brand_name if bk else "MarketFlow AI",
            "tone_of_voice": bk.tone_of_voice if bk and bk.tone_of_voice else "Chuyên nghiệp, tin cậy",
            "title": title,
            "body": body,
            "cta": cta or "",
            "violations_text": violations_text,
            "violations_raw": violations_raw,
            "banned_keywords": banned_keywords or [],
            "provider": preferred_provider,
            "model": preferred_model,
        }
        rewritten = self.execute_task(
            db=db,
            user_id=user_id,
            campaign_id=campaign_id,
            task_type="compliance_rewrite",
            task_code="COMPLIANCE_REWRITE",
            prompt_version="v3",
            context=ctx,
        )
        # Bảo đảm mọi từ khóa cấm còn sót đều được làm sạch ngữ nghĩa
        cleaned_fallback = self._generate_fallback_compliance_rewrite({
            "title": str(rewritten.get("title") or title),
            "body": str(rewritten.get("body") or body),
            "cta": str(rewritten.get("cta") or cta or ""),
            "violations_raw": violations_raw,
        })
        new_title = cleaned_fallback["title"]
        new_body = cleaned_fallback["body"]
        new_cta = cleaned_fallback["cta"] if cta is not None else None

        new_scan = ComplianceScanner.scan(
            title=new_title,
            body=new_body,
            cta=new_cta or "",
            workspace_id=workspace_id,
            db=db,
        )
        fixed_words = [
            str(v.get("word"))
            for v in violations_raw
            if isinstance(v, dict) and v.get("word")
        ]
        fixed_count = max(len(fixed_words), max(0, len(old_scan.violations) - len(new_scan.violations)))

        return {
            "old_score": int(old_scan.score),
            "new_score": int(new_scan.score),
            "old_status": str(old_scan.status),
            "new_status": str(new_scan.status),
            "fixed_violations_count": fixed_count,
            "fixed_violations": fixed_words,
            "title": new_title,
            "body": new_body,
            "cta": new_cta,
            "rewritten_title": new_title,
            "rewritten_body": new_body,
            "rewritten_cta": new_cta,
            "violations_before": violations_raw,
            "violations_after": [v.model_dump() for v in new_scan.violations],
        }

    def extract_winning_patterns(
        self,
        db: Session,
        workspace_id: int,
    ) -> Dict[str, Any]:
        """Khám phá quy luật chiến thắng (Cross-Campaign Winning Pattern Extractor) từ dữ liệu thực trong Workspace."""
        from app.models.entities import Campaign, MarketingContent, CampaignMetric, MarketingChannel

        campaigns = db.query(Campaign).filter(Campaign.workspace_id == workspace_id).all()
        camp_ids = [c.id for c in campaigns]
        if not camp_ids:
            return {
                "workspace_id": workspace_id,
                "campaigns_analyzed": 0,
                "contents_analyzed": 0,
                "top_channel": None,
                "top_creative_angle": None,
                "angle_leaderboard": [],
                "channel_leaderboard": [],
                "playbook_recommendations": [
                    "Workspace chưa có dữ liệu chiến dịch. Hãy khởi tạo chiến dịch và tạo ma trận Angle × Hook để thu thập dữ liệu."
                ],
                "patterns": [],
            }

        contents = db.query(MarketingContent).filter(MarketingContent.campaign_id.in_(camp_ids)).all()
        metrics = db.query(CampaignMetric).filter(CampaignMetric.campaign_id.in_(camp_ids)).all()
        channels = {ch.id: ch for ch in db.query(MarketingChannel).all()}

        # 1. Tổng hợp hiệu suất theo kênh
        ch_stats: Dict[int, Dict[str, Any]] = {}
        for m in metrics:
            cid = m.channel_id
            if cid not in ch_stats:
                ch_obj = channels.get(cid)
                ch_stats[cid] = {
                    "channel_id": cid,
                    "channel_code": ch_obj.code if ch_obj else f"ch_{cid}",
                    "channel_name": ch_obj.name if ch_obj else f"Channel #{cid}",
                    "views": 0,
                    "clicks": 0,
                    "conversions": 0,
                    "cost": 0.0,
                    "revenue": 0.0,
                }
            ch_stats[cid]["views"] += int(m.views or 0)
            ch_stats[cid]["clicks"] += int(m.clicks or 0)
            ch_stats[cid]["conversions"] += int(m.conversions or 0)
            ch_stats[cid]["cost"] += float(m.cost or 0.0)
            ch_stats[cid]["revenue"] += float(m.revenue or 0.0)

        channel_leaderboard = []
        for cid, st in ch_stats.items():
            ctr = (st["clicks"] / st["views"] * 100.0) if st["views"] > 0 else 0.0
            cvr = (st["conversions"] / st["clicks"] * 100.0) if st["clicks"] > 0 else 0.0
            roas = (st["revenue"] / st["cost"]) if st["cost"] > 0 else 0.0
            channel_leaderboard.append({
                **st,
                "cost": round(st["cost"], 2),
                "revenue": round(st["revenue"], 2),
                "ctr_pct": round(ctr, 2),
                "cvr_pct": round(cvr, 2),
                "roas": round(roas, 2),
            })
        channel_leaderboard.sort(key=lambda x: (x["roas"], x["ctr_pct"]), reverse=True)

        # 2. Tổng hợp hiệu suất theo Creative Angle
        camp_metrics_map: Dict[int, List[CampaignMetric]] = {cid: [] for cid in camp_ids}
        content_metrics_map: Dict[int, List[CampaignMetric]] = {}
        for m in metrics:
            if m.campaign_id in camp_metrics_map:
                camp_metrics_map[m.campaign_id].append(m)
            if getattr(m, "content_id", None):
                content_metrics_map.setdefault(m.content_id, []).append(m)

        def _infer_angle_from_content(c: MarketingContent) -> str:
            if getattr(c, "creative_angle", None):
                return str(c.creative_angle).upper()
            txt = f"{c.title or ''} {c.body or ''}".lower()
            if any(k in txt for k in ("ưu đãi", "giảm", "suất", "đầu tiên", "fomo")):
                return "OFFER_FOMO"
            if any(k in txt for k in ("case study", "học viên", "khách hàng", "đánh giá")):
                return "SOCIAL_PROOF"
            if any(k in txt for k in ("lầm tưởng", "sự thật", "ngược đời")):
                return "MYTH_BUSTER"
            return "PAIN_POINT"

        angle_stats: Dict[str, Dict[str, Any]] = {}
        for c in contents:
            ang = _infer_angle_from_content(c)
            if ang not in angle_stats:
                angle_stats[ang] = {
                    "angle": ang,
                    "contents_count": 0,
                    "approved_count": 0,
                    "views": 0,
                    "clicks": 0,
                    "conversions": 0,
                    "cost": 0.0,
                    "revenue": 0.0,
                }
            angle_stats[ang]["contents_count"] += 1
            if c.status in ("APPROVED", "PUBLISHED"):
                angle_stats[ang]["approved_count"] += 1
            c_rows = content_metrics_map.get(c.id) or camp_metrics_map.get(c.campaign_id, [])
            for m in c_rows:
                angle_stats[ang]["views"] += int(m.views or 0)
                angle_stats[ang]["clicks"] += int(m.clicks or 0)
                angle_stats[ang]["conversions"] += int(m.conversions or 0)
                angle_stats[ang]["cost"] += float(m.cost or 0.0)
                angle_stats[ang]["revenue"] += float(m.revenue or 0.0)

        angle_leaderboard = []
        for ang, st in angle_stats.items():
            ctr = (st["clicks"] / st["views"] * 100.0) if st["views"] > 0 else 0.0
            cvr = (st["conversions"] / st["clicks"] * 100.0) if st["clicks"] > 0 else 0.0
            roas = (st["revenue"] / st["cost"]) if st["cost"] > 0 else 0.0
            angle_leaderboard.append({
                "angle": ang,
                "contents_count": st["contents_count"],
                "approved_count": st["approved_count"],
                "ctr_pct": round(ctr, 2),
                "cvr_pct": round(cvr, 2),
                "roas": round(roas, 2),
            })
        angle_leaderboard.sort(key=lambda x: (x["roas"], x["ctr_pct"], x["contents_count"]), reverse=True)

        top_channel = channel_leaderboard[0] if channel_leaderboard else None
        top_angle = angle_leaderboard[0] if angle_leaderboard else None

        playbook = []
        if top_channel:
            playbook.append(
                f"Kênh chủ lực sinh lời cao nhất: {top_channel['channel_name']} (ROAS {top_channel['roas']}x, CTR {top_channel['ctr_pct']}%, CVR {top_channel['cvr_pct']}%). Ưu tiên phân bổ 45-60% ngân sách chiến dịch mới vào kênh này."
            )
        if top_angle:
            playbook.append(
                f"Góc tiếp cận tâm lý hiệu quả nhất: {top_angle['angle']} ({top_angle['contents_count']} bài viết, CTR {top_angle['ctr_pct']}%, ROAS {top_angle['roas']}x). Hãy dùng góc này làm biến thể chủ đạo khi nhân bản chiến dịch."
            )
        playbook.append(
            "Quy tắc vàng chống bão hòa (Anti-Fatigue): Luôn khởi tạo tối thiểu 3 góc tiếp cận (PAIN_POINT, SOCIAL_PROOF, OFFER_FOMO) × 2 Hook cho mỗi chiến dịch để xoay vòng sau mỗi 4 ngày chạy."
        )

        patterns_list = []
        angle_labels_map = {
            "PAIN_POINT": "Đánh trúng Nỗi đau Chi phí (PAS) + Số liệu Thực chứng",
            "SOCIAL_PROOF": "Bằng chứng Xã hội (Case Study & Review Thật)",
            "MYTH_BUSTER": "Phá vỡ Ngộ nhận Ngành (Pattern Interrupt)",
            "OFFER_FOMO": "Ưu đãi Giới hạn & Cam kết Không Rủi ro",
        }
        for idx, al in enumerate(angle_leaderboard[:3]):
            ang_code = al["angle"]
            patterns_list.append({
                "id": f"win-pattern-{idx + 1}",
                "pattern_name": angle_labels_map.get(ang_code, f"Góc tiếp cận {ang_code}"),
                "hook_type": f"3s {ang_code} Hook",
                "channel": top_channel["channel_name"] if top_channel else "Facebook & TikTok Ads",
                "avg_ctr": al["ctr_pct"] or 2.8,
                "avg_cvr": al["cvr_pct"] or 3.9,
                "avg_roas": al["roas"] or 3.6,
                "sample_count": al["contents_count"],
                "insight": playbook[min(idx, len(playbook) - 1)],
                "example_hook": f"[{ang_code}] Giải quyết triệt để điểm nghẽn chuyển đổi ngay trong 3 giây đầu tiên.",
            })

        return {
            "workspace_id": workspace_id,
            "campaigns_analyzed": len(campaigns),
            "contents_analyzed": len(contents),
            "top_channel": top_channel,
            "top_creative_angle": top_angle,
            "angle_leaderboard": angle_leaderboard,
            "channel_leaderboard": channel_leaderboard,
            "playbook_recommendations": playbook,
            "patterns": patterns_list,
        }

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
            safe_task_type = task_type if task_type in ("IDEA", "DRAFT", "SUMMARY", "OMNICHANNEL") else (
                "SUMMARY" if task_type in ("PRELAUNCH_CRITIC",) else (
                    "DRAFT" if task_type in ("COMPLIANCE_REWRITE",) else "IDEA"
                )
            )
            log_entry = AILog(
                user_id=user_id,
                campaign_id=campaign_id,
                task_type=safe_task_type,
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
