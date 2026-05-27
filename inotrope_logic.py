# inotrope_logic.py
# Logic inotrope.

INOTROPE_PRESETS = {
    "Dobutamine 250 mg/50 mL": {"drug": "Dobutamine", "total_drug_mg": 250.0, "final_volume_ml": 50.0},
    "Dobutamine 500 mg/50 mL": {"drug": "Dobutamine", "total_drug_mg": 500.0, "final_volume_ml": 50.0},
    "Milrinone 20 mg/100 mL": {"drug": "Milrinone", "total_drug_mg": 20.0, "final_volume_ml": 100.0},
    "Milrinone 10 mg/50 mL": {"drug": "Milrinone", "total_drug_mg": 10.0, "final_volume_ml": 50.0},
}


def suggest_inotrope(
    cardiogenic_active: bool,
    septic_active: bool,
    fluid_overload_risk: bool,
    fluid_responsive: bool,
    map_mmHg: float,
    lactate: float,
    ef_reduced: bool,
    cold_hypoperfusion: bool,
    pulmonary_edema: bool,
    rapid_af: bool,
    ckd: bool,
) -> dict:
    """Gợi ý có cần inotrope, chọn thuốc và liều khởi đầu thận trọng."""
    persistent_hypoperfusion = map_mmHg < 65 or lactate > 4 or cold_hypoperfusion
    low_co_phenotype = cardiogenic_active or ef_reduced or (fluid_overload_risk and cold_hypoperfusion)

    recommendation = {
        "need_inotrope": False,
        "level": "BLUE",
        "drug": "Dobutamine",
        "dose": 2.5,
        "preset": "Dobutamine 250 mg/50 mL",
        "text": "Chưa đủ dữ kiện để gợi ý inotrope. Tiếp tục đánh giá EF, VTI/CO, tưới máu mô và MAP.",
        "warnings": [],
    }

    if septic_active and low_co_phenotype and persistent_hypoperfusion:
        recommendation["need_inotrope"] = True
        recommendation["level"] = "ORANGE"
        recommendation["drug"] = "Dobutamine"
        recommendation["dose"] = 2.5
        recommendation["preset"] = "Dobutamine 250 mg/50 mL"
        recommendation["text"] = (
            "Có sốc nhiễm khuẩn kèm rối loạn chức năng tim/low-output phenotype và còn giảm tưới máu. "
            "Sau khi đã nâng MAP đủ bằng norepinephrine và không còn chiến lược dịch an toàn, cân nhắc thêm dobutamine liều thấp rồi chỉnh theo VTI/CO, CRT, lactate và nước tiểu."
        )

    if cardiogenic_active and fluid_overload_risk and persistent_hypoperfusion:
        recommendation["need_inotrope"] = True
        recommendation["level"] = "RED"
        recommendation["drug"] = "Dobutamine"
        recommendation["dose"] = 2.5
        recommendation["preset"] = "Dobutamine 250 mg/50 mL"
        recommendation["text"] = (
            "Bệnh cảnh sốc tim/sốc hỗn hợp kèm sung huyết và giảm tưới máu. "
            "Cân nhắc inotrope sớm, thường bắt đầu dobutamine liều thấp khi MAP đã được hỗ trợ; theo dõi tụt HA, nhịp nhanh và loạn nhịp."
        )

    if map_mmHg < 60:
        recommendation["warnings"].append(
            "MAP còn rất thấp: dobutamine có thể gây giãn mạch/tụt HA. Thường cần norepinephrine trước hoặc song song để giữ MAP."
        )

    if rapid_af:
        recommendation["warnings"].append(
            "Rung nhĩ đáp ứng thất nhanh/nhịp nhanh: dobutamine có thể làm tăng nhịp và loạn nhịp. Cần ICU/tim mạch và theo dõi sát."
        )

    if ckd:
        recommendation["warnings"].append(
            "CKD: tránh tự động ưu tiên milrinone vì thuốc thải qua thận, dễ tích lũy và gây tụt HA/loạn nhịp; nếu dùng cần giảm liều và theo dõi sát."
        )

    if pulmonary_edema:
        recommendation["warnings"].append(
            "Phù phổi/B-lines lan tỏa: mục tiêu là tăng cung lượng tim mà không truyền thêm dịch không cần thiết."
        )

    return recommendation



