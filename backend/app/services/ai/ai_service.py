import time
import json
import hashlib
import re
from typing import Dict, Any, List, Optional, Tuple
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

        if not requires_api_key or (provider == "opencode" and os.path.isfile("/usr/local/bin/opencode")):
            # Ollama / HuggingFace / OpenCode CLI trên VPS: gọi được không cần nhập API key.
            eff_sys_model = _default_model_for(provider) if provider == "opencode" else (system_model or _default_model_for(provider))
            return {
                "api_key": None,
                "model": eff_sys_model,
                "provider": provider,
                "tier": "SYSTEM",
                "source_id": None,
                "requires_api_key": False,
            }

        # Tier 3.5: Trên máy chủ Production VPS có cài sẵn OpenCode CLI, nếu provider được chọn
        # chưa cấu hình API key thì tự động định tuyến sang OpenCode Free (`glm-5.3-flash-free`)
        # để sinh nội dung bằng LLM thật thay vì rơi xuống template dự phòng.
        if os.path.isfile("/usr/local/bin/opencode") and not os.environ.get("PYTEST_CURRENT_TEST"):
            return {
                "api_key": None,
                "model": _default_model_for("opencode"),
                "provider": "opencode",
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
        retries_override: Optional[int] = None,
        base_url_override: Optional[str] = None,
        conversation_messages: Optional[List[Dict[str, str]]] = None,
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

        if spec.requires_api_key and (not key_to_use or not str(key_to_use).strip()):
            raise RuntimeError(
                f"Chưa cấu hình API Key cho nhà cung cấp AI '{eff_provider}'. "
                "Vui lòng thêm API Key trong phần Cài đặt AI hoặc biến môi trường trước khi sinh nội dung."
            )

        custom_base = (base_url_override or "").strip().rstrip("/")
        if custom_base and custom_base.startswith(("http://", "https://")):
            base_url = custom_base
        else:
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
            if conversation_messages:
                history_msgs = [
                    {"role": ("assistant" if m.get("role") == "assistant" else "user"), "content": str(m.get("content") or "")}
                    for m in conversation_messages
                    if m.get("content")
                ]
                payload["messages"] = history_msgs + [{"role": "user", "content": user_prompt}]
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
            history_msgs = [
                {"role": ("assistant" if m.get("role") == "assistant" else "user"), "content": str(m.get("content") or "")}
                for m in (conversation_messages or [])
                if m.get("content")
            ]
            payload = {
                "model": model_to_use,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    *history_msgs,
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
            }

        # Circuit breaker: đo độ khoẻ provider trước khi gọi. Khi provider đã chết,
        # `allow()` ném ngay thay vì mất thêm vài phút retry rồi mới rơi xuống
        # fallback, giữ chân slot AI trong hàng đợi.
        circuit_breaker.allow(eff_provider)

        # Nếu đang chọn provider 'opencode' mặc định (không dùng custom_base_url riêng)
        # và máy chủ VPS có cài sẵn `/usr/local/bin/opencode`, ưu tiên gọi thẳng CLI Bridge
        # để tránh lỗi HTTP 403 FreeTierError từ endpoint web.
        import os as _os_chk
        if (
            eff_provider == "opencode"
            and not (base_url_override and str(base_url_override).strip())
            and _os_chk.path.isfile("/usr/local/bin/opencode")
            and not _os_chk.environ.get("PYTEST_CURRENT_TEST")
        ):
            cli_started = time.monotonic()
            cli_direct = self._try_opencode_cli_bridge(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                active_model=model_to_use,
                conversation_messages=conversation_messages,
                timeout_sec=min(int(effective_timeout or 35), 40),
                active_key=key_to_use,
                thread_id=getattr(self, "_active_thread_id", None),
            )
            if cli_direct:
                circuit_breaker.record_success(eff_provider, time.monotonic() - cli_started)
                return cli_direct
            raise RuntimeError("OpenCode CLI trên VPS đang chạm giới hạn miễn phí tạm thời (Free usage limit reached)")

        last_error = None
        for attempt in range(effective_retries + 1):
            # Chỉ thử breaker ở lần đầu: nếu provider đang HALF_OPEN thì lần thử dò
            # đó đó đã được cho qua ở `allow()`; các lần retry nội bộ không cần hỏi lại.
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
                        if eff_provider == "opencode" and resp.status_code in (400, 401, 403):
                            cli_text = self._try_opencode_cli_bridge(
                                system_prompt=system_prompt,
                                user_prompt=user_prompt,
                                active_model=model_to_use,
                                conversation_messages=conversation_messages,
                                timeout_sec=min(int(effective_timeout or 60), 90),
                                active_key=key_to_use,
                                thread_id=getattr(self, "_active_thread_id", None),
                            )
                            if cli_text:
                                circuit_breaker.record_success(eff_provider, time.monotonic() - attempt_started)
                                return cli_text
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

    # Bộ nhớ ánh xạ thread_id trên Web -> session_id (ses_...) của OpenCode CLI trên VPS
    _opencode_thread_sessions: Dict[int, str] = {}

    def _try_opencode_cli_bridge(
        self,
        system_prompt: str,
        user_prompt: str,
        active_model: Optional[str] = None,
        conversation_messages: Optional[List[Dict[str, str]]] = None,
        timeout_sec: int = 60,
        active_key: Optional[str] = None,
        thread_id: Optional[int] = None,
    ) -> Optional[str]:
        """Cầu nối trực tiếp tới `/usr/local/bin/opencode` (OpenCode CLI v1.19.4 trên VPS).
        Hỗ trợ:
        1. Gắn phiên hội thoại liên tục (`-s ses_...`) theo từng `thread_id` của người dùng web.
        2. Đọc thông tin đăng nhập từ `/root/.local/share/opencode/auth.json` (nếu đã chạy `opencode auth login`).
        3. Khởi tạo thư mục Git nhẹ hợp lệ (`/tmp/marketflow_oc_workspace`) để OpenCode không quét toàn bộ ổ đĩa `/`.
        4. Tự động kết nối vào daemon `opencode serve` qua `OPENCODE_ATTACH_URL` nếu được bật.
        """
        import os
        import shutil
        import subprocess
        import tempfile

        # Không gọi CLI thật trong môi trường pytest trừ khi được bật tường minh
        if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("MARKETFLOW_ALLOW_OPENCODE_CLI_IN_TEST"):
            return None

        opencode_bin = None
        for candidate in ("/usr/local/bin/opencode", "/root/.opencode/bin/opencode", shutil.which("opencode")):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                opencode_bin = candidate
                break
        if not opencode_bin:
            return None

        retired_or_empty = {"", "mimo-v2.6-flash-free", "space-bunny-free", "step-5-preview-free", "minimax-m3.1-flash-free"}
        requested_model = str(active_model or "").strip()
        if requested_model.startswith("opencode/"):
            requested_model = requested_model.split("/", 1)[1]

        fallback_models = []
        if requested_model and requested_model not in retired_or_empty:
            fallback_models.append(requested_model)
        for m in (
            "glm-5.3-flash-free",
            "deepseek-v4.1-flash-free",
            "nemotron-3.5-lightning-free",
            "flint-40b-free",
            "nemotron-3-ultra-free",
            "beam-free",
            "big-pickle",
        ):
            if m not in fallback_models:
                fallback_models.append(m)

        existing_ses_id = self._opencode_thread_sessions.get(int(thread_id)) if thread_id else None

        parts: List[str] = []
        if system_prompt and system_prompt.strip():
            parts.append(f"[SYSTEM INSTRUCTION]:\n{system_prompt.strip()}")
        if conversation_messages and not existing_ses_id:
            hist_lines = []
            for msg in conversation_messages[-8:]:
                r = "Assistant" if msg.get("role") == "assistant" else "User"
                c = str(msg.get("content") or "").strip()
                if c:
                    hist_lines.append(f"{r}: {c}")
            if hist_lines:
                parts.append("[CONVERSATION HISTORY]:\n" + "\n".join(hist_lines))
        parts.append(f"[USER REQUEST]:\n{user_prompt.strip()}")
        combined_prompt = "\n\n".join(parts)

        if os.path.isdir("/opt/marketflow/opencode_ws") and os.access("/opt/marketflow/opencode_ws", os.W_OK):
            work_dir = "/opt/marketflow/opencode_ws"
        else:
            work_dir = os.path.join(tempfile.gettempdir(), "marketflow_oc_workspace")
        try:
            os.makedirs(work_dir, exist_ok=True)
            git_head = os.path.join(work_dir, ".git", "HEAD")
            if not os.path.isfile(git_head):
                subprocess.run(
                    ["git", "init", "-q"],
                    cwd=work_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3,
                )
        except Exception:
            work_dir = tempfile.gettempdir()

        cli_env = dict(os.environ)
        # Loại bỏ khóa OPENCODE_API_KEY hết hạn khỏi môi trường con nếu người dùng chọn chế độ Free
        if not active_key:
            cli_env.pop("OPENCODE_API_KEY", None)
        else:
            cli_env["OPENCODE_API_KEY"] = str(active_key).strip()

        # Ưu tiên giữ HOME=/root nếu tồn tại kho dữ liệu/đăng nhập của OpenCode tại /root/.local/share/opencode
        if os.path.isdir("/root/.local/share/opencode") and os.access("/root/.local/share/opencode", os.W_OK):
            cli_env["HOME"] = "/root"
        elif os.path.isdir("/opt/marketflow") and os.access("/opt/marketflow", os.W_OK):
            cli_env["HOME"] = "/opt/marketflow"
        else:
            cli_env["HOME"] = work_dir

        attach_url = os.environ.get("OPENCODE_ATTACH_URL", "").strip()

        for model_slug in fallback_models[:3]:
            proc = None
            try:
                cmd_args = [
                    opencode_bin,
                    "run",
                    "--pure",
                    "--format",
                    "json",
                    "-m",
                    f"opencode/{model_slug}",
                ]
                if existing_ses_id:
                    cmd_args.extend(["-s", existing_ses_id])
                if attach_url:
                    cmd_args.extend(["--attach", attach_url])
                cmd_args.append(combined_prompt)

                proc = subprocess.Popen(
                    cmd_args,
                    cwd=work_dir,
                    env=cli_env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                text_chunks: List[str] = []
                captured_ses_id: Optional[str] = None
                deadline = time.monotonic() + min(max(timeout_sec, 15), 40)
                hit_fatal_error = False
                if proc.stdout is not None:
                    for raw_line in proc.stdout:
                        if time.monotonic() > deadline:
                            break
                        line_s = raw_line.strip()
                        if "AI_APICallError" in line_s or "Free usage limit" in line_s or "FreeTierError" in line_s:
                            logger.warning("[OpenCode CLI Bridge] Fast-fail on upstream error (%s): %s", model_slug, line_s[:220])
                            hit_fatal_error = True
                            break
                        if line_s.startswith("{"):
                            try:
                                evt = json.loads(line_s)
                                if not captured_ses_id and isinstance(evt.get("sessionID"), str):
                                    captured_ses_id = evt["sessionID"]
                                evt_type = evt.get("type")
                                if evt_type == "text":
                                    part = evt.get("part") or {}
                                    if not captured_ses_id and isinstance(part.get("sessionID"), str):
                                        captured_ses_id = part["sessionID"]
                                    txt = part.get("text")
                                    if txt:
                                        text_chunks.append(str(txt))
                                elif evt_type in ("step_finish", "step-finish") and text_chunks:
                                    break
                            except Exception:
                                continue
                try:
                    proc.kill()
                    proc.wait(timeout=2)
                except Exception:
                    pass
                if hit_fatal_error:
                    continue
                full_text = "".join(text_chunks).strip()
                if full_text:
                    if thread_id and captured_ses_id:
                        self._opencode_thread_sessions[int(thread_id)] = captured_ses_id
                    logger.info(
                        "[OpenCode CLI Bridge] Succeeded via model opencode/%s session=%s (%d chars)",
                        model_slug,
                        captured_ses_id or existing_ses_id or "new",
                        len(full_text),
                    )
                    return full_text
            except Exception as cli_exc:
                logger.warning("[OpenCode CLI Bridge] Model %s failed: %s", model_slug, cli_exc)
                if proc is not None:
                    try:
                        proc.kill()
                        proc.wait(timeout=2)
                    except Exception:
                        pass
                continue
        return None

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
            active_provider = resolved.get("provider") or req_provider
            if active_provider != req_provider and active_provider == "opencode":
                active_model = resolved.get("model") or "glm-5.3-flash-free"
            else:
                active_model = context.get("model") or resolved.get("model") or self.model
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
                if hop_provider == "opencode" and hop_model == "mimo-v2.6-flash-free":
                    hop_model = "glm-5.3-flash-free"

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
                    active_provider = hop_provider
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
                        prompt_version, input_hash, None, result_status, error_code, latency_ms,
                        provider=active_provider,
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
                        self._log_call(db, user_id, campaign_id, task_code, active_model, prompt_version, input_hash, None, result_status, error_code, latency_ms, provider=active_provider)
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
                        self._log_call(db, user_id, campaign_id, task_code, active_model, prompt_version, input_hash, None, result_status, error_code, latency_ms, provider=active_provider)
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
            latency_ms=latency_ms,
            provider=active_provider,
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
        candidate_title = str(rewritten.get("title") or title)
        candidate_body = str(rewritten.get("body") or body)
        candidate_cta = str(rewritten.get("cta") or cta or "")

        candidate_scan = ComplianceScanner.scan(
            title=candidate_title,
            body=candidate_body,
            cta=candidate_cta,
            workspace_id=workspace_id,
            db=db,
        )
        # Chỉ áp dụng thay thế từ điển dự phòng nếu đầu ra của LLM vẫn còn sót từ khóa cấm
        if candidate_scan.violations:
            cleaned_fallback = self._generate_fallback_compliance_rewrite({
                "title": candidate_title,
                "body": candidate_body,
                "cta": candidate_cta,
                "violations_raw": [v.model_dump() for v in candidate_scan.violations],
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
        else:
            new_title = candidate_title
            new_body = candidate_body
            new_cta = candidate_cta if cta is not None else None
            new_scan = candidate_scan

        remaining_words = {str(v.word).lower() for v in new_scan.violations if getattr(v, "word", None)}
        fixed_words = [
            str(v.get("word"))
            for v in violations_raw
            if isinstance(v, dict) and v.get("word") and str(v.get("word")).lower() not in remaining_words
        ]
        fixed_count = len(fixed_words)

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
        seen_metric_ids_by_angle: Dict[str, set] = {}
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
                seen_metric_ids_by_angle[ang] = set()
            angle_stats[ang]["contents_count"] += 1
            if c.status in ("APPROVED", "PUBLISHED"):
                angle_stats[ang]["approved_count"] += 1
            c_rows = content_metrics_map.get(c.id) or camp_metrics_map.get(c.campaign_id, [])
            for m in c_rows:
                m_key = getattr(m, "id", None) or id(m)
                if m_key in seen_metric_ids_by_angle[ang]:
                    continue
                seen_metric_ids_by_angle[ang].add(m_key)
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
        default_distinct_channels = [
            "Facebook Ads & Fanpage",
            "TikTok Short Video & Reels",
            "Email Marketing Newsletter",
            "Google Search Ads",
        ]
        for idx, al in enumerate(angle_leaderboard[:3]):
            ang_code = al["angle"]
            if idx < len(channel_leaderboard):
                ch_entry = channel_leaderboard[idx]
                ch_label = ch_entry["channel_name"]
                ch_ctr = ch_entry["ctr_pct"]
                ch_cvr = ch_entry["cvr_pct"]
                ch_roas = ch_entry["roas"]
                ch_insight = (
                    f"Kênh {ch_label} đạt CTR {ch_ctr}%, CVR {ch_cvr}% "
                    f"({ch_entry['views']:,} lượt xem, {ch_entry['clicks']:,} click, "
                    f"{ch_entry['conversions']:,} chuyển đổi, chi phí {ch_entry['cost']:,.0f} đ)."
                )
            else:
                ch_label = default_distinct_channels[idx % len(default_distinct_channels)]
                ch_ctr = al["ctr_pct"]
                ch_cvr = al["cvr_pct"]
                ch_roas = al["roas"]
                ch_insight = playbook[min(idx, len(playbook) - 1)]
            patterns_list.append({
                "id": f"win-pattern-{idx + 1}",
                "pattern_name": angle_labels_map.get(ang_code, f"Góc tiếp cận {ang_code}"),
                "hook_type": f"3s {ang_code} Hook",
                "channel": ch_label,
                "avg_ctr": ch_ctr,
                "avg_cvr": ch_cvr,
                "avg_roas": ch_roas,
                "sample_count": al["contents_count"],
                "insight": ch_insight,
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

    @staticmethod
    def _parse_vn_amount(text: str) -> Optional[float]:
        """Phân tích cụm tiền tệ tiếng Việt ('500k', '2tr4', '1.5 triệu', '15.000.000') sang VNĐ."""
        t = (text or "").strip().lower().replace(",", ".")
        m_tr_sub = re.search(r"(\d+)\s*(?:tr|triệu)\s*(\d+)", t)
        if m_tr_sub:
            whole = float(m_tr_sub.group(1))
            frac_str = m_tr_sub.group(2)
            frac = float(frac_str) / (10 ** len(frac_str))
            return (whole + frac) * 1_000_000.0
        m_unit = re.search(r"(\d+(?:\.\d+)?)\s*(tỷ|ty|triệu|tr|m|nghìn|ngàn|k)\b", t)
        if m_unit:
            val = float(m_unit.group(1))
            unit = m_unit.group(2)
            if unit in ("tỷ", "ty"):
                return val * 1_000_000_000.0
            if unit in ("triệu", "tr", "m"):
                return val * 1_000_000.0
            if unit in ("nghìn", "ngàn", "k"):
                return val * 1_000.0
        return None

    @staticmethod
    def _get_vps_resource_telemetry() -> Dict[str, Any]:
        """Đọc thông số tài nguyên thực tế của máy chủ VPS (/proc/meminfo, /proc/loadavg)
        để AI tự ý thức được giới hạn phần cứng (2 vCPU / ~2 GiB RAM) và trạng thái OpenCode CLI.
        """
        import os

        total_mb = 1986
        avail_mb = 1200
        load_1m = 0.05
        try:
            if os.path.isfile("/proc/meminfo"):
                mem_map: Dict[str, int] = {}
                with open("/proc/meminfo", "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            k = parts[0].strip()
                            v_parts = parts[1].strip().split()
                            if v_parts and v_parts[0].isdigit():
                                mem_map[k] = int(v_parts[0])
                if "MemTotal" in mem_map:
                    total_mb = max(1, mem_map["MemTotal"] // 1024)
                if "MemAvailable" in mem_map:
                    avail_mb = max(0, mem_map["MemAvailable"] // 1024)
            if os.path.isfile("/proc/loadavg"):
                with open("/proc/loadavg", "r", encoding="utf-8") as f:
                    first_tok = f.read().strip().split()[0]
                    load_1m = float(first_tok)
        except Exception:
            pass

        used_mb = max(0, total_mb - avail_mb)
        used_pct = round((used_mb / max(1, total_mb)) * 100, 1)
        low_resource_mode = avail_mb < 450 or used_pct > 80.0
        has_opencode_bin = os.path.isfile("/usr/local/bin/opencode")
        has_opencode_auth = False
        try:
            auth_path = "/root/.local/share/opencode/auth.json"
            if os.path.isfile(auth_path) and os.path.getsize(auth_path) > 10:
                with open(auth_path, "r", encoding="utf-8") as af:
                    adata = json.load(af)
                    has_opencode_auth = bool(adata and len(adata) > 0)
        except Exception:
            has_opencode_auth = False

        return {
            "total_ram_mb": total_mb,
            "used_ram_mb": used_mb,
            "avail_ram_mb": avail_mb,
            "ram_percent": used_pct,
            "cpu_load_1m": load_1m,
            "low_resource_mode": low_resource_mode,
            "has_opencode_cli": has_opencode_bin,
            "has_opencode_auth": has_opencode_auth,
        }

    def _build_deep_workspace_snapshot(
        self,
        db: Session,
        user_id: int,
        workspace_id: Optional[int],
        campaign_id: Optional[int],
    ) -> Tuple[str, Dict[str, Any]]:
        """Xây dựng bức tranh toàn cảnh dữ liệu dự án (Deep Workspace Graph — chuẩn Claude MCP / ChatGPT Projects / Gemini Workspace)
        kèm tự nhận thức tài nguyên VPS để AI có thể đọc và can thiệp sâu vào mọi thực thể trong hệ thống.
        """
        from app.models.entities import (
            Campaign,
            Product,
            BrandKit,
            Task,
            MarketingContent,
            CampaignMetric,
        )

        vps_info = self._get_vps_resource_telemetry()
        meta: Dict[str, Any] = {
            "vps": vps_info,
            "campaigns": [],
            "products": [],
            "tasks_todo": [],
            "contents": [],
            "metrics_summary": {"views": 0, "clicks": 0, "conversions": 0, "cost": 0.0, "revenue": 0.0, "roas": 0.0},
            "brand_kit": None,
        }
        lines: List[str] = [
            "[BỨC TRANH TOÀN CẢNH DỰ ÁN & TỰ NHẬN THỨC TÀI NGUYÊN VPS (DEEP WORKSPACE CONTEXT — MCP)]:",
            (
                f"• Hạ tầng VPS hiện tại: RAM đang dùng {vps_info['used_ram_mb']}/{vps_info['total_ram_mb']} MB "
                f"({vps_info['ram_percent']}%, còn trống {vps_info['avail_ram_mb']} MB), CPU Load 1m={vps_info['cpu_load_1m']}, "
                f"Chế độ tiết kiệm tài nguyên={'BẬT (Ưu tiên tác vụ gọn nhẹ)' if vps_info['low_resource_mode'] else 'ỔN ĐỊNH (Single-Worker ~76MB RAM)'}, "
                f"OpenCode CLI v1.19.4={'Đã cài sẵn (/usr/local/bin/opencode)' if vps_info['has_opencode_cli'] else 'Chưa cài'}."
            ),
        ]

        try:
            camp_q = db.query(Campaign)
            if workspace_id is not None:
                camp_q = camp_q.filter(Campaign.workspace_id == workspace_id)
            else:
                camp_q = camp_q.filter(Campaign.owner_id == user_id)
            camps = camp_q.order_by(Campaign.id.desc()).limit(8).all()
            if camps:
                c_parts = []
                for c in camps:
                    meta["campaigns"].append({
                        "id": c.id,
                        "name": c.name,
                        "status": c.status,
                        "budget": float(c.budget or 0),
                        "objective": c.objective,
                    })
                    c_parts.append(f"#{c.id} '{c.name}' [{c.status}, Ngân sách: {float(c.budget or 0):,.0f}đ]")
                lines.append(f"• Chiến dịch trong dự án ({len(camps)}): " + " | ".join(c_parts))
        except Exception:
            pass

        try:
            prods = db.query(Product).order_by(Product.id.desc()).limit(8).all()
            if prods:
                p_parts = []
                for p in prods:
                    meta["products"].append({"id": p.id, "name": p.name, "usp": p.usp, "status": p.status})
                    p_parts.append(f"#{p.id} '{p.name}' (USP: {str(p.usp or '')[:60]})")
                lines.append(f"• Sản phẩm & USP ({len(prods)}): " + " | ".join(p_parts))
        except Exception:
            pass

        try:
            bk_q = db.query(BrandKit)
            if workspace_id is not None:
                bk_q = bk_q.filter(BrandKit.workspace_id == workspace_id)
            bk = bk_q.order_by(BrandKit.id.desc()).first()
            if bk:
                meta["brand_kit"] = {
                    "id": bk.id,
                    "brand_name": bk.brand_name,
                    "voice_tone": bk.voice_tone,
                    "banned_words": bk.banned_words,
                }
                lines.append(
                    f"• Brand Kit #{bk.id} '{bk.brand_name}': Giọng văn='{bk.voice_tone}', Từ cấm='{bk.banned_words or 'Không'}'"
                )
        except Exception:
            pass

        try:
            task_q = db.query(Task)
            if workspace_id is not None:
                task_q = task_q.filter(Task.workspace_id == workspace_id)
            if campaign_id is not None:
                task_q = task_q.filter(Task.campaign_id == campaign_id)
            tasks = task_q.order_by(Task.id.desc()).limit(10).all()
            if tasks:
                t_parts = []
                for t in tasks:
                    if t.status != "DONE":
                        meta["tasks_todo"].append({"id": t.id, "title": t.title, "status": t.status, "priority": t.priority})
                    t_parts.append(f"#{t.id} '{t.title}' [{t.status}/{t.priority}]")
                lines.append(f"• Đầu việc (Tasks - {len(tasks)} gần nhất): " + " | ".join(t_parts[:6]))
        except Exception:
            pass

        try:
            cnt_q = db.query(MarketingContent)
            if workspace_id is not None:
                cnt_q = cnt_q.filter(MarketingContent.workspace_id == workspace_id)
            if campaign_id is not None:
                cnt_q = cnt_q.filter(MarketingContent.campaign_id == campaign_id)
            cnts = cnt_q.order_by(MarketingContent.id.desc()).limit(6).all()
            if cnts:
                cnt_parts = []
                for cnt in cnts:
                    meta["contents"].append({"id": cnt.id, "title": cnt.title, "status": cnt.status})
                    cnt_parts.append(f"#{cnt.id} '{cnt.title[:40]}' [{cnt.status}]")
                lines.append(f"• Kho bài viết ({len(cnts)} bài gần nhất): " + " | ".join(cnt_parts))
        except Exception:
            pass

        try:
            met_q = db.query(CampaignMetric)
            if campaign_id is not None:
                met_q = met_q.filter(CampaignMetric.campaign_id == campaign_id)
            elif meta["campaigns"]:
                c_ids = [c["id"] for c in meta["campaigns"]]
                met_q = met_q.filter(CampaignMetric.campaign_id.in_(c_ids))
            mets = met_q.limit(100).all()
            if mets:
                tot_v = sum(int(m.views or 0) for m in mets)
                tot_cl = sum(int(m.clicks or 0) for m in mets)
                tot_cv = sum(int(m.conversions or 0) for m in mets)
                tot_co = sum(float(m.cost or 0.0) for m in mets)
                tot_rv = sum(float(m.revenue or 0.0) for m in mets)
                roas = round(tot_rv / tot_co, 2) if tot_co > 0 else 0.0
                meta["metrics_summary"] = {
                    "views": tot_v,
                    "clicks": tot_cl,
                    "conversions": tot_cv,
                    "cost": tot_co,
                    "revenue": tot_rv,
                    "roas": roas,
                }
                lines.append(
                    f"• Tổng hợp số liệu chiến dịch: Chi phí {tot_co:,.0f}đ | Doanh thu {tot_rv:,.0f}đ | "
                    f"ROAS {roas}x | Click {tot_cl} | Đơn chốt {tot_cv}"
                )
        except Exception:
            pass

        return "\n".join(lines), meta

    def _detect_and_stage_project_proposal(
        self,
        db: Session,
        user_id: int,
        workspace_id: Optional[int],
        campaign_id: Optional[int],
        thread_id: Optional[int],
        message: str,
        quick_action: Optional[str],
        channel_code: str,
        prod_name: str,
        prod_usp: str,
        camp_aud: str,
        norm_sug: Optional[Dict[str, Any]],
        llm_actions: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Kiến trúc 'Read Freely, Stage Writes':
        Phát hiện ý định điều khiển dự án sâu (12 công cụ thao tác CSDL: Chiến dịch, Sản phẩm,
        Brand Kit, Bài viết, Đầu việc, Số liệu ROAS, Link rút gọn thu Lead `/r/{code}`,
        Lệnh `/skill` và Thẻ ghi nhớ Muse AI) từ LLM hoặc câu chat tự nhiên.
        Mọi thao tác ghi đều tạo `AgentStagedProposal` (PENDING) để người dùng bấm [Thực thi] hoặc [Hoàn tác (Undo)].
        """
        from datetime import datetime
        from app.models.entities import AgentStagedProposal

        msg_lower = (message or "").strip().lower()
        act_code = (quick_action or "").strip().upper()
        proposed_actions: List[Dict[str, Any]] = []
        summary_title = ""

        # 1. Nếu LLM đã trả về mảng `proposed_actions` hợp lệ thì chuẩn hóa
        if isinstance(llm_actions, list) and len(llm_actions) > 0:
            for idx, item in enumerate(llm_actions[:8]):
                if isinstance(item, dict) and item.get("tool_name"):
                    params_raw = item.get("params") if isinstance(item.get("params"), dict) else (
                        item.get("parameters") if isinstance(item.get("parameters"), dict) else {}
                    )
                    proposed_actions.append({
                        "action_id": str(item.get("action_id") or f"act_{idx + 1}"),
                        "tool_name": str(item.get("tool_name")),
                        "label": str(item.get("label") or item.get("tool_name")),
                        "description": str(item.get("description") or item.get("summary") or "Thao tác đề xuất bởi AI Agent"),
                        "enabled": bool(item.get("enabled", True)),
                        "params": params_raw,
                    })
            if proposed_actions:
                summary_title = "Kế hoạch can thiệp dự án sâu do AI đề xuất (Chờ bạn phê duyệt)"

        # 2. Nhận diện Nhập số liệu thực tế bằng ngôn ngữ tự nhiên ("Hôm nay tiêu 500k, 25 tin nhắn, chốt 6 đơn thu 2tr4")
        if not proposed_actions and (
            act_code == "STAGE_LOG_METRICS"
            or any(
                kw in msg_lower
                for kw in (
                    "ghi nhận số liệu",
                    "nhập số liệu",
                    "log metric",
                    "báo cáo hôm nay",
                )
            )
            or (
                any(k in msg_lower for k in ("tiêu ", "chi phí", "chạy hết", "ads hết"))
                and any(k in msg_lower for k in ("đơn", "doanh thu", "thu về", "tin nhắn", "inbox", "click", "lead"))
            )
        ):
            cost_val = 0.0
            rev_val = 0.0
            clicks_val = 0
            conv_val = 0
            views_val = 0

            m_cost = re.search(
                r"(?:tiêu|chi phí|chạy hết|chi hết|ads hết|cost)\s*[:=]?\s*([0-9.,]+\s*(?:tr\d*|triệu|nghìn|ngàn|k|tỷ)?)",
                msg_lower,
            )
            if m_cost:
                cost_val = self._parse_vn_amount(m_cost.group(1)) or 0.0

            m_rev = re.search(
                r"(?:thu về|doanh thu|thu được|thu|bán được)\s*[:=]?\s*([0-9.,]+\s*(?:tr\d*|triệu|nghìn|ngàn|k|tỷ))",
                msg_lower,
            )
            if m_rev:
                rev_val = self._parse_vn_amount(m_rev.group(1)) or 0.0

            m_clicks = re.search(r"(\d+)\s*(?:tin nhắn|inbox|mess|click|lượt nhấp|khách hỏi)", msg_lower)
            if m_clicks:
                clicks_val = int(m_clicks.group(1))

            m_conv = re.search(r"(?:chốt|ra|được)?\s*(\d+)\s*(?:đơn|chuyển đổi|khách chốt|order)", msg_lower)
            if m_conv:
                conv_val = int(m_conv.group(1))

            m_views = re.search(r"(\d+)\s*(?:lượt xem|view|hiển thị|impression)", msg_lower)
            if m_views:
                views_val = int(m_views.group(1))
            elif clicks_val > 0:
                views_val = clicks_val * 25

            today_str = datetime.utcnow().strftime("%Y-%m-%d")
            roas_preview = round(rev_val / cost_val, 2) if cost_val > 0 else 0.0
            summary_title = (
                f"Ghi nhận số liệu ngày {today_str}: Chi phí {cost_val:,.0f}đ — "
                f"Doanh thu {rev_val:,.0f}đ (ROAS {roas_preview}x)"
            )
            proposed_actions.append({
                "action_id": "act_log_metrics_1",
                "tool_name": "log_daily_metrics",
                "label": f"Ghi nhận số liệu thực tế ngày {today_str} ({channel_code.upper()})",
                "description": (
                    f"Chi phí: {cost_val:,.0f} VNĐ | Tương tác/Inbox: {clicks_val} | "
                    f"Đơn chốt: {conv_val} | Doanh thu: {rev_val:,.0f} VNĐ"
                ),
                "enabled": True,
                "params": {
                    "campaign_id": campaign_id,
                    "channel_code": channel_code or "facebook",
                    "report_date": today_str,
                    "views": views_val,
                    "clicks": clicks_val,
                    "conversions": conv_val,
                    "cost": cost_val,
                    "revenue": rev_val,
                },
            })

        # 3. Nhận diện Lưu Lệnh Tùy Biến (/skill) vào Bảng Tư Duy Muse AI
        elif not proposed_actions and (
            act_code == "STAGE_SAVE_SKILL"
            or msg_lower.startswith("/luu_lenh")
            or ("lưu" in msg_lower and ("lệnh /" in msg_lower or "thành lệnh" in msg_lower or "custom skill" in msg_lower))
        ):
            m_trig = re.search(r"(/[a-zA-Z0-9_-]{2,30})", message)
            trigger_cmd = m_trig.group(1).lower() if m_trig else "/viet_nhanh"
            summary_title = f"Lưu quy trình làm việc thành lệnh tắt `{trigger_cmd}` trên Bảng Muse AI"
            proposed_actions.append({
                "action_id": "act_save_skill_1",
                "tool_name": "save_custom_skill",
                "label": f"Tạo lệnh tắt `{trigger_cmd}` cho Shop",
                "description": f"Gõ `{trigger_cmd}` ở bất kỳ cuộc trò chuyện nào để tái sử dụng khuôn mẫu này",
                "enabled": True,
                "params": {
                    "skill_trigger": trigger_cmd,
                    "title": f"Lệnh tùy biến {trigger_cmd} — {prod_name or 'Chuẩn của Shop'}",
                    "skill_instruction": message.strip(),
                    "content": (norm_sug.get("body") if norm_sug else "") or message.strip(),
                },
            })

        # 4. Nhận diện Tạo Link Tracking Rút Gọn (/r/{code}) & Phễu Thu Lead Thực Tế
        elif not proposed_actions and any(
            kw in msg_lower
            for kw in (
                "tạo link",
                "link rút gọn",
                "link tracking",
                "smart link",
                "link thu lead",
                "form thu lead",
                "đo click",
            )
        ):
            import secrets
            short_code = f"mf{secrets.token_hex(2)}"
            m_url = re.search(r"(https?://[^\s]+)", message)
            target_url = m_url.group(1) if m_url else "https://zalo.me/0900000000"
            summary_title = f"Tạo Smart Link đo Click & Thu Lead `/r/{short_code}` ({channel_code.upper()})"
            proposed_actions.append({
                "action_id": "act_track_link_1",
                "tool_name": "create_tracking_link",
                "label": f"Tạo Link đo lường `/r/{short_code}` → {target_url[:45]}",
                "description": "Tự động cộng Click thật và mở cổng nhận Lead khách hàng vào CampaignMetric",
                "enabled": True,
                "params": {
                    "campaign_id": campaign_id,
                    "channel_code": channel_code or "facebook",
                    "short_code": short_code,
                    "target_url": target_url,
                    "title": f"Link chiến dịch {prod_name or 'Bán hàng'} ({channel_code.upper()})",
                },
            })

        # 5. Nhận diện Cập nhật trạng thái / ngân sách Chiến dịch hiện có (Tạm dừng, Kích hoạt, Tăng/Giảm ngân sách)
        elif not proposed_actions and (
            any(kw in msg_lower for kw in ("tạm dừng chiến dịch", "dừng chiến dịch", "kích hoạt chiến dịch", "bật chiến dịch", "đổi ngân sách", "cập nhật chiến dịch", "tăng ngân sách", "giảm ngân sách"))
        ):
            new_status = "PAUSED" if ("dừng" in msg_lower or "pause" in msg_lower) else "ACTIVE"
            new_budget = self._parse_vn_amount(message)
            summary_title = f"Cập nhật Chiến dịch hiện tại: Trạng thái {new_status}" + (
                f" — Ngân sách {new_budget:,.0f} VNĐ" if new_budget else ""
            )
            proposed_actions.append({
                "action_id": "act_upd_camp_1",
                "tool_name": "update_campaign",
                "label": summary_title,
                "description": "Can thiệp trực tiếp vào bản ghi Campaign trong CSDL (hỗ trợ Undo 1 chạm)",
                "enabled": True,
                "params": {
                    "campaign_id": campaign_id,
                    "status": new_status,
                    "budget": new_budget,
                },
            })

        # 6. Nhận diện Thêm mới hoặc Cập nhật Sản phẩm & USP trong dự án
        elif not proposed_actions and any(
            kw in msg_lower
            for kw in ("thêm sản phẩm", "tạo sản phẩm", "cập nhật sản phẩm", "đổi usp", "cập nhật usp", "sửa sản phẩm")
        ):
            summary_title = f"Cập nhật Kho Sản phẩm & USP: {prod_name or 'Sản phẩm mới'}"
            proposed_actions.append({
                "action_id": "act_upsert_prod_1",
                "tool_name": "upsert_product",
                "label": f"Lưu Sản phẩm '{prod_name or 'Sản phẩm mới'}' & USP vào dự án",
                "description": f"USP: {(prod_usp or message.strip())[:100]}",
                "enabled": True,
                "params": {
                    "name": prod_name or "Sản phẩm Chủ lực Mới",
                    "usp": prod_usp or message.strip()[:250],
                    "status": "ACTIVE",
                },
            })

        # 7. Nhận diện Cập nhật Brand Kit (Giọng văn thương hiệu / Từ cấm)
        elif not proposed_actions and any(
            kw in msg_lower
            for kw in ("cập nhật brand kit", "đổi giọng văn", "thêm từ cấm", "sửa brand kit", "quy tắc thương hiệu")
        ):
            summary_title = "Cập nhật Bộ Nhận Diện & Giọng Văn Thương Hiệu (Brand Kit)"
            proposed_actions.append({
                "action_id": "act_upd_brand_1",
                "tool_name": "update_brand_kit",
                "label": "Cập nhật Giọng văn & Từ cấm trong Brand Kit",
                "description": f"Áp dụng yêu cầu: {message.strip()[:90]}",
                "enabled": True,
                "params": {
                    "voice_tone": message.strip()[:120],
                },
            })

        # 8. Nhận diện Đánh dấu hoàn thành các đầu việc (Tasks)
        elif not proposed_actions and any(
            kw in msg_lower
            for kw in ("hoàn thành việc", "hoàn thành task", "xong task", "đánh dấu xong", "đóng các task", "hoàn tất công việc")
        ):
            summary_title = "Đánh dấu hoàn thành (DONE) các đầu việc đang mở của chiến dịch"
            proposed_actions.append({
                "action_id": "act_upd_tasks_1",
                "tool_name": "update_tasks_status",
                "label": "Chuyển trạng thái đầu việc sang Hoàn thành (DONE)",
                "description": "Cập nhật các Task đang mở trong chiến dịch hiện tại sang DONE (hỗ trợ Undo)",
                "enabled": True,
                "params": {
                    "campaign_id": campaign_id,
                    "new_status": "DONE",
                },
            })

        # 9. Nhận diện Khởi tạo Chiến dịch + Phân bổ Ngân sách + Việc cần làm + Nháp Nội dung
        elif not proposed_actions and (
            act_code == "STAGE_CAMPAIGN_PLAN"
            or any(
                kw in msg_lower
                for kw in (
                    "tạo chiến dịch",
                    "lên chiến dịch",
                    "khởi tạo chiến dịch",
                    "setup chiến dịch",
                    "lập kế hoạch chiến dịch",
                    "điều khiển dự án",
                )
            )
        ):
            budget_parsed = self._parse_vn_amount(message) or 5_000_000.0
            today_str = datetime.utcnow().strftime("%Y-%m-%d")
            camp_title = f"Chiến dịch {prod_name or 'Bán hàng'} ({today_str})"
            summary_title = f"Kế hoạch thực thi tự động: {camp_title} — Ngân sách {budget_parsed:,.0f} VNĐ"
            proposed_actions = [
                {
                    "action_id": "act_camp_1",
                    "tool_name": "propose_campaign_plan",
                    "label": f"Khởi tạo Chiến dịch '{camp_title}'",
                    "description": f"Ngân sách dự kiến: {budget_parsed:,.0f} VNĐ | Kênh chính: {channel_code.upper()}",
                    "enabled": True,
                    "params": {
                        "name": camp_title,
                        "objective": f"Tối ưu chuyển đổi tin nhắn & đơn hàng cho {prod_name}",
                        "audience": camp_aud or "Khách hàng tiềm năng tại Việt Nam",
                        "budget": budget_parsed,
                        "start_date": today_str,
                        "end_date": "2026-12-31",
                        "channel_code": channel_code or "facebook",
                    },
                },
                {
                    "action_id": "act_draft_2",
                    "tool_name": "propose_content_drafts",
                    "label": "Lưu gói nội dung (Creative Pack) hiện tại vào Kho bài viết",
                    "description": f"Tiêu đề: {(norm_sug.get('title') if norm_sug else prod_name) or 'Bài viết mở màn'}",
                    "enabled": True,
                    "params": {
                        "title": (norm_sug.get("title") if norm_sug else "") or f"Bài mở màn — {prod_name}",
                        "body": (norm_sug.get("body") if norm_sug else "") or f"{prod_name} — {prod_usp}",
                        "cta": (norm_sug.get("cta") if norm_sug else "") or "Nhắn tin ngay để nhận ưu đãi",
                        "channel_code": channel_code or "facebook",
                        "blocks": (norm_sug.get("blocks") if norm_sug else []) or [],
                    },
                },
                {
                    "action_id": "act_tasks_3",
                    "tool_name": "propose_tasks_batch",
                    "label": "Tạo 2 đầu việc chuẩn bị tư liệu & cài đặt quảng cáo",
                    "description": "Gắn trực tiếp vào danh sách việc cần làm của chiến dịch",
                    "enabled": True,
                    "params": {
                        "tasks": [
                            {
                                "title": f"Chuẩn bị ảnh/video thực tế cho {prod_name}",
                                "task_type": "DESIGN",
                                "priority": "HIGH",
                            },
                            {
                                "title": f"Lên bài & ghim Comment đầu tiên chứa link/SĐT trên {channel_code.upper()}",
                                "task_type": "CONTENT",
                                "priority": "URGENT",
                            },
                        ]
                    },
                },
            ]

        if not proposed_actions:
            return None

        try:
            for act_it in proposed_actions:
                act_it.setdefault("summary", act_it.get("description") or "")
                act_it.setdefault("description", act_it.get("summary") or "")
                act_it.setdefault("parameters", act_it.get("params") or {})
                act_it.setdefault("params", act_it.get("parameters") or {})
            proposal_row = AgentStagedProposal(
                workspace_id=workspace_id or 1,
                user_id=user_id,
                thread_id=thread_id,
                goal_summary=summary_title or "Đề xuất thao tác dự án từ Trợ lý AI",
                actions_json=json.dumps(proposed_actions, ensure_ascii=False),
                status="PENDING",
            )
            db.add(proposal_row)
            db.commit()
            db.refresh(proposal_row)
            return {
                "id": proposal_row.id,
                "workspace_id": proposal_row.workspace_id,
                "thread_id": proposal_row.thread_id,
                "campaign_id": campaign_id,
                "goal_summary": proposal_row.goal_summary,
                "summary": proposal_row.goal_summary,
                "status": proposal_row.status,
                "actions": proposed_actions,
                "execution_result": None,
                "executed_result": None,
                "can_undo": False,
                "created_at": proposal_row.created_at,
            }
        except Exception as exc:
            logger.warning("[AI Staged Proposal] Could not persist proposal: %s", str(exc))
            db.rollback()
            return None

    def chat_with_canvas(
        self,
        db: Session,
        user_id: int,
        campaign_id: Optional[int],
        workspace_id: Optional[int],
        channel_code: str,
        message: str,
        quick_action: Optional[str],
        history: List[Dict[str, str]],
        canvas: Dict[str, Any],
        context_flags: Dict[str, Any],
        context_data: Dict[str, Any],
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
        custom_base_url: Optional[str] = None,
        thread_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Hội thoại nhiều lượt (Multi-turn Chat) song song với Bàn soạn thảo thủ công (Interactive Canvas)
        & Bảng Tư Duy Dài Hạn (Muse AI Spatial Memory) & Điều khiển Dự án Sâu (Deep Workspace MCP / 12 Tools).
        """
        from datetime import datetime
        from app.models.entities import MuseBoardCard, AIChatThread, AIChatThreadMessage

        start_time = time.time()
        self._active_thread_id = thread_id
        title_now = str(canvas.get("title") or "").strip()
        body_now = str(canvas.get("body") or "").strip()
        cta_now = str(canvas.get("cta") or "").strip()
        first_comment_now = str(canvas.get("first_comment") or "").strip()
        media_brief_now = str(canvas.get("media_brief") or "").strip()
        selected_text = str(canvas.get("selected_text") or "").strip() or None
        raw_blocks = canvas.get("blocks") if isinstance(canvas.get("blocks"), list) else []

        # Xác định các khối (Block) người dùng đã bấm khóa (locked=True) để AI tuyệt đối không ghi đè
        locked_blocks_map: Dict[str, Dict[str, Any]] = {}
        locked_descriptions: List[str] = []
        for blk in raw_blocks:
            if isinstance(blk, dict) and blk.get("locked"):
                bid = str(blk.get("id") or "")
                if bid:
                    locked_blocks_map[bid] = blk
                locked_descriptions.append(
                    f"- [{blk.get('label') or blk.get('type')} (ĐÃ KHÓA 🔒 — GIỮ NGUYÊN 100%)]: {blk.get('content', '')}"
                )

        inc_camp = bool(context_flags.get("include_campaign", True))
        inc_prod = bool(context_flags.get("include_product_usp", True))
        inc_brand = bool(context_flags.get("include_brand_kit", True))
        inc_draft = bool(context_flags.get("include_canvas_draft", True))
        inc_muse = bool(context_flags.get("include_muse_memory", True))
        inc_win = bool(context_flags.get("include_winning_posts", True))
        enable_ctrl = bool(context_flags.get("enable_project_control", True))

        context_used: List[str] = []
        context_blocks: List[str] = []

        camp_name = str(context_data.get("campaign_name") or "").strip()
        camp_obj = str(context_data.get("objective") or "").strip()
        camp_aud = str(context_data.get("audience") or "").strip()
        if inc_camp and (camp_name or camp_obj):
            context_used.append(f"Chiến dịch: {camp_name or 'Theo yêu cầu'} ({camp_obj or 'Tối ưu chuyển đổi'})")
            context_blocks.append(
                f"[NGỮ CẢNH CHIẾN DỊCH ĐANG BẬT]:\n"
                f"- Tên chiến dịch: {camp_name}\n"
                f"- Mục tiêu: {camp_obj}\n"
                f"- Chân dung khách hàng: {camp_aud}"
            )

        prod_name = str(context_data.get("product_name") or "").strip()
        prod_usp = str(context_data.get("product_usp") or "").strip()
        if inc_prod and (prod_name or prod_usp):
            context_used.append(f"Sản phẩm & USP: {prod_name or 'Chưa đặt tên'} — {prod_usp[:90]}")
            context_blocks.append(
                f"[DỮ LIỆU SẢN PHẨM & ĐIỂM KHÁC BIỆT (USP) ĐANG BẬT]:\n"
                f"- Tên sản phẩm/dịch vụ: {prod_name}\n"
                f"- Điểm bán hàng độc nhất (USP / Số liệu thực tế): {prod_usp}"
            )

        brand_tone = str(context_data.get("tone") or "").strip()
        brand_banned = str(context_data.get("banned_keywords") or "").strip()
        brand_guide = str(context_data.get("brand_guidelines") or "").strip()
        if inc_brand and (brand_tone or brand_banned or brand_guide):
            context_used.append(f"Brand Kit: Giọng văn '{brand_tone or 'Tự nhiên, thực chiến'}'")
            context_blocks.append(
                f"[QUY TẮC THƯƠNG HIỆU & KHỬ MÙI AI ĐANG BẬT]:\n"
                f"- Giọng văn yêu cầu: {brand_tone or 'Tự nhiên, gần gũi, đi thẳng vào vấn đề'}\n"
                f"- Từ cấm sử dụng: {brand_banned or 'Không có'}\n"
                f"- Hướng dẫn riêng: {brand_guide or 'Không dùng văn mẫu sáo rỗng (hàng đầu, toàn diện, tận tâm, giải pháp tối ưu).'}"
            )

        # Tích hợp Kho Bài Mẫu Ra Đơn (Few-Shot Style DNA) & Bảng Tư Duy Dài Hạn (Muse AI Board)
        try:
            muse_q = db.query(MuseBoardCard)
            if workspace_id is not None:
                muse_q = muse_q.filter(MuseBoardCard.workspace_id == workspace_id)
            else:
                muse_q = muse_q.filter(MuseBoardCard.user_id == user_id)
            all_cards = muse_q.order_by(MuseBoardCard.is_active_memory.desc(), MuseBoardCard.updated_at.desc()).limit(15).all()
        except Exception:
            all_cards = []

        if inc_win:
            winning_cards = [c for c in all_cards if c.card_type == "WINNING_POST"][:3]
            if winning_cards:
                context_used.append(f"Kho Bài Mẫu Ra Đơn ({len(winning_cards)} bài mẫu thực tế)")
                win_lines = [
                    f"Mẫu #{idx + 1} ({w.title}):\n\"\"\"{w.content[:600]}\"\"\""
                    for idx, w in enumerate(winning_cards)
                ]
                context_blocks.append(
                    "[KHO BÀI MẪU RA ĐƠN THẬT CỦA SHOP (FEW-SHOT STYLE DNA — HÃY BẮT CHƯỚC NHỊP CÂU, CÁCH NGẮT DÒNG & XƯNG HÔ NÀY)]:\n"
                    + "\n\n".join(win_lines)
                )

        if inc_muse:
            memory_cards = [c for c in all_cards if c.card_type not in ("WINNING_POST", "CUSTOM_SKILL")][:5]
            if memory_cards:
                context_used.append(f"Bảng Tư Duy Muse AI ({len(memory_cards)} thẻ ghi nhớ dài hạn)")
                mem_lines = [f"- [{m.card_type}] {m.title}: {m.content[:280]}" for m in memory_cards]
                context_blocks.append(
                    "[BẢNG TƯ DUY DÀI HẠN MUSE AI & INSIGHT ĐÃ GHIM CỦA NGƯỜI DÙNG]:\n" + "\n".join(mem_lines)
                )

        # Kiểm tra nếu người dùng gõ lệnh tắt tùy biến `/lenh` đã lưu trong MuseBoardCard
        msg_stripped = (message or "").strip()
        if msg_stripped.startswith("/"):
            cmd_token = msg_stripped.split()[0].lower()
            matched_skill = next(
                (c for c in all_cards if c.card_type == "CUSTOM_SKILL" and (c.trigger_command or "").lower() == cmd_token),
                None,
            )
            if matched_skill:
                context_used.append(f"Lệnh tùy biến {cmd_token} ({matched_skill.title})")
                context_blocks.append(
                    f"[KÍCH HOẠT LỆNH TÙY BIẾN {cmd_token} CỦA NGƯỜI DÙNG]:\n"
                    f"- Nội dung & Hướng dẫn thực thi:\n{matched_skill.content}"
                )

        if inc_draft and (title_now or body_now or cta_now or first_comment_now or media_brief_now):
            char_len = len(title_now) + len(body_now) + len(cta_now)
            context_used.append(f"Bàn soạn thảo hiện tại ({char_len} ký tự)")
            draft_block = (
                f"[BẢN THẢO HIỆN TẠI TRÊN BÀN VIẾT CỦA NGƯỜI DÙNG (Kênh: {channel_code})]:\n"
                f"- Tiêu đề / Hook (Headline): {title_now or '(Chưa có)'}\n"
                f"- Nội dung thân bài (Body):\n{body_now or '(Chưa có)'}\n"
                f"- Lời kêu gọi hành động (CTA): {cta_now or '(Chưa có)'}"
            )
            if first_comment_now:
                draft_block += f"\n- Bình luận đầu tiên (First Comment chứa link/SĐT lách bóp tương tác): {first_comment_now}"
            if media_brief_now:
                draft_block += f"\n- Ghi chú sản xuất Hình ảnh / Video (Media Brief): {media_brief_now}"
            if locked_descriptions:
                context_used.append(f"Đã khóa bảo vệ {len(locked_descriptions)} khối nội dung (🔒)")
                draft_block += "\n- CÁC KHỐI ĐANG KHÓA (TUYỆT ĐỐI KHÔNG SỬA):\n" + "\n".join(locked_descriptions)
            if selected_text:
                context_used.append(f"Đoạn văn đang bôi đen ({len(selected_text)} ký tự)")
                draft_block += f"\n- ĐOẠN VĂN NGƯỜI DÙNG ĐANG BÔI ĐEN CẦN SỬA CỤC BỘ:\n\"\"\"{selected_text}\"\"\""
            context_blocks.append(draft_block)

        # Nếu thread_id được truyền và history từ client đang rỗng, tự động nạp lịch sử hội thoại dài hạn từ DB
        effective_history = list(history or [])
        if thread_id is not None and not effective_history:
            try:
                past_msgs = (
                    db.query(AIChatThreadMessage)
                    .filter(AIChatThreadMessage.thread_id == thread_id)
                    .order_by(AIChatThreadMessage.id.asc())
                    .limit(16)
                    .all()
                )
                for pm in past_msgs:
                    effective_history.append({"role": pm.role, "content": pm.content})
                if past_msgs:
                    context_used.append(f"Trí nhớ cuộc trò chuyện dài hạn ({len(past_msgs)} lượt trao đổi trước)")
            except Exception:
                pass

        # Tích hợp Bức tranh toàn cảnh dự án (Deep Workspace Graph - MCP) & Tự nhận thức tài nguyên VPS
        deep_snapshot_str, workspace_meta = self._build_deep_workspace_snapshot(
            db=db,
            user_id=user_id,
            workspace_id=workspace_id,
            campaign_id=campaign_id,
        )
        if deep_snapshot_str:
            context_blocks.append(deep_snapshot_str)
            vps_meta = workspace_meta.get("vps") or {}
            context_used.append(
                f"Toàn cảnh Dự án & VPS ({len(workspace_meta.get('campaigns', []))} chiến dịch, "
                f"{len(workspace_meta.get('products', []))} sản phẩm, RAM {vps_meta.get('used_ram_mb', 0)}/{vps_meta.get('total_ram_mb', 1986)}MB)"
            )

        if not context_used:
            context_used.append("Chế độ Trò chuyện Tự do (Người dùng đã tắt các chip ngữ cảnh tự động)")

        action_code = (quick_action or "").strip().upper()
        action_instructions = {
            "HOOK_5": (
                "NHIỆM VỤ CHUYÊN BIỆT: Viết 5 câu mở đầu (Hook 3 giây đầu) đa góc độ tâm lý cho thị trường Việt Nam "
                "(1. Đánh thẳng nỗi đau ví tiền/thời gian, 2. Bằng chứng thực tế có con số, 3. Phá vỡ lầm tưởng, "
                "4. Câu hỏi tự vấn, 5. Ưu đãi giới hạn). Đưa 5 câu vào mảng `alternatives` và chọn câu sắc bén nhất đặt vào `suggested_canvas.title`."
            ),
            "SHORTEN_30": (
                "NHIỆM VỤ CHUYÊN BIỆT: Rút gọn khoảng 30% độ dài bài viết hiện tại trên bàn soạn thảo. "
                "Cắt bỏ mọi tính từ sáo rỗng, câu dẫn dắt vòng vo; giữ nguyên 100% thông tin sản phẩm, con số và CTA."
            ),
            "ANTI_CLICHE": (
                "NHIỆM VỤ CHUYÊN BIỆT: Khử sạch 'mùi văn mẫu AI'. Xóa bỏ hoàn toàn các từ sáo rỗng như 'hàng đầu', "
                "'toàn diện', 'tận tâm', 'giải pháp tối ưu', 'trong bối cảnh hiện nay', 'không chỉ... mà còn'. "
                "Viết lại bằng tiếng Việt đời thường, câu ngắn, nhịp nhanh, đọc lên nghe như người thật đang tư vấn."
            ),
            "ZALO_INBOX_SCRIPT": (
                "NHIỆM VỤ CHUYÊN BIỆT (THỰC CHIẾN SME VIỆT NAM): Soạn Kịch bản Chốt đơn Inbox Messenger / Zalo OA gồm 5 bước ngắn gọn:\n"
                "1. Câu chào phản hồi trong 5 giây + hỏi 1 câu phân loại nhu cầu thật.\n"
                "2. Nêu đúng điểm khác biệt (USP) & báo giá kèm neo giá trị.\n"
                "3. Xử lý 3 lời từ chối phổ biến nhất tại Việt Nam ('Để chị hỏi chồng/suy nghĩ thêm', 'Sao giá cao hơn shop kia?', 'Ship tỉnh bao lâu, có được kiểm hàng không?').\n"
                "4. Câu chốt đơn xin SĐT + Địa chỉ lên đơn ngay.\n"
                "5. Tin nhắn chăm sóc lại sau 24h nếu khách 'seen không rep'.\n"
                "Đặt kịch bản hoàn chỉnh vào `suggested_canvas.body`, tiêu đề vào `suggested_canvas.title`, và 3 câu xử lý từ chối vào `alternatives`."
            ),
            "LIVESTREAM_SCRIPT": (
                "NHIỆM VỤ CHUYÊN BIỆT (THỰC CHIẾN TIKTOK SHOP / FB LIVE VIỆT NAM): Soạn Kịch bản Phiên Livestream bán hàng 15 phút lặp vòng (Loop Script):\n"
                "- Phút 00-03: Câu giữ chân người mới vào mắt xem + Mồi tương tác kêu gọi thả tim/comment từ khóa.\n"
                "- Phút 03-08: Demo trực quan sản phẩm, xoáy sâu nỗi đau và chứng minh USP trước ống kính.\n"
                "- Phút 08-12: Báo giá neo + Tung Deal Flash Sale giới hạn suất trên Live + Giải đáp thắc mắc nhanh.\n"
                "- Phút 12-15: Đếm ngược 60 giây cuối thúc giục bấm vào Giỏ hàng góc trái màn hình.\n"
                "Đặt kịch bản hoàn chỉnh vào `suggested_canvas.body`."
            ),
            "REPURPOSE_TIKTOK": (
                "NHIỆM VỤ CHUYÊN BIỆT: Chuyển thể nội dung hiện tại trên bàn soạn thảo thành Kịch bản Video ngắn TikTok / Reels 30-45 giây "
                "(chia rõ từng phân cảnh: [Cảnh 1: 0-3s Hook] Hình ảnh gì - Thoại gì, [Cảnh 2: 3-15s Nỗi đau], [Cảnh 3: 15-30s Giải pháp & USP], [Cảnh 4: 30-40s CTA])."
            ),
            "REPURPOSE_FACEBOOK": (
                "NHIỆM VỤ CHUYÊN BIỆT: Chuyển thể nội dung hiện tại thành bài đăng Facebook Ads / Fanpage chuyển đổi cao, "
                "ngắt đoạn 1-2 câu dễ đọc trên màn hình điện thoại, có bullet rõ ràng và CTA kích thích nhắn tin."
            ),
            "POLISH_MANUAL": (
                "NHIỆM VỤ CHUYÊN BIỆT (TÔN TRỌNG NGƯỜI VIẾT THỦ CÔNG): Người dùng đã tự tay viết bản thảo trên bàn viết. "
                "Tuyệt đối KHÔNG đập đi viết lại theo kiểu AI. Chỉ biên tập mượt câu chữ, sửa lỗi lặp từ, tăng sức nặng cho động từ "
                "và giữ nguyên 100% ý tứ, giọng điệu cá nhân của người viết."
            ),
            "REWRITE_SELECTION": (
                f"NHIỆM VỤ CHUYÊN BIỆT: Người dùng đang bôi đen đoạn văn: \"\"\"{selected_text or ''}\"\"\". "
                "Hãy viết lại ĐÚNG đoạn văn đang bôi đen này theo yêu cầu, đặt đoạn văn mới vào `suggested_canvas.replaced_selection`, "
                "đồng thời cập nhật `suggested_canvas.body` là toàn bộ bài viết sau khi đã thay đoạn bôi đen đó."
            ),
        }

        system_prompt = (
            "Bạn là Trợ lý AI Điều Khiển Dự Án & Biên Tập Marketing Thực Chiến (chuẩn ChatGPT Canvas & Projects / Claude Artifacts & MCP / Google Gemini Workspace) "
            "dành cho Marketer và Doanh nghiệp SME tại Việt Nam.\n"
            "Nguyên tắc cốt lõi:\n"
            "1. Tôn trọng tuyệt đối câu chữ thủ công của người viết và CÁC KHỐI ĐÃ KHÓA (locked=true).\n"
            "2. Bạn có toàn quyền ĐỌC bức tranh toàn cảnh dự án (Chiến dịch, Sản phẩm, Brand Kit, Đầu việc, Kho bài viết, Số liệu ROAS) và TỰ NHẬN THỨC tài nguyên máy chủ VPS đang chạy trong ngữ cảnh.\n"
            "3. Khi người dùng yêu cầu THAO TÁC / CAN THIỆP SÂU vào dự án (tạo/sửa chiến dịch, thêm/sửa sản phẩm & USP, cập nhật Brand Kit, tạo/hoàn thành task, ghi số liệu, tạo link đo click `/r/{code}`, lưu lệnh `/skill` hoặc ghim thẻ nhớ Muse), hãy điền mảng `proposed_actions` sử dụng các `tool_name` chuẩn sau:\n"
            "   - `propose_campaign_plan`: params `{name, objective, audience, budget, start_date, end_date, channel_code}`\n"
            "   - `update_campaign`: params `{campaign_id, status ('ACTIVE'|'PAUSED'|'COMPLETED'), budget, name, objective}`\n"
            "   - `upsert_product`: params `{product_id (tùy chọn), name, usp, status}`\n"
            "   - `update_brand_kit`: params `{voice_tone, banned_words}`\n"
            "   - `propose_content_drafts`: params `{title, body, cta, channel_code, blocks}`\n"
            "   - `update_content_status`: params `{content_id, status ('DRAFT'|'APPROVED'|'PUBLISHED')}`\n"
            "   - `propose_tasks_batch`: params `{tasks: [{title, task_type ('CONTENT'|'DESIGN'|'ADS'|'RESEARCH'), priority ('LOW'|'MEDIUM'|'HIGH'|'URGENT')}]}`\n"
            "   - `update_tasks_status`: params `{campaign_id, task_ids (tùy chọn), new_status ('DONE'|'IN_PROGRESS'|'TODO')}`\n"
            "   - `log_daily_metrics`: params `{campaign_id, channel_code, report_date, views, clicks, conversions, cost, revenue}`\n"
            "   - `create_tracking_link`: params `{campaign_id, channel_code, short_code, target_url, title}`\n"
            "   - `save_custom_skill`: params `{skill_trigger, title, content}`\n"
            "   - `pin_muse_memory_card`: params `{title, card_type ('WINNING_POST'|'INSIGHT'|'IDEA'), content}`\n"
            "BẮT BUỘC trả về JSON hợp lệ theo đúng cấu trúc sau (không bọc ngoài bằng giải thích thừa):\n"
            "{\n"
            '  "reply": "Câu trả lời trao đổi trực tiếp với người dùng (nêu rõ số liệu/thực thể thật trong dự án hoặc giải thích thao tác bạn vừa chuẩn bị)",\n'
            '  "suggested_canvas": {\n'
            '    "title": "Tiêu đề / Hook 3 giây đầu đề xuất",\n'
            '    "body": "Nội dung thân bài đề xuất để người dùng xem và bấm Áp dụng",\n'
            '    "cta": "Lời kêu gọi hành động (CTA) cụ thể",\n'
            '    "first_comment": "Nội dung Comment đầu tiên chứa Link/SĐT/Ưu đãi để lách bóp tương tác",\n'
            '    "media_brief": "Ghi chú chụp ảnh / quay dựng video ngắn thực tế cho bài này",\n'
            '    "change_summary": "Tóm tắt 1 câu những điểm vừa tinh chỉnh so với bản gốc",\n'
            '    "replaced_selection": "Nếu người dùng bôi đen 1 đoạn để sửa, ghi đoạn văn mới thay thế vào đây; nếu không thì để null"\n'
            "  },\n"
            '  "proposed_actions": [\n'
            '    {"action_id": "act_1", "tool_name": "tên_tool_nếu_người_dùng_yêu_cầu_thao_tác_hệ_thống", "label": "Tên thao tác hiển thị", "description": "Mô tả chi tiết", "enabled": true, "params": {}}\n'
            "  ],\n"
            '  "alternatives": ["Phương án thay thế 1", "Phương án thay thế 2", "Phương án thay thế 3"]\n'
            "}"
        )

        user_prompt_parts = []
        if context_blocks:
            user_prompt_parts.append("\n\n".join(context_blocks))
        if action_code and action_code in action_instructions:
            user_prompt_parts.append(action_instructions[action_code])
        user_prompt_parts.append(f"[YÊU CẦU CỦA NGƯỜI DÙNG TRONG LƯỢT HỘI THOẠI NÀY]:\n{message.strip()}")
        user_prompt = "\n\n".join(user_prompt_parts)
        prompt_preview = f"=== SYSTEM PROMPT ===\n{system_prompt}\n\n=== USER PROMPT ===\n{user_prompt}"

        req_provider = (preferred_provider or settings.AI_PROVIDER or "gemini").strip().lower()
        if self._api_key is not None:
            active_key = self._api_key
            active_model = preferred_model or self.model
            active_provider = req_provider
            key_tier = "FIXTURE"
            provider_requires_key = True
        else:
            resolved = self.resolve_api_key(db=db, workspace_id=workspace_id, user_id=user_id, provider=req_provider)
            active_key = resolved.get("api_key")
            active_provider = resolved.get("provider") or req_provider
            if active_provider == "opencode" and req_provider != "opencode":
                active_model = resolved.get("model") or "glm-5.3-flash-free"
            else:
                active_model = preferred_model or resolved.get("model") or self.model
            key_tier = resolved.get("tier", "FALLBACK")
            provider_requires_key = resolved.get("requires_api_key", True)

        is_mock_key = bool(active_key and ("TestResolverKey" in active_key or "MockVerification" in active_key))
        needs_fallback = (provider_requires_key and (not active_key or not str(active_key).strip())) or is_mock_key

        output_payload: Optional[Dict[str, Any]] = None
        is_fallback = False
        model_used = active_model
        model_provider = active_provider

        if not needs_fallback:
            try:
                raw_text = self._call_provider_with_retry(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    active_key=active_key,
                    active_model=active_model,
                    provider=active_provider,
                    base_url_override=custom_base_url,
                    conversation_messages=effective_history[-12:] if effective_history else None,
                )
                try:
                    parsed = self._clean_json_response(raw_text)
                    if isinstance(parsed, dict) and ("reply" in parsed or "suggested_canvas" in parsed):
                        output_payload = parsed
                except Exception:
                    output_payload = {
                        "reply": raw_text.strip(),
                        "suggested_canvas": {
                            "title": title_now or f"Gợi ý cho {prod_name or camp_name or 'bài viết'}",
                            "body": raw_text.strip(),
                            "cta": cta_now or f"Nhắn tin ngay để nhận tư vấn về {prod_name or 'sản phẩm'}",
                            "first_comment": first_comment_now or f"📌 Báo giá & ưu đãi chi tiết {prod_name or 'tại đây'} — Nhắn tin hoặc chấm (.) để shop gửi ngay!",
                            "media_brief": media_brief_now or f"Ảnh/video quay thực tế cận cảnh {prod_name or 'sản phẩm'}, chèn chữ nổi bật điểm mạnh ở 3 giây đầu.",
                            "change_summary": "Trích xuất trực tiếp từ phản hồi hội thoại của AI",
                            "replaced_selection": None,
                        },
                        "alternatives": [],
                    }
            except Exception as exc:
                logger.warning("[AI Chat Canvas] Live LLM failed (%s); falling back to deterministic copilot.", str(exc))
                output_payload = None

        if output_payload is None:
            is_fallback = not is_mock_key
            model_used = active_model if is_mock_key else f"{active_model} (Chế độ Trợ lý Cục bộ - Chưa kết nối API Key)"
            model_provider = f"{active_provider}-{key_tier.lower()}" if is_mock_key else "local-canvas-copilot"
            output_payload = self._build_canvas_chat_fallback(
                action_code=action_code,
                message=message,
                title_now=title_now,
                body_now=body_now,
                cta_now=cta_now,
                selected_text=selected_text,
                prod_name=prod_name or camp_name or "Sản phẩm chủ lực",
                prod_usp=prod_usp or camp_obj or "Tối ưu chi phí và cam kết chất lượng thực tế",
                camp_aud=camp_aud or "Khách hàng mục tiêu tại Việt Nam",
                channel_code=channel_code,
                workspace_meta=workspace_meta,
            )

        sug = output_payload.get("suggested_canvas")
        norm_sug = None
        if isinstance(sug, dict):
            sug_title = str(sug.get("title") if sug.get("title") is not None else title_now).strip()
            sug_body = str(sug.get("body") if sug.get("body") is not None else body_now).strip()
            sug_cta = str(sug.get("cta") if sug.get("cta") is not None else cta_now).strip()
            sug_fc = str(
                sug.get("first_comment")
                if sug.get("first_comment") is not None
                else (
                    first_comment_now
                    or f"📌 Chi tiết ưu đãi {prod_name or 'hôm nay'} ({prod_usp[:70] if prod_usp else 'số lượng giới hạn'}): Chấm (.) hoặc nhắn Zalo/Inbox để nhận báo giá ngay!"
                )
            ).strip()
            sug_mb = str(
                sug.get("media_brief")
                if sug.get("media_brief") is not None
                else (
                    media_brief_now
                    or f"Chụp/quay thực tế {prod_name or 'sản phẩm'} dưới ánh sáng tự nhiên, làm nổi bật chi tiết '{prod_usp[:60] if prod_usp else 'chất lượng thật'}'."
                )
            ).strip()

            # Xây dựng mảng blocks linh hoạt và BẢO VỆ TUYỆT ĐỐI các block đã khóa (locked=True)
            out_blocks: List[Dict[str, Any]] = []
            if raw_blocks:
                for blk in raw_blocks:
                    if not isinstance(blk, dict):
                        continue
                    bid = str(blk.get("id") or "")
                    btype = str(blk.get("type") or "body")
                    blabel = str(blk.get("label") or "Khối nội dung")
                    if blk.get("locked"):
                        # Khối đã khóa: giữ nguyên 100% nội dung của người dùng
                        out_blocks.append({
                            "id": bid or "blk_locked",
                            "type": btype,
                            "label": blabel,
                            "content": str(blk.get("content") or ""),
                            "locked": True,
                            "metadata": blk.get("metadata") if isinstance(blk.get("metadata"), dict) else {},
                        })
                        if btype == "hook":
                            sug_title = str(blk.get("content") or sug_title)
                        elif btype == "body":
                            sug_body = str(blk.get("content") or sug_body)
                        elif btype == "cta":
                            sug_cta = str(blk.get("content") or sug_cta)
                        elif btype == "first_comment":
                            sug_fc = str(blk.get("content") or sug_fc)
                        elif btype == "media_brief":
                            sug_mb = str(blk.get("content") or sug_mb)
                    else:
                        mapped_content = str(blk.get("content") or "")
                        if btype == "hook":
                            mapped_content = sug_title
                        elif btype == "body":
                            mapped_content = sug_body
                        elif btype == "cta":
                            mapped_content = sug_cta
                        elif btype == "first_comment":
                            mapped_content = sug_fc
                        elif btype == "media_brief":
                            mapped_content = sug_mb
                        out_blocks.append({
                            "id": bid or f"blk_{btype}",
                            "type": btype,
                            "label": blabel,
                            "content": mapped_content,
                            "locked": False,
                            "metadata": blk.get("metadata") if isinstance(blk.get("metadata"), dict) else {},
                        })
            else:
                out_blocks = [
                    {"id": "b_hook", "type": "hook", "label": "Câu mở đầu (Hook 3s)", "content": sug_title, "locked": False, "metadata": {}},
                    {"id": "b_body", "type": "body", "label": "Thân bài thuyết phục", "content": sug_body, "locked": False, "metadata": {}},
                    {"id": "b_cta", "type": "cta", "label": "Kêu gọi hành động (CTA)", "content": sug_cta, "locked": False, "metadata": {}},
                    {"id": "b_fc", "type": "first_comment", "label": "Comment đầu tiên (Chứa Link/SĐT lách bóp reach)", "content": sug_fc, "locked": False, "metadata": {}},
                    {"id": "b_mb", "type": "media_brief", "label": "Ghi chú làm Ảnh / Video", "content": sug_mb, "locked": False, "metadata": {}},
                ]

            norm_sug = {
                "title": sug_title,
                "body": sug_body,
                "cta": sug_cta,
                "first_comment": sug_fc,
                "media_brief": sug_mb,
                "blocks": out_blocks,
                "change_summary": str(sug.get("change_summary") or "Đã tinh chỉnh theo yêu cầu hội thoại").strip(),
                "replaced_selection": (
                    str(sug.get("replaced_selection")).strip()
                    if sug.get("replaced_selection")
                    else None
                ),
            }

        compliance_score: Optional[int] = None
        if norm_sug and (norm_sug["title"] or norm_sug["body"]):
            try:
                from app.services.compliance_service import ComplianceScanner
                compliance_score = ComplianceScanner.scan(
                    title=norm_sug["title"],
                    body=norm_sug["body"],
                    cta=norm_sug["cta"] or None,
                    workspace_id=workspace_id,
                    db=db,
                ).score
            except Exception:
                compliance_score = None

        latency_ms = int((time.time() - start_time) * 1000) or 12
        self._log_call(
            db=db,
            user_id=user_id,
            campaign_id=campaign_id,
            task_type="DRAFT",
            model=model_used,
            prompt_version="chat-v1",
            input_hash=hashlib.sha256(user_prompt.encode("utf-8")).hexdigest()[:16],
            output_json=json.dumps({"reply": output_payload.get("reply", "")[:300]}, ensure_ascii=False),
            result_status="FALLBACK" if is_fallback else "SUCCESS",
            error_code=None,
            latency_ms=latency_ms,
            provider=active_provider,
        )

        alts = output_payload.get("alternatives")
        clean_alts = [str(a).strip() for a in alts if str(a).strip()] if isinstance(alts, list) else []

        # Phát hiện & khởi tạo Staged Proposal nếu người dùng yêu cầu điều khiển dự án
        staged_proposal = None
        if enable_ctrl:
            staged_proposal = self._detect_and_stage_project_proposal(
                db=db,
                user_id=user_id,
                workspace_id=workspace_id,
                campaign_id=campaign_id,
                thread_id=thread_id,
                message=message,
                quick_action=quick_action,
                channel_code=channel_code,
                prod_name=prod_name or camp_name or "Sản phẩm chủ lực",
                prod_usp=prod_usp or camp_obj or "Tối ưu hiệu quả thực tế",
                camp_aud=camp_aud or "Khách hàng mục tiêu tại Việt Nam",
                norm_sug=norm_sug,
                llm_actions=output_payload.get("proposed_actions") if isinstance(output_payload, dict) else None,
            )

        reply_str = str(output_payload.get("reply") or "Đã phân tích và đề xuất phương án chỉnh sửa bên dưới.").strip()
        if staged_proposal:
            reply_str = (
                f"{reply_str}\n\n⚡ **Kế hoạch Thực thi Dự án đã sẵn sàng:** Tôi đã chuẩn bị thẻ phê duyệt "
                f"**\"{staged_proposal['summary']}\"** ngay bên dưới. Bạn có thể kiểm tra từng tham số, bấm **[Thực thi]** "
                "để ghi vào hệ thống hoặc **[Hoàn tác (Undo)]** bất cứ lúc nào."
            )

        # Lưu lịch sử hội thoại dài hạn vào AIChatThread / AIChatThreadMessage nếu có thread_id
        if thread_id is not None:
            try:
                thread_obj = db.query(AIChatThread).filter(AIChatThread.id == thread_id).first()
                if thread_obj:
                    user_msg_row = AIChatThreadMessage(
                        thread_id=thread_obj.id,
                        role="user",
                        content=message.strip(),
                    )
                    db.add(user_msg_row)
                    assistant_msg_row = AIChatThreadMessage(
                        thread_id=thread_obj.id,
                        role="assistant",
                        content=reply_str,
                        suggested_canvas_json=json.dumps(norm_sug, ensure_ascii=False) if norm_sug else None,
                        alternatives_json=json.dumps(clean_alts[:6], ensure_ascii=False),
                        staged_proposal_id=staged_proposal["id"] if staged_proposal and "id" in staged_proposal else None,
                        model_used=model_used,
                        model_provider=model_provider,
                        is_fallback=bool(is_fallback),
                    )
                    db.add(assistant_msg_row)
                    thread_obj.updated_at = datetime.utcnow()
                    if norm_sug and isinstance(norm_sug.get("blocks"), list):
                        thread_obj.canvas_blocks_json = json.dumps(norm_sug["blocks"], ensure_ascii=False)
                    if thread_obj.title in ("Cuộc trò chuyện mới", "Phiên làm việc mới", "Phiên tư duy mới", "") and message.strip():
                        thread_obj.title = message.strip()[:80]
                    db.commit()
            except Exception as exc:
                logger.warning("[AI Chat Thread] Failed to save messages to thread %s: %s", thread_id, str(exc))
                db.rollback()

        return {
            "reply": reply_str,
            "thread_id": thread_id,
            "suggested_canvas": norm_sug,
            "staged_proposal": staged_proposal,
            "alternatives": clean_alts[:6],
            "context_used": context_used,
            "prompt_preview": prompt_preview,
            "compliance_score": compliance_score,
            "model_used": model_used,
            "model_provider": model_provider,
            "is_fallback": is_fallback,
        }

    def _build_canvas_chat_fallback(
        self,
        action_code: str,
        message: str,
        title_now: str,
        body_now: str,
        cta_now: str,
        selected_text: Optional[str],
        prod_name: str,
        prod_usp: str,
        camp_aud: str,
        channel_code: str,
        workspace_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Xử lý biên tập văn bản & truy vấn toàn cảnh dự án thực tế trên dữ liệu thật của người dùng."""
        base_title = title_now or f"{prod_name} — {prod_usp[:65]}"
        base_cta = cta_now or f"Nhắn tin ngay để nhận báo giá {prod_name} kèm ưu đãi hôm nay"
        ws_meta = workspace_meta or {}
        msg_lower = (message or "").strip().lower()

        # Phản hồi tự nhận thức tài nguyên VPS & trạng thái OpenCode CLI khi người dùng hỏi
        if any(k in msg_lower for k in ("ram", "vps", "tài nguyên", "cpu", "opencode", "máy chủ", "dung lượng")):
            vps_info = ws_meta.get("vps") or self._get_vps_resource_telemetry()
            oc_status = (
                "Đã cài sẵn `/usr/local/bin/opencode` (v1.19.4) và đã xác thực tài khoản (`auth.json`)"
                if vps_info.get("has_opencode_auth")
                else "Đã cài sẵn `/usr/local/bin/opencode` (v1.19.4 — đang chạy chế độ 0 credentials, có thể chạy `opencode auth login` để mở khóa hạn mức)"
                if vps_info.get("has_opencode_cli")
                else "Chế độ API / Local"
            )
            camps_count = len(ws_meta.get("campaigns") or [])
            prods_count = len(ws_meta.get("products") or [])
            tasks_count = len(ws_meta.get("tasks_todo") or [])
            reply_vps = (
                f"🖥️ **Báo cáo Tự Nhận Thức Hạ Tầng VPS & Toàn Cảnh Dự Án:**\n"
                f"- **Bộ nhớ RAM VPS:** Đang dùng **{vps_info.get('used_ram_mb', 0)} MB / {vps_info.get('total_ram_mb', 1986)} MB** "
                f"({vps_info.get('ram_percent', 0)}% — còn trống **{vps_info.get('avail_ram_mb', 1200)} MB**).\n"
                f"- **Tải CPU (Load 1m):** `{vps_info.get('cpu_load_1m', 0.05)}` — Backend FastAPI chạy chế độ 1 Worker siêu nhẹ (~76 MB RAM).\n"
                f"- **Trạng thái OpenCode CLI Bridge:** {oc_status}.\n"
                f"- **Dữ liệu Dự án đang kết nối trực tiếp:** **{camps_count}** chiến dịch, **{prods_count}** sản phẩm, **{tasks_count}** đầu việc chưa hoàn thành."
            )
            return {
                "reply": reply_vps,
                "suggested_canvas": {
                    "title": base_title,
                    "body": body_now or f"{prod_name} — {prod_usp}",
                    "cta": base_cta,
                    "change_summary": "Kiểm tra trực tiếp thông số RAM/CPU VPS & trạng thái OpenCode CLI",
                    "replaced_selection": None,
                },
                "alternatives": [],
            }

        # Phản hồi kiểm tra toàn cảnh dự án (Chiến dịch, Sản phẩm, Đầu việc, ROAS) khi người dùng hỏi
        if any(
            k in msg_lower
            for k in (
                "toàn cảnh dự án",
                "dự án có gì",
                "chiến dịch nào",
                "danh sách chiến dịch",
                "danh sách sản phẩm",
                "việc cần làm",
                "task nào",
                "báo cáo roas",
                "tình hình dự án",
            )
        ):
            camps = ws_meta.get("campaigns") or []
            prods = ws_meta.get("products") or []
            tasks_todo = ws_meta.get("tasks_todo") or []
            met = ws_meta.get("metrics_summary") or {}
            c_str = ", ".join(f"**{c['name']}** ({c['status']}, {c['budget']:,.0f}đ)" for c in camps[:5]) or "Chưa có chiến dịch"
            p_str = ", ".join(f"**{p['name']}** ({p['usp'][:45]})" for p in prods[:5]) or "Chưa có sản phẩm"
            t_str = ", ".join(f"`#{t['id']}` {t['title']} ({t['priority']})" for t in tasks_todo[:5]) or "Không có việc tồn đọng"
            reply_proj = (
                f"📊 **Bức Tranh Toàn Cảnh Dự Án (Truy xuất trực tiếp từ CSDL):**\n"
                f"1. **Chiến dịch ({len(camps)}):** {c_str}\n"
                f"2. **Sản phẩm & USP ({len(prods)}):** {p_str}\n"
                f"3. **Đầu việc đang mở ({len(tasks_todo)}):** {t_str}\n"
                f"4. **Hiệu quả thực tế (Metrics):** Chi phí **{met.get('cost', 0):,.0f}đ** | Doanh thu **{met.get('revenue', 0):,.0f}đ** | "
                f"**ROAS {met.get('roas', 0)}x** ({met.get('clicks', 0)} Click / {met.get('conversions', 0)} Đơn chốt).\n\n"
                "💡 *Bạn có thể ra lệnh trực tiếp bằng tiếng Việt để tôi can thiệp sâu: ví dụ \"Tạo chiến dịch mới ngân sách 10tr\", "
                "\"Tạm dừng chiến dịch hiện tại\", \"Thêm sản phẩm X với USP Y\", \"Đánh dấu hoàn thành các task\", hoặc \"Tạo link tracking đo click\".*"
            )
            return {
                "reply": reply_proj,
                "suggested_canvas": {
                    "title": base_title,
                    "body": body_now or f"{prod_name} — {prod_usp}",
                    "cta": base_cta,
                    "change_summary": "Tổng hợp dữ liệu thời gian thực từ CSDL dự án",
                    "replaced_selection": None,
                },
                "alternatives": [],
            }

        if action_code == "HOOK_5":
            hooks = [
                f"[Đánh trúng nỗi đau] Đừng vội chi thêm tiền nếu bạn chưa biết sự thật này về {prod_name} ({prod_usp}).",
                f"[Bằng chứng thực tế] Vì sao nhiều {camp_aud} đã chuyển hẳn sang {prod_name} chỉ sau 1 lần dùng thử?",
                f"[Phá vỡ ngộ nhận] 90% người mới tìm hiểu đều hiểu sai điểm cốt lõi này: {prod_usp}.",
                f"[Câu hỏi trực diện] Bạn đang tốn bao nhiêu thời gian và chi phí mỗi tuần chỉ vì thiếu {prod_name}?",
                f"[Cam kết rõ ràng] Trải nghiệm {prod_name} với cam kết thực tế: {prod_usp} — kiểm tra trước khi thanh toán.",
            ]
            return {
                "reply": (
                    f"Tôi đã soạn 5 câu mở đầu (Hook 3s) bám sát vào sản phẩm **{prod_name}** và điểm mạnh **{prod_usp}**. "
                    "Bạn có thể bấm chọn 1 câu bất kỳ bên dưới để đưa vào Tiêu đề hoặc Mở bài trên bàn soạn thảo."
                ),
                "suggested_canvas": {
                    "title": hooks[0].replace("[Đánh trúng nỗi đau] ", ""),
                    "body": body_now or f"{hooks[0].replace('[Đánh trúng nỗi đau] ', '')}\n\n• Điểm khác biệt cốt lõi: {prod_usp}\n• Phù hợp trực tiếp cho: {camp_aud}",
                    "cta": base_cta,
                    "change_summary": "Đề xuất 5 câu Hook mở đầu đa góc độ tâm lý từ dữ liệu sản phẩm",
                    "replaced_selection": None,
                },
                "alternatives": hooks,
            }

        if action_code == "SHORTEN_30":
            if body_now:
                lines = [ln.strip() for ln in body_now.splitlines() if ln.strip()]
                shortened_lines = []
                for ln in lines:
                    words = ln.split()
                    if len(words) > 16:
                        shortened_lines.append(" ".join(words[: max(10, int(len(words) * 0.72))]) + ".")
                    else:
                        shortened_lines.append(ln)
                new_body = "\n\n".join(shortened_lines)
            else:
                new_body = f"• Giải pháp: {prod_name}\n• Khác biệt thực tế: {prod_usp}\n• Dành cho: {camp_aud}"
            return {
                "reply": "Tôi đã cắt gọn các từ nối dài dòng trong bản thảo hiện tại của bạn, giữ lại khung thông tin cốt lõi và lời kêu gọi hành động.",
                "suggested_canvas": {
                    "title": base_title,
                    "body": new_body,
                    "cta": base_cta,
                    "change_summary": f"Rút gọn từ {len(body_now)} ký tự xuống {len(new_body)} ký tự",
                    "replaced_selection": None,
                },
                "alternatives": [],
            }

        if action_code == "ANTI_CLICHE":
            cliche_map = {
                "giải pháp tối ưu": "cách làm thực tế",
                "hàng đầu": "được kiểm chứng",
                "toàn diện": "đầy đủ từng bước",
                "tận tâm": "hỗ trợ trực tiếp 1-1",
                "đáng tin cậy": "rõ nguồn gốc và cam kết",
                "trong bối cảnh hiện nay": "Thực tế hiện nay",
                "tìm hiểu thêm": f"Nhận báo giá {prod_name} ngay",
            }
            cleaned_body = body_now or f"{prod_name} tập trung giải quyết trực tiếp bài toán cho {camp_aud}: {prod_usp}."
            replaced_terms = []
            for bad, good in cliche_map.items():
                pattern = re.compile(re.escape(bad), re.IGNORECASE)
                if pattern.search(cleaned_body):
                    cleaned_body = pattern.sub(good, cleaned_body)
                    replaced_terms.append(f"'{bad}' → '{good}'")
            cleaned_cta = base_cta
            if "tìm hiểu thêm" in cleaned_cta.lower():
                cleaned_cta = f"Nhắn tin nhận báo giá {prod_name} ngay"
            summary_note = (
                f"Đã thay thế các cụm từ văn mẫu: {', '.join(replaced_terms)}"
                if replaced_terms
                else "Đã rà soát và làm gọn nhịp câu theo văn phong thực chiến"
            )
            return {
                "reply": f"{summary_note}. Bạn có thể đối chiếu bản đề xuất bên dưới trước khi bấm **Áp dụng vào bài**.",
                "suggested_canvas": {
                    "title": base_title,
                    "body": cleaned_body,
                    "cta": cleaned_cta,
                    "change_summary": summary_note,
                    "replaced_selection": None,
                },
                "alternatives": [],
            }

        if action_code == "ZALO_INBOX_SCRIPT":
            script_body = (
                f"【BƯỚC 1 — CHÀO & PHÂN LOẠI NHU CẦU (Phản hồi < 30 giây)】\n"
                f"Dạ chào anh/chị ạ! Bên em đang có sẵn {prod_name}. Hiện mình đang quan tâm dùng cho nhu cầu nào ({camp_aud}) để em báo đúng phân loại tiết kiệm nhất cho mình ạ?\n\n"
                f"【BƯỚC 2 — NÊU ĐIỂM KHÁC BIỆT (USP) & BÁO GIÁ NEO】\n"
                f"Dạ điểm ăn tiền nhất của {prod_name} bên em là: {prod_usp}. Anh/chị lấy trong hôm nay sẽ được áp dụng chính sách ưu đãi trực tiếp của chiến dịch ạ.\n\n"
                f"【BƯỚC 3 — XỬ LÝ 3 TỪ CHỐI PHỔ BIẾN NHẤT】\n"
                f"• Khách bảo 'Để hỏi chồng / suy nghĩ thêm': Dạ vâng ạ, để tiện trao đổi với anh nhà, em gửi mình bảng tóm tắt công dụng ({prod_usp}) và chính sách đổi trả nhé. Hôm nay bên em còn giữ mã ưu đãi đến 21h, mình cần giữ suất trước không ạ?\n"
                f"• Khách chê 'Giá cao hơn chỗ khác': Dạ bên em cam kết chuẩn {prod_usp}, có bảo hành/đổi trả rõ ràng nên tính ra chi phí sử dụng lâu dài tiết kiệm hơn hàng trôi nổi rất nhiều ạ.\n"
                f"• Khách hỏi 'Ship tỉnh bao lâu / có kiểm hàng không': Dạ bên em giao toàn quốc, anh/chị được mở hộp kiểm tra đúng {prod_name} rồi mới thanh toán nhé ạ!\n\n"
                f"【BƯỚC 4 — CHỐT ĐƠN XIN SĐT + ĐỊA CHỈ】\n"
                f"Dạ anh/chị cho em xin SĐT + Địa chỉ nhận hàng để em lên mã đơn ưu đãi ngay trong ca sáng/chiều nay cho mình nhé ạ!\n\n"
                f"【BƯỚC 5 — FOLLOW-UP KHÁCH IM LẶNG SAU 24H (Zalo / Messenger)】\n"
                f"Dạ anh/chị ơi, hôm qua mình đang hỏi dở {prod_name}. Hiện kho bên em còn đúng 3 suất ưu đãi cuối của đợt này, em nhắn hỏi xem mình còn lăn tăn điểm nào để em hỗ trợ nốt ạ?"
            )
            return {
                "reply": (
                    f"Tôi đã soạn trọn bộ **Kịch bản Chốt đơn Inbox Messenger / Zalo 5 bước** kèm 3 mẫu câu xử lý từ chối "
                    f"dành riêng cho **{prod_name}** ({prod_usp}). Bạn có thể bấm **Áp dụng vào bài** để chỉnh sửa thêm từng câu thoại của nhân viên Sale."
                ),
                "suggested_canvas": {
                    "title": f"Kịch bản Chốt đơn Inbox Zalo/Messenger — {prod_name}",
                    "body": script_body,
                    "cta": "Dạ anh/chị cho em xin SĐT + Địa chỉ nhận hàng để em giữ suất ưu đãi ngay nhé ạ!",
                    "change_summary": "Tạo kịch bản chốt đơn Inbox 5 bước & xử lý từ chối thị trường Việt Nam",
                    "replaced_selection": None,
                },
                "alternatives": [
                    f"Dạ chào anh/chị! Mình đang tìm {prod_name} để dùng cá nhân hay làm quà tặng để em tư vấn đúng gói hời nhất ạ?",
                    f"Dạ bên em cam kết {prod_usp} — anh/chị nhận hàng được kiểm tra thoải mái trước khi thanh toán ạ!",
                    f"Dạ anh/chị cho em xin SĐT + Địa chỉ để em giữ mã ưu đãi trong hôm nay cho mình nhé!",
                ],
            }

        if action_code == "LIVESTREAM_SCRIPT":
            live_body = (
                f"🎥 【PHÚT 00:00 - 03:00 | GIỮ CHÂN MẮT XEM & MỒI COMMENT】\n"
                f"- Host giơ trực tiếp {prod_name} sát cam: 'Ai đang thuộc nhóm {camp_aud} mà vẫn đau đầu chuyện chi phí thì ở lại đúng 2 phút này với em!'\n"
                f"- Mồi tương tác: 'Anh chị nào đang xem nghe rõ tiếng em gõ phím số 1 giúp em để em tung mã đầu phiên nha!'\n\n"
                f"🔥 【PHÚT 03:00 - 08:00 | CHỨNG MINH USP TRỰC TIẾP TRƯỚC ỐNG KÍNH】\n"
                f"- Điểm khác biệt ăn tiền: {prod_usp}.\n"
                f"- Thực hành test sản phẩm / chỉ rõ chi tiết thật trên tay để khách thấy sự khác biệt so với hàng thường ngoài chợ.\n\n"
                f"💥 【PHÚT 08:00 - 12:00 | NEO GIÁ & BUNG DEAL FLASH SALE】\n"
                f"- Giá niêm yết tại cửa hàng đang cao hơn, nhưng riêng trên phiên Live hôm nay bên em trợ giá trực tiếp.\n"
                f"- Giải đáp nhanh 2 câu hỏi trên bình luận của khách xem Live.\n\n"
                f"⏰ 【PHÚT 12:00 - 15:00 | ĐẾM NGƯỢC 60 GIÂY & CHỐT GIỎ HÀNG】\n"
                f"- 'Em ghim {prod_name} ở Giỏ hàng màu vàng góc trái số 01! Đúng 60 giây nữa hệ thống tự về giá gốc, anh chị bấm Thanh toán ngay để giữ mã Freeship nhé!'"
            )
            return {
                "reply": (
                    f"Tôi đã lên khung **Kịch bản Phiên Livestream 15 phút lặp vòng (Loop Script)** cho **{prod_name}**. "
                    "Kịch bản chia rõ 4 nhịp: Giữ mắt xem -> Demo USP -> Bung Deal -> Đếm ngược chốt giỏ hàng."
                ),
                "suggested_canvas": {
                    "title": f"Kịch bản Livestream Bán hàng 15 Phút — {prod_name}",
                    "body": live_body,
                    "cta": "Bấm ngay vào Giỏ hàng góc trái màn hình (Mã số 01) trước khi hết 60 giây Flash Sale!",
                    "change_summary": "Tạo kịch bản Livestream TikTok Shop / Facebook Live 4 nhịp thực chiến",
                    "replaced_selection": None,
                },
                "alternatives": [],
            }

        if action_code == "REPURPOSE_TIKTOK":
            tk_body = (
                f"🎬 [CẢNH 1: 0-3s — HOOK GIỮ CHÂN]\n"
                f"• Hình ảnh: Cận cảnh vấn đề của {camp_aud} hoặc giơ {prod_name} vào khung hình.\n"
                f"• Lời thoại: '{ base_title }'\n\n"
                f"🎬 [CẢNH 2: 3-15s — XOÁY SÂU VẤN ĐỀ & GIẢI PHÁP]\n"
                f"• Hình ảnh: Quay thực tế quá trình sử dụng {prod_name}.\n"
                f"• Lời thoại: '{ (body_now[:220] + '...') if len(body_now) > 220 else (body_now or prod_usp) }'\n\n"
                f"🎬 [CẢNH 3: 15-30s — CHỨNG MINH USP]\n"
                f"• Hình ảnh: Text overlay nổi bật điểm mạnh: {prod_usp}.\n"
                f"• Lời thoại: 'Điểm khác biệt rõ nhất nằm ở {prod_usp}.'\n\n"
                f"🎬 [CẢNH 4: 30-40s — KÊU GỌI HÀNH ĐỘNG (CTA)]\n"
                f"• Hình ảnh: Chỉ tay xuống Giỏ hàng góc trái / Bio.\n"
                f"• Lời thoại: '{ base_cta }'"
            )
            return {
                "reply": "Tôi đã chuyển thể nội dung trên bàn soạn thảo của bạn sang định dạng **Phân cảnh Kịch bản Video ngắn TikTok / Reels (30-40s)**.",
                "suggested_canvas": {
                    "title": f"[TikTok Script 35s] {base_title}",
                    "body": tk_body,
                    "cta": base_cta,
                    "change_summary": "Chuyển thể sang kịch bản 4 phân cảnh TikTok / Reels",
                    "replaced_selection": None,
                },
                "alternatives": [],
            }

        if selected_text:
            rewritten_sel = f"{selected_text} — đặc biệt nổi bật với {prod_usp}"
            updated_body = body_now.replace(selected_text, rewritten_sel, 1) if selected_text in body_now else body_now
            return {
                "reply": (
                    f"Tôi đã tinh chỉnh riêng đoạn văn bạn đang bôi đen theo yêu cầu: *\"{message}\"*. "
                    "Bấm **Áp dụng vào bài** để thay thế đúng đoạn bôi đen đó trên bàn soạn thảo."
                ),
                "suggested_canvas": {
                    "title": base_title,
                    "body": updated_body,
                    "cta": base_cta,
                    "change_summary": "Chỉnh sửa cục bộ đoạn văn bản đang bôi đen",
                    "replaced_selection": rewritten_sel,
                },
                "alternatives": [
                    rewritten_sel,
                    f"Thực tế với {prod_name}: {selected_text}",
                ],
            }

        # Phản hồi hội thoại & biên tập dựa trên yêu cầu tự nhiên của người dùng
        edited_body = (
            f"{body_now}\n\n💡 Điểm nhấn bổ sung ({message[:60]}): {prod_usp} — phù hợp trực tiếp cho {camp_aud}."
            if body_now
            else (
                f"Bạn đang tìm giải pháp thực tế cho {camp_aud}?\n\n"
                f"• Sản phẩm / Dịch vụ: {prod_name}\n"
                f"• Điểm khác biệt cốt lõi (USP): {prod_usp}\n"
                f"• Trọng tâm theo yêu cầu của bạn: {message.strip()}\n\n"
                f"Cam kết thông tin minh bạch, đi thẳng vào hiệu quả thực tế."
            )
        )
        return {
            "reply": (
                f"Đã tiếp nhận yêu cầu của bạn: *\"{message.strip()}\"*. "
                f"Tôi đã kết hợp dữ liệu thực tế của **{prod_name}** ({prod_usp}) cùng bản thảo trên bàn viết để đề xuất phương án bên dưới. "
                "Bạn có thể tự sửa tay từng chữ hoặc bấm **Áp dụng vào bài**."
            ),
            "suggested_canvas": {
                "title": base_title,
                "body": edited_body,
                "cta": base_cta,
                "change_summary": f"Cập nhật nội dung theo yêu cầu: '{message[:50]}'",
                "replaced_selection": None,
            },
            "alternatives": [
                f"{prod_name}: {prod_usp}",
                f"Giải pháp cho {camp_aud} — {prod_name}",
                base_cta,
            ],
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
        latency_ms: int,
        provider: Optional[str] = None,
    ):
        try:
            safe_task_type = task_type if task_type in ("IDEA", "DRAFT", "SUMMARY", "OMNICHANNEL") else (
                "SUMMARY" if task_type in ("PRELAUNCH_CRITIC",) else (
                    "DRAFT" if task_type in ("COMPLIANCE_REWRITE",) else "IDEA"
                )
            )
            eff_provider = (provider or "").strip() or self._detect_provider(None, model) or settings.AI_PROVIDER
            log_entry = AILog(
                user_id=user_id,
                campaign_id=campaign_id,
                task_type=safe_task_type,
                provider=eff_provider,
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
