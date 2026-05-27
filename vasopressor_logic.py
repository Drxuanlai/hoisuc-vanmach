# vasopressor_logic.py
# Logic vận mạch và tính tốc độ bơm tiêm điện.

def calculate_infusion_rate(
    weight_kg: float,
    desired_dose_mcg_kg_min: float,
    total_drug_mg: float,
    final_volume_ml: float,
) -> dict:
    """
    Tính tốc độ bơm tiêm điện mL/giờ cho thuốc tính theo mcg/kg/phút.

    total_drug_mcg = total_drug_mg × 1000
    final_concentration_mcg_ml = total_drug_mcg / final_volume_ml
    required_mcg_min = desired_dose_mcg_kg_min × weight_kg
    pump_rate_ml_hour = required_mcg_min × 60 / final_concentration_mcg_ml
    """
    total_drug_mcg = total_drug_mg * 1000.0
    final_concentration_mcg_ml = total_drug_mcg / final_volume_ml
    required_mcg_min = desired_dose_mcg_kg_min * weight_kg
    pump_rate_ml_hour = required_mcg_min * 60.0 / final_concentration_mcg_ml

    return {
        "total_drug_mg": total_drug_mg,
        "total_drug_mcg": total_drug_mcg,
        "final_concentration_mcg_ml": final_concentration_mcg_ml,
        "required_mcg_min": required_mcg_min,
        "pump_rate_ml_hour": pump_rate_ml_hour,
    }


# Backward-compatible alias
calculate_vasopressor_rate = calculate_infusion_rate


# Backward-compatible alias
calculate_vasopressor_rate = calculate_infusion_rate

VASOPRESSOR_PRESETS = {
    "Noradrenaline 4 mg/50 mL": {"drug": "Noradrenaline", "total_drug_mg": 4.0, "final_volume_ml": 50.0},
    "Noradrenaline 8 mg/50 mL": {"drug": "Noradrenaline", "total_drug_mg": 8.0, "final_volume_ml": 50.0},
    "Noradrenaline 16 mg/50 mL": {"drug": "Noradrenaline", "total_drug_mg": 16.0, "final_volume_ml": 50.0},
    "Adrenaline 4 mg/50 mL": {"drug": "Adrenaline", "total_drug_mg": 4.0, "final_volume_ml": 50.0},
    "Adrenaline 8 mg/50 mL": {"drug": "Adrenaline", "total_drug_mg": 8.0, "final_volume_ml": 50.0},
}


def suggest_noradrenaline_dose(map_mmHg: float, lactate: float, cardiogenic_active: bool, fluid_overload_risk: bool) -> tuple[float, str]:
    """
    Gợi ý liều khởi đầu norepinephrine mang tính thực hành.
    App không tự tạo y lệnh; bác sĩ phải xác nhận.
    """
    # Quan trọng: lactate cao một mình KHÔNG phải chỉ định norepinephrine nếu MAP không thấp.
    if map_mmHg >= 65:
        dose = 0.03
        reason = "MAP hiện ≥ 65 → không có chỉ định tự động dùng norepinephrine. Nếu mở máy tính thủ công, chỉ dùng liều test/tham khảo rất thấp và phải có chỉ định lâm sàng riêng."
    elif map_mmHg < 55:
        dose = 0.10
        reason = "MAP rất thấp → gợi ý bắt đầu khoảng 0,10 mcg/kg/phút rồi chỉnh theo MAP/tưới máu."
    else:
        dose = 0.05
        reason = "MAP < 65 → gợi ý bắt đầu khoảng 0,05 mcg/kg/phút rồi chỉnh theo MAP/tưới máu."

    if map_mmHg < 65 and lactate > 4:
        reason += " Lactate cao củng cố tình trạng giảm tưới máu, cần song song tìm nguyên nhân và theo dõi đáp ứng."

    if cardiogenic_active and fluid_overload_risk:
        reason += " Có HFrEF/sung huyết: dùng liều thấp nhất đủ đạt MAP, tránh tăng hậu tải quá mức và đánh giá sớm nhu cầu inotrope."

    return dose, reason


def choose_vasopressor_preset_for_rate(weight_kg: float, dose: float) -> tuple[str, dict, dict]:
    """
    Tự gợi ý nồng độ noradrenaline sao cho tốc độ bơm nằm trong khoảng dễ thao tác.
    Mục tiêu thực hành: khoảng 2–20 mL/giờ nếu có thể.
    """
    candidates = [
        "Noradrenaline 4 mg/50 mL",
        "Noradrenaline 8 mg/50 mL",
        "Noradrenaline 16 mg/50 mL",
    ]
    results = {}
    best_name = candidates[0]
    best_score = 999

    for name in candidates:
        p = VASOPRESSOR_PRESETS[name]
        r = calculate_infusion_rate(weight_kg, dose, p["total_drug_mg"], p["final_volume_ml"])
        rate = r["pump_rate_ml_hour"]
        results[name] = r
        if 2 <= rate <= 20:
            score = abs(rate - 6)  # ưu tiên quanh 6 mL/h để dễ chỉnh
        else:
            score = min(abs(rate - 2), abs(rate - 20)) + 20
        if score < best_score:
            best_score = score
            best_name = name

    return best_name, VASOPRESSOR_PRESETS[best_name], results


