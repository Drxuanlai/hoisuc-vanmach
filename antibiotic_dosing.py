# ============================================================
# Antibiotic renal dosing helper for ICU prototype
# ------------------------------------------------------------
# This module provides Cockcroft-Gault CrCl estimation and
# renal-dose suggestion cards for a limited list of ICU antibiotics.
# It is decision support only and must be checked against local
# antibiogram, pharmacy protocol, drug levels, MIC, severity and RRT.
# ============================================================

from __future__ import annotations


def calculate_ibw(height_cm: float, is_male: bool) -> float:
    """Ideal Body Weight by Devine formula."""
    height_in = height_cm / 2.54
    inches_over_5ft = max(0.0, height_in - 60.0)
    if is_male:
        return 50.0 + 2.3 * inches_over_5ft
    return 45.5 + 2.3 * inches_over_5ft


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """Body mass index, kg/m²."""
    height_m = height_cm / 100.0
    if height_m <= 0:
        return 0.0
    return weight_kg / (height_m ** 2)


def choose_weight_for_cg(weight_kg: float, height_cm: float, is_male: bool) -> tuple[float, str, float, float]:
    """
    Choose weight for Cockcroft-Gault.

    Prototype rule:
    - BMI <= 30: Actual body weight.
    - BMI > 30 and actual weight > IBW: Adjusted body weight.

    Adjusted Body Weight = IBW + 0.4 × (Actual - IBW)

    Clinical note:
    In ICU patients with edema, ascites, amputation, pregnancy, severe cachexia,
    severe obesity, AKI or dialysis, Cockcroft-Gault can be misleading.
    """
    bmi = calculate_bmi(weight_kg, height_cm)
    ibw = calculate_ibw(height_cm, is_male)

    if bmi > 30 and weight_kg > ibw:
        adjusted_weight = ibw + 0.4 * (weight_kg - ibw)
        return adjusted_weight, "Adjusted Body Weight do BMI > 30", bmi, ibw

    return weight_kg, "Actual Body Weight", bmi, ibw


def calculate_crcl(age: float, weight: float, is_male: bool, serum_creatinine: float) -> float:
    """
    Cockcroft-Gault creatinine clearance, mL/min.

    Male:
        CrCl = ((140 - age) × weight) / (72 × SCr)
    Female:
        CrCl = male CrCl × 0.85

    weight should be the selected CG weight: actual, IBW or adjusted weight.
    """
    if age <= 0 or weight <= 0 or serum_creatinine <= 0:
        return 0.0

    crcl = ((140.0 - age) * weight) / (72.0 * serum_creatinine)
    if not is_male:
        crcl *= 0.85
    return max(crcl, 0.0)


def get_renal_band(crcl: float, on_hemodialysis: bool = False) -> str:
    """Return renal band key for dosing."""
    if on_hemodialysis or crcl < 10:
        return "lt10_or_hd"
    if 10 <= crcl < 30:
        return "10_29"
    if 30 <= crcl <= 50:
        return "30_50"
    return "gt50"


