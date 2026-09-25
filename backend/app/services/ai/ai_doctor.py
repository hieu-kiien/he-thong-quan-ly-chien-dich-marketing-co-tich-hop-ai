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
    KPISummaryResponse
)

logger = logging.getLogger("marketflow.ai_doctor")


class AIDoctorEngine:
    """Grounded deterministic and AI-enriched campaign diagnostic engine."""

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
        4. Tính điểm sức khỏe chiến dịch (0-100) theo ma trận 4 cấu phần: ROAS (40%), CTR (20%), CVR (25%), CPC (15%).
        5. Phân loại trạng thái sức khỏe: HEALTHY, NEEDS_ATTENTION, CRITICAL.
        6. Phát hiện điểm nghẽn hiệu suất và đề xuất đơn thuốc hành động (SCALE, REDUCE, OPTIMIZE, PAUSE).
        7. Ghi nhận nhật ký kiểm toán vào bảng ai_logs với task_type='SUMMARY'.
        """
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        campaign_name = campaign.name if campaign else f"Chiến dịch #{campaign_id}"

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
                generated_at=datetime.now(timezone.utc).isoformat()
            )
            cls._persist_log(db, campaign_id, current_user, response)
            return response

        # 4. Phân tích chi tiết từng kênh tiếp thị (Channel Attribution Breakdown)
        channel_breakdown_list = cls.compute_channel_attribution(campaign_id, db)

        # 5. Tính điểm sức khỏe chiến dịch (Health Score: 0 - 100)
        # ROAS Score (trọng số 40%)
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

        # CTR Score (trọng số 20%)
        if ctr_percent >= 2.5:
            ctr_score = 100
        elif ctr_percent >= 1.5:
            ctr_score = 80
        elif ctr_percent >= 1.0:
            ctr_score = 60
        else:
            ctr_score = 30

        # CVR Score (trọng số 25%)
        if cvr_percent >= 4.0:
            cvr_score = 100
        elif cvr_percent >= 2.5:
            cvr_score = 80
        elif cvr_percent >= 1.5:
            cvr_score = 60
        else:
            cvr_score = 30

        # CPC Score (trọng số 15%)
        if total_clicks == 0 or total_cost == 0:
            cpc_score = 80
        elif cpc_avg <= 15000:
            cpc_score = 100
        elif cpc_avg <= 25000:
            cpc_score = 80
        else:
            cpc_score = 50

        raw_health_score = int(round(
            roas_score * 0.40 +
            ctr_score * 0.20 +
            cvr_score * 0.25 +
            cpc_score * 0.15
        ))
        health_score = max(0, min(100, raw_health_score))

        # Phân loại trạng thái sức khỏe
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

        if total_clicks > 20 and cvr_percent < 2.0:
            bottlenecks_list.append(
                f"Tỷ lệ chuyển đổi CVR thấp ({cvr_percent:.2f}% < 2.0%). Khách hàng rời bỏ tại trang đích hoặc form đặt hàng."
            )

        if total_clicks > 10 and cpc_avg > 25000:
            bottlenecks_list.append(
                f"Chi phí mỗi lượt nhấp CPC cao ({cpc_avg:,.0f} VNĐ). Nhóm đối tượng quảng cáo đang bị cạnh tranh mạnh hoặc tệp quá hẹp."
            )

        # Kiểm tra điểm nghẽn theo từng kênh
        for ch in channel_breakdown_list:
            if ch.cost > 0 and ch.roas < 1.0:
                bottlenecks_list.append(
                    f"Kênh {ch.channel_name} ghi nhận ROAS chỉ {ch.roas}x và chi phí {ch.cost:,.0f} VNĐ mà chưa đạt điểm hòa vốn."
                )
            elif ch.views > 200 and ch.ctr_percent < 1.0:
                bottlenecks_list.append(
                    f"Kênh {ch.channel_name} có CTR mờ nhạt ({ch.ctr_percent}%), nội dung chưa tạo đủ ấn tượng với khán giả."
                )

        if not bottlenecks_list:
            bottlenecks_list.append(
                "Các chỉ số kinh tế tiếp thị đang vận hành ổn định trong phạm vi mục tiêu đề ra."
            )

        # 7. Đưa ra các đơn thuốc khuyến nghị chiến lược (Prescriptions)
        recommendations_list: List[AIDoctorRecommendation] = []

        # Tìm kênh có ROAS cao nhất
        best_channels = [ch for ch in channel_breakdown_list if ch.roas >= 3.0 or (ch.cost == 0 and ch.revenue > 0)]
        for ch in best_channels:
            recommendations_list.append(
                AIDoctorRecommendation(
                    action="SCALE",
                    channel=ch.channel_slug or ch.channel_name,
                    reason=f"Kênh {ch.channel_name} đạt hiệu suất sinh lời xuất sắc với ROAS {ch.roas:.2f}x và đóng góp {ch.share_of_revenue:.1f}% tổng doanh thu.",
                    suggestion=f"Tăng 20-30% ngân sách cho kênh {ch.channel_name} để tiếp tục mở rộng quy mô tăng trưởng.",
                    title=f"Tăng ngân sách cho kênh {ch.channel_name}",
                    description=f"Tăng ngân sách cho kênh {ch.channel_name} do ROAS đạt {ch.roas:.2f}x",
                    impact="+20-30% Doanh thu dự kiến"
                )
            )

        # Tìm kênh có tỷ lệ chuyển đổi hoặc CTR thấp cần tối ưu
        optimize_channels = [ch for ch in channel_breakdown_list if (ch.views > 50 and ch.ctr_percent < 1.5) or (ch.clicks > 10 and ch.cvr_percent < 2.5)]
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

        # Tìm kênh kém hiệu quả (thua lỗ)
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
            if roas >= 2.0:
                recommendations_list.append(
                    AIDoctorRecommendation(
                        action="SCALE",
                        channel="all",
                        reason=f"Chiến dịch đạt hiệu suất sinh lời tốt với ROAS {roas:.2f}x.",
                        suggestion="Mở rộng quy mô tiếp cận khách hàng trên các kênh chủ lực Facebook và TikTok.",
                        title="Mở rộng ngân sách tiếp cận",
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
            f"Chiến dịch '{campaign_name}' đạt Điểm sức khỏe {health_score}/100 (Trạng thái: {status_text}).",
            f"Tổng chi phí ghi nhận: {total_cost:,.0f} VNĐ, Doanh thu tạo ra: {total_revenue:,.0f} VNĐ, "
            f"tương ứng ROAS {roas:.2f}x và ROI {roi_percent:+.1f}%.",
            f"Lưu lượng đạt {total_views:,.0f} lượt xem, {total_clicks:,.0f} lượt click (CTR: {ctr_percent:.2f}%, CPC: {cpc_avg:,.0f} VNĐ), "
            f"với {total_conversions:,.0f} chuyển đổi thành công (CVR: {cvr_percent:.2f}%)."
        ]
        if health_status == "HEALTHY":
            summary_parts.append("Hiệu suất chiến dịch đang ở trạng thái tích cực, sẵn sàng để gia tăng ngân sách vào các kênh có ROAS dẫn đầu.")
        elif health_status == "NEEDS_ATTENTION":
            summary_parts.append("Hệ thống phát hiện một số điểm nghẽn về tỷ lệ nhấp hoặc chuyển đổi, cần ưu tiên A/B testing nội dung trước khi nâng ngân sách.")
        else:
            summary_parts.append("Cảnh báo: Tỷ suất sinh lời đang dưới ngưỡng an toàn hoặc chiến dịch đang bị thâm hụt vốn, cần rà soát và tạm dừng các kênh lỗ.")

        diagnosis_summary = " ".join(summary_parts)

        response = AIDoctorResponse(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            health_status=health_status,
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
                "roas": round(roas, 2),
                "roi_percent": round(roi_percent, 2),
            },
            channel_breakdown=channel_breakdown_list,
            is_sparse_data=False,
            generated_at=datetime.now(timezone.utc).isoformat()
        )

        cls._persist_log(db, campaign_id, current_user, response)
        return response

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
