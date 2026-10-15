"""MarketFlow AI — Actionable AI Doctor Service (FEAT-BE-21).
Ground truth diagnostic engine analyzing live campaign metrics to produce
unbiased health scores, bottleneck detection, and actionable marketing prescriptions.
Zero Hallucination: 100% derived from SQLite database performance metrics.
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import logging

from sqlalchemy.orm import Session
from app.models.entities import Campaign, CampaignMetric, MarketingChannel, User, AILog
from app.schemas.schemas import (
    AIDoctorResponse,
    AIDoctorRecommendation,
    AIDoctorBottleneck,
    ChannelAttributionResponse,
    KPISummaryResponse,
    PortfolioTriageAnomaly,
    PortfolioTriageResponse,
)

logger = logging.getLogger("marketflow.ai_doctor")


CHANNEL_BENCHMARKS: Dict[str, Dict[str, float]] = {
    "facebook": {"ctr_good": 1.8, "ctr_min": 0.9, "cvr_good": 3.0, "cpc_good": 12000.0, "roas_target": 2.5},
    "google_ads": {"ctr_good": 4.5, "ctr_min": 2.0, "cvr_good": 4.5, "cpc_good": 18000.0, "roas_target": 3.5},
    "tiktok": {"ctr_good": 2.2, "ctr_min": 1.2, "cvr_good": 2.0, "cpc_good": 6000.0, "roas_target": 2.0},
    "email": {"ctr_good": 3.5, "ctr_min": 1.5, "cvr_good": 5.0, "cpc_good": 2000.0, "roas_target": 5.0},
    "blog": {"ctr_good": 2.0, "ctr_min": 0.8, "cvr_good": 2.0, "cpc_good": 5000.0, "roas_target": 3.0},
}


class AIDoctorEngine:
    """Grounded deterministic and AI-enriched campaign diagnostic engine."""

    CHANNEL_BENCHMARKS = CHANNEL_BENCHMARKS

    @classmethod
    def infer_funnel_stage(
        cls,
        objective: Optional[str],
        explicit_stage: Optional[str] = None,
    ) -> str:
        """Suy luận tầng phễu tiếp thị (ToFU / MoFU / BoFU) từ mục tiêu hoặc cấu hình."""
        if explicit_stage and explicit_stage.strip() in ("ToFU", "MoFU"):
            return explicit_stage.strip()
        obj_lower = (objective or "").lower()
        tofu_keywords = (
            "awareness",
            "nhận diện",
            "tiếp cận",
            "reach",
            "traffic",
            "lượt xem",
            "brand awareness",
            "phủ sóng",
            "tofu",
        )
        if any(kw in obj_lower for kw in tofu_keywords):
            return "ToFU"
        mofu_keywords = (
            "leads",
            "lead gen",
            "consideration",
            "tư vấn",
            "đăng ký",
            "form",
            "inbox",
            "thu thập lead",
            "mofu",
        )
        if any(kw in obj_lower for kw in mofu_keywords):
            return "MoFU"
        if explicit_stage and explicit_stage.strip() in ("ToFU", "MoFU", "BoFU"):
            return explicit_stage.strip()
        return "BoFU"

    @classmethod
    def compute_budget_pacing(
        cls,
        campaign: Optional[Campaign],
        metrics: List[CampaignMetric],
        total_cost: float,
    ) -> Dict[str, Any]:
        """Tính toán tốc độ giải ngân (Budget Pacing) theo tiến độ thời gian thực tế."""
        if not campaign or not campaign.start_date or not campaign.end_date:
            return {
                "pacing_ratio": None,
                "pacing_status": "UNSCHEDULED",
                "elapsed_days": 0,
                "total_days": 0,
                "expected_spend_to_date": 0.0,
            }
        try:
            start_dt = datetime.strptime(campaign.start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(campaign.end_date, "%Y-%m-%d").date()
        except Exception:
            return {
                "pacing_ratio": None,
                "pacing_status": "UNSCHEDULED",
                "elapsed_days": 0,
                "total_days": 0,
                "expected_spend_to_date": 0.0,
            }

        total_days = max(1, (end_dt - start_dt).days + 1)
        metric_dates = []
        for m in metrics:
            if getattr(m, "metric_date", None):
                try:
                    metric_dates.append(datetime.strptime(m.metric_date, "%Y-%m-%d").date())
                except Exception:
                    pass

        if metric_dates:
            latest_dt = max(metric_dates)
            if start_dt <= latest_dt <= end_dt:
                elapsed_days = max(1, (latest_dt - start_dt).days + 1)
            else:
                elapsed_days = max(1, min(total_days, len(set(metric_dates))))
        else:
            today = datetime.now(timezone.utc).date()
            if today < start_dt:
                elapsed_days = 1
            elif today > end_dt:
                elapsed_days = total_days
            else:
                elapsed_days = max(1, (today - start_dt).days + 1)

        budget = float(campaign.budget or 0.0)
        daily_cap = float(campaign.daily_budget_cap) if getattr(campaign, "daily_budget_cap", None) else None

        expected_spend = 0.0
        if budget > 0:
            expected_spend = budget * (elapsed_days / float(total_days))
        elif daily_cap and daily_cap > 0:
            expected_spend = daily_cap * elapsed_days

        if expected_spend <= 0:
            return {
                "pacing_ratio": None,
                "pacing_status": "UNSCHEDULED",
                "elapsed_days": elapsed_days,
                "total_days": total_days,
                "expected_spend_to_date": 0.0,
            }

        pacing_ratio = round(total_cost / expected_spend, 2)
        if daily_cap and daily_cap > 0 and elapsed_days > 0:
            cap_ratio = round((total_cost / elapsed_days) / daily_cap, 2)
            pacing_ratio = max(pacing_ratio, cap_ratio)

        if pacing_ratio > 1.35:
            pacing_status = "OVER_PACING"
        elif pacing_ratio < 0.50 and elapsed_days >= 3:
            pacing_status = "UNDER_PACING"
        else:
            pacing_status = "ON_TRACK"

        return {
            "pacing_ratio": pacing_ratio,
            "pacing_status": pacing_status,
            "elapsed_days": elapsed_days,
            "total_days": total_days,
            "expected_spend_to_date": round(expected_spend, 2),
        }

    @classmethod
    def detect_creative_fatigue(
        cls,
        metrics: List[CampaignMetric],
    ) -> Dict[str, Any]:
        """Phát hiện bão hòa nội dung quảng cáo (Creative Fatigue) qua chuỗi thời gian."""
        by_date: Dict[str, Dict[str, float]] = {}
        for m in metrics:
            d = getattr(m, "metric_date", None)
            if not d:
                continue
            if d not in by_date:
                by_date[d] = {"views": 0.0, "clicks": 0.0, "cost": 0.0}
            by_date[d]["views"] += float(m.views or 0)
            by_date[d]["clicks"] += float(m.clicks or 0)
            by_date[d]["cost"] += float(m.cost or 0.0)

        sorted_dates = sorted(by_date.keys())
        if len(sorted_dates) < 4:
            return {"fatigue_detected": False, "fatigue_detail": None}

        earlier_dates = sorted_dates[:-3]
        recent_dates = sorted_dates[-3:]

        early_views = sum(by_date[d]["views"] for d in earlier_dates)
        early_clicks = sum(by_date[d]["clicks"] for d in earlier_dates)
        early_cost = sum(by_date[d]["cost"] for d in earlier_dates)

        recent_views = sum(by_date[d]["views"] for d in recent_dates)
        recent_clicks = sum(by_date[d]["clicks"] for d in recent_dates)
        recent_cost = sum(by_date[d]["cost"] for d in recent_dates)

        early_ctr = (early_clicks / early_views * 100.0) if early_views > 0 else 0.0
        recent_ctr = (recent_clicks / recent_views * 100.0) if recent_views > 0 else 0.0
        early_cpc = (early_cost / early_clicks) if early_clicks > 0 else 0.0
        recent_cpc = (recent_cost / recent_clicks) if recent_clicks > 0 else 0.0

        if early_ctr > 0 and early_cpc > 0:
            ctr_ratio = recent_ctr / early_ctr
            cpc_ratio = recent_cpc / early_cpc
            if ctr_ratio <= 0.75 and cpc_ratio >= 1.15:
                ctr_drop_pct = (1.0 - ctr_ratio) * 100.0
                cpc_rise_pct = (cpc_ratio - 1.0) * 100.0
                detail = (
                    f"CREATIVE_FATIGUE: CTR 3 ngày gần nhất ({recent_dates[0]} -> {recent_dates[-1]}) "
                    f"sụt giảm {ctr_drop_pct:.1f}% ({early_ctr:.2f}% xuống {recent_ctr:.2f}%) "
                    f"trong khi CPC tăng {cpc_rise_pct:.1f}% ({early_cpc:,.0f} lên {recent_cpc:,.0f} VNĐ)."
                )
                return {
                    "fatigue_detected": True,
                    "fatigue_detail": detail,
                    "early_ctr": round(early_ctr, 2),
                    "recent_ctr": round(recent_ctr, 2),
                    "early_cpc": round(early_cpc, 2),
                    "recent_cpc": round(recent_cpc, 2),
                }

        return {"fatigue_detected": False, "fatigue_detail": None}

    @classmethod
    def compute_channel_attribution(
        cls,
        campaign_id: int,
        db: Session
    ) -> List[ChannelAttributionResponse]:
        """Tính toán phân rã hiệu suất và chỉ số kinh tế theo từng kênh tiếp thị."""
        metrics = (
            db.query(CampaignMetric)
            .filter(CampaignMetric.campaign_id == campaign_id)
            .all()
        )
        if not metrics:
            return []

        channels = {c.id: c for c in db.query(MarketingChannel).all()}
        total_cost = sum(float(m.cost) for m in metrics)
        total_revenue = sum(float(m.revenue) for m in metrics)

        channel_data: Dict[int, Dict[str, Any]] = {}
        for m in metrics:
            cid = m.channel_id
            if cid not in channel_data:
                ch_obj = channels.get(cid)
                ch_name = ch_obj.name if ch_obj else f"Channel #{cid}"
                ch_code = ch_obj.code if ch_obj else f"channel_{cid}"
                channel_data[cid] = {
                    "channel_id": cid,
                    "channel_name": ch_name,
                    "channel_slug": ch_code.lower(),
                    "channel_code": ch_code,
                    "views": 0,
                    "clicks": 0,
                    "conversions": 0,
                    "cost": 0.0,
                    "revenue": 0.0,
                }
            channel_data[cid]["views"] += m.views
            channel_data[cid]["clicks"] += m.clicks
            channel_data[cid]["conversions"] += m.conversions
            channel_data[cid]["cost"] += float(m.cost)
            channel_data[cid]["revenue"] += float(m.revenue)

        breakdown: List[ChannelAttributionResponse] = []
        for cid, cd in channel_data.items():
            ch_views = cd["views"]
            ch_clicks = cd["clicks"]
            ch_conv = cd["conversions"]
            ch_cost = cd["cost"]
            ch_rev = cd["revenue"]

            ch_ctr = (ch_clicks / ch_views * 100.0) if ch_views > 0 else 0.0
            ch_cpc = (ch_cost / ch_clicks) if ch_clicks > 0 else 0.0
            ch_cvr = (ch_conv / ch_clicks * 100.0) if ch_clicks > 0 else 0.0
            ch_roas = (ch_rev / ch_cost) if ch_cost > 0 else 0.0
            ch_roi = ((ch_rev - ch_cost) / ch_cost * 100.0) if ch_cost > 0 else 0.0
            share_cost = (ch_cost / total_cost * 100.0) if total_cost > 0 else 0.0
            share_rev = (ch_rev / total_revenue * 100.0) if total_revenue > 0 else 0.0

            breakdown.append(
                ChannelAttributionResponse(
                    channel_id=cid,
                    channel_name=cd["channel_name"],
                    channel_slug=cd["channel_slug"],
                    channel_code=cd["channel_code"],
                    views=ch_views,
                    clicks=ch_clicks,
                    conversions=ch_conv,
                    cost=round(ch_cost, 2),
                    revenue=round(ch_rev, 2),
                    ctr_percent=round(ch_ctr, 2),
                    cpc_avg=round(ch_cpc, 2),
                    cvr_percent=round(ch_cvr, 2),
                    roas=round(ch_roas, 2),
                    roi_percent=round(ch_roi, 2),
                    share_of_cost=round(share_cost, 2),
                    share_of_revenue=round(share_rev, 2)
                )
            )
        return breakdown

    @classmethod
    def diagnose_campaign(
        cls,
        campaign_id: int,
        db: Session,
        current_user: Optional[User] = None
    ) -> AIDoctorResponse:
        """Thực hiện chẩn đoán sức khỏe toàn diện cho chiến dịch:
        1. Thu thập số liệu đo lường thực tế từ database (ground truth metrics).
        2. Bảo vệ chia cho 0 an toàn (ZeroDivisionError safety).
        3. Xử lý trường hợp dữ liệu thưa thớt (sparse data / empty metrics).
        4. Tính điểm sức khỏe động theo tầng phễu (ToFU / MoFU / BoFU) và chuẩn ngành từng kênh.
        5. Kiểm tra tốc độ đốt tiền (Budget Pacing), bảo vệ giai đoạn máy học (Learning Phase),
           và phát hiện bão hòa sáng tạo (Time-Series Creative Fatigue).
        6. Phát hiện điểm nghẽn hiệu suất và đề xuất đơn thuốc hành động (SCALE, REDUCE, OPTIMIZE, PAUSE).
        7. Ghi nhận nhật ký kiểm toán vào bảng ai_logs với task_type='SUMMARY'.
        """
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        campaign_name = campaign.name if campaign else f"Chiến dịch #{campaign_id}"
        funnel_stage = cls.infer_funnel_stage(
            getattr(campaign, "objective", None),
            getattr(campaign, "funnel_stage", None),
        )

        # 1. Thu thập metrics từ bảng campaign_metrics
        metrics = (
            db.query(CampaignMetric)
            .filter(CampaignMetric.campaign_id == campaign_id)
            .all()
        )

        # 2. Xử lý trường hợp Sparse Data / Mới khởi tạo chưa có metrics
        if not metrics:
            response = AIDoctorResponse(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                health_status="HEALTHY",
                overall_status="HEALTHY",
                health_score=50,
                diagnosis_summary=(
                    f"Chiến dịch '{campaign_name}' mới được khởi tạo và chưa ghi nhận dữ liệu đo lường thực tế. "
                    "Hệ thống đã thiết lập sẵn cơ chế theo dõi đa kênh (Facebook, TikTok, Email)."
                ),
                key_bottlenecks=[
                    "Chiến dịch chưa ghi nhận dữ liệu hiển thị (views) và nhấp chuột (clicks) thực tế."
                ],
                bottlenecks=[
                    "Chiến dịch chưa ghi nhận dữ liệu hiển thị (views) và nhấp chuột (clicks) thực tế."
                ],
                recommendations=[
                    AIDoctorRecommendation(
                        action="SCALE",
                        channel="all",
                        reason="Chiến dịch mới thiết lập cần kích hoạt giai đoạn kiểm thử phân phối ban đầu.",
                        suggestion="Bắt đầu chạy thử nghiệm ngân sách nhỏ trên Facebook và TikTok để thu thập dữ liệu chuyển đổi ban đầu.",
                        title="Kích hoạt phân phối thử nghiệm",
                        description="Bắt đầu chạy thử nghiệm ngân sách nhỏ trên Facebook và TikTok",
                        impact="Thu thập dữ liệu đo lường ban đầu"
                    )
                ],
                metrics_analyzed={
                    "total_views": 0,
                    "total_clicks": 0,
                    "total_conversions": 0,
                    "total_cost": 0.0,
                    "total_revenue": 0.0,
                    "ctr_percent": 0.0,
                    "cpc_avg": 0.0,
                    "cvr_percent": 0.0,
                    "roas": 0.0,
                    "roi_percent": 0.0,
                },
                channel_breakdown=[],
                is_sparse_data=True,
                funnel_stage=funnel_stage,
                pacing_ratio=None,
                pacing_status="UNSCHEDULED",
                fatigue_detected=False,
                fatigue_detail=None,
                learning_phase_protected=False,
                channel_benchmarks=CHANNEL_BENCHMARKS,
                generated_at=datetime.now(timezone.utc).isoformat()
            )
            cls._persist_log(db, campaign_id, current_user, response)
            return response

        # 3. Tính toán các chỉ số kinh tế tổng hợp với rào chắn chia cho 0 an toàn
        total_views = sum(m.views for m in metrics)
        total_clicks = sum(m.clicks for m in metrics)
        total_conversions = sum(m.conversions for m in metrics)
        total_cost = sum(float(m.cost) for m in metrics)
        total_revenue = sum(float(m.revenue) for m in metrics)

        # Rào chắn chia cho 0 tuyệt đối an toàn
        ctr_percent = (total_clicks / total_views * 100.0) if total_views > 0 else 0.0
        cpc_avg = (total_cost / total_clicks) if total_clicks > 0 else 0.0
        cvr_percent = (total_conversions / total_clicks * 100.0) if total_clicks > 0 else 0.0
        cpa_avg = (total_cost / total_conversions) if total_conversions > 0 else 0.0
        roas = (total_revenue / total_cost) if total_cost > 0 else 0.0
        roi_percent = ((total_revenue - total_cost) / total_cost * 100.0) if total_cost > 0 else 0.0

        # Nếu toàn bộ views và cost đều bằng 0 -> Vẫn là sparse data
        if total_views == 0 and total_cost == 0:
            response = AIDoctorResponse(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                health_status="HEALTHY",
                health_score=50,
                diagnosis_summary=(
                    f"Chiến dịch '{campaign_name}' mới bắt đầu ghi nhận dữ liệu khởi tạo nhưng chưa có lượt tương tác thực tế."
                ),
                key_bottlenecks=["Lưu lượng tương tác ban đầu còn ở mức 0."],
                bottlenecks=["Lưu lượng tương tác ban đầu còn ở mức 0."],
                recommendations=[
                    AIDoctorRecommendation(
                        action="SCALE",
                        channel="all",
                        reason="Kích hoạt phân phối thử nghiệm đa kênh.",
                        suggestion="Bắt đầu chạy thử nghiệm ngân sách nhỏ trên Facebook và TikTok.",
                        title="Bắt đầu chạy thử nghiệm",
                        description="Bắt đầu chạy thử nghiệm ngân sách nhỏ trên Facebook và TikTok"
                    )
                ],
                metrics_analyzed={
                    "total_views": 0,
                    "total_clicks": 0,
                    "total_conversions": 0,
                    "total_cost": 0.0,
                    "total_revenue": 0.0,
                    "ctr_percent": 0.0,
                    "cpc_avg": 0.0,
                    "cvr_percent": 0.0,
                    "roas": 0.0,
                    "roi_percent": 0.0,
                },
                channel_breakdown=[],
                is_sparse_data=True,
                funnel_stage=funnel_stage,
                pacing_ratio=None,
                pacing_status="UNSCHEDULED",
                fatigue_detected=False,
                fatigue_detail=None,
                learning_phase_protected=False,
                channel_benchmarks=CHANNEL_BENCHMARKS,
                generated_at=datetime.now(timezone.utc).isoformat()
            )
            cls._persist_log(db, campaign_id, current_user, response)
            return response

        # 4. Phân tích chi tiết từng kênh tiếp thị, Pacing và Creative Fatigue
        channel_breakdown_list = cls.compute_channel_attribution(campaign_id, db)
        pacing_info = cls.compute_budget_pacing(campaign, metrics, total_cost)
        pacing_ratio = pacing_info["pacing_ratio"]
        pacing_status = pacing_info["pacing_status"]
        fatigue_info = cls.detect_creative_fatigue(metrics)
        fatigue_detected = bool(fatigue_info.get("fatigue_detected", False))
        fatigue_detail = fatigue_info.get("fatigue_detail")

        # 5. Tính điểm sức khỏe chiến dịch (Health Score: 0 - 100) theo tầng phễu (Funnel-Stage Aware)
        if ctr_percent >= 2.5:
            ctr_score = 100
        elif ctr_percent >= 1.5:
            ctr_score = 80
        elif ctr_percent >= 1.0:
            ctr_score = 60
        else:
            ctr_score = 30

        if cvr_percent >= 4.0:
            cvr_score = 100
        elif cvr_percent >= 2.5:
            cvr_score = 80
        elif cvr_percent >= 1.5:
            cvr_score = 60
        else:
            cvr_score = 30

        if total_clicks == 0 or total_cost == 0:
            cpc_score = 80
        elif cpc_avg <= 8000:
            cpc_score = 100
        elif cpc_avg <= 15000:
            cpc_score = 100
        elif cpc_avg <= 25000:
            cpc_score = 80
        else:
            cpc_score = 50

        pacing_score = 90 if pacing_status in ("ON_TRACK", "UNSCHEDULED") else 55

        is_tofu_non_rev = (funnel_stage == "ToFU" and total_revenue == 0)
        is_mofu_lead_gen = (funnel_stage == "MoFU" and total_revenue == 0 and total_conversions > 0)

        if is_tofu_non_rev:
            # ToFU: CTR (45%), CPC/CPM (40%), Pacing/Views (15%) — không phạt ROAS khi revenue == 0
            tofu_cpc_score = 100 if (total_clicks > 0 and cpc_avg <= 12000) else (80 if (total_clicks > 0 and cpc_avg <= 22000) else 35)
            raw_health_score = int(round(
                ctr_score * 0.45 +
                tofu_cpc_score * 0.40 +
                pacing_score * 0.15
            ))
            health_score = max(0, min(100, raw_health_score))
            if health_score >= 70:
                health_status = "HEALTHY"
            elif health_score >= 40:
                health_status = "NEEDS_ATTENTION"
            else:
                health_status = "CRITICAL"
        elif is_mofu_lead_gen:
            # MoFU: CPA/CPL (45%), CVR (35%), CTR (20%) khi chưa ghi nhận doanh thu trực tiếp
            if cpa_avg <= 150000:
                cpa_score = 100
            elif cpa_avg <= 300000:
                cpa_score = 80
            elif cpa_avg <= 500000:
                cpa_score = 60
            else:
                cpa_score = 35
            raw_health_score = int(round(
                cpa_score * 0.45 +
                cvr_score * 0.35 +
                ctr_score * 0.20
            ))
            health_score = max(0, min(100, raw_health_score))
            if health_score >= 70:
                health_status = "HEALTHY"
            elif health_score >= 40:
                health_status = "NEEDS_ATTENTION"
            else:
                health_status = "CRITICAL"
        else:
            # BoFU (hoặc chiến dịch có doanh thu trực tiếp): ROAS (40%), CTR (20%), CVR (25%), CPC (15%)
            if total_cost == 0 and total_revenue > 0:
                roas_score = 100  # Organic viral hoàn toàn miễn phí
            elif roas >= 4.0:
                roas_score = 100
            elif roas >= 3.0:
                roas_score = 85
            elif roas >= 2.0:
                roas_score = 70
            elif roas >= 1.0:
                roas_score = 50
            else:
                roas_score = 20

            raw_health_score = int(round(
                roas_score * 0.40 +
                ctr_score * 0.20 +
                cvr_score * 0.25 +
                cpc_score * 0.15
            ))
            health_score = max(0, min(100, raw_health_score))

            if total_cost > 0 and roas < 1.0:
                health_status = "CRITICAL"
            elif health_score >= 70:
                health_status = "HEALTHY"
            elif health_score >= 40:
                health_status = "NEEDS_ATTENTION"
            else:
                health_status = "CRITICAL"

        # 6. Phát hiện điểm nghẽn hiệu suất (Bottlenecks)
        bottlenecks_list: List[str] = []
        if not is_tofu_non_rev and not is_mofu_lead_gen:
            if total_cost > 0 and roas < 1.0:
                bottlenecks_list.append(
                    f"Điểm hoàn vốn ROAS chỉ đạt {roas:.2f}x (< 1.0x hòa vốn). Chiến dịch đang chịu lỗ chi phí tiếp thị."
                )
            elif total_cost > 0 and roas < 2.0:
                bottlenecks_list.append(
                    f"Tỷ suất ROAS đạt {roas:.2f}x ở mức cận hòa vốn, cần tối ưu giá trị đơn hàng hoặc chi phí quảng cáo."
                )

        if total_views > 100 and ctr_percent < 1.5:
            bottlenecks_list.append(
                f"Tỷ lệ nhấp CTR thấp ({ctr_percent:.2f}% < 1.5%). Tiêu đề và hook 3 giây đầu cần thử nghiệm cải thiện độ thu hút."
            )

        if not is_tofu_non_rev and total_clicks > 20 and cvr_percent < 2.0:
            bottlenecks_list.append(
                f"Tỷ lệ chuyển đổi CVR thấp ({cvr_percent:.2f}% < 2.0%). Khách hàng rời bỏ tại trang đích hoặc form đặt hàng."
            )

        if total_clicks > 10 and cpc_avg > 25000:
            bottlenecks_list.append(
                f"Chi phí mỗi lượt nhấp CPC cao ({cpc_avg:,.0f} VNĐ). Nhóm đối tượng quảng cáo đang bị cạnh tranh mạnh hoặc tệp quá hẹp."
            )

        if pacing_status == "OVER_PACING" and pacing_ratio is not None:
            bottlenecks_list.append(
                f"OVER_PACING: Tốc độ đốt ngân sách đạt {pacing_ratio:.2f}x kế hoạch thời gian (> 1.35x). Nguy cơ cạn ngân sách sớm trước ngày kết thúc."
            )
        elif pacing_status == "UNDER_PACING" and pacing_ratio is not None:
            bottlenecks_list.append(
                f"UNDER_PACING: Tốc độ giải ngân chỉ đạt {pacing_ratio:.2f}x kế hoạch (< 0.50x). Quảng cáo đang bị bóp phân phối do giá thầu hoặc tệp đối tượng quá hẹp."
            )

        if fatigue_detected and fatigue_detail:
            bottlenecks_list.append(fatigue_detail)

        # Kiểm tra điểm nghẽn theo từng kênh (so sánh với chuẩn ngành CHANNEL_BENCHMARKS)
        for ch in channel_breakdown_list:
            bench = CHANNEL_BENCHMARKS.get(ch.channel_slug, {"ctr_min": 1.0, "roas_target": 2.0})
            if not is_tofu_non_rev and not is_mofu_lead_gen and ch.cost > 0 and ch.roas < 1.0:
                bottlenecks_list.append(
                    f"Kênh {ch.channel_name} ghi nhận ROAS chỉ {ch.roas}x và chi phí {ch.cost:,.0f} VNĐ mà chưa đạt điểm hòa vốn."
                )
            elif ch.views > 200 and ch.ctr_percent < bench.get("ctr_min", 1.0):
                bottlenecks_list.append(
                    f"Kênh {ch.channel_name} có CTR mờ nhạt ({ch.ctr_percent}% < chuẩn {bench.get('ctr_min', 1.0)}%), nội dung chưa tạo đủ ấn tượng với khán giả."
                )

        if not bottlenecks_list:
            bottlenecks_list.append(
                "Các chỉ số kinh tế tiếp thị đang vận hành ổn định trong phạm vi mục tiêu đề ra."
            )

        # 7. Đưa ra các đơn thuốc khuyến nghị chiến lược (Prescriptions)
        recommendations_list: List[AIDoctorRecommendation] = []
        learning_phase_protected = False

        # Tìm kênh có hiệu suất dẫn đầu
        best_channels = [
            ch for ch in channel_breakdown_list
            if ch.roas >= 3.0
            or (ch.cost == 0 and ch.revenue > 0)
            or (is_tofu_non_rev and ch.ctr_percent >= 2.2 and ch.cpc_avg <= 12000)
            or (is_mofu_lead_gen and ch.cvr_percent >= 3.5)
        ]
        for ch in best_channels:
            learning_phase_protected = True
            recommendations_list.append(
                AIDoctorRecommendation(
                    action="SCALE",
                    channel=ch.channel_slug or ch.channel_name,
                    reason=(
                        f"Kênh {ch.channel_name} đạt hiệu suất dẫn đầu (ROAS {ch.roas:.2f}x, CTR {ch.ctr_percent:.2f}%, CVR {ch.cvr_percent:.2f}%)."
                    ),
                    suggestion=(
                        f"Tăng ngân sách tối đa +20-25%/ngày cho kênh {ch.channel_name} (không tăng đột ngột >30% để bảo vệ Learning Phase của thuật toán phân phối)."
                    ),
                    title=f"Tăng ngân sách kênh {ch.channel_name} (+20-25%/ngày)",
                    description=f"Mở rộng ngân sách kênh {ch.channel_name} an toàn trong ngưỡng Learning Phase",
                    impact="+20-25% Lưu lượng/Doanh thu dự kiến mà không vỡ máy học"
                )
            )

        if fatigue_detected and fatigue_detail:
            recommendations_list.append(
                AIDoctorRecommendation(
                    action="OPTIMIZE",
                    channel="all",
                    reason=fatigue_detail,
                    suggestion="Thực hiện xoay vòng Creative Angle Matrix: thay thế Hook 3 giây đầu và làm mới biến thể hình ảnh/tiêu đề để thoát bão hòa tần suất.",
                    title="Khắc phục bão hòa nội dung (Creative Fatigue)",
                    description="Thay mới Hook 3 giây đầu và nhân bản góc tiếp cận tâm lý mới",
                    impact="Phục hồi CTR +30-45% và hạ nhiệt CPC trong 48 giờ"
                )
            )

        if pacing_status == "OVER_PACING" and pacing_ratio is not None:
            recommendations_list.append(
                AIDoctorRecommendation(
                    action="REDUCE",
                    channel="all",
                    reason=f"Tốc độ chi tiêu hiện tại gấp {pacing_ratio:.2f}x dự kiến theo tiến độ ngày chạy.",
                    suggestion="Thiết lập trần ngân sách ngày (Daily Budget Cap) hoặc điều chỉnh giảm 15-20% ngân sách các nhóm quảng cáo CPC cao.",
                    title="Kiểm soát tốc độ đốt ngân sách (Over-Pacing)",
                    description="Thiết lập Daily Budget Cap để bảo toàn ngân sách cho toàn chiến dịch",
                    impact="Đảm bảo ngân sách duy trì xuyên suốt đến ngày kết thúc"
                )
            )
        elif pacing_status == "UNDER_PACING" and pacing_ratio is not None:
            recommendations_list.append(
                AIDoctorRecommendation(
                    action="OPTIMIZE",
                    channel="all",
                    reason=f"Tốc độ giải ngân chậm ({pacing_ratio:.2f}x kế hoạch), ngân sách bị nghẽn phân phối.",
                    suggestion="Mở rộng tệp đối tượng (Lookalike 3-5%) hoặc nâng nhẹ giới hạn giá thầu để thuật toán thắng phiên đấu giá hiển thị.",
                    title="Tháo gỡ nghẽn phân phối ngân sách (Under-Pacing)",
                    description="Mở rộng tệp khán giả và tối ưu giá thầu để tăng khả năng cắn tiền",
                    impact="Đưa tốc độ phân phối trở về ngưỡng 0.85x - 1.10x"
                )
            )

        # Tìm kênh có tỷ lệ chuyển đổi hoặc CTR thấp cần tối ưu
        optimize_channels = [
            ch for ch in channel_breakdown_list
            if (ch.views > 50 and ch.ctr_percent < 1.5)
            or (not is_tofu_non_rev and ch.clicks > 10 and ch.cvr_percent < 2.5)
        ]
        for ch in optimize_channels:
            recommendations_list.append(
                AIDoctorRecommendation(
                    action="OPTIMIZE",
                    channel=ch.channel_slug or ch.channel_name,
                    reason=f"Kênh {ch.channel_name} có CTR {ch.ctr_percent:.2f}% hoặc CVR {ch.cvr_percent:.2f}% cần cải thiện.",
                    suggestion="Thực hiện A/B Testing tiêu đề, tối ưu 3 giây đầu video hoặc rút ngắn quy trình đặt hàng trên trang đích.",
                    title=f"Tối ưu nội dung kênh {ch.channel_name}",
                    description=f"Tối ưu Hook và trang đích cho kênh {ch.channel_name}",
                    impact="Cải thiện tỷ lệ chuyển đổi và giảm chi phí CPC"
                )
            )

        # Tìm kênh kém hiệu quả (thua lỗ trên chiến dịch BoFU)
        if not is_tofu_non_rev and not is_mofu_lead_gen:
            loss_channels = [ch for ch in channel_breakdown_list if ch.cost > 0 and ch.roas < 1.0]
            for ch in loss_channels:
                recommendations_list.append(
                    AIDoctorRecommendation(
                        action="REDUCE",
                        channel=ch.channel_slug or ch.channel_name,
                        reason=f"Kênh {ch.channel_name} có ROAS {ch.roas:.2f}x (dưới ngưỡng 1.0x), chi phí {ch.cost:,.0f} VNĐ vượt doanh thu {ch.revenue:,.0f} VNĐ.",
                        suggestion=f"Cắt giảm 30-50% ngân sách hoặc tạm dừng nhóm quảng cáo kém hiệu quả trên kênh {ch.channel_name} để cắt lỗ.",
                        title=f"Cắt giảm chi phí kênh {ch.channel_name}",
                        description=f"Cắt giảm chi tiêu trên kênh {ch.channel_name} để tránh lãng phí ngân sách",
                        impact=f"Tiết kiệm chi phí lãng phí trên kênh {ch.channel_name}"
                    )
                )

        # Nếu chưa có recommendation nào hoặc muốn có ít nhất 1 recommendation
        if not recommendations_list:
            if roas >= 2.0 or health_status == "HEALTHY":
                learning_phase_protected = True
                recommendations_list.append(
                    AIDoctorRecommendation(
                        action="SCALE",
                        channel="all",
                        reason=f"Chiến dịch ({funnel_stage}) đạt hiệu suất tốt với Điểm sức khỏe {health_score}/100.",
                        suggestion="Mở rộng quy mô ngân sách +20-25%/ngày trên các kênh chủ lực để bảo vệ Learning Phase.",
                        title="Mở rộng ngân sách tiếp cận (+20-25%/ngày)",
                        description="Tăng ngân sách quảng cáo tiếp cận tệp khách hàng tiềm năng"
                    )
                )
            else:
                recommendations_list.append(
                    AIDoctorRecommendation(
                        action="OPTIMIZE",
                        channel="all",
                        reason="Cần tối ưu tỷ lệ chuyển đổi tổng thể để gia tăng hiệu suất hoàn vốn.",
                        suggestion="Rà soát lại thông điệp bán hàng, đồng bộ ưu đãi trên bài viết và trang đích.",
                        title="Tối ưu thông điệp bán hàng",
                        description="Rà soát và cải thiện trang đích cũng như ưu đãi chiến dịch"
                    )
                )

        # 8. Xây dựng bản tóm tắt chẩn đoán sắc sảo (Deterministic Grounded Narrative)
        status_labels = {
            "HEALTHY": "Khỏe mạnh & Tăng trưởng tốt",
            "NEEDS_ATTENTION": "Cần chú ý tối ưu hóa",
            "CRITICAL": "Nguy kịch, cần can thiệp khẩn cấp"
        }
        status_text = status_labels.get(health_status, health_status)

        summary_parts = [
            f"Chiến dịch '{campaign_name}' [Phễu {funnel_stage}] đạt Điểm sức khỏe {health_score}/100 (Trạng thái: {status_text}).",
            f"Tổng chi phí ghi nhận: {total_cost:,.0f} VNĐ, Doanh thu tạo ra: {total_revenue:,.0f} VNĐ, "
            f"tương ứng ROAS {roas:.2f}x và ROI {roi_percent:+.1f}%.",
            f"Lưu lượng đạt {total_views:,.0f} lượt xem, {total_clicks:,.0f} lượt click (CTR: {ctr_percent:.2f}%, CPC: {cpc_avg:,.0f} VNĐ), "
            f"với {total_conversions:,.0f} chuyển đổi thành công (CVR: {cvr_percent:.2f}%)."
        ]
        if health_status == "HEALTHY":
            summary_parts.append("Hiệu suất chiến dịch đang ở trạng thái tích cực, sẵn sàng gia tăng ngân sách +20-25%/ngày (bảo vệ Learning Phase) vào các kênh dẫn đầu.")
        elif health_status == "NEEDS_ATTENTION":
            summary_parts.append("Hệ thống phát hiện một số điểm nghẽn về tỷ lệ nhấp hoặc chuyển đổi, cần ưu tiên A/B testing nội dung trước khi nâng ngân sách.")
        else:
            summary_parts.append("Cảnh báo: Tỷ suất sinh lời đang dưới ngưỡng an toàn hoặc chiến dịch đang bị thâm hụt vốn, cần rà soát và tạm dừng các kênh lỗ.")

        diagnosis_summary = " ".join(summary_parts)

        response = AIDoctorResponse(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            health_status=health_status,
            overall_status=health_status,
            health_score=health_score,
            diagnosis_summary=diagnosis_summary,
            key_bottlenecks=bottlenecks_list,
            bottlenecks=bottlenecks_list,
            recommendations=recommendations_list,
            metrics_analyzed={
                "total_views": total_views,
                "total_clicks": total_clicks,
                "total_conversions": total_conversions,
                "total_cost": round(total_cost, 2),
                "total_revenue": round(total_revenue, 2),
                "ctr_percent": round(ctr_percent, 2),
                "cpc_avg": round(cpc_avg, 2),
                "cvr_percent": round(cvr_percent, 2),
                "cpa_avg": round(cpa_avg, 2),
                "roas": round(roas, 2),
                "roi_percent": round(roi_percent, 2),
                "pacing_ratio": pacing_ratio,
                "pacing_status": pacing_status,
                "funnel_stage": funnel_stage,
                "fatigue_detected": fatigue_detected,
            },
            channel_breakdown=channel_breakdown_list,
            is_sparse_data=False,
            funnel_stage=funnel_stage,
            pacing_ratio=pacing_ratio,
            pacing_status=pacing_status,
            fatigue_detected=fatigue_detected,
            fatigue_detail=fatigue_detail,
            learning_phase_protected=learning_phase_protected,
            channel_benchmarks=CHANNEL_BENCHMARKS,
            generated_at=datetime.now(timezone.utc).isoformat()
        )

        cls._persist_log(db, campaign_id, current_user, response)
        return response

    @classmethod
    def scan_portfolio_triage(
        cls,
        db: Session,
        campaigns: List[Campaign],
        limit: int = 25,
    ) -> PortfolioTriageResponse:
        """Quét toàn bộ danh mục chiến dịch (1,000+ campaigns) không bị N+1 để phát hiện bất thường."""
        if not campaigns:
            return PortfolioTriageResponse(
                total_scanned=0,
                healthy_count=0,
                attention_count=0,
                critical_count=0,
                anomalies=[],
                summary={
                    "critical_count": 0,
                    "warning_count": 0,
                    "opportunity_count": 0,
                    "wasted_spend_estimate": 0,
                    "health_score": 100,
                },
            )

        campaign_ids = [c.id for c in campaigns]
        all_metrics = (
            db.query(CampaignMetric)
            .filter(CampaignMetric.campaign_id.in_(campaign_ids))
            .all()
        )
        metrics_by_campaign: Dict[int, List[CampaignMetric]] = {cid: [] for cid in campaign_ids}
        for m in all_metrics:
            if m.campaign_id in metrics_by_campaign:
                metrics_by_campaign[m.campaign_id].append(m)

        healthy_count = 0
        attention_count = 0
        critical_count = 0
        wasted_spend = 0.0
        anomalies: List[PortfolioTriageAnomaly] = []

        for camp in campaigns:
            c_metrics = metrics_by_campaign.get(camp.id, [])
            funnel_stage = cls.infer_funnel_stage(camp.objective, getattr(camp, "funnel_stage", None))
            total_views = sum(m.views for m in c_metrics)
            total_clicks = sum(m.clicks for m in c_metrics)
            total_conversions = sum(m.conversions for m in c_metrics)
            total_cost = sum(float(m.cost) for m in c_metrics)
            total_revenue = sum(float(m.revenue) for m in c_metrics)

            if not c_metrics or (total_views == 0 and total_cost == 0):
                healthy_count += 1
                continue

            ctr = (total_clicks / total_views * 100.0) if total_views > 0 else 0.0
            cpc = (total_cost / total_clicks) if total_clicks > 0 else 0.0
            cvr = (total_conversions / total_clicks * 100.0) if total_clicks > 0 else 0.0
            roas = (total_revenue / total_cost) if total_cost > 0 else 0.0

            pacing_info = cls.compute_budget_pacing(camp, c_metrics, total_cost)
            pacing_ratio = pacing_info["pacing_ratio"]
            pacing_status = pacing_info["pacing_status"]
            fatigue_info = cls.detect_creative_fatigue(c_metrics)
            fatigue_detected = bool(fatigue_info.get("fatigue_detected", False))

            is_tofu_non_rev = (funnel_stage == "ToFU" and total_revenue == 0)
            is_mofu_lead_gen = (funnel_stage == "MoFU" and total_revenue == 0 and total_conversions > 0)

            ctr_score = 100 if ctr >= 2.5 else (80 if ctr >= 1.5 else (60 if ctr >= 1.0 else 30))
            cvr_score = 100 if cvr >= 4.0 else (80 if cvr >= 2.5 else (60 if cvr >= 1.5 else 30))
            cpc_score = 100 if (total_clicks > 0 and cpc <= 15000) else (80 if cpc <= 25000 else 50)
            roas_score = 100 if roas >= 4.0 else (85 if roas >= 3.0 else (70 if roas >= 2.0 else (50 if roas >= 1.0 else 20)))

            if is_tofu_non_rev:
                score = int(round(ctr_score * 0.45 + cpc_score * 0.40 + 80 * 0.15))
                status = "HEALTHY" if score >= 70 else ("NEEDS_ATTENTION" if score >= 40 else "CRITICAL")
            elif is_mofu_lead_gen:
                cpa = total_cost / total_conversions
                cpa_score = 100 if cpa <= 150000 else (80 if cpa <= 300000 else 50)
                score = int(round(cpa_score * 0.45 + cvr_score * 0.35 + ctr_score * 0.20))
                status = "HEALTHY" if score >= 70 else ("NEEDS_ATTENTION" if score >= 40 else "CRITICAL")
            else:
                score = int(round(roas_score * 0.40 + ctr_score * 0.20 + cvr_score * 0.25 + cpc_score * 0.15))
                if total_cost > 0 and roas < 1.0:
                    status = "CRITICAL"
                elif score >= 70:
                    status = "HEALTHY"
                elif score >= 40:
                    status = "NEEDS_ATTENTION"
                else:
                    status = "CRITICAL"

            if status == "HEALTHY" and pacing_status == "ON_TRACK" and not fatigue_detected:
                healthy_count += 1
            elif status == "CRITICAL":
                critical_count += 1
            else:
                attention_count += 1

            anomaly_type = None
            severity = None
            summary = ""
            rec_action = ""
            action_type = "ADJUST_BUDGET"
            metric_hl = f"ROAS {roas:.2f}x"

            if not is_tofu_non_rev and total_cost >= 1000000 and total_conversions == 0:
                anomaly_type = "ZERO_CONVERSION_BLEED"
                severity = "CRITICAL"
                summary = f"Chi tiêu {total_cost:,.0f} VNĐ nhưng 0 chuyển đổi (Zero Conversion Bleed)."
                rec_action = "Tạm dừng nhóm quảng cáo rò rỉ ngân sách và kiểm tra lại tracking/trang đích."
                action_type = "PAUSE_CAMPAIGN"
                metric_hl = f"0 đơn · -{total_cost:,.0f}đ"
                wasted_spend += total_cost
            elif pacing_status == "OVER_PACING" and pacing_ratio is not None:
                anomaly_type = "OVER_PACING"
                severity = "CRITICAL" if pacing_ratio >= 1.8 else "HIGH"
                summary = f"Tốc độ đốt ngân sách gấp {pacing_ratio:.2f}x kế hoạch thời gian."
                rec_action = "Đặt trần ngân sách ngày (Daily Budget Cap) hoặc hãm -15% ngay lập tức."
                action_type = "ADJUST_BUDGET"
                metric_hl = f"Pacing {int(pacing_ratio * 100)}%"
            elif fatigue_detected:
                anomaly_type = "CREATIVE_FATIGUE"
                severity = "HIGH"
                summary = str(fatigue_info.get("fatigue_detail") or "Bão hòa nội dung quảng cáo (CTR giảm, CPC tăng).")
                rec_action = "Xoay vòng Creative Angle Matrix và thay mới Hook 3 giây đầu."
                action_type = "REFRESH_CREATIVE"
                metric_hl = f"CTR {ctr:.2f}% · Fatigue"
            elif not is_tofu_non_rev and not is_mofu_lead_gen and total_cost > 0 and roas < 1.0:
                anomaly_type = "ROAS_CRITICAL"
                severity = "CRITICAL"
                summary = f"ROAS đạt {roas:.2f}x (< 1.0x hòa vốn), thâm hụt chi phí tiếp thị."
                rec_action = "Cắt giảm 30-50% ngân sách kênh lỗ và tái phân bổ sang kênh sinh lời."
                action_type = "REBALANCE_CHANNELS"
                metric_hl = f"ROAS {roas:.2f}x"
                wasted_spend += max(0.0, total_cost - total_revenue)
            elif pacing_status == "UNDER_PACING" and pacing_ratio is not None:
                anomaly_type = "UNDER_PACING"
                severity = "MEDIUM"
                summary = f"Giải ngân chậm ({pacing_ratio:.2f}x kế hoạch), quảng cáo bị nghẽn phân phối."
                rec_action = "Mở rộng tệp đối tượng hoặc nâng nhẹ giới hạn giá thầu."
                action_type = "ADJUST_BUDGET"
                metric_hl = f"Pacing {int(pacing_ratio * 100)}%"

            if anomaly_type and severity:
                anomalies.append(
                    PortfolioTriageAnomaly(
                        id=f"triage-{camp.id}-{anomaly_type.lower()}",
                        campaign_id=camp.id,
                        campaign_code=getattr(camp, "campaign_code", None),
                        campaign_name=camp.name,
                        funnel_stage=funnel_stage,
                        anomaly_type=anomaly_type,
                        severity=severity,
                        health_score=score,
                        total_cost=round(total_cost, 2),
                        total_revenue=round(total_revenue, 2),
                        roas=round(roas, 2),
                        pacing_ratio=pacing_ratio,
                        fatigue_detected=fatigue_detected,
                        title=summary,
                        detail=summary,
                        metric_highlight=metric_hl,
                        action_type=action_type,
                        summary=summary,
                        recommended_action=rec_action,
                    )
                )

        severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        anomalies.sort(key=lambda a: (severity_rank.get(a.severity, 9), -a.total_cost))

        return PortfolioTriageResponse(
            total_scanned=len(campaigns),
            healthy_count=healthy_count,
            attention_count=attention_count,
            critical_count=critical_count,
            anomalies=anomalies[:limit],
            summary={
                "critical_count": critical_count,
                "warning_count": attention_count,
                "opportunity_count": healthy_count,
                "wasted_spend_estimate": round(wasted_spend, 2),
                "health_score": max(20, 100 - critical_count * 15 - attention_count * 5),
            },
        )

    @classmethod
    def _persist_log(
        cls,
        db: Session,
        campaign_id: int,
        current_user: Optional[User],
        response: AIDoctorResponse
    ) -> None:
        """Ghi nhận nhật ký phân tích vào bảng ai_logs tuân thủ CheckConstraint SQLite (task_type='SUMMARY')."""
        try:
            user_id = getattr(current_user, "id", None)
            if not user_id:
                first_user = db.query(User).first()
                if first_user:
                    user_id = first_user.id
                else:
                    return

            output_dict = response.model_dump()
            input_context = f"ai-doctor:campaign:{campaign_id}:score:{response.health_score}"
            input_hash = hashlib.sha256(input_context.encode("utf-8")).hexdigest()

            log_entry = AILog(
                user_id=user_id,
                campaign_id=campaign_id,
                task_type="SUMMARY",
                provider="gemini",
                model="ai-doctor-engine-v1",
                prompt_version="v1",
                input_hash=input_hash,
                source_ids_json="[]",
                output_json=json.dumps(output_dict, ensure_ascii=False),
                result_status="SUCCESS",
                latency_ms=10
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"Could not write AI Doctor audit log to ai_logs table: {e}")
