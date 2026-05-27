# antibiotic_logic.py
# Logic kháng sinh kinh nghiệm. Không tạo y lệnh cố định.

from antibiotic_presets_local import ANTIBIOTIC_PROTOCOLS

def assess_mdr_risk(
    recent_hospitalization: bool,
    recent_antibiotics: bool,
    prior_mdr: bool,
    nursing_home: bool,
    hemodialysis: bool,
    immunosuppression: bool,
    invasive_device: bool,
) -> tuple[bool, list]:
    """Đánh giá nguy cơ vi khuẩn đa kháng theo checklist thực hành."""
    factors = []
    if recent_hospitalization:
        factors.append("Nhập viện trong 90 ngày")
    if recent_antibiotics:
        factors.append("Dùng kháng sinh trong 90 ngày")
    if prior_mdr:
        factors.append("Tiền sử cấy MDR/ESBL/MRSA/CRE")
    if nursing_home:
        factors.append("Chăm sóc dài hạn/viện dưỡng lão")
    if hemodialysis:
        factors.append("Lọc máu chu kỳ")
    if immunosuppression:
        factors.append("Suy giảm miễn dịch")
    if invasive_device:
        factors.append("Dụng cụ xâm lấn/catheter/sonde lâu ngày")
    return len(factors) > 0, factors


def antibiotic_timing_advice(septic_shock: bool, possible_sepsis: bool) -> tuple[str, str]:
    """Gợi ý thời điểm kháng sinh."""
    if septic_shock:
        return (
            "RED",
            "Septic shock hoặc khả năng nhiễm khuẩn cao kèm giảm tưới máu: dùng kháng sinh phổ rộng càng sớm càng tốt, lý tưởng trong 1 giờ. Lấy cấy trước nếu không làm trì hoãn."
        )
    if possible_sepsis:
        return (
            "ORANGE",
            "Nghi sepsis chưa sốc: đánh giá nhanh khả năng nhiễm khuẩn, lấy cấy phù hợp và dùng kháng sinh sớm nếu xác suất nhiễm khuẩn cao."
        )
    return (
        "BLUE",
        "Chưa đủ dữ kiện nhiễm khuẩn rõ. Tiếp tục đánh giá và tránh lạm dụng kháng sinh nếu có chẩn đoán khác phù hợp."
    )


def recommend_antibiotic_coverage(
    infection_focus: str,
    community_or_hospital: str,
    mdr_risk: bool,
    mrsa_risk: bool,
    pseudomonas_risk: bool,
    esbl_risk: bool,
    candida_risk: bool,
    beta_lactam_allergy: bool,
    egfr: float,
) -> dict:
    """
    Gợi ý coverage và nhóm kháng sinh.
    Không tạo y lệnh cố định, vì phải phụ thuộc phác đồ bệnh viện và antibiogram.
    """
    protocol = ANTIBIOTIC_PROTOCOLS.get(infection_focus, ANTIBIOTIC_PROTOCOLS["Chưa rõ ổ nhiễm"])
    coverage = list(protocol["base_coverage"])
    suggestions = list(protocol["base_suggestion"])
    warnings = []
    notes = [protocol["source_control"]]

    if community_or_hospital in ["Bệnh viện", "ICU/VAP"]:
        coverage.append("Tác nhân bệnh viện và vi khuẩn kháng thuốc tùy antibiogram")
        suggestions.append("Ưu tiên phác đồ bệnh viện/ICU thay vì phác đồ cộng đồng thông thường")

    if mdr_risk:
        coverage.append("Vi khuẩn đa kháng theo yếu tố nguy cơ")
        suggestions.extend(protocol["mdr_addon"])

    if mrsa_risk:
        coverage.append("MRSA")
        suggestions.append("Thêm thuốc anti-MRSA theo phác đồ bệnh viện nếu nguy cơ MRSA có ý nghĩa")

    if pseudomonas_risk:
        coverage.append("Pseudomonas aeruginosa")
        suggestions.append("Chọn beta-lactam có phổ Pseudomonas theo phác đồ bệnh viện")

    if esbl_risk:
        coverage.append("ESBL Enterobacterales")
        suggestions.append("Cân nhắc carbapenem theo phác đồ bệnh viện nếu sốc hoặc nguy cơ ESBL cao")

    if candida_risk:
        coverage.append("Candida/nấm xâm lấn trong bối cảnh nguy cơ cao")
        suggestions.append("Cân nhắc kháng nấm kinh nghiệm khi sốc kéo dài và nguy cơ Candida cao; nên hội chẩn nhiễm/ICU")

    if beta_lactam_allergy:
        warnings.append("Dị ứng beta-lactam nặng: cần phác đồ thay thế theo bệnh viện, cân nhắc hội chẩn dị ứng/nhiễm.")

    if egfr < 30:
        warnings.append("eGFR/CrCl < 30 mL/phút: cần chỉnh liều nhiều kháng sinh theo chức năng thận.")
    elif egfr < 60:
        warnings.append("eGFR/CrCl giảm: kiểm tra liều duy trì và khoảng cách liều theo thận.")

    # Remove duplicates while preserving order
    coverage = list(dict.fromkeys(coverage))
    suggestions = list(dict.fromkeys(suggestions))
    warnings = list(dict.fromkeys(warnings))
    notes = list(dict.fromkeys(notes))

    return {
        "coverage": coverage,
        "suggestions": suggestions,
        "warnings": warnings,
        "cultures": protocol["cultures"],
        "notes": notes,
    }

