import streamlit as st

# ============================================================
# Shock Resuscitation Mini-App By DR.XuanLai
# ------------------------------------------------------------
# Modules:
# 1. Patient data
# 2. Multi-label shock phenotype checklist
# 3. Mixed shock detection
# 4. Fluid overload / fluid intolerance warning
# 5. Fluid responsiveness assessment
# 6. Fluid strategy recommendation
# 7. Vasopressor dose suggestion + dilution presets + pump-rate calculator
# 8. Inotrope decision support + dose suggestion + pump-rate calculator
# 9. High-dose vasoactive warning
# 10. Empiric antibiotic assistant
# 11. Final clinical summary
#
# DISCLAIMER:
# Đây là công cụ hỗ trợ quyết định, không thay thế đánh giá lâm sàng.
# Luôn kiểm tra lại bệnh cảnh, đường truyền, nồng độ pha thuốc,
# bơm tiêm điện, phác đồ bệnh viện và y lệnh trước khi sử dụng.
# ============================================================


# ============================================================
# 1. Calculator functions
# ============================================================

def calculate_fluid_volume(weight_kg: float, dose_ml_per_kg: float = 30.0) -> float:
    """Tính lượng dịch tinh thể theo mL/kg."""
    return weight_kg * dose_ml_per_kg


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


# ============================================================
# 2. Shock phenotype logic
# ============================================================

def classify_shock_multilabel(scores: dict) -> dict:
    """
    Phân loại sốc đa nhãn.
    Không chọn một loại sốc duy nhất.

    Threshold gợi ý:
    - >= 4 điểm: khả năng cao
    - 2-3 điểm: khả năng trung bình
    - 1 điểm: có vài dấu hiệu gợi ý
    - 0 điểm: chưa gợi ý rõ
    """
    result = {}
    for shock_type, score in scores.items():
        if score >= 4:
            result[shock_type] = "Cao"
        elif score >= 2:
            result[shock_type] = "Trung bình"
        elif score >= 1:
            result[shock_type] = "Thấp"
        else:
            result[shock_type] = "Không gợi ý"
    return result


def detect_mixed_shock(shock_result: dict) -> tuple[list, list]:
    """Nhận diện các kiểu sốc hỗn hợp thường gặp."""
    active = [
        shock for shock, level in shock_result.items()
        if level in ["Cao", "Trung bình"]
    ]

    mixed_patterns = []

    if "Sốc nhiễm khuẩn" in active and "Sốc tim" in active:
        mixed_patterns.append(
            "Sốc hỗn hợp nhiễm khuẩn - tim: septic shock with cardiogenic component."
        )

    if "Sốc nhiễm khuẩn" in active and "Sốc giảm thể tích" in active:
        mixed_patterns.append("Sốc hỗn hợp nhiễm khuẩn - giảm thể tích.")

    if "Sốc nhiễm khuẩn" in active and "Sốc tắc nghẽn" in active:
        mixed_patterns.append(
            "Sốc nhiễm khuẩn kèm khả năng sốc tắc nghẽn: cần loại trừ PE, tamponade, tension pneumothorax."
        )

    if "Sốc phản vệ" in active and "Sốc tắc nghẽn" in active:
        mixed_patterns.append(
            "Bệnh cảnh phản vệ/tắc nghẽn cần xử trí cấp cứu song song theo nguyên nhân."
        )

    if "Sốc tim" in active and "Sốc tắc nghẽn" in active:
        mixed_patterns.append(
            "Sốc tim/tắc nghẽn có thể chồng lấp: cần POCUS tim-phổi, ECG, đánh giá RV, màng tim và tràn khí màng phổi."
        )

    return active, mixed_patterns


# ============================================================
# 3. Fluid responsiveness and fluid strategy logic
# ============================================================

def interpret_fluid_responsiveness(
    plr_positive: bool,
    vti_increase_percent: float,
    ppv_percent: float,
    svv_percent: float,
    ivc_comment: str,
) -> tuple[str, list]:
    """
    Đánh giá fluid responsiveness bằng thông số động.

    Gợi ý threshold thường dùng:
    - VTI LVOT tăng >= 10% sau PLR hoặc mini-fluid challenge: gợi ý đáp ứng dịch.
    - PPV/SVV >= 13%: chỉ diễn giải khi điều kiện đo phù hợp.
    - IVC chỉ dùng hỗ trợ, không dùng đơn độc.
    """
    reasons = []
    positive_count = 0

    if plr_positive:
        positive_count += 1
        reasons.append("PLR dương tính")

    if vti_increase_percent >= 10:
        positive_count += 1
        reasons.append(f"VTI LVOT tăng {vti_increase_percent:.1f}%")

    if ppv_percent >= 13:
        positive_count += 1
        reasons.append(f"PPV {ppv_percent:.1f}%")

    if svv_percent >= 13:
        positive_count += 1
        reasons.append(f"SVV {svv_percent:.1f}%")

    if ivc_comment != "Không đánh giá":
        reasons.append(f"IVC: {ivc_comment} — chỉ dùng hỗ trợ, không dùng đơn độc")

    if positive_count >= 1:
        interpretation = "Có bằng chứng gợi ý còn đáp ứng dịch"
    else:
        interpretation = "Chưa có bằng chứng rõ còn đáp ứng dịch"

    return interpretation, reasons


def fluid_strategy_for_mixed_shock(
    septic_level: str,
    cardiogenic_level: str,
    hypovolemic_level: str,
    obstructive_level: str,
    anaphylactic_level: str,
    fluid_overload_risk: bool,
    fluid_responsive: bool,
    map_mmHg: float,
    lactate: float,
) -> tuple[str, str]:
    """Đưa ra gợi ý chiến lược dịch theo phenotype sốc."""
    septic_active = septic_level in ["Cao", "Trung bình"]
    cardiogenic_active = cardiogenic_level in ["Cao", "Trung bình"]
    hypovolemic_active = hypovolemic_level in ["Cao", "Trung bình"]
    obstructive_active = obstructive_level in ["Cao", "Trung bình"]
    anaphylactic_active = anaphylactic_level in ["Cao", "Trung bình"]
    severe_hypoperfusion = map_mmHg < 65 or lactate > 4

    if obstructive_active:
        return (
            "RED",
            "Có phenotype sốc tắc nghẽn. Không trì hoãn xử trí nguyên nhân đảo ngược: "
            "tension pneumothorax, tamponade tim, thuyên tắc phổi nguy cơ cao. "
            "Dịch và vận mạch chỉ là cầu nối trong khi xử trí nguyên nhân."
        )

    if anaphylactic_active:
        return (
            "RED",
            "Có phenotype phản vệ. Ưu tiên adrenaline, đảm bảo đường thở, oxy, dịch tinh thể "
            "và xử trí phản vệ theo phác đồ. Không chờ hoàn tất checklist mới điều trị."
        )

    if septic_active and cardiogenic_active and fluid_overload_risk and severe_hypoperfusion:
        if fluid_responsive:
            return (
                "ORANGE",
                "Sốc hỗn hợp nhiễm khuẩn - tim kèm nguy cơ quá tải dịch. "
                "Có dữ kiện gợi ý còn đáp ứng dịch, nhưng không truyền 30 mL/kg máy móc. "
                "Cân nhắc bolus rất nhỏ 100–250 mL, đánh giá lại ngay bằng MAP, CRT, SpO₂, "
                "siêu âm phổi, VTI LVOT, nước tiểu và lactate. Khởi động norepinephrine sớm nếu MAP < 65."
            )
        return (
            "RED",
            "Sốc hỗn hợp nhiễm khuẩn - tim kèm sung huyết/fluid intolerance. "
            "Không truyền dịch ồ ạt 30 mL/kg. Ưu tiên norepinephrine sớm để đạt MAP ≥ 65 mmHg, "
            "POCUS lặp lại, kiểm soát nhiễm khuẩn, kháng sinh sớm, đánh giá nhu cầu inotrope và ICU."
        )

    if cardiogenic_active and fluid_overload_risk:
        return (
            "RED",
            "Bệnh cảnh ưu thế sốc tim/sung huyết. Tránh bolus dịch lớn. "
            "Ưu tiên vận mạch/inotrope theo đánh giá huyết động, POCUS tim-phổi, ECG, men tim "
            "và xử trí nguyên nhân."
        )

    if septic_active and hypovolemic_active and not fluid_overload_risk and severe_hypoperfusion:
        return (
            "GREEN",
            "Sốc nhiễm khuẩn kèm giảm thể tích và chưa có dấu quá tải dịch. "
            "Có thể tham khảo dịch tinh thể 30 mL/kg trong 3 giờ đầu, song song đánh giá đáp ứng dịch động."
        )

    if septic_active and severe_hypoperfusion and not fluid_overload_risk:
        return (
            "GREEN",
            "Sốc nhiễm khuẩn/giảm tưới máu, chưa có red flag quá tải dịch. "
            "Có thể tham khảo dịch tinh thể 30 mL/kg trong 3 giờ đầu nếu phù hợp lâm sàng."
        )

    if fluid_overload_risk:
        return (
            "ORANGE",
            "Có nguy cơ quá tải dịch. Ưu tiên đánh giá đáp ứng dịch động; nếu cần truyền, dùng bolus nhỏ và đánh giá lại sát."
        )

    return (
        "BLUE",
        "Cần bổ sung dữ kiện để quyết định dịch. Ưu tiên đánh giá tưới máu, lactate, nước tiểu, POCUS và đáp ứng dịch động."
    )