ANTIBIOTIC_DOSING = {
    "Meropenem": {
        "standard": "1 g IV mỗi 8 giờ; nhiễm nặng/ICU có thể cần truyền kéo dài theo phác đồ",
        "renal": {
            "30_50": "1 g IV mỗi 12 giờ",
            "10_29": "500 mg IV mỗi 12 giờ",
            "lt10_or_hd": "500 mg IV mỗi 24 giờ; nếu lọc máu, thường dùng sau phiên lọc theo phác đồ",
        },
        "warnings": [
            "Hiệu chỉnh liều khi CrCl ≤50 mL/phút.",
            "Nguy cơ co giật/độc thần kinh tăng khi suy thận hoặc bệnh lý thần kinh trung ương.",
            "Cân nhắc truyền kéo dài trong sepsis/ICU nếu phác đồ bệnh viện cho phép.",
        ],
    },
    "Piperacillin/Tazobactam": {
        "standard": "4.5 g IV mỗi 6 giờ; ICU có thể dùng truyền kéo dài theo phác đồ",
        "renal": {
            "30_50": "3.375–4.5 g IV mỗi 6–8 giờ tùy mức độ nặng và phác đồ",
            "10_29": "2.25–3.375 g IV mỗi 6–8 giờ",
            "lt10_or_hd": "2.25 g IV mỗi 8–12 giờ; nếu lọc máu, cần liều sau lọc theo phác đồ",
        },
        "warnings": [
            "Cần chỉnh liều theo CrCl.",
            "Có tải natri; thận trọng ở suy tim/phù phổi/quá tải dịch.",
            "Phối hợp vancomycin có thể tăng nguy cơ AKI trong một số bối cảnh.",
        ],
    },
    "Imipenem/Cilastatin": {
        "standard": "500 mg IV mỗi 6 giờ hoặc 1 g IV mỗi 8 giờ tùy chỉ định",
        "renal": {
            "30_50": "250–500 mg IV mỗi 6–8 giờ",
            "10_29": "250–500 mg IV mỗi 12 giờ",
            "lt10_or_hd": "Thường tránh hoặc dùng rất thận trọng; cần phác đồ thận/lọc máu cụ thể",
        },
        "warnings": [
            "Nguy cơ co giật cao hơn ở suy thận/CNS disease; bắt buộc chỉnh liều.",
            "Không tự động chọn nếu CrCl rất thấp mà chưa có dược lâm sàng/hồi sức hỗ trợ.",
        ],
    },
    "Cefepime": {
        "standard": "2 g IV mỗi 8–12 giờ tùy ổ nhiễm và mức độ nặng",
        "renal": {
            "30_50": "2 g IV mỗi 12–24 giờ tùy chỉ định",
            "10_29": "1–2 g IV mỗi 24 giờ",
            "lt10_or_hd": "1 g IV mỗi 24 giờ; nếu lọc máu, dùng sau lọc theo phác đồ",
        },
        "warnings": [
            "Cần chỉnh liều theo CrCl.",
            "Nguy cơ độc thần kinh/encephalopathy/co giật tăng rõ khi suy thận hoặc quá liều.",
        ],
    },
    "Ciprofloxacin": {
        "standard": "400 mg IV mỗi 8–12 giờ",
        "renal": {
            "30_50": "400 mg IV mỗi 12 giờ",
            "10_29": "400 mg IV mỗi 18–24 giờ",
            "lt10_or_hd": "400 mg IV mỗi 24 giờ; dùng sau lọc máu nếu có",
        },
        "warnings": [
            "Fluoroquinolone: nguy cơ kéo dài QT, loạn nhịp, viêm/đứt gân, rối loạn đường huyết, tác dụng phụ thần kinh.",
            "Không phải lựa chọn đơn độc đáng tin cho sepsis nặng nếu nguy cơ kháng thuốc cao.",
        ],
    },
    "Levofloxacin": {
        "standard": "750 mg IV/PO mỗi 24 giờ",
        "renal": {
            "30_50": "750 mg liều đầu, sau đó 750 mg mỗi 48 giờ",
            "10_29": "750 mg liều đầu, sau đó 500 mg mỗi 48 giờ",
            "lt10_or_hd": "750 mg liều đầu, sau đó 500 mg mỗi 48 giờ; dùng sau lọc máu nếu có",
        },
        "warnings": [
            "Fluoroquinolone: nguy cơ kéo dài QT/xoắn đỉnh, đặc biệt khi nhịp nhanh, hạ K/Mg, bệnh tim, phối hợp thuốc kéo dài QT.",
            "Cảnh báo viêm/đứt gân, rối loạn đường huyết, tác dụng phụ thần kinh.",
        ],
    },
    "Vancomycin": {
        "standard": "Loading 20–25 mg/kg IV nếu nhiễm nặng; duy trì theo AUC/MIC hoặc nồng độ và chức năng thận",
        "renal": {
            "30_50": "Cá thể hóa khoảng cách liều; đo nồng độ sớm và chỉnh theo AUC/trough theo protocol",
            "10_29": "Cá thể hóa; thường kéo dài khoảng cách liều và theo dõi nồng độ",
            "lt10_or_hd": "Liều theo protocol lọc máu; thường cần loading dose rồi đo nồng độ trước/sau lọc tùy trung tâm",
        },
        "warnings": [
            "Nguy cơ độc thận, nhất là khi phối hợp thuốc độc thận hoặc bệnh thận nền.",
            "Ưu tiên theo dõi AUC/MIC 400–600 trong nhiễm MRSA nặng nếu có điều kiện.",
            "Nếu không có AUC, cần theo dõi nồng độ theo protocol bệnh viện; không chỉnh liều mù.",
        ],
    },
}


