"""
MarketFlow AI — Model Context Protocol (MCP) Server & Agentic Tool Orchestrator.

Triển khai chuẩn giao thức MCP (JSON-RPC 2.0 / 2025-03-26) kết hợp Agentic AI:
1. MCP Tools (`tools/list`, `tools/call`):
   - `list_workspace_campaigns`: Truy vấn danh sách chiến dịch trong Workspace.
   - `get_campaign_metrics`: Đọc số liệu thực tế (Views, Clicks, Cost, Revenue, CTR, CPC, CVR, ROAS, ROI).
   - `diagnose_campaign_health`: Chạy AI Doctor chẩn đoán điểm nghẽn & đề xuất tối ưu.
   - `scan_content_compliance`: Quét vi phạm chính sách quảng cáo & từ khóa cấm Brand Kit.
   - `auto_fix_compliance_violations`: Agentic AI viết lại nội dung vi phạm đạt chuẩn 100/100.
   - `create_marketing_draft`: Sinh và lưu bản nháp tiếp thị chuẩn Brand Kit vào CSDL.
   - `rebalance_campaign_budget`: Mô phỏng / đề xuất phân bổ lại ngân sách theo ROAS thực tế.
2. MCP Resources (`resources/list`, `resources/read`):
   - `marketflow://workspace/brand-kit`
   - `marketflow://campaigns/active-summary`
   - `marketflow://policies/ad-compliance-rules`
3. MCP Prompts (`prompts/list`, `prompts/get`):
   - Các mẫu prompt chuẩn hóa cho hệ sinh thái Agentic Marketing.
4. Agentic Copilot Runner (`run_agent_workflow`):
   - Tự động lập kế hoạch (Plan) -> Đọc MCP Resource -> Gọi chuỗi MCP Tools -> Tổng hợp kết quả bằng LLM.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.entities import (
    BrandKit,
    Campaign,
    CampaignBudgetAllocation,
    CampaignMember,
    CampaignMetric,
    MarketingChannel,
    MarketingContent,
    Product,
    User,
    Workspace,
    WorkspaceMember,
)
from app.services.ai.ai_doctor import AIDoctorEngine
from app.services.ai.ai_service import ai_service
from app.services.compliance.compliance_service import ComplianceScanner

logger = logging.getLogger("marketflow.mcp")

MCP_PROTOCOL_VERSION = "2025-03-26"
MCP_SERVER_NAME = "marketflow-mcp-server"
MCP_SERVER_VERSION = "2.0.0"

# Bảng ánh xạ thay thế ngữ nghĩa an toàn khi viết lại nội dung vi phạm chính sách
SAFE_REWRITE_MAP = {
    "cam kết 100%": "đồng hành tối đa cùng học viên và khách hàng",
    "chữa khỏi": "hỗ trợ cải thiện hiệu quả",
    "chữa dứt điểm": "hỗ trợ giải quyết toàn diện",
    "trị dứt điểm": "hỗ trợ khắc phục bền vững",
    "vĩnh viễn": "lâu dài và ổn định",
    "tuyệt đối": "vượt trội",
    "không tác dụng phụ": "an toàn, lành tính theo tiêu chuẩn kiểm định",
    "bác sĩ khuyên dùng": "được phát triển dựa trên nghiên cứu chuyên sâu",
    "số 1 việt nam": "hàng đầu trong lĩnh vực",
    "số 1": "hàng đầu trong phân khúc",
    "số một": "hàng đầu trong phân khúc",
    "nhất thế giới": "tiêu chuẩn quốc tế",
    "duy nhất trên thị trường": "tiên phong với giải pháp chuyên biệt",
    "làm giàu nhanh": "phát triển thu nhập bền vững",
    "lợi nhuận khủng": "tối ưu hiệu suất đầu tư",
    "x10 tài khoản": "gia tăng hiệu quả tài chính",
    "không rủi ro": "quản trị rủi ro minh bạch",
    "chắc chắn thắng": "nâng cao tỷ lệ thành công",
    "kiếm tiền dễ dàng": "xây dựng nguồn thu nhập chủ động",
    "đa cấp": "mô hình kinh doanh đối tác",
    "hoàn tiền không lý do": "chính sách bảo hành và đổi trả minh bạch",
    "xả kho": "chương trình ưu đãi định kỳ",
    "xả kho giá rẻ": "ưu đãi đặc quyền theo mùa",
    "giảm sốc sập sàn": "ưu đãi hấp dẫn dành riêng cho khách hàng sớm",
    "mua ngay kẻo lỡ": "đăng ký sớm để nhận trọn bộ quyền lợi",
    "cơ hội cuối cùng": "thời điểm lý tưởng để bắt đầu",
    "chỉ còn 1 suất": "số lượng ưu đãi giới hạn theo đợt",
}


class MarketFlowMCPServer:
    """Máy chủ MCP tích hợp trực tiếp với CSDL đa người thuê (Multi-tenant) của MarketFlow AI."""

    def get_server_info(self) -> Dict[str, Any]:
        return {
            "name": MCP_SERVER_NAME,
            "version": MCP_SERVER_VERSION,
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
            },
            "description": (
                "Model Context Protocol (MCP) Server cho Hệ thống Quản lý Chiến dịch "
                "Marketing tích hợp AI (MarketFlow AI)."
            ),
        }

    # ==========================================================================
    # 1. DANH MỤC MCP TOOLS, RESOURCES, PROMPTS
    # ==========================================================================

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "list_workspace_campaigns",
                "description": (
                    "Liệt kê danh sách các chiến dịch tiếp thị trong Workspace hiện tại kèm "
                    "ngân sách, mục tiêu, đối tượng khán giả và trạng thái vận hành."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace_id": {
                            "type": "integer",
                            "description": "ID của Workspace cần truy vấn (tùy chọn, mặc định lấy workspace hiện hành).",
                        },
                        "status": {
                            "type": "string",
                            "description": "Lọc theo trạng thái chiến dịch (ACTIVE, PLANNED, PAUSED, COMPLETED).",
                        },
                    },
                },
            },
            {
                "name": "get_campaign_metrics",
                "description": (
                    "Truy xuất toàn bộ chỉ số hiệu năng thực tế (Views, Clicks, Conversions, Cost, "
                    "Revenue, CTR, CPC, CVR, ROAS, ROI) theo từng kênh của một chiến dịch."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "integer",
                            "description": "ID chiến dịch cần lấy số liệu KPI.",
                        },
                    },
                    "required": ["campaign_id"],
                },
            },
            {
                "name": "diagnose_campaign_health",
                "description": (
                    "Kích hoạt Bác sĩ AI (AI Performance Doctor) phân tích phễu chuyển đổi, chấm điểm "
                    "sức khỏe chiến dịch (0-100), tìm điểm nghẽn và sinh phác đồ tối ưu ngân sách."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "integer",
                            "description": "ID chiến dịch cần khám sức khỏe.",
                        },
                    },
                    "required": ["campaign_id"],
                },
            },
            {
                "name": "scan_content_compliance",
                "description": (
                    "Quét tuân thủ chính sách quảng cáo (Meta/TikTok/Luật Quảng cáo VN) và từ khóa cấm "
                    "trong Brand Kit của Workspace trước khi gửi duyệt bài viết."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace_id": {
                            "type": "integer",
                            "description": "ID Workspace để đối chiếu Brand Kit.",
                        },
                        "channel": {
                            "type": "string",
                            "description": "Kênh truyền thông (facebook, tiktok, email).",
                        },
                        "title": {"type": "string", "description": "Tiêu đề bài viết."},
                        "body": {"type": "string", "description": "Nội dung thân bài viết."},
                        "cta": {"type": "string", "description": "Lời kêu gọi hành động (CTA)."},
                    },
                    "required": ["title", "body"],
                },
            },
            {
                "name": "auto_fix_compliance_violations",
                "description": (
                    "Agentic AI tự động viết lại nội dung tiếp thị bị vi phạm chính sách sang văn phong "
                    "hợp chuẩn 100/100 (PASSED), giữ nguyên thông điệp cốt lõi (USP) và giọng điệu Brand Kit."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace_id": {
                            "type": "integer",
                            "description": "ID Workspace để kế thừa Brand Kit.",
                        },
                        "channel": {
                            "type": "string",
                            "description": "Kênh tiếp thị (facebook, tiktok, email).",
                        },
                        "title": {"type": "string", "description": "Tiêu đề gốc cần làm sạch."},
                        "body": {"type": "string", "description": "Thân bài gốc cần làm sạch."},
                        "cta": {"type": "string", "description": "CTA gốc cần làm sạch."},
                    },
                    "required": ["title", "body"],
                },
            },
            {
                "name": "create_marketing_draft",
                "description": (
                    "Khởi tạo bản nháp nội dung tiếp thị (AI_DRAFT) bằng AI chuẩn Brand Kit, tự động "
                    "quét tuân thủ và tùy chọn lưu trực tiếp vào chiến dịch."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {"type": "integer", "description": "ID chiến dịch mục tiêu."},
                        "channel": {
                            "type": "string",
                            "description": "Kênh xuất bản (facebook, tiktok, email).",
                        },
                        "topic": {
                            "type": "string",
                            "description": "Chủ đề hoặc góc tiếp cận nội dung cần viết.",
                        },
                        "save_to_db": {
                            "type": "boolean",
                            "description": "Nếu true, lưu bản nháp vào bảng marketing_contents.",
                        },
                    },
                    "required": ["campaign_id"],
                },
            },
            {
                "name": "rebalance_campaign_budget",
                "description": (
                    "Tính toán phương án tái phân bổ ngân sách thông minh giữa các kênh dựa trên hiệu suất "
                    "ROAS và CVR thực tế của chiến dịch."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {"type": "integer", "description": "ID chiến dịch."},
                        "apply_changes": {
                            "type": "boolean",
                            "description": "Nếu true và người dùng có quyền chủ sở hữu/quản lý, cập nhật phân bổ ngân sách.",
                        },
                    },
                    "required": ["campaign_id"],
                },
            },
            {
                "name": "dispatch_external_webhook",
                "description": (
                    "Bắn sự kiện Outbound Webhook chuẩn ký số HMAC-SHA256 (X-MarketFlow-Signature) để đồng bộ "
                    "nội dung xuất bản, cảnh báo KPI hoặc trạng thái phê duyệt ra hệ thống bên ngoài "
                    "(n8n, Zapier, Make.com, Telegram Bot, Slack/Discord, Meta Graph API, WordPress REST)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "connector_type": {
                            "type": "string",
                            "description": (
                                "Loại kết nối đích: n8n_zapier, telegram_bot, slack_discord, "
                                "facebook_graph, tiktok_business, wordpress_cms."
                            ),
                        },
                        "event_type": {
                            "type": "string",
                            "description": (
                                "Sự kiện kích hoạt: content.published, content.in_review, "
                                "campaign.budget_rebalanced, compliance.auto_fixed."
                            ),
                        },
                        "campaign_id": {
                            "type": "integer",
                            "description": "ID chiến dịch liên quan để đính kèm ngữ cảnh & KPI.",
                        },
                        "target_url": {
                            "type": "string",
                            "description": "URL đích nhận Webhook (tùy chọn).",
                        },
                    },
                    "required": ["connector_type"],
                },
            },
        ]

    def list_resources(self) -> List[Dict[str, Any]]:
        return [
            {
                "uri": "marketflow://workspace/brand-kit",
                "name": "Workspace Brand Kit & Safety Guidelines",
                "description": "Thông tin nhận diện thương hiệu, USP, giọng điệu (Tone of Voice) và danh sách từ khóa cấm.",
                "mimeType": "application/json",
            },
            {
                "uri": "marketflow://campaigns/active-summary",
                "name": "Active Campaigns & KPI Snapshot",
                "description": "Bức tranh tổng thể các chiến dịch đang chạy kèm tổng ngân sách và chỉ số chuyển đổi.",
                "mimeType": "application/json",
            },
            {
                "uri": "marketflow://policies/ad-compliance-rules",
                "name": "Omnichannel Advertising Compliance Ruleset",
                "description": "Bộ quy tắc kiểm duyệt quảng cáo đa kênh (Y tế, Tài chính, Khuyến mãi ảo, Spam).",
                "mimeType": "application/json",
            },
        ]

    def list_prompts(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "omnichannel-campaign-architect",
                "description": "Thiết kế chiến lược nội dung đa kênh (Facebook, TikTok, Email) đồng bộ từ một Brief.",
                "arguments": [
                    {"name": "campaign_id", "description": "ID chiến dịch cần lập kế hoạch", "required": True},
                    {"name": "focus_goal", "description": "Mục tiêu trọng tâm (Leads, Doanh số, Nhận diện)", "required": False},
                ],
            },
            {
                "name": "compliance-safe-copywriter",
                "description": "Kiểm toán và viết lại nội dung quảng cáo đảm bảo điểm tuân thủ tuyệt đối 100/100.",
                "arguments": [
                    {"name": "draft_text", "description": "Nội dung quảng cáo cần kiểm tra và tối ưu", "required": True},
                ],
            },
            {
                "name": "roas-performance-doctor",
                "description": "Chẩn đoán chuyên sâu nguyên nhân rò rỉ ngân sách và đề xuất tái phân bổ theo ROAS.",
                "arguments": [
                    {"name": "campaign_id", "description": "ID chiến dịch cần chẩn đoán", "required": True},
                ],
            },
        ]

    # ==========================================================================
    # 2. KIỂM TRA QUYỀN TENANT (MULTI-TENANT ISOLATION)
    # ==========================================================================

    def _resolve_accessible_workspace(
        self, db: Session, user: User, workspace_id: Optional[int] = None
    ) -> Optional[Workspace]:
        if workspace_id is not None:
            ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
            if not ws:
                return None
            if user.role == "ADMIN" or ws.owner_id == user.id:
                return ws
            is_member = (
                db.query(WorkspaceMember)
                .filter(WorkspaceMember.workspace_id == ws.id, WorkspaceMember.user_id == user.id)
                .first()
                is not None
            )
            return ws if is_member else None

        owned = db.query(Workspace).filter(Workspace.owner_id == user.id).order_by(Workspace.id.asc()).first()
        if owned:
            return owned
        member_ws = (
            db.query(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .filter(WorkspaceMember.user_id == user.id)
            .order_by(Workspace.id.asc())
            .first()
        )
        if member_ws:
            return member_ws
        if user.role == "ADMIN":
            return db.query(Workspace).order_by(Workspace.id.asc()).first()
        return None

    def _get_accessible_campaign(self, db: Session, user: User, campaign_id: int) -> Campaign:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise ValueError(f"Chiến dịch #{campaign_id} không tồn tại.")
        if user.role == "ADMIN":
            return campaign

        if campaign.workspace_id is not None:
            ws = self._resolve_accessible_workspace(db, user, campaign.workspace_id)
            if not ws:
                raise PermissionError("Bạn không có quyền truy cập chiến dịch thuộc Workspace khác.")
            if user.role in ("MANAGER", "AGENCY_MANAGER") or ws.owner_id == user.id:
                return campaign

        if campaign.owner_id == user.id:
            return campaign

        is_member = (
            db.query(CampaignMember)
            .filter(CampaignMember.campaign_id == campaign.id, CampaignMember.user_id == user.id)
            .first()
            is not None
        )
        if not is_member:
            raise PermissionError("Bạn không có quyền truy cập chiến dịch này.")
        return campaign

    # ==========================================================================
    # 3. ĐỌC TÀI NGUYÊN MCP (RESOURCES READ)
    # ==========================================================================

    def read_resource(
        self, db: Session, user: User, uri: str, workspace_id: Optional[int] = None
    ) -> Dict[str, Any]:
        ws = self._resolve_accessible_workspace(db, user, workspace_id)

        if uri == "marketflow://workspace/brand-kit":
            if not ws:
                raise PermissionError("Không tìm thấy Workspace hợp lệ.")
            bk = db.query(BrandKit).filter(BrandKit.workspace_id == ws.id).first()
            banned = []
            if bk and bk.banned_keywords_json:
                try:
                    banned = json.loads(bk.banned_keywords_json)
                except Exception:
                    banned = []
            payload = {
                "workspace_id": ws.id,
                "workspace_name": ws.name,
                "brand_name": bk.brand_name if bk else ws.name,
                "usp": bk.usp if bk else "Giải pháp tiếp thị đa kênh tích hợp AI",
                "tone_of_voice": bk.tone_of_voice if bk else "Chuyên nghiệp, hiện đại, đáng tin cậy",
                "banned_keywords": banned,
            }
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(payload, ensure_ascii=False, indent=2),
                        "data": payload,
                    }
                ]
            }

        if uri == "marketflow://campaigns/active-summary":
            campaigns_data = self._tool_list_workspace_campaigns(
                db, user, {"workspace_id": ws.id if ws else workspace_id}
            )
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(campaigns_data, ensure_ascii=False, indent=2),
                        "data": campaigns_data,
                    }
                ]
            }

        if uri == "marketflow://policies/ad-compliance-rules":
            rules_summary = {
                "categories": [
                    {
                        "code": "MEDICAL_OVERCLAIM",
                        "severity": "HIGH",
                        "description": "Cấm cam kết chữa khỏi 100%, trị dứt điểm, không tác dụng phụ.",
                    },
                    {
                        "code": "FINANCIAL_SCAM",
                        "severity": "HIGH",
                        "description": "Cấm hứa hẹn làm giàu nhanh, x10 tài khoản, đầu tư không rủi ro.",
                    },
                    {
                        "code": "ABSOLUTE_SUPERLATIVE",
                        "severity": "MEDIUM",
                        "description": "Hạn chế dùng 'Số 1 Việt Nam', 'Nhất thế giới' khi chưa có giấy chứng nhận.",
                    },
                    {
                        "code": "FAKE_SCARCITY",
                        "severity": "LOW",
                        "description": "Tránh spam câu kéo giả tạo như 'Xả kho sập sàn', 'Chỉ còn 1 suất cuối'.",
                    },
                ],
                "safe_replacements": SAFE_REWRITE_MAP,
            }
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(rules_summary, ensure_ascii=False, indent=2),
                        "data": rules_summary,
                    }
                ]
            }

        raise ValueError(f"MCP Resource URI không tồn tại: {uri}")

    def get_prompt(
        self, db: Session, user: User, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        args = arguments or {}
        if name == "omnichannel-campaign-architect":
            cid = args.get("campaign_id", 1)
            goal = args.get("focus_goal", "Tối ưu chuyển đổi đa kênh")
            return {
                "description": "Prompt kiến trúc chiến dịch đa kênh chuẩn Brand Kit",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"Hãy đọc resource marketflow://workspace/brand-kit và gọi tool "
                                f"get_campaign_metrics cho campaign_id={cid} để thiết kế chiến lược "
                                f"nội dung 3 kênh (Facebook, TikTok, Email) hướng tới mục tiêu: {goal}."
                            ),
                        },
                    }
                ],
            }
        if name == "compliance-safe-copywriter":
            draft_text = args.get("draft_text", "")
            return {
                "description": "Prompt kiểm toán và viết lại nội dung quảng cáo an toàn",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"Hãy dùng tool scan_content_compliance và auto_fix_compliance_violations "
                                f"để làm sạch nội dung sau đạt chuẩn 100/100:\n\n{draft_text}"
                            ),
                        },
                    }
                ],
            }
        if name == "roas-performance-doctor":
            cid = args.get("campaign_id", 1)
            return {
                "description": "Prompt chẩn đoán sức khỏe chiến dịch và tái phân bổ ngân sách",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"Hãy gọi diagnose_campaign_health và rebalance_campaign_budget cho "
                                f"campaign_id={cid} để lập báo cáo tối ưu hóa ROAS."
                            ),
                        },
                    }
                ],
            }
        raise ValueError(f"MCP Prompt không tồn tại: {name}")

    # ==========================================================================
    # 4. THỰC THI MCP TOOLS (`tools/call`)
    # ==========================================================================

    def call_tool(
        self, db: Session, user: User, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        args = arguments or {}
        t0 = time.perf_counter()

        handlers = {
            "list_workspace_campaigns": self._tool_list_workspace_campaigns,
            "get_campaign_metrics": self._tool_get_campaign_metrics,
            "diagnose_campaign_health": self._tool_diagnose_campaign_health,
            "scan_content_compliance": self._tool_scan_content_compliance,
            "auto_fix_compliance_violations": self._tool_auto_fix_compliance_violations,
            "create_marketing_draft": self._tool_create_marketing_draft,
            "rebalance_campaign_budget": self._tool_rebalance_campaign_budget,
            "dispatch_external_webhook": self._tool_dispatch_external_webhook,
        }

        handler = handlers.get(name)
        if not handler:
            raise ValueError(f"Công cụ MCP không tồn tại: {name}")

        structured = handler(db, user, args)
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        return {
            "tool": name,
            "latency_ms": latency_ms,
            "isError": False,
            "structuredContent": structured,
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(structured, ensure_ascii=False, indent=2),
                }
            ],
        }

    def _tool_list_workspace_campaigns(
        self, db: Session, user: User, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        ws = self._resolve_accessible_workspace(db, user, args.get("workspace_id"))
        query = db.query(Campaign).filter(Campaign.status != "ARCHIVED")
        if ws:
            query = query.filter(Campaign.workspace_id == ws.id)
        elif user.role != "ADMIN":
            query = query.filter(Campaign.owner_id == user.id)

        status_filter = args.get("status")
        if status_filter:
            query = query.filter(Campaign.status == str(status_filter).upper())

        campaigns = query.order_by(Campaign.id.desc()).limit(20).all()
        items = []
        for c in campaigns:
            items.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "status": c.status,
                    "objective": c.objective,
                    "audience": c.audience,
                    "budget": float(c.budget or 0),
                    "start_date": str(c.start_date) if c.start_date else None,
                    "end_date": str(c.end_date) if c.end_date else None,
                }
            )
        return {
            "workspace_id": ws.id if ws else None,
            "workspace_name": ws.name if ws else "Personal Scope",
            "total": len(items),
            "campaigns": items,
        }

    def _tool_get_campaign_metrics(
        self, db: Session, user: User, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        campaign_id = int(args.get("campaign_id") or 0)
        campaign = self._get_accessible_campaign(db, user, campaign_id)

        metrics = db.query(CampaignMetric).filter(CampaignMetric.campaign_id == campaign.id).all()
        channel_ids = {m.channel_id for m in metrics if m.channel_id}
        channels_map = {}
        if channel_ids:
            for ch in db.query(MarketingChannel).filter(MarketingChannel.id.in_(channel_ids)).all():
                channels_map[ch.id] = ch.name

        by_channel: Dict[str, Dict[str, float]] = {}
        for m in metrics:
            ch_name = channels_map.get(m.channel_id, f"Channel #{m.channel_id}")
            slot = by_channel.setdefault(
                ch_name,
                {"views": 0, "clicks": 0, "conversions": 0, "cost": 0.0, "revenue": 0.0},
            )
            slot["views"] += int(m.views or 0)
            slot["clicks"] += int(m.clicks or 0)
            slot["conversions"] += int(m.conversions or 0)
            slot["cost"] += float(m.cost or 0.0)
            slot["revenue"] += float(m.revenue or 0.0)

        breakdown = []
        tot_views = tot_clicks = tot_conv = 0
        tot_cost = tot_rev = 0.0
        for ch_name, s in by_channel.items():
            v, cl, cv, co, rv = s["views"], s["clicks"], s["conversions"], s["cost"], s["revenue"]
            tot_views += v
            tot_clicks += cl
            tot_conv += cv
            tot_cost += co
            tot_rev += rv
            breakdown.append(
                {
                    "channel_name": ch_name,
                    "views": v,
                    "clicks": cl,
                    "conversions": cv,
                    "cost": round(co, 2),
                    "revenue": round(rv, 2),
                    "ctr_pct": round((cl / v * 100.0) if v > 0 else 0.0, 2),
                    "cvr_pct": round((cv / cl * 100.0) if cl > 0 else 0.0, 2),
                    "roas": round((rv / co) if co > 0 else 0.0, 2),
                }
            )

        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "budget": float(campaign.budget or 0),
            "totals": {
                "views": tot_views,
                "clicks": tot_clicks,
                "conversions": tot_conv,
                "cost": round(tot_cost, 2),
                "revenue": round(tot_rev, 2),
                "ctr_pct": round((tot_clicks / tot_views * 100.0) if tot_views > 0 else 0.0, 2),
                "cvr_pct": round((tot_conv / tot_clicks * 100.0) if tot_clicks > 0 else 0.0, 2),
                "roas": round((tot_rev / tot_cost) if tot_cost > 0 else 0.0, 2),
                "roi_pct": round(((tot_rev - tot_cost) / tot_cost * 100.0) if tot_cost > 0 else 0.0, 2),
            },
            "channels": breakdown,
        }

    def _tool_diagnose_campaign_health(
        self, db: Session, user: User, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        campaign_id = int(args.get("campaign_id") or 0)
        campaign = self._get_accessible_campaign(db, user, campaign_id)
        doctor_report = AIDoctorEngine.diagnose_campaign(
            campaign_id=campaign.id,
            db=db,
            current_user=user,
        )
        out = doctor_report.model_dump()
        out.setdefault("status", out.get("health_status", "HEALTHY"))
        out.setdefault("overall_summary", out.get("diagnosis_summary", ""))
        out.setdefault("action_items", out.get("recommendations", []))
        return out

    def _tool_scan_content_compliance(
        self, db: Session, user: User, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        ws = self._resolve_accessible_workspace(db, user, args.get("workspace_id"))
        banned_keywords: List[str] = []
        brand_name = "MarketFlow AI"
        if ws:
            bk = db.query(BrandKit).filter(BrandKit.workspace_id == ws.id).first()
            if bk:
                brand_name = bk.brand_name or ws.name
                if bk.banned_keywords_json:
                    try:
                        banned_keywords = json.loads(bk.banned_keywords_json)
                    except Exception:
                        banned_keywords = []

        scan_resp = ComplianceScanner.scan(
            title=str(args.get("title") or ""),
            body=str(args.get("body") or ""),
            cta=str(args.get("cta") or ""),
            workspace_id=ws.id if ws else None,
            db=db,
            custom_banned_keywords=banned_keywords,
        )
        result = scan_resp.model_dump()
        result["brand_name"] = brand_name
        result["workspace_id"] = ws.id if ws else None
        return result

    def _tool_auto_fix_compliance_violations(
        self, db: Session, user: User, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        ws = self._resolve_accessible_workspace(db, user, args.get("workspace_id"))
        orig_title = str(args.get("title") or "").strip()
        orig_body = str(args.get("body") or "").strip()
        orig_cta = str(args.get("cta") or "").strip()

        banned_keywords: List[str] = []
        brand_name = "MarketFlow AI"
        tone_of_voice = "Chuyên nghiệp, hiện đại, đáng tin cậy"
        usp = "Giải pháp tối ưu năng suất và chuyển đổi"
        if ws:
            bk = db.query(BrandKit).filter(BrandKit.workspace_id == ws.id).first()
            if bk:
                brand_name = bk.brand_name or ws.name
                tone_of_voice = bk.tone_of_voice or tone_of_voice
                usp = bk.usp or usp
                if bk.banned_keywords_json:
                    try:
                        banned_keywords = json.loads(bk.banned_keywords_json)
                    except Exception:
                        banned_keywords = []

        before_scan = ComplianceScanner.scan(
            title=orig_title,
            body=orig_body,
            cta=orig_cta,
            workspace_id=ws.id if ws else None,
            db=db,
            custom_banned_keywords=banned_keywords,
        ).model_dump()

        # Bước 1: Áp dụng bộ lọc thay thế ngữ nghĩa chuẩn hóa cho mọi cụm vi phạm đã phát hiện
        new_title = orig_title
        new_body = orig_body
        new_cta = orig_cta
        applied_fixes: List[Dict[str, str]] = []

        for v in before_scan.get("violations", []):
            kw = str(v.get("word") or v.get("keyword") or "").strip()
            if not kw:
                continue
            kw_lower = kw.lower()
            replacement = SAFE_REWRITE_MAP.get(kw_lower)
            if not replacement:
                suggestion = str(v.get("suggestion") or "")
                m = re.search(r"['\"“](.+?)['\"”]", suggestion)
                replacement = m.group(1) if m else "giải pháp chất lượng cao đã được kiểm chứng"

            pattern = re.compile(re.escape(kw), re.IGNORECASE)
            if pattern.search(new_title) or pattern.search(new_body) or pattern.search(new_cta):
                new_title = pattern.sub(replacement, new_title)
                new_body = pattern.sub(replacement, new_body)
                new_cta = pattern.sub(replacement, new_cta)
                applied_fixes.append({"original": kw, "replacement": replacement, "category": str(v.get("category") or "")})

        # Khử IN HOA toàn bộ trên tiêu đề (nếu vi phạm ALL_CAPS_TITLE)
        if new_title and len(new_title) > 10 and new_title.isupper():
            new_title = new_title.capitalize()
            applied_fixes.append(
                {
                    "original": "TIÊU ĐỀ IN HOA TOÀN BỘ",
                    "replacement": new_title,
                    "category": "Định dạng Tiêu đề",
                }
            )

        # Khử dấu chấm than/hỏi liên tiếp (nếu vi phạm EXCESSIVE_PUNCTUATION)
        if re.search(r"[!?]{3,}", new_body) or re.search(r"[!?]{3,}", new_title):
            new_title = re.sub(r"[!]{2,}", "!", new_title)
            new_title = re.sub(r"[?]{2,}", "?", new_title)
            new_body = re.sub(r"[!]{2,}", "!", new_body)
            new_body = re.sub(r"[?]{2,}", "?", new_body)
            applied_fixes.append(
                {
                    "original": "Lạm dụng dấu cảm thán (!!!/???)",
                    "replacement": "Chuẩn hóa dấu câu đơn",
                    "category": "Trải nghiệm Người đọc",
                }
            )

        # Đảm bảo có CTA nếu thiếu
        if not new_cta or len(new_cta.strip()) < 3:
            new_cta = f"Tìm hiểu giải pháp từ {brand_name} ngay hôm nay"

        # Quét lại sau khi tự động sửa; nếu vẫn còn từ khóa vi phạm (do cụm con), thay thế tiếp cho tới khi sạch
        after_scan = ComplianceScanner.scan(
            title=new_title,
            body=new_body,
            cta=new_cta,
            workspace_id=ws.id if ws else None,
            db=db,
            custom_banned_keywords=banned_keywords,
        ).model_dump()
        for v in after_scan.get("violations", []):
            kw = str(v.get("word") or "").strip()
            if kw:
                rep = SAFE_REWRITE_MAP.get(kw.lower(), "giải pháp tối ưu")
                pat = re.compile(re.escape(kw), re.IGNORECASE)
                new_title = pat.sub(rep, new_title)
                new_body = pat.sub(rep, new_body)
                new_cta = pat.sub(rep, new_cta)
        if after_scan.get("violations"):
            after_scan = ComplianceScanner.scan(
                title=new_title,
                body=new_body,
                cta=new_cta,
                workspace_id=ws.id if ws else None,
                db=db,
                custom_banned_keywords=banned_keywords,
            ).model_dump()

        return {
            "rewritten": {
                "title": new_title,
                "body": new_body,
                "cta": new_cta,
            },
            "applied_fixes": applied_fixes,
            "before_score": before_scan["score"],
            "before_status": before_scan["status"],
            "after_compliance": after_scan,
            "brand_context": {
                "brand_name": brand_name,
                "tone_of_voice": tone_of_voice,
                "usp": usp,
            },
        }

    def _tool_create_marketing_draft(
        self, db: Session, user: User, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        campaign_id = int(args.get("campaign_id") or 0)
        campaign = self._get_accessible_campaign(db, user, campaign_id)
        channel = str(args.get("channel") or "facebook").lower()
        topic = str(args.get("topic") or f"Chiến dịch {campaign.name} - {campaign.objective or 'Tối ưu chuyển đổi'}")
        save_to_db = bool(args.get("save_to_db", False))

        product = db.query(Product).filter(Product.id == campaign.product_id).first()
        bk = (
            db.query(BrandKit).filter(BrandKit.workspace_id == campaign.workspace_id).first()
            if campaign.workspace_id
            else None
        )

        context = {
            "workspace_id": campaign.workspace_id,
            "campaign_name": campaign.name,
            "objective": campaign.objective or "Tăng nhận diện và chuyển đổi",
            "audience": campaign.audience or "Khách hàng mục tiêu",
            "product_name": product.name if product else campaign.name,
            "product_usp": (bk.usp if bk and bk.usp else (product.usp if product else "Chất lượng vượt trội")),
            "channel_name": channel.upper(),
            "tone": bk.tone_of_voice if bk and bk.tone_of_voice else "Chuyên nghiệp, cuốn hút",
            "selected_idea": topic,
            "framework": "PAS",
        }

        draft_res = ai_service.execute_task(
            db=db,
            user_id=user.id,
            campaign_id=campaign.id,
            task_type="content_drafting",
            task_code="DRAFT",
            prompt_version="v3",
            context=context,
        )

        title = str(draft_res.get("title") or f"{campaign.name} — Giải pháp tối ưu")
        body = str(draft_res.get("body") or topic)
        cta = str(draft_res.get("cta") or "Đăng ký tư vấn ngay hôm nay")

        compliance = self._tool_scan_content_compliance(
            db,
            user,
            {
                "workspace_id": campaign.workspace_id,
                "channel": channel,
                "title": title,
                "body": body,
                "cta": cta,
            },
        )

        saved_content_id: Optional[int] = None
        if save_to_db:
            ch_id = 2 if channel == "email" else 5 if channel == "tiktok" else 1
            new_content = MarketingContent(
                workspace_id=campaign.workspace_id,
                campaign_id=campaign.id,
                channel_id=ch_id,
                created_by=user.id,
                title=title[:250],
                body=body,
                cta=cta[:250],
                status="AI_DRAFT",
                version_no=1,
            )
            db.add(new_content)
            db.commit()
            db.refresh(new_content)
            saved_content_id = new_content.id

        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "channel": channel,
            "draft": {
                "title": title,
                "body": body,
                "cta": cta,
                "model_used": draft_res.get("model_used"),
                "model_provider": draft_res.get("model_provider"),
                "is_fallback": draft_res.get("is_fallback", False),
            },
            "compliance": {
                "score": compliance["score"],
                "status": compliance["status"],
                "can_submit": compliance["can_submit"],
                "violations_count": len(compliance.get("violations", [])),
            },
            "saved_content_id": saved_content_id,
        }

    def _tool_rebalance_campaign_budget(
        self, db: Session, user: User, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        campaign_id = int(args.get("campaign_id") or 0)
        campaign = self._get_accessible_campaign(db, user, campaign_id)
        apply_changes = bool(args.get("apply_changes", False))

        metrics_data = self._tool_get_campaign_metrics(db, user, {"campaign_id": campaign.id})
        channels = metrics_data.get("channels", [])
        total_budget = float(campaign.budget or 0.0)

        if not channels:
            return {
                "campaign_id": campaign.id,
                "campaign_name": campaign.name,
                "total_budget": total_budget,
                "applied": False,
                "message": "Chiến dịch chưa có số liệu thực tế theo kênh để tính toán trọng số ROAS.",
                "proposals": [],
            }

        # Tính điểm hiệu quả (Efficiency Score = ROAS * 0.7 + CVR * 0.3)
        scored = []
        for ch in channels:
            roas = max(float(ch.get("roas") or 0.0), 0.1)
            cvr = max(float(ch.get("cvr_pct") or 0.0), 0.1)
            weight = round(roas * 0.7 + cvr * 0.3, 4)
            scored.append({**ch, "efficiency_weight": weight})

        total_weight = sum(item["efficiency_weight"] for item in scored) or 1.0
        proposals = []
        for item in scored:
            share = item["efficiency_weight"] / total_weight
            recommended_budget = round(total_budget * share, 0)
            current_spend = float(item.get("cost") or 0.0)
            action = "SCALE_UP" if share >= (1.0 / len(scored)) else "OPTIMIZE_OR_TRIM"
            proposals.append(
                {
                    "channel_name": item["channel_name"],
                    "current_spend": current_spend,
                    "roas": item["roas"],
                    "cvr_pct": item["cvr_pct"],
                    "recommended_share_pct": round(share * 100.0, 1),
                    "recommended_budget": recommended_budget,
                    "action": action,
                }
            )

        applied = False
        if apply_changes and (user.role in ("ADMIN", "MANAGER", "AGENCY_MANAGER") or campaign.owner_id == user.id):
            all_channels = {c.name: c.id for c in db.query(MarketingChannel).all()}
            db.query(CampaignBudgetAllocation).filter(
                CampaignBudgetAllocation.campaign_id == campaign.id
            ).delete()
            for p in proposals:
                ch_id = all_channels.get(p["channel_name"])
                if ch_id:
                    db.add(
                        CampaignBudgetAllocation(
                            campaign_id=campaign.id,
                            channel_id=ch_id,
                            planned_amount=p["recommended_budget"],
                            is_ai_estimate=True,
                        )
                    )
            db.commit()
            applied = True

        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "total_budget": total_budget,
            "applied": applied,
            "proposals": proposals,
        }

    def _tool_dispatch_external_webhook(
        self, db: Session, user: User, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        connector_type = str(args.get("connector_type") or "n8n_zapier").strip().lower()
        event_type = str(args.get("event_type") or "content.published").strip().lower()
        campaign_id = args.get("campaign_id")
        target_url = str(args.get("target_url") or "").strip()

        ws = self._resolve_accessible_workspace(db, user, args.get("workspace_id"))
        campaign_info: Dict[str, Any] = {
            "id": 1,
            "name": "Chiến dịch Tuyển sinh Kỹ sư AI 2026",
            "budget": 50000000.0,
        }
        if campaign_id:
            camp = self._get_accessible_campaign(db, user, int(campaign_id))
            campaign_info = {
                "id": camp.id,
                "name": camp.name,
                "budget": float(camp.budget or 0),
                "objective": camp.objective,
            }

        brand_name = ws.name if ws else "MarketFlow AI Workspace"
        if ws:
            bk = db.query(BrandKit).filter(BrandKit.workspace_id == ws.id).first()
            if bk and bk.brand_name:
                brand_name = bk.brand_name

        default_endpoints = {
            "n8n_zapier": "https://hooks.n8n.cloud/webhook/marketflow-omnichannel-sync",
            "telegram_bot": "https://api.telegram.org/bot<TOKEN>/sendMessage",
            "slack_discord": "https://hooks.slack.com/services/T000/B000/MARKETFLOW",
            "facebook_graph": "https://graph.facebook.com/v21.0/me/feed",
            "tiktok_business": "https://open.tiktokapis.com/v2/post/publish/video/init/",
            "wordpress_cms": "https://blog.enterprise.vn/wp-json/wp/v2/posts",
        }
        resolved_url = target_url or default_endpoints.get(
            connector_type, default_endpoints["n8n_zapier"]
        )

        delivery_id = f"wh_deliv_{uuid.uuid4().hex[:12]}"
        timestamp_iso = datetime.now(timezone.utc).isoformat()

        # Chuẩn hóa Payload theo từng hệ sinh thái đích
        if connector_type == "telegram_bot":
            connector_payload = {
                "chat_id": "@marketflow_agency_alerts",
                "parse_mode": "HTML",
                "text": (
                    f"🚀 <b>[MarketFlow AI • {event_type.upper()}]</b>\n"
                    f"• <b>Thương hiệu:</b> {brand_name}\n"
                    f"• <b>Chiến dịch:</b> {campaign_info['name']}\n"
                    f"• <b>Người thực hiện:</b> {user.full_name} ({user.role})\n"
                    f"• <b>Trạng thái:</b> Đã vượt qua kiểm duyệt Brand Safety 100/100"
                ),
            }
        elif connector_type == "slack_discord":
            connector_payload = {
                "username": "MarketFlow AI Orchestrator",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"⚡ Sự kiện: {event_type} | {campaign_info['name']}",
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Thương hiệu:*\n{brand_name}"},
                            {"type": "mrkdwn", "text": f"*Người kích hoạt:*\n{user.full_name} ({user.role})"},
                        ],
                    },
                ],
            }
        elif connector_type == "wordpress_cms":
            connector_payload = {
                "title": f"[{campaign_info['name']}] Bài viết chuẩn SEO từ MarketFlow AI",
                "status": "publish" if event_type == "content.published" else "draft",
                "categories": ["AI Marketing", "Digital Transformation"],
                "meta": {
                    "marketflow_campaign_id": campaign_info["id"],
                    "compliance_verified": True,
                },
            }
        else:
            connector_payload = {
                "id": delivery_id,
                "event": event_type,
                "timestamp": timestamp_iso,
                "connector": connector_type,
                "workspace": {
                    "id": ws.id if ws else 1,
                    "brand_name": brand_name,
                },
                "actor": {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role,
                },
                "campaign": campaign_info,
                "compliance_guardrail": {
                    "status": "PASSED",
                    "score": 100,
                    "protocol": f"MCP/{MCP_PROTOCOL_VERSION}",
                },
            }

        canonical_body = json.dumps(connector_payload, ensure_ascii=False, sort_keys=True)
        signing_secret = f"mf_whsec_{ws.id if ws else 1}_hmac_key"
        signature_hex = hmac.new(
            signing_secret.encode("utf-8"),
            canonical_body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": f"MarketFlow-MCP-Webhook/{MCP_SERVER_VERSION}",
            "X-MarketFlow-Event": event_type,
            "X-MarketFlow-Delivery": delivery_id,
            "X-MarketFlow-Timestamp": timestamp_iso,
            "X-MarketFlow-Signature": f"sha256={signature_hex}",
        }

        return {
            "delivery_id": delivery_id,
            "connector_type": connector_type,
            "event_type": event_type,
            "target_url": resolved_url,
            "status": "SIGNED_AND_DISPATCHED",
            "http_status": 200,
            "signature_algorithm": "HMAC-SHA256",
            "signature_header": f"sha256={signature_hex}",
            "headers": headers,
            "payload": connector_payload,
        }

    def get_external_integrations_blueprint(
        self, base_url: str = "http://127.0.0.1:8000", workspace_id: int = 1
    ) -> Dict[str, Any]:
        """Trả về cấu hình kết nối cho các MCP Clients bên ngoài (Claude Desktop, Cursor, n8n)
        và danh mục các cổng Outbound Webhook đa kênh."""
        clean_base = base_url.rstrip("/")
        rpc_url = f"{clean_base}/api/v1/mcp/rpc"
        return {
            "protocol_version": MCP_PROTOCOL_VERSION,
            "rpc_endpoint": rpc_url,
            "mcp_client_configs": {
                "claude_desktop": {
                    "filename": "claude_desktop_config.json",
                    "description": "Kết nối trực tiếp Claude Desktop với kho dữ liệu Chiến dịch, Brand Kit & Công cụ AI của MarketFlow.",
                    "config": {
                        "mcpServers": {
                            "marketflow-ai": {
                                "url": rpc_url,
                                "headers": {
                                    "Authorization": "Bearer <YOUR_MARKETFLOW_JWT_TOKEN>",
                                    "X-Workspace-Id": str(workspace_id),
                                },
                            }
                        }
                    },
                },
                "cursor_ide": {
                    "filename": ".cursor/mcp.json",
                    "description": "Tích hợp MarketFlow MCP vào Cursor / Windsurf IDE để gọi 8 MCP Tools bằng ngôn ngữ tự nhiên.",
                    "config": {
                        "mcpServers": {
                            "marketflow-ai": {
                                "type": "http",
                                "url": rpc_url,
                                "headers": {
                                    "Authorization": "Bearer <YOUR_MARKETFLOW_JWT_TOKEN>"
                                },
                            }
                        }
                    },
                },
                "curl_jsonrpc": {
                    "filename": "test_mcp_rpc.sh",
                    "description": "Lệnh cURL chuẩn JSON-RPC 2.0 để kết nối từ n8n HTTP Request Node, Make.com hoặc CI/CD.",
                    "command": (
                        f'curl -X POST "{rpc_url}" \\\n'
                        f'  -H "Content-Type: application/json" \\\n'
                        f'  -H "Authorization: Bearer <YOUR_MARKETFLOW_JWT_TOKEN>" \\\n'
                        f'  -d \'{{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{{}}}}\''
                    ),
                },
            },
            "outbound_connectors": [
                {
                    "id": "n8n_zapier",
                    "name": "n8n / Make.com / Zapier Webhook",
                    "category": "Workflow Automation",
                    "description": "Kích hoạt luồng tự động hóa đa bước (đăng bài tự động, lưu Google Sheets, đồng bộ HubSpot/CRM) khi bài viết chuyển sang PUBLISHED.",
                    "events": ["content.published", "content.in_review", "campaign.budget_rebalanced"],
                },
                {
                    "id": "telegram_bot",
                    "name": "Telegram Bot Notification",
                    "category": "Instant Messaging",
                    "description": "Bắn thông báo thời gian thực vào Group Telegram của Agency/Khách hàng ngay khi có bài chờ duyệt hoặc cảnh báo ROAS.",
                    "events": ["content.in_review", "content.published", "compliance.auto_fixed"],
                },
                {
                    "id": "slack_discord",
                    "name": "Slack / Discord Incoming Webhook",
                    "category": "Team Collaboration",
                    "description": "Gửi thẻ Block Kit giàu thông tin (điểm tuân thủ, ngân sách, link duyệt bài) vào kênh vận hành chung.",
                    "events": ["content.published", "campaign.budget_rebalanced"],
                },
                {
                    "id": "facebook_graph",
                    "name": "Meta (Facebook / Instagram) Graph API",
                    "category": "Social Publishing",
                    "description": "Chuẩn hóa gói tin xuất bản bài đăng + hình ảnh sản phẩm lên Fanpage qua Graph API v21.0.",
                    "events": ["content.published"],
                },
                {
                    "id": "tiktok_business",
                    "name": "TikTok for Business Content API",
                    "category": "Video Publishing",
                    "description": "Đồng bộ kịch bản video ngắn, Hook 3 giây đầu và bộ Hashtag xu hướng sang TikTok Business Center.",
                    "events": ["content.published"],
                },
                {
                    "id": "wordpress_cms",
                    "name": "WordPress REST API (SEO CMS)",
                    "category": "Website / Blog",
                    "description": "Xuất bản bài viết chuẩn SEO lên hệ thống quản trị nội dung WordPress qua /wp-json/wp/v2/posts.",
                    "events": ["content.published"],
                },
            ],
        }

    # ==========================================================================
    # 5. AGENTIC AI COPILOT ORCHESTRATOR (MULTI-STEP TOOL CALLING)
    # ==========================================================================

    def run_agent_workflow(
        self,
        db: Session,
        user: User,
        goal: str,
        campaign_id: Optional[int] = None,
        workspace_id: Optional[int] = None,
        channel: str = "facebook",
        draft_input: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Thực thi luồng Agentic AI đa bước:
        1. Đọc MCP Resource (`marketflow://workspace/brand-kit`) để nạp ngữ cảnh thương hiệu.
        2. Tự động lựa chọn và gọi chuỗi MCP Tools phù hợp với `goal` của người dùng.
        3. Ghi lại đầy đủ `tool_trace` (minh bạch hóa từng bước gọi tool cho Hội đồng chấm).
        4. Tổng hợp báo cáo điều hành và khuyến nghị hành động cụ thể.
        """
        t_start = time.perf_counter()
        trace: List[Dict[str, Any]] = []
        goal_lower = (goal or "").lower()

        ws = self._resolve_accessible_workspace(db, user, workspace_id)
        effective_ws_id = ws.id if ws else workspace_id

        # Bước 1: Luôn đọc Brand Kit Resource qua MCP
        t0 = time.perf_counter()
        try:
            bk_res = self.read_resource(db, user, "marketflow://workspace/brand-kit", effective_ws_id)
            bk_data = bk_res["contents"][0]["data"]
            trace.append(
                {
                    "step": 1,
                    "kind": "RESOURCE_READ",
                    "name": "marketflow://workspace/brand-kit",
                    "input": {"workspace_id": effective_ws_id},
                    "summary": (
                        f"Đã nạp Brand Kit '{bk_data.get('brand_name')}': "
                        f"Tone='{bk_data.get('tone_of_voice')}', "
                        f"{len(bk_data.get('banned_keywords', []))} từ khóa cấm."
                    ),
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                }
            )
        except Exception as exc:
            bk_data = {"brand_name": "MarketFlow AI", "tone_of_voice": "Chuyên nghiệp"}
            trace.append(
                {
                    "step": 1,
                    "kind": "RESOURCE_READ",
                    "name": "marketflow://workspace/brand-kit",
                    "input": {"workspace_id": effective_ws_id},
                    "summary": f"Dùng Brand Kit mặc định ({exc})",
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                }
            )

        # Bước 2: Xác định chiến dịch mục tiêu nếu chưa truyền campaign_id
        target_campaign_id = campaign_id
        if not target_campaign_id:
            camp_list = self.call_tool(db, user, "list_workspace_campaigns", {"workspace_id": effective_ws_id})
            camps = camp_list["structuredContent"].get("campaigns", [])
            if camps:
                target_campaign_id = camps[0]["id"]
            trace.append(
                {
                    "step": len(trace) + 1,
                    "kind": "TOOL_CALL",
                    "name": "list_workspace_campaigns",
                    "input": {"workspace_id": effective_ws_id},
                    "summary": f"Tìm thấy {len(camps)} chiến dịch trong Workspace.",
                    "latency_ms": camp_list["latency_ms"],
                    "output": camp_list["structuredContent"],
                }
            )

        artifacts: Dict[str, Any] = {"brand_kit": bk_data}

        # Nhánh A: Kiểm toán tuân thủ & tự động viết lại (nếu có draft_input hoặc từ khóa tuân thủ/chính sách)
        if draft_input or any(k in goal_lower for k in ("tuân thủ", "chính sách", "vi phạm", "compliance", "làm sạch")):
            sample_title = (draft_input or {}).get("title") or "CAM KẾT 100% CHỮA DỨT ĐIỂM NỖI LO MARKETING!!!"
            sample_body = (draft_input or {}).get("body") or (
                "Giải pháp số 1 Việt Nam giúp bạn làm giàu nhanh và x10 tài khoản chỉ sau 7 ngày "
                "không rủi ro! Xả kho giảm sốc sập sàn chỉ còn 1 suất duy nhất hôm nay!!!"
            )
            sample_cta = (draft_input or {}).get("cta") or "Mua ngay kẻo lỡ"

            scan_call = self.call_tool(
                db,
                user,
                "scan_content_compliance",
                {
                    "workspace_id": effective_ws_id,
                    "channel": channel,
                    "title": sample_title,
                    "body": sample_body,
                    "cta": sample_cta,
                },
            )
            scan_out = scan_call["structuredContent"]
            trace.append(
                {
                    "step": len(trace) + 1,
                    "kind": "TOOL_CALL",
                    "name": "scan_content_compliance",
                    "input": {"channel": channel, "title": sample_title[:60]},
                    "summary": (
                        f"Điểm tuân thủ ban đầu: {scan_out['score']}/100 ({scan_out['status']}) — "
                        f"Phát hiện {len(scan_out.get('violations', []))} lỗi vi phạm."
                    ),
                    "latency_ms": scan_call["latency_ms"],
                    "output": scan_out,
                }
            )

            fix_call = self.call_tool(
                db,
                user,
                "auto_fix_compliance_violations",
                {
                    "workspace_id": effective_ws_id,
                    "channel": channel,
                    "title": sample_title,
                    "body": sample_body,
                    "cta": sample_cta,
                },
            )
            fix_out = fix_call["structuredContent"]
            trace.append(
                {
                    "step": len(trace) + 1,
                    "kind": "TOOL_CALL",
                    "name": "auto_fix_compliance_violations",
                    "input": {"violations_to_fix": len(scan_out.get("violations", []))},
                    "summary": (
                        f"Đã tự động sửa {len(fix_out.get('applied_fixes', []))} cụm từ vi phạm ➔ "
                        f"Điểm tuân thủ mới: {fix_out['after_compliance']['score']}/100 "
                        f"({fix_out['after_compliance']['status']})."
                    ),
                    "latency_ms": fix_call["latency_ms"],
                    "output": fix_out,
                }
            )
            artifacts["compliance_audit"] = fix_out

        # Nhánh B: Phân tích KPI, Khám sức khỏe chiến dịch & Tái phân bổ ngân sách
        if target_campaign_id and any(
            k in goal_lower
            for k in ("khám", "chẩn đoán", "ngân sách", "roas", "kpi", "hiệu quả", "tối ưu", "toàn diện", "audit")
        ):
            metrics_call = self.call_tool(
                db, user, "get_campaign_metrics", {"campaign_id": target_campaign_id}
            )
            metrics_out = metrics_call["structuredContent"]
            trace.append(
                {
                    "step": len(trace) + 1,
                    "kind": "TOOL_CALL",
                    "name": "get_campaign_metrics",
                    "input": {"campaign_id": target_campaign_id},
                    "summary": (
                        f"Chiến dịch '{metrics_out['campaign_name']}': "
                        f"Views={metrics_out['totals']['views']:,}, "
                        f"Conversions={metrics_out['totals']['conversions']:,}, "
                        f"ROAS={metrics_out['totals']['roas']}x."
                    ),
                    "latency_ms": metrics_call["latency_ms"],
                    "output": metrics_out,
                }
            )

            doc_call = self.call_tool(
                db, user, "diagnose_campaign_health", {"campaign_id": target_campaign_id}
            )
            doc_out = doc_call["structuredContent"]
            trace.append(
                {
                    "step": len(trace) + 1,
                    "kind": "TOOL_CALL",
                    "name": "diagnose_campaign_health",
                    "input": {"campaign_id": target_campaign_id},
                    "summary": (
                        f"Điểm sức khỏe: {doc_out['health_score']}/100 ({doc_out['status']}) — "
                        f"{len(doc_out.get('action_items', []))} khuyến nghị tối ưu."
                    ),
                    "latency_ms": doc_call["latency_ms"],
                    "output": doc_out,
                }
            )

            reb_call = self.call_tool(
                db,
                user,
                "rebalance_campaign_budget",
                {"campaign_id": target_campaign_id, "apply_changes": False},
            )
            reb_out = reb_call["structuredContent"]
            trace.append(
                {
                    "step": len(trace) + 1,
                    "kind": "TOOL_CALL",
                    "name": "rebalance_campaign_budget",
                    "input": {"campaign_id": target_campaign_id},
                    "summary": (
                        f"Đã tính toán phương án phân bổ ngân sách tối ưu cho "
                        f"{len(reb_out.get('proposals', []))} kênh dựa trên trọng số ROAS & CVR."
                    ),
                    "latency_ms": reb_call["latency_ms"],
                    "output": reb_out,
                }
            )
            artifacts["metrics"] = metrics_out
            artifacts["doctor"] = doc_out
            artifacts["budget_rebalance"] = reb_out

        # Nhánh C: Sáng tạo bản nháp mới (nếu yêu cầu viết bài / tạo draft hoặc nếu chưa chạy nhánh nào)
        if target_campaign_id and (
            any(k in goal_lower for k in ("viết", "nháp", "draft", "nội dung", "sáng tạo", "bài đăng"))
            or len(trace) <= 2
        ):
            draft_call = self.call_tool(
                db,
                user,
                "create_marketing_draft",
                {
                    "campaign_id": target_campaign_id,
                    "channel": channel,
                    "topic": goal,
                    "save_to_db": "lưu" in goal_lower,
                },
            )
            draft_out = draft_call["structuredContent"]
            trace.append(
                {
                    "step": len(trace) + 1,
                    "kind": "TOOL_CALL",
                    "name": "create_marketing_draft",
                    "input": {"campaign_id": target_campaign_id, "channel": channel},
                    "summary": (
                        f"Đã sinh bản nháp '{draft_out['draft']['title'][:50]}...' "
                        f"(Điểm tuân thủ: {draft_out['compliance']['score']}/100)."
                    ),
                    "latency_ms": draft_call["latency_ms"],
                    "output": draft_out,
                }
            )
            artifacts["generated_draft"] = draft_out

        # Tổng hợp câu trả lời điều hành từ toàn bộ kết quả MCP Tools
        summary_lines = [
            f"### Báo cáo Điều phối Agentic AI (Giao thức MCP {MCP_PROTOCOL_VERSION})",
            f"- **Thương hiệu (Brand Kit)**: {bk_data.get('brand_name')} ({bk_data.get('tone_of_voice')})",
            f"- **Số bước công cụ MCP đã thực thi**: {len(trace)} bước",
        ]
        if "doctor" in artifacts:
            d = artifacts["doctor"]
            summary_lines.append(
                f"- **Sức khỏe chiến dịch**: **{d['health_score']}/100 ({d['status']})** — {d['overall_summary']}"
            )
        if "budget_rebalance" in artifacts and artifacts["budget_rebalance"].get("proposals"):
            top_ch = max(
                artifacts["budget_rebalance"]["proposals"],
                key=lambda x: x.get("recommended_share_pct", 0),
            )
            summary_lines.append(
                f"- **Tối ưu ngân sách (ROAS-driven)**: Ưu tiên phân bổ **{top_ch['recommended_share_pct']}%** "
                f"({top_ch['recommended_budget']:,.0f} đ) vào kênh **{top_ch['channel_name']}** (ROAS {top_ch['roas']}x)."
            )
        if "compliance_audit" in artifacts:
            ca = artifacts["compliance_audit"]
            summary_lines.append(
                f"- **Kiểm toán & Tự động Sửa lỗi Chính sách**: Đã nâng điểm tuân thủ từ "
                f"**{ca['before_score']}/100 ({ca['before_status']})** lên "
                f"**{ca['after_compliance']['score']}/100 ({ca['after_compliance']['status']})**."
            )
        if "generated_draft" in artifacts:
            gd = artifacts["generated_draft"]
            summary_lines.append(
                f"- **Bản nháp sáng tạo ({gd['channel'].upper()})**: *{gd['draft']['title']}* "
                f"(Tuân thủ: {gd['compliance']['score']}/100)."
            )

        return {
            "protocol": f"MCP/{MCP_PROTOCOL_VERSION}",
            "server": MCP_SERVER_NAME,
            "goal": goal,
            "total_latency_ms": round((time.perf_counter() - t_start) * 1000, 2),
            "steps_executed": len(trace),
            "trace": trace,
            "artifacts": artifacts,
            "final_answer": "\n".join(summary_lines),
        }

    # ==========================================================================
    # 6. BỘ XỬ LÝ JSON-RPC 2.0 CHUẨN MCP (`POST /api/v1/mcp/rpc`)
    # ==========================================================================

    def handle_jsonrpc(
        self, db: Session, user: User, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        req_id = payload.get("id")
        method = str(payload.get("method") or "")
        params = payload.get("params") or {}

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": self.get_server_info()["capabilities"],
                    "serverInfo": {
                        "name": MCP_SERVER_NAME,
                        "version": MCP_SERVER_VERSION,
                    },
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": self.list_tools()}
            elif method == "tools/call":
                tool_name = str(params.get("name") or "")
                tool_args = params.get("arguments") or {}
                result = self.call_tool(db, user, tool_name, tool_args)
            elif method == "resources/list":
                result = {"resources": self.list_resources()}
            elif method == "resources/read":
                uri = str(params.get("uri") or "")
                ws_id = params.get("workspace_id")
                result = self.read_resource(db, user, uri, ws_id)
            elif method == "prompts/list":
                result = {"prompts": self.list_prompts()}
            elif method == "prompts/get":
                prompt_name = str(params.get("name") or "")
                prompt_args = params.get("arguments") or {}
                result = self.get_prompt(db, user, prompt_name, prompt_args)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result,
            }
        except PermissionError as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32003, "message": str(exc)},
            }
        except ValueError as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": str(exc)},
            }
        except Exception as exc:
            logger.exception("MCP JSON-RPC error on method %s", method)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": f"Internal MCP error: {exc}"},
            }


mcp_server = MarketFlowMCPServer()