# ============================================================
# 4. Vasoactive decision logic and presets
# ============================================================

VASOPRESSOR_PRESETS = {
    "Noradrenaline 4 mg/50 mL": {"drug": "Noradrenaline", "total_drug_mg": 4.0, "final_volume_ml": 50.0},
    "Noradrenaline 8 mg/50 mL": {"drug": "Noradrenaline", "total_drug_mg": 8.0, "final_volume_ml": 50.0},
    "Noradrenaline 16 mg/50 mL": {"drug": "Noradrenaline", "total_drug_mg": 16.0, "final_volume_ml": 50.0},
    "Adrenaline 4 mg/50 mL": {"drug": "Adrenaline", "total_drug_mg": 4.0, "final_volume_ml": 50.0},
    "Adrenaline 8 mg/50 mL": {"drug": "Adrenaline", "total_drug_mg": 8.0, "final_volume_ml": 50.0},
}

INOTROPE_PRESETS = {
    "Dobutamine 250 mg/50 mL": {"drug": "Dobutamine", "total_drug_mg": 250.0, "final_volume_ml": 50.0},
    "Dobutamine 500 mg/50 mL": {"drug": "Dobutamine", "total_drug_mg": 500.0, "final_volume_ml": 50.0},
    "Milrinone 20 mg/100 mL": {"drug": "Milrinone", "total_drug_mg": 20.0, "final_volume_ml": 100.0},
    "Milrinone 10 mg/50 mL": {"drug": "Milrinone", "total_drug_mg": 10.0, "final_volume_ml": 50.0},
}


def suggest_noradrenaline_dose(map_mmHg: float, lactate: float, cardiogenic_active: bool, fluid_overload_risk: bool) -> tuple[float, str]:
    """
    Gợi ý liều khởi đầu norepinephrine mang tính thực hành.
    App không tự tạo y lệnh; bác sĩ phải xác nhận.
    """
    if map_mmHg < 55 or lactate > 4:
        dose = 0.10
        reason = "MAP rất thấp hoặc lactate cao → gợi ý bắt đầu khoảng 0,10 mcg/kg/phút rồi chỉnh theo MAP/tưới máu."
    elif map_mmHg < 65:
        dose = 0.05
        reason = "MAP < 65 → gợi ý bắt đầu khoảng 0,05 mcg/kg/phút rồi chỉnh theo MAP/tưới máu."
    else:
        dose = 0.03
        reason = "MAP hiện chưa quá thấp → nếu vẫn cần vận mạch, cân nhắc liều thấp và chỉnh theo mục tiêu."

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



# ============================================================
# 5. Empiric antibiotic decision support logic
# ============================================================