def get_antibiotic_dose_recommendation(antibiotic_name: str, crcl: float, on_hemodialysis: bool = False) -> dict:
    """Return renal-adjusted dose recommendation for selected antibiotic."""
    data = ANTIBIOTIC_DOSING[antibiotic_name]
    band = get_renal_band(crcl, on_hemodialysis)

    if band == "gt50":
        dose_text = data["standard"]
        renal_label = "CrCl > 50 mL/phút"
    elif band == "30_50":
        dose_text = data["renal"]["30_50"]
        renal_label = "CrCl 30–50 mL/phút"
    elif band == "10_29":
        dose_text = data["renal"]["10_29"]
        renal_label = "CrCl 10–29 mL/phút"
    else:
        dose_text = data["renal"]["lt10_or_hd"]
        renal_label = "CrCl <10 mL/phút hoặc lọc máu"

    return {
        "antibiotic": antibiotic_name,
        "renal_label": renal_label,
        "dose_text": dose_text,
        "warnings": data["warnings"],
    }


def generate_antibiotic_clinical_alerts(
    antibiotic_name: str,
    heart_rate: float,
    drug_name: str,
    inotrope_name: str,
    desired_dose: float,
    inotrope_dose: float,
    crcl: float,
    on_hemodialysis: bool,
    ckd_any: bool,
    anuric_ckd: bool,
    pulmonary_edema: bool,
) -> list[tuple[str, str]]:
    """
    Generate patient-specific clinical alerts.

    severity values: "error", "warning", "info".
    """
    alerts: list[tuple[str, str]] = []

    vasoactive_running = (
        (drug_name not in ["Không dùng vận mạch", "", None] and desired_dose > 0)
        or (inotrope_name not in ["Không dùng inotrope", "", None] and inotrope_dose > 0)
    )

    if antibiotic_name in ["Levofloxacin", "Ciprofloxacin"]:
        if heart_rate > 120 or vasoactive_running:
            alerts.append((
                "error",
                "Cảnh giác nguy cơ kéo dài QT / xoắn đỉnh / loạn nhịp vì bệnh nhân đang có nhịp nhanh "
                "và/hoặc đang dùng vận mạch/inotrope. Kiểm tra ECG, QTc, K⁺, Mg²⁺ và thuốc kéo dài QT khác.",
            ))
        else:
            alerts.append((
                "warning",
                "Fluoroquinolone có nguy cơ kéo dài QT, rối loạn đường huyết, tác dụng phụ thần kinh và bệnh lý gân. "
                "Nên kiểm tra ECG/QTc nếu bệnh nhân có nguy cơ tim mạch.",
            ))

    if antibiotic_name == "Vancomycin":
        alerts.append((
            "error",
            "Vancomycin: nguy cơ độc thận. Cần therapeutic drug monitoring. "
            "Ưu tiên AUC/MIC 400–600 nếu có điều kiện; nếu không, theo dõi nồng độ theo protocol bệnh viện.",
        ))
        if crcl < 50 or ckd_any or anuric_ckd or on_hemodialysis:
            alerts.append((
                "error",
                "Bệnh nhân có suy thận/CKD/lọc máu: không dùng liều duy trì vancomycin cố định. "
                "Cần loading dose nếu nhiễm nặng rồi chỉnh theo nồng độ và lịch lọc máu.",
            ))

    if antibiotic_name in ["Meropenem", "Imipenem/Cilastatin", "Cefepime"] and crcl < 50:
        alerts.append((
            "warning",
            "Beta-lactam này cần chỉnh liều theo thận. Suy thận làm tăng nguy cơ độc thần kinh/co giật nếu quá liều.",
        ))

    if antibiotic_name == "Piperacillin/Tazobactam" and pulmonary_edema:
        alerts.append((
            "warning",
            "Piperacillin/Tazobactam có tải natri đáng kể; thận trọng ở bệnh nhân suy tim/phù phổi/quá tải dịch.",
        ))

    return alerts
