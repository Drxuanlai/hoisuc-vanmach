# shock_logic.py
# Logic phân loại sốc, dịch và đáp ứng dịch.

def calculate_fluid_volume(weight_kg: float, dose_ml_per_kg: float = 30.0) -> float:
    """Tính lượng dịch tinh thể theo mL/kg."""
    return weight_kg * dose_ml_per_kg


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
    esrd_or_anuric: bool = False,
    pulmonary_edema: bool = False,
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

    if esrd_or_anuric and pulmonary_edema and map_mmHg >= 65:
    return (
        "RED",
        "ESRD/chạy thận hoặc vô niệu kèm phù phổi cấp và MAP hiện không thấp. "
        "Không bolus dịch. Ưu tiên xử trí suy hô hấp, POCUS tim-phổi, cân nhắc lọc máu/siêu lọc cấp cứu, "
        "kháng sinh sớm nếu nghi nhiễm khuẩn và tìm source control."
    )
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