ANTIBIOTIC_PROTOCOLS = {
    "Viêm phổi cộng đồng nặng": {
        "base_coverage": [
            "Phế cầu và tác nhân hô hấp cộng đồng thường gặp",
            "Gram âm hô hấp thường gặp",
            "Tác nhân không điển hình",
        ],
        "base_suggestion": [
            "Beta-lactam theo phác đồ bệnh viện + macrolide",
            "Hoặc beta-lactam + respiratory fluoroquinolone nếu phù hợp",
        ],
        "mdr_addon": [
            "Nếu nguy cơ Pseudomonas: chọn beta-lactam có phổ kháng Pseudomonas theo phác đồ bệnh viện",
            "Nếu nguy cơ MRSA: thêm thuốc anti-MRSA theo phác đồ bệnh viện",
            "Nếu nguy cơ ESBL cao và sốc: cân nhắc carbapenem theo phác đồ bệnh viện",
        ],
        "cultures": ["Cấy máu 2 bộ", "Cấy đàm hoặc hút đàm nếu đặt nội khí quản", "X-quang/CT ngực nếu ổn định"],
        "source_control": "Tìm biến chứng cần dẫn lưu/kiểm soát nguồn: mủ màng phổi, áp xe phổi, ổ nhiễm ngoài phổi."
    },
    "Viêm phổi bệnh viện / ICU / VAP": {
        "base_coverage": [
            "Gram âm bệnh viện",
            "Pseudomonas nếu có nguy cơ hoặc ICU có tỷ lệ cao",
            "MRSA nếu có nguy cơ hoặc dịch tễ khoa phù hợp",
        ],
        "base_suggestion": [
            "Anti-pseudomonal beta-lactam theo phác đồ HAP/VAP của bệnh viện",
            "Thêm anti-MRSA khi có nguy cơ MRSA hoặc tỷ lệ MRSA tại khoa cao",
        ],
        "mdr_addon": [
            "Cân nhắc phối hợp hai thuốc kháng Pseudomonas nếu sốc và nguy cơ kháng thuốc cao theo antibiogram",
            "Cân nhắc Acinetobacter/CRE nếu có tiền sử cấy hoặc dịch tễ ICU",
        ],
        "cultures": ["Cấy máu 2 bộ", "Cấy hút nội khí quản/BAL nếu có", "Đánh giá catheter/ổ nhiễm khác"],
        "source_control": "Đánh giá VAP, catheter, dịch màng phổi, áp xe và các ổ nhiễm bệnh viện khác."
    },
    "Nhiễm khuẩn tiết niệu phức tạp / Pyelonephritis": {
        "base_coverage": [
            "Enterobacterales",
            "Gram âm niệu thường gặp",
        ],
        "base_suggestion": [
            "Cephalosporin thế hệ 3 hoặc beta-lactam/beta-lactamase inhibitor theo phác đồ bệnh viện",
        ],
        "mdr_addon": [
            "Nếu nguy cơ ESBL/MDR hoặc sốc: cân nhắc carbapenem theo phác đồ bệnh viện",
            "Nếu nghi Pseudomonas: chọn thuốc có phổ Pseudomonas theo phác đồ",
        ],
        "cultures": ["Cấy máu 2 bộ", "Cấy nước tiểu trước kháng sinh nếu không trì hoãn", "Siêu âm/CT nếu nghi tắc nghẽn"],
        "source_control": "Loại trừ tắc nghẽn đường niệu, áp xe thận/quanh thận, sonde nhiễm khuẩn cần thay/rút."
    },
    "Nhiễm khuẩn ổ bụng": {
        "base_coverage": [
            "Gram âm đường ruột",
            "Kỵ khí",
            "Enterococcus trong một số bối cảnh bệnh viện/ICU",
        ],
        "base_suggestion": [
            "Beta-lactam/beta-lactamase inhibitor theo phác đồ bệnh viện",
            "Hoặc cephalosporin + metronidazole nếu phù hợp phác đồ địa phương",
        ],
        "mdr_addon": [
            "Nếu nguy cơ ESBL/MDR hoặc sốc: cân nhắc carbapenem theo phác đồ bệnh viện",
            "Nếu nhiễm bệnh viện/ổ bụng phức tạp: cân nhắc Enterococcus và nấm theo nguy cơ",
        ],
        "cultures": ["Cấy máu 2 bộ", "Cấy dịch ổ bụng nếu dẫn lưu/phẫu thuật", "CT bụng khi ổn định"],
        "source_control": "Source control là trọng tâm: dẫn lưu ổ mủ, phẫu thuật, xử trí thủng/tắc, ERCP nếu nhiễm trùng đường mật."
    },
    "Da - mô mềm nặng": {
        "base_coverage": [
            "Streptococcus",
            "Staphylococcus aureus",
            "Gram âm/kỵ khí nếu hoại tử, đái tháo đường hoặc nhiễm vùng tầng sinh môn",
        ],
        "base_suggestion": [
            "Phác đồ bệnh viện cho nhiễm da mô mềm nặng",
            "Thêm anti-MRSA nếu có nguy cơ hoặc bệnh cảnh nặng",
        ],
        "mdr_addon": [
            "Nếu nghi viêm cân mạc hoại tử: cần phẫu thuật khẩn, phối hợp kháng sinh rộng theo phác đồ",
            "Cân nhắc độc tố liên cầu/tụ cầu theo bệnh cảnh",
        ],
        "cultures": ["Cấy máu 2 bộ", "Cấy mô/dịch mủ sâu nếu có", "Không trì hoãn phẫu thuật nếu nghi hoại tử"],
        "source_control": "Rạch dẫn lưu, cắt lọc mô hoại tử, hội chẩn ngoại khoa sớm."
    },
    "Nhiễm khuẩn huyết liên quan catheter": {
        "base_coverage": [
            "Staphylococcus aureus/coagulase-negative staphylococci",
            "Gram âm bệnh viện tùy bối cảnh",
            "Candida nếu nguy cơ cao",
        ],
        "base_suggestion": [
            "Anti-MRSA + bao phủ Gram âm theo phác đồ bệnh viện nếu sốc",
            "Cân nhắc kháng nấm nếu nguy cơ Candida cao",
        ],
        "mdr_addon": [
            "Mở rộng phổ theo tiền sử cấy MDR và antibiogram khoa",
        ],
        "cultures": ["Cấy máu 2 bộ ngoại biên", "Cấy máu qua catheter nếu có thể", "Cấy đầu catheter khi rút"],
        "source_control": "Cân nhắc rút/thay catheter nghi nhiễm, đặc biệt khi sốc, S. aureus, Candida hoặc nhiễm dai dẳng."
    },
    "Chưa rõ ổ nhiễm": {
        "base_coverage": [
            "Cần bao phủ rộng theo bối cảnh cộng đồng/bệnh viện và mức độ sốc",
            "Tìm ổ nhiễm song song: phổi, niệu, bụng, da-mô mềm, catheter, thần kinh trung ương",
        ],
        "base_suggestion": [
            "Dùng phác đồ sepsis/septic shock chưa rõ ổ của bệnh viện",
            "Ưu tiên coverage đủ rộng ban đầu nếu sốc, sau đó xuống thang khi có dữ kiện",
        ],
        "mdr_addon": [
            "Mở rộng phổ nếu có nguy cơ MDR/MRSA/Pseudomonas/ESBL hoặc nhiễm bệnh viện",
        ],
        "cultures": ["Cấy máu 2 bộ", "Cấy nước tiểu", "Cấy đàm nếu triệu chứng hô hấp", "Cấy dịch/mủ/catheter theo lâm sàng"],
        "source_control": "Tìm ổ cần can thiệp bằng khám lại, POCUS, X-quang/CT và hội chẩn chuyên khoa."
    },
}


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

# ============================================================
# 6. Streamlit app
# ============================================================

st.set_page_config(
    page_title="Shock Resuscitation Mini-App By DR.XuanLai",
    page_icon="🫀",
    layout="wide",
)

st.title("🫀 Shock Resuscitation Mini-App By DR.XuanLai")
st.caption("Định hướng sốc hỗn hợp, chiến lược dịch, vận mạch và inotrope.")

st.warning(
    "Công cụ này chỉ hỗ trợ quyết định. Không thay thế đánh giá của bác sĩ hồi sức. "
    "Luôn kiểm tra lại bệnh cảnh, đường truyền, nồng độ pha thuốc, phác đồ bệnh viện và y lệnh."
)

# ============================================================
# Sidebar: patient information
# ============================================================

st.sidebar.header("Thông tin bệnh nhân")

weight_kg = st.sidebar.number_input("Cân nặng (kg)", min_value=1.0, max_value=300.0, value=60.0, step=1.0)
map_mmHg = st.sidebar.number_input("MAP hiện tại (mmHg)", min_value=0.0, max_value=200.0, value=50.0, step=1.0)
lactate = st.sidebar.number_input("Lactate (mmol/L)", min_value=0.0, max_value=30.0, value=7.5, step=0.1)
urine_output_ml_kg_h = st.sidebar.number_input("Nước tiểu (mL/kg/giờ)", min_value=0.0, max_value=10.0, value=0.3, step=0.1)
spo2 = st.sidebar.number_input("SpO₂ (%)", min_value=0.0, max_value=100.0, value=85.0, step=1.0)
heart_rate = st.sidebar.number_input("Tần số tim (lần/phút)", min_value=0.0, max_value=250.0, value=135.0, step=1.0)
temperature = st.sidebar.number_input("Nhiệt độ (°C)", min_value=25.0, max_value=45.0, value=39.5, step=0.1)

standard_fluid_ml = calculate_fluid_volume(weight_kg, 30.0)
shock_or_hypoperfusion = map_mmHg < 65 or lactate > 4 or urine_output_ml_kg_h < 0.5

# ============================================================
# Module 1: Multi-label shock checklist
# ============================================================

st.header("1. Checklist phân loại sốc đa nhãn")
st.write("App không chọn một loại sốc duy nhất. Mục tiêu là nhận diện nhiều phenotype sốc có thể cùng tồn tại.")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.subheader("Nhiễm khuẩn")
    septic_items = {
        "Ổ nhiễm khuẩn nghi ngờ/rõ": st.checkbox("Ổ nhiễm khuẩn", value=True, key="septic_1"),
        "Sốt/hạ thân nhiệt": st.checkbox("Sốt/hạ thân nhiệt", value=True, key="septic_2"),
        "Marker nhiễm khuẩn": st.checkbox("Marker nhiễm khuẩn", value=False, key="septic_3"),
        "Lactate tăng": lactate > 2,
        "Da ấm/giãn mạch": st.checkbox("Da ấm/giãn mạch", value=False, key="septic_5"),
    }
    septic_points = sum(bool(v) for v in septic_items.values())

with col2:
    st.subheader("Sốc tim")
    cardiogenic_items = {
        "Đau ngực/ECG bất thường": st.checkbox("Đau ngực/ECG bất thường", value=False, key="cardio_1"),
        "HFrEF/bệnh tim nặng": st.checkbox("HFrEF/bệnh tim nặng", value=True, key="cardio_2"),
        "Phù phổi/ran ẩm": st.checkbox("Phù phổi/ran ẩm", value=True, key="cardio_3"),
        "EF giảm/giảm co bóp": st.checkbox("EF giảm/giảm co bóp", value=True, key="cardio_4"),
        "Chi lạnh/JVP tăng": st.checkbox("Chi lạnh/JVP tăng", value=True, key="cardio_5"),
    }
    cardiogenic_points = sum(bool(v) for v in cardiogenic_items.values())

with col3:
    st.subheader("Giảm thể tích")
    hypovolemic_items = {
        "Xuất huyết/mất máu": st.checkbox("Xuất huyết/mất máu", value=False, key="hypo_1"),
        "Nôn/tiêu chảy": st.checkbox("Nôn/tiêu chảy", value=False, key="hypo_2"),
        "Bỏng/khoang ba": st.checkbox("Bỏng/khoang ba", value=False, key="hypo_3"),
        "Da khô/niêm khô": st.checkbox("Da khô/niêm khô", value=False, key="hypo_4"),
        "Đáp ứng dịch rõ": st.checkbox("Đáp ứng dịch rõ", value=False, key="hypo_5"),
    }
    hypovolemic_points = sum(bool(v) for v in hypovolemic_items.values())

with col4:
    st.subheader("Phản vệ")
    anaphylactic_items = {
        "Dị nguyên": st.checkbox("Dị nguyên", value=False, key="ana_1"),
        "Mày đay/phù mạch": st.checkbox("Mày đay/phù mạch", value=False, key="ana_2"),
        "Khò khè": st.checkbox("Khò khè", value=False, key="ana_3"),
        "Tụt HA nhanh sau tiếp xúc": st.checkbox("Tụt HA nhanh", value=False, key="ana_4"),
        "Đau bụng/nôn": st.checkbox("Đau bụng/nôn", value=False, key="ana_5"),
    }
    anaphylactic_points = sum(bool(v) for v in anaphylactic_items.values())

with col5:
    st.subheader("Tắc nghẽn")
    obstructive_items = {
        "Nghi PE": st.checkbox("Nghi PE", value=False, key="obs_1"),
        "Nghi tension PTX": st.checkbox("Nghi tension PTX", value=False, key="obs_2"),
        "Nghi tamponade": st.checkbox("Nghi tamponade", value=False, key="obs_3"),
        "JVP tăng/phổi sạch": st.checkbox("JVP tăng/phổi sạch", value=False, key="obs_4"),
        "POCUS RV/dịch màng tim": st.checkbox("POCUS RV/dịch màng tim", value=False, key="obs_5"),
    }
    obstructive_points = sum(bool(v) for v in obstructive_items.values())

scores = {
    "Sốc nhiễm khuẩn": septic_points,
    "Sốc tim": cardiogenic_points,
    "Sốc giảm thể tích": hypovolemic_points,
    "Sốc phản vệ": anaphylactic_points,
    "Sốc tắc nghẽn": obstructive_points,
}

shock_result = classify_shock_multilabel(scores)
active_shocks, mixed_patterns = detect_mixed_shock(shock_result)
septic_active = shock_result["Sốc nhiễm khuẩn"] in ["Cao", "Trung bình"]
cardiogenic_active = shock_result["Sốc tim"] in ["Cao", "Trung bình"]

st.subheader("Kết quả định hướng đa nhãn")
score_col1, score_col2, score_col3, score_col4, score_col5 = st.columns(5)
score_col1.metric("Nhiễm khuẩn", septic_points)
score_col2.metric("Tim", cardiogenic_points)
score_col3.metric("Giảm thể tích", hypovolemic_points)
score_col4.metric("Phản vệ", anaphylactic_points)
score_col5.metric("Tắc nghẽn", obstructive_points)

for shock_type, level in shock_result.items():
    if level == "Cao":
        st.error(f"{shock_type}: khả năng cao")
    elif level == "Trung bình":
        st.warning(f"{shock_type}: khả năng trung bình")
    elif level == "Thấp":
        st.info(f"{shock_type}: có vài dấu hiệu gợi ý")
    else:
        st.write(f"{shock_type}: chưa gợi ý rõ")

if len(active_shocks) >= 2:
    st.error("Bệnh cảnh gợi ý SỐC HỖN HỢP.")
    st.write("Các phenotype đang hoạt động: " + ", ".join(active_shocks))

if mixed_patterns:
    for pattern in mixed_patterns:
        st.warning(pattern)

if anaphylactic_points >= 3:
    st.error("Cảnh báo phản vệ: ưu tiên adrenaline, đường thở, oxy, dịch và gọi hỗ trợ.")

if obstructive_points >= 3:
    st.error("Cảnh báo sốc tắc nghẽn: cần xử trí nguyên nhân đảo ngược ngay: tension PTX, tamponade, massive PE.")

if cardiogenic_points >= 3:
    st.error("Cảnh báo sốc tim/sung huyết: tránh truyền dịch ồ ạt; ưu tiên POCUS, ECG, vận mạch/inotrope và xử trí nguyên nhân.")

# ============================================================
# Module 2: Fluid overload / fluid intolerance warning
# ============================================================

st.header("2. Cảnh báo không truyền dịch ồ ạt")
col_a, col_b, col_c = st.columns(3)

with col_a:
    pulmonary_edema = st.checkbox("Phù phổi / ran ẩm lan tỏa", value=True)
    severe_hfrEF = st.checkbox("HFrEF nặng", value=True)
    suspected_cardiogenic_shock = st.checkbox("Nghi sốc tim", value=True)

with col_b:
    anuric_ckd = st.checkbox("CKD vô niệu / ESRD", value=False)
    ckd_any = st.checkbox("CKD bất kỳ / giảm eGFR", value=True)
    diffuse_b_lines = st.checkbox("Siêu âm phổi có B-lines lan tỏa", value=True)
    oxygen_worse_with_fluid = st.checkbox("SpO₂ xấu đi khi truyền dịch", value=False)

with col_c:
    high_jvp = st.checkbox("JVP cao / sung huyết", value=True)
    severe_valve_disease = st.checkbox("Bệnh van tim nặng", value=False)
    clinician_concern_overload = st.checkbox("Bác sĩ lo ngại quá tải dịch", value=True)

fluid_overload_risk = any([
    pulmonary_edema, severe_hfrEF, suspected_cardiogenic_shock, anuric_ckd,
    diffuse_b_lines, oxygen_worse_with_fluid, high_jvp, severe_valve_disease,
    clinician_concern_overload,
])

if shock_or_hypoperfusion:
    st.error("Có tiêu chí sốc / giảm tưới máu: MAP thấp, lactate cao hoặc thiểu niệu.")
    st.metric("Mốc dịch 30 mL/kg để tham khảo", f"{standard_fluid_ml:.0f} mL")
else:
    st.success("Chưa có tiêu chí rõ của sốc / giảm tưới máu nặng.")

if fluid_overload_risk:
    st.error("RED FLAG: Nguy cơ quá tải dịch/fluid intolerance. Không truyền 30 mL/kg một cách máy móc.")
else:
    st.success("Chưa ghi nhận red flag quá tải dịch rõ.")

# ============================================================
# Module 3: Fluid responsiveness
# ============================================================

st.header("3. Đánh giá Fluid Responsiveness")
st.write("Ưu tiên dấu hiệu động. IVC chỉ dùng hỗ trợ, không dùng đơn độc để quyết định truyền dịch.")

col_fr1, col_fr2 = st.columns(2)

with col_fr1:
    plr_positive = st.checkbox("Passive leg raise dương tính", value=False)
    vti_increase_percent = st.number_input("VTI LVOT tăng sau PLR/mini-fluid challenge (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    ppv_percent = st.number_input("Pulse Pressure Variation - PPV (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)

with col_fr2:
    svv_percent = st.number_input("Stroke Volume Variation - SVV (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    ivc_comment = st.selectbox("Nhận xét IVC", ["Không đánh giá", "IVC nhỏ, xẹp nhiều", "IVC giãn, ít thay đổi", "IVC khó diễn giải"], index=2)
    ppv_svv_valid = st.checkbox("Điều kiện PPV/SVV đáng tin: thở máy kiểm soát, nhịp đều, không thở tự nhiên nhiều", value=False)

fr_interpretation, fr_reasons = interpret_fluid_responsiveness(
    plr_positive=plr_positive,
    vti_increase_percent=vti_increase_percent,
    ppv_percent=ppv_percent if ppv_svv_valid else 0.0,
    svv_percent=svv_percent if ppv_svv_valid else 0.0,
    ivc_comment=ivc_comment,
)
fluid_responsive = fr_interpretation.startswith("Có bằng chứng")

if (ppv_percent > 0 or svv_percent > 0) and not ppv_svv_valid:
    st.warning("PPV/SVV đã nhập nhưng điều kiện đo không đáng tin. App không dùng PPV/SVV để kết luận.")

if fluid_responsive:
    st.success(fr_interpretation)
else:
    st.warning(fr_interpretation)

if fr_reasons:
    st.write("Dữ kiện hỗ trợ:")
    for reason in fr_reasons:
        st.write(f"- {reason}")

if fluid_overload_risk and fluid_responsive:
    st.info("Dù có dấu hiệu đáp ứng dịch, bệnh nhân có nguy cơ quá tải. Chỉ nên bolus nhỏ và đánh giá lại sát.")

# ============================================================
# Module 4: Fluid strategy by phenotype
# ============================================================

st.header("4. Chiến lược dịch theo phenotype sốc")
strategy_level, strategy_text = fluid_strategy_for_mixed_shock(
    septic_level=shock_result["Sốc nhiễm khuẩn"],
    cardiogenic_level=shock_result["Sốc tim"],
    hypovolemic_level=shock_result["Sốc giảm thể tích"],
    obstructive_level=shock_result["Sốc tắc nghẽn"],
    anaphylactic_level=shock_result["Sốc phản vệ"],
    fluid_overload_risk=fluid_overload_risk,
    fluid_responsive=fluid_responsive,
    map_mmHg=map_mmHg,
    lactate=lactate,
)

if strategy_level == "RED":
    st.error(strategy_text)
elif strategy_level == "ORANGE":
    st.warning(strategy_text)
elif strategy_level == "GREEN":
    st.success(strategy_text)
else:
    st.info(strategy_text)

if fluid_overload_risk:
    cautious_fluid = st.selectbox(
        "Chọn chiến lược dịch thận trọng",
        [
            "Không bolus thêm ngay - ưu tiên POCUS/vận mạch nếu MAP < 65",
            "Mini-fluid challenge 100 mL rồi đánh giá lại",
            "Fluid challenge 250 mL rồi đánh giá lại",
            "Fluid challenge 500 mL chỉ khi có bằng chứng đáp ứng dịch rõ",
        ],
        index=0,
    )
    st.write(f"Chiến lược đang chọn: **{cautious_fluid}**")
else:
    st.metric("Dịch tinh thể tham khảo 30 mL/kg", f"{standard_fluid_ml:.0f} mL")

# ============================================================
# Module 5: Vasopressor dose suggestion and calculator
# ============================================================

st.header("5. Vận mạch: gợi ý liều, nồng độ pha và tốc độ bơm")

suggested_ne_dose, ne_reason = suggest_noradrenaline_dose(
    map_mmHg=map_mmHg,
    lactate=lactate,
    cardiogenic_active=cardiogenic_active,
    fluid_overload_risk=fluid_overload_risk,
)
recommended_preset_name, recommended_preset, all_ne_rates = choose_vasopressor_preset_for_rate(weight_kg, suggested_ne_dose)

st.info("Gợi ý tự động: " + ne_reason)

with st.expander("Xem bảng tốc độ bơm theo các nồng độ Noradrenaline ở liều gợi ý"):
    for name, result in all_ne_rates.items():
        st.write(f"- {name}: **{result['pump_rate_ml_hour']:.2f} mL/giờ**")

col_vaso_input1, col_vaso_input2 = st.columns(2)

preset_options = list(VASOPRESSOR_PRESETS.keys()) + ["Tùy chỉnh"]
recommended_index = preset_options.index(recommended_preset_name)

with col_vaso_input1:
    drug_preset = st.selectbox("Chọn preset pha thuốc", preset_options, index=recommended_index)

with col_vaso_input2:
    desired_dose = st.number_input(
        "Liều mong muốn (mcg/kg/phút)",
        min_value=0.001,
        max_value=5.0,
        value=float(suggested_ne_dose),
        step=0.01,
        format="%.3f",
    )

if drug_preset != "Tùy chỉnh":
    selected = VASOPRESSOR_PRESETS[drug_preset]
    drug_name = selected["drug"]
    total_drug_mg = selected["total_drug_mg"]
    final_volume_ml = selected["final_volume_ml"]
else:
    col_custom1, col_custom2, col_custom3 = st.columns(3)
    with col_custom1:
        drug_name = st.selectbox("Tên thuốc", ["Noradrenaline", "Adrenaline", "Khác"])
    with col_custom2:
        total_drug_mg = st.number_input("Tổng lượng thuốc trong bơm tiêm (mg)", min_value=0.001, max_value=500.0, value=8.0, step=1.0)
    with col_custom3:
        final_volume_ml = st.number_input("Tổng thể tích sau pha (mL)", min_value=1.0, max_value=500.0, value=50.0, step=1.0)

vasopressor_result = calculate_infusion_rate(weight_kg, desired_dose, total_drug_mg, final_volume_ml)

st.subheader("Kết quả vận mạch")
vaso_col1, vaso_col2, vaso_col3, vaso_col4 = st.columns(4)
vaso_col1.metric("Thuốc", drug_name)
vaso_col2.metric("Pha thuốc", f"{total_drug_mg:.1f} mg/{final_volume_ml:.0f} mL")
vaso_col3.metric("Nồng độ", f"{vasopressor_result['final_concentration_mcg_ml']:.1f} mcg/mL")
vaso_col4.metric("Tốc độ bơm", f"{vasopressor_result['pump_rate_ml_hour']:.2f} mL/giờ")

st.write(f"Nhu cầu thuốc: **{vasopressor_result['required_mcg_min']:.2f} mcg/phút** ở bệnh nhân **{weight_kg:.1f} kg**, liều **{desired_dose:.3f} mcg/kg/phút**.")
st.info("Công thức: mL/giờ = liều mcg/kg/phút × cân nặng kg × 60 ÷ nồng độ sau pha mcg/mL.")

if drug_name == "Noradrenaline" and map_mmHg < 65:
    st.warning("MAP < 65 mmHg. Noradrenaline thường là vận mạch đầu tay trong sốc nhiễm khuẩn; ưu tiên đường truyền trung tâm nếu có. Nếu dùng ngoại biên, cần theo dõi thoát mạch sát theo phác đồ bệnh viện.")

# ============================================================
# Module 6: Inotrope decision support and calculator
# ============================================================

st.header("6. Inotrope: quyết định dùng, chọn thuốc và tính tốc độ bơm")

st.write(
    "Mục này dành cho bệnh cảnh có rối loạn chức năng tim/low-output phenotype: EF giảm, chi lạnh, lactate cao, CRT kéo dài, "
    "tưới máu kém dù MAP đã được hỗ trợ hoặc không thể truyền thêm dịch an toàn."
)

col_ino_a, col_ino_b, col_ino_c = st.columns(3)
with col_ino_a:
    ef_reduced = st.checkbox("EF giảm rõ / LV co bóp kém", value=severe_hfrEF or cardiogenic_active)
    cold_hypoperfusion = st.checkbox("Chi lạnh / CRT kéo dài / mottling", value=True)
    persistent_lactate = st.checkbox("Lactate cao hoặc không giảm", value=lactate > 4)

with col_ino_b:
    norepi_running_or_planned = st.checkbox("Đang/chuẩn bị chạy Noradrenaline", value=map_mmHg < 65)
    map_supported = st.checkbox("MAP đã/đang được hỗ trợ bằng vận mạch", value=map_mmHg >= 60 or norepi_running_or_planned)
    rapid_af = st.checkbox("Rung nhĩ nhanh / nhịp nhanh đáng kể", value=heart_rate >= 120)

with col_ino_c:
    low_vti_or_low_co = st.checkbox("VTI/CO thấp trên POCUS/monitor", value=False)
    rv_failure = st.checkbox("Nghi suy thất phải / tăng áp phổi", value=False)
    ischemia_concern = st.checkbox("Nghi thiếu máu cơ tim cấp", value=False)

inotrope_rec = suggest_inotrope(
    cardiogenic_active=cardiogenic_active,
    septic_active=septic_active,
    fluid_overload_risk=fluid_overload_risk,
    fluid_responsive=fluid_responsive,
    map_mmHg=map_mmHg,
    lactate=lactate,
    ef_reduced=ef_reduced,
    cold_hypoperfusion=cold_hypoperfusion or persistent_lactate or low_vti_or_low_co,
    pulmonary_edema=pulmonary_edema or diffuse_b_lines,
    rapid_af=rapid_af,
    ckd=ckd_any or anuric_ckd,
)

if inotrope_rec["level"] == "RED":
    st.error(inotrope_rec["text"])
elif inotrope_rec["level"] == "ORANGE":
    st.warning(inotrope_rec["text"])
else:
    st.info(inotrope_rec["text"])

for warning in inotrope_rec["warnings"]:
    st.warning(warning)

if rv_failure:
    st.info("Suy thất phải/tăng áp phổi: cân nhắc chuyên gia hồi sức/tim mạch; lựa chọn inotrope/giãn mạch phổi tùy huyết động và oxy hóa.")

if ischemia_concern:
    st.warning("Nghi thiếu máu cơ tim cấp: kiểm soát nhịp, ECG/troponin, hội chẩn tim mạch/cathlab; inotrope có thể tăng nhu cầu oxy cơ tim.")

st.subheader("Tính tốc độ bơm inotrope")

inotrope_preset_options = list(INOTROPE_PRESETS.keys()) + ["Tùy chỉnh"]
ino_default_index = inotrope_preset_options.index(inotrope_rec["preset"])

col_ino_calc1, col_ino_calc2 = st.columns(2)
with col_ino_calc1:
    inotrope_preset = st.selectbox("Chọn preset inotrope", inotrope_preset_options, index=ino_default_index)
with col_ino_calc2:
    inotrope_dose = st.number_input(
        "Liều inotrope mong muốn (mcg/kg/phút)",
        min_value=0.001,
        max_value=30.0,
        value=float(inotrope_rec["dose"]),
        step=0.5,
        format="%.3f",
    )

if inotrope_preset != "Tùy chỉnh":
    ino_selected = INOTROPE_PRESETS[inotrope_preset]
    inotrope_name = ino_selected["drug"]
    ino_total_drug_mg = ino_selected["total_drug_mg"]
    ino_final_volume_ml = ino_selected["final_volume_ml"]
else:
    col_ino_custom1, col_ino_custom2, col_ino_custom3 = st.columns(3)
    with col_ino_custom1:
        inotrope_name = st.selectbox("Tên inotrope", ["Dobutamine", "Milrinone", "Khác"])
    with col_ino_custom2:
        ino_total_drug_mg = st.number_input("Tổng lượng inotrope trong bơm (mg)", min_value=0.001, max_value=1000.0, value=250.0, step=10.0)
    with col_ino_custom3:
        ino_final_volume_ml = st.number_input("Tổng thể tích inotrope sau pha (mL)", min_value=1.0, max_value=500.0, value=50.0, step=1.0)

inotrope_result = calculate_infusion_rate(weight_kg, inotrope_dose, ino_total_drug_mg, ino_final_volume_ml)

ino_col1, ino_col2, ino_col3, ino_col4 = st.columns(4)
ino_col1.metric("Inotrope", inotrope_name)
ino_col2.metric("Pha thuốc", f"{ino_total_drug_mg:.1f} mg/{ino_final_volume_ml:.0f} mL")
ino_col3.metric("Nồng độ", f"{inotrope_result['final_concentration_mcg_ml']:.0f} mcg/mL")
ino_col4.metric("Tốc độ bơm", f"{inotrope_result['pump_rate_ml_hour']:.2f} mL/giờ")

if inotrope_name == "Dobutamine":
    if inotrope_dose < 2.5:
        st.info("Dobutamine liều rất thấp. Có thể phù hợp để test đáp ứng ở bệnh nhân dễ tụt HA/loạn nhịp.")
    elif 2.5 <= inotrope_dose <= 20:
        st.success("Khoảng liều Dobutamine thường dùng: 2,5–20 mcg/kg/phút, chỉnh theo đáp ứng tưới máu và tác dụng phụ.")
    else:
        st.warning("Dobutamine >20 mcg/kg/phút: liều cao, nguy cơ nhịp nhanh/loạn nhịp/tăng nhu cầu oxy cơ tim.")

if inotrope_name == "Milrinone":
    st.warning("Milrinone có thể gây tụt HA và tích lũy ở bệnh thận. Trong sốc, thường tránh bolus loading và cần giảm liều nếu CKD.")
    if inotrope_dose > 0.75:
        st.error("Milrinone >0,75 mcg/kg/phút: kiểm tra lại liều và chức năng thận.")

# ============================================================
# Module 7: High-dose vasoactive warning
# ============================================================

st.header("7. Cảnh báo liều cao và checklist tìm nguyên nhân")

if drug_name == "Noradrenaline":
    if desired_dose > 1.0:
        st.error("CẢNH BÁO ĐỎ: Noradrenaline > 1 mcg/kg/phút. Đây là liều rất cao. Cần gọi hỗ trợ hồi sức, đánh giá lại nguyên nhân sốc và cân nhắc phối hợp vận mạch/inotrope/mechanical support.")
    elif desired_dose > 0.5:
        st.warning("Cảnh báo: Noradrenaline > 0,5 mcg/kg/phút. Cần đánh giá lại nguyên nhân sốc, đáp ứng dịch, chức năng tim và nguồn nhiễm.")
    else:
        st.success("Liều Noradrenaline hiện chưa vượt ngưỡng cảnh báo cao trong app.")

elif drug_name == "Adrenaline":
    if desired_dose > 0.5:
        st.warning("Adrenaline liều cao. Theo dõi loạn nhịp, lactate, thiếu máu cơ tim và đánh giá lại chỉ định.")
    else:
        st.success("Liều Adrenaline hiện chưa vượt ngưỡng cảnh báo cao trong app.")

st.subheader("Checklist cần xem lại khi cần vận mạch/inotrope liều cao")
col_hd1, col_hd2, col_hd3 = st.columns(3)
with col_hd1:
    severe_acidosis = st.checkbox("Toan máu nặng")
    hypocalcemia = st.checkbox("Hạ calci")
    hypovolemia_unresolved = st.checkbox("Còn thiếu thể tích tuần hoàn")
with col_hd2:
    tension_pneumothorax = st.checkbox("Tràn khí màng phổi áp lực")
    tamponade = st.checkbox("Tamponade tim")
    massive_pe = st.checkbox("Thuyên tắc phổi nguy cơ cao")
with col_hd3:
    heart_failure = st.checkbox("Suy tim / rối loạn co bóp")
    uncontrolled_source = st.checkbox("Nguồn nhiễm chưa kiểm soát")
    bleeding = st.checkbox("Xuất huyết chưa kiểm soát")

high_dose_red_flags = any([
    severe_acidosis, hypocalcemia, hypovolemia_unresolved, tension_pneumothorax,
    tamponade, massive_pe, heart_failure, uncontrolled_source, bleeding,
])

if high_dose_red_flags:
    st.error("Có yếu tố có thể làm sốc kháng trị hoặc tăng nhu cầu thuốc vận mạch/inotrope. Cần xử trí nguyên nhân song song, không chỉ tăng liều thuốc.")
else:
    st.info("Chưa chọn yếu tố làm tăng nhu cầu vận mạch/inotrope trong checklist.")


# ============================================================
# Module 8: Empiric antibiotic assistant
# ============================================================

st.header("8. Kháng sinh kinh nghiệm trong nghi nhiễm khuẩn / sepsis")

st.warning(
    "Module này chỉ gợi ý coverage và nhóm kháng sinh kinh nghiệm. Không tự động kê đơn cố định. "
    "Luôn đối chiếu phác đồ bệnh viện, antibiogram, dị ứng thuốc, chức năng thận, cân nặng và cấy vi sinh."
)

auto_show_antibiotic = septic_active or temperature >= 38.0 or shock_or_hypoperfusion
enable_antibiotic_module = st.checkbox(
    "Mở module kháng sinh kinh nghiệm",
    value=auto_show_antibiotic,
    key="abx_enable_module",
)

antibiotic_summary_lines = []
antibiotic_recommendation = None
infection_focus = "Không đánh giá"
community_or_hospital = "Không đánh giá"

if enable_antibiotic_module:
    possible_sepsis = septic_active or temperature >= 38.0
    septic_shock_for_abx = possible_sepsis and (map_mmHg < 65 or lactate >= 4)

    timing_level, timing_text = antibiotic_timing_advice(
        septic_shock=septic_shock_for_abx,
        possible_sepsis=possible_sepsis,
    )

    st.subheader("8.1. Thời điểm dùng kháng sinh")

    if timing_level == "RED":
        st.error(timing_text)
    elif timing_level == "ORANGE":
        st.warning(timing_text)
    else:
        st.info(timing_text)

    st.subheader("8.2. Ổ nhiễm nghi ngờ và bối cảnh mắc phải")

    col_abx_focus1, col_abx_focus2, col_abx_focus3 = st.columns(3)

    with col_abx_focus1:
        infection_focus = st.selectbox(
            "Ổ nhiễm nghi ngờ",
            [
                "Viêm phổi cộng đồng nặng",
                "Viêm phổi bệnh viện / ICU / VAP",
                "Nhiễm khuẩn tiết niệu phức tạp / Pyelonephritis",
                "Nhiễm khuẩn ổ bụng",
                "Da - mô mềm nặng",
                "Nhiễm khuẩn huyết liên quan catheter",
                "Chưa rõ ổ nhiễm",
            ],
            index=0,
            key="abx_infection_focus",
        )

    with col_abx_focus2:
        community_or_hospital = st.selectbox(
            "Bối cảnh nhiễm khuẩn",
            ["Cộng đồng", "Bệnh viện", "ICU/VAP"],
            index=0 if infection_focus == "Viêm phổi cộng đồng nặng" else 1,
            key="abx_context",
        )

    with col_abx_focus3:
        egfr = st.number_input(
            "eGFR/CrCl ước tính (mL/phút)",
            min_value=0.0,
            max_value=200.0,
            value=45.0 if ckd_any else 80.0,
            step=1.0,
            key="abx_egfr",
        )

    st.subheader("8.3. Cấy bệnh phẩm trước kháng sinh nếu không trì hoãn")

    col_culture1, col_culture2, col_culture3 = st.columns(3)

    with col_culture1:
        blood_culture = st.checkbox("Cấy máu 2 bộ", value=septic_shock_for_abx, key="abx_culture_blood")
        sputum_culture = st.checkbox("Cấy đàm / hút đàm", value="phổi" in infection_focus.lower(), key="abx_culture_sputum")

    with col_culture2:
        urine_culture = st.checkbox("Cấy nước tiểu", value="tiết niệu" in infection_focus.lower(), key="abx_culture_urine")
        sterile_fluid_culture = st.checkbox("Cấy dịch vô khuẩn / dịch ổ bụng / màng phổi", value=False, key="abx_culture_fluid")

    with col_culture3:
        catheter_culture = st.checkbox("Cấy catheter nếu nghi liên quan", value="catheter" in infection_focus.lower(), key="abx_culture_catheter")
        source_control_needed = st.checkbox("Cần đánh giá kiểm soát nguồn nhiễm", value=infection_focus in ["Nhiễm khuẩn ổ bụng", "Da - mô mềm nặng"], key="abx_source_control")

    if septic_shock_for_abx:
        st.error("Septic shock: không trì hoãn kháng sinh để chờ cấy nếu việc lấy cấy gây chậm trễ đáng kể.")

    st.write("Gợi ý bệnh phẩm theo ổ nhiễm:")
    for culture_item in ANTIBIOTIC_PROTOCOLS.get(infection_focus, ANTIBIOTIC_PROTOCOLS["Chưa rõ ổ nhiễm"])["cultures"]:
        st.write(f"- {culture_item}")

    if source_control_needed:
        st.error("Cần đánh giá source control song song, vì kháng sinh đơn độc có thể không đủ nếu còn ổ nhiễm cần dẫn lưu/can thiệp.")

    st.subheader("8.4. Nguy cơ vi khuẩn đa kháng và yếu tố cần mở rộng phổ")

    col_mdr1, col_mdr2, col_mdr3 = st.columns(3)

    with col_mdr1:
        recent_hospitalization = st.checkbox("Nhập viện trong 90 ngày", value=False, key="abx_recent_hosp")
        recent_antibiotics = st.checkbox("Dùng kháng sinh trong 90 ngày", value=False, key="abx_recent_abx")
        prior_mdr = st.checkbox("Tiền sử cấy MDR/ESBL/MRSA/CRE", value=False, key="abx_prior_mdr")

    with col_mdr2:
        nursing_home = st.checkbox("Chăm sóc dài hạn / viện dưỡng lão", value=False, key="abx_nursing_home")
        hemodialysis = st.checkbox("Lọc máu chu kỳ", value=False, key="abx_hemodialysis")
        immunosuppression = st.checkbox("Suy giảm miễn dịch", value=False, key="abx_immunosuppression")

    with col_mdr3:
        invasive_device = st.checkbox("Catheter/sonde/dụng cụ xâm lấn lâu ngày", value=False, key="abx_invasive_device")
        beta_lactam_allergy = st.checkbox("Dị ứng beta-lactam nặng", value=False, key="abx_beta_allergy")
        prior_colonization_unknown = st.checkbox("Chưa rõ tiền sử vi sinh / thiếu dữ liệu", value=True, key="abx_unknown_micro")

    mdr_risk, mdr_factors = assess_mdr_risk(
        recent_hospitalization=recent_hospitalization,
        recent_antibiotics=recent_antibiotics,
        prior_mdr=prior_mdr,
        nursing_home=nursing_home,
        hemodialysis=hemodialysis,
        immunosuppression=immunosuppression,
        invasive_device=invasive_device,
    )

    col_cov1, col_cov2, col_cov3, col_cov4 = st.columns(4)
    with col_cov1:
        mrsa_risk = st.checkbox("Nguy cơ MRSA", value=prior_mdr, key="abx_mrsa")
    with col_cov2:
        pseudomonas_risk = st.checkbox(
            "Nguy cơ Pseudomonas",
            value=infection_focus in ["Viêm phổi bệnh viện / ICU / VAP"] or recent_hospitalization,
            key="abx_pseudomonas",
        )
    with col_cov3:
        esbl_risk = st.checkbox("Nguy cơ ESBL", value=prior_mdr or recent_antibiotics, key="abx_esbl")
    with col_cov4:
        candida_risk = st.checkbox("Nguy cơ Candida/nấm xâm lấn", value=False, key="abx_candida")

    if mdr_risk:
        st.warning("Có yếu tố nguy cơ MDR: " + ", ".join(mdr_factors))
    elif prior_colonization_unknown:
        st.info("Chưa có yếu tố MDR rõ, nhưng tiền sử vi sinh chưa đầy đủ. Cần kiểm tra hồ sơ cấy cũ nếu có.")
    else:
        st.success("Chưa ghi nhận yếu tố nguy cơ MDR rõ.")

    antibiotic_recommendation = recommend_antibiotic_coverage(
        infection_focus=infection_focus,
        community_or_hospital=community_or_hospital,
        mdr_risk=mdr_risk,
        mrsa_risk=mrsa_risk,
        pseudomonas_risk=pseudomonas_risk,
        esbl_risk=esbl_risk,
        candida_risk=candida_risk,
        beta_lactam_allergy=beta_lactam_allergy,
        egfr=egfr,
    )

    st.subheader("8.5. Gợi ý coverage và nhóm kháng sinh")

    st.write("**Cần bao phủ:**")
    for item in antibiotic_recommendation["coverage"]:
        st.write(f"- {item}")

    st.write("**Gợi ý nhóm kháng sinh kinh nghiệm:**")
    for item in antibiotic_recommendation["suggestions"]:
        st.write(f"- {item}")

    if antibiotic_recommendation["warnings"]:
        for warning in antibiotic_recommendation["warnings"]:
            st.warning(warning)

    st.write("**Ghi chú source control:**")
    for note in antibiotic_recommendation["notes"]:
        st.write(f"- {note}")

    st.subheader("8.6. Stewardship và review sau 24–48–72 giờ")
    st.write("- Đánh giá lại chẩn đoán nhiễm khuẩn khi có diễn tiến lâm sàng, hình ảnh học và kết quả cấy.")
    st.write("- Xuống thang kháng sinh khi có kháng sinh đồ hoặc khi xác suất MDR thấp.")
    st.write("- Ngưng kháng sinh nếu xác suất nhiễm khuẩn thấp và có chẩn đoán thay thế phù hợp.")
    st.write("- Chỉnh liều theo eGFR/CrCl, cân nặng, mức độ nặng, lọc máu và khuyến cáo dược lâm sàng.")

    antibiotic_summary_lines.append(f"- Kháng sinh: đã bật module; ổ nhiễm nghi ngờ: {infection_focus}; bối cảnh: {community_or_hospital}")
    antibiotic_summary_lines.append(f"- Timing: {timing_text}")
    antibiotic_summary_lines.append("- Coverage chính: " + "; ".join(antibiotic_recommendation["coverage"][:5]))
    antibiotic_summary_lines.append("- Gợi ý nhóm: " + "; ".join(antibiotic_recommendation["suggestions"][:4]))

else:
    st.info("Module kháng sinh đang tắt. Có thể bật khi nghi nhiễm khuẩn/sepsis hoặc cần checklist cấy bệnh phẩm.")
    antibiotic_summary_lines.append("- Kháng sinh: module chưa bật")


# ============================================================
# Module 9: Final summary
# ============================================================

st.header("9. Tóm tắt quyết định")

summary_lines = []
summary_lines.append(f"- Cân nặng: {weight_kg:.1f} kg")
summary_lines.append(f"- MAP hiện tại: {map_mmHg:.0f} mmHg")
summary_lines.append(f"- Lactate: {lactate:.1f} mmol/L")
summary_lines.append(f"- Nước tiểu: {urine_output_ml_kg_h:.1f} mL/kg/giờ")
summary_lines.append(f"- SpO₂: {spo2:.0f}%")
summary_lines.append(f"- Tần số tim: {heart_rate:.0f} lần/phút")

if active_shocks:
    summary_lines.append(f"- Phenotype sốc đang hoạt động: {', '.join(active_shocks)}")
else:
    summary_lines.append("- Phenotype sốc: chưa rõ")

if mixed_patterns:
    summary_lines.append("- Kết luận: bệnh cảnh gợi ý sốc hỗn hợp")
else:
    summary_lines.append("- Kết luận: chưa đủ dữ kiện kết luận sốc hỗn hợp")

if fluid_overload_risk:
    summary_lines.append("- Dịch: nguy cơ quá tải/fluid intolerance → không truyền 30 mL/kg máy móc")
else:
    summary_lines.append(f"- Dịch: có thể tham khảo 30 mL/kg = {standard_fluid_ml:.0f} mL nếu phù hợp")

summary_lines.append(f"- Fluid responsiveness: {fr_interpretation}")
summary_lines.append(f"- Chiến lược dịch: {strategy_text}")
summary_lines.append(f"- Vận mạch: {drug_name}, pha {total_drug_mg:.1f} mg/{final_volume_ml:.0f} mL, nồng độ {vasopressor_result['final_concentration_mcg_ml']:.1f} mcg/mL")
summary_lines.append(f"- Liều vận mạch: {desired_dose:.3f} mcg/kg/phút → {vasopressor_result['pump_rate_ml_hour']:.2f} mL/giờ")

if inotrope_rec["need_inotrope"]:
    summary_lines.append(f"- Inotrope: cân nhắc {inotrope_name}, pha {ino_total_drug_mg:.1f} mg/{ino_final_volume_ml:.0f} mL, liều {inotrope_dose:.3f} mcg/kg/phút → {inotrope_result['pump_rate_ml_hour']:.2f} mL/giờ")
else:
    summary_lines.append("- Inotrope: chưa đủ dữ kiện để tự động gợi ý; tiếp tục đánh giá EF/VTI/CO và tưới máu")

summary_lines.extend(antibiotic_summary_lines)

for line in summary_lines:
    st.write(line)

st.divider()
st.caption(
    "Clinical reminder: điều trị sốc cần song song ABC, oxy/thở máy khi cần, cấy bệnh phẩm, kháng sinh sớm nếu nghi nhiễm khuẩn, "
    "kiểm soát nguồn nhiễm, POCUS lặp lại, theo dõi MAP/CRT/lactate/nước tiểu và hội chẩn ICU."
)
