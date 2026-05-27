# ============================================================
# Antibiotic renal dosing helper for ICU prototype
# ------------------------------------------------------------
# Decision-support only. Dose recommendations must be validated
# against local protocol/Sanford/UpToDate, antibiogram, MIC,
# dialysis/CRRT prescription, TDM and ICU pharmacist review.
# ============================================================

from __future__ import annotations


def calculate_ibw(height_cm: float, is_male: bool) -> float:
    """Ideal Body Weight by Devine formula."""
    height_in = height_cm / 2.54
    inches_over_5ft = max(0.0, height_in - 60.0)
    return (50.0 if is_male else 45.5) + 2.3 * inches_over_5ft


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
    Clinical note: ICU patients with edema/ascites/amputation/pregnancy/cachexia/
    AKI/dialysis can have misleading Cockcroft-Gault estimates.
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
    Male: CrCl = ((140 - age) × weight) / (72 × SCr)
    Female: CrCl = male CrCl × 0.85
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
        return "crcl_lt_10"
    if 10 <= crcl < 30:
        return "crcl_10_29"
    if 30 <= crcl <= 50:
        return "crcl_30_50"
    return "crcl_gt_50"


# Required copy-friendly dictionary format.
ANTIBIOTIC_DICT = {
    "Levofloxacin": {
        "crcl_gt_50": "750 mg IV mỗi 24 giờ",
        "crcl_30_50": "750 mg IV liều đầu, sau đó 750 mg IV mỗi 48 giờ",
        "crcl_10_29": "750 mg IV liều đầu, sau đó 500 mg IV mỗi 48 giờ",
        "crcl_lt_10": "750 mg IV liều đầu, sau đó 500 mg IV mỗi 48 giờ; nếu lọc máu, dùng sau phiên lọc theo phác đồ bệnh viện",
        "warnings": [
            "Fluoroquinolone: nguy cơ kéo dài QT, xoắn đỉnh, loạn nhịp; kiểm tra ECG/QTc, K⁺, Mg²⁺ nếu nguy cơ cao.",
            "Cảnh báo đỏ nếu rung nhĩ/nhịp nhanh >120 lần/phút hoặc đang dùng Dobutamine/Noradrenaline: tăng nguy cơ QT/loạn nhịp.",
            "Nguy cơ rối loạn đường huyết, tác dụng phụ thần kinh, viêm gân/đứt gân; thận trọng ở người già, CKD, dùng corticosteroid.",
            "Không nên dùng đơn độc trong septic shock nếu nguy cơ kháng thuốc cao; đối chiếu kháng sinh đồ địa phương.",
        ],
    },
    "Meropenem": {
        "crcl_gt_50": "1 g IV mỗi 8 giờ; nhiễm rất nặng/ICU có thể cân nhắc 2 g IV mỗi 8 giờ hoặc truyền kéo dài theo phác đồ",
        "crcl_30_50": "1 g IV mỗi 12 giờ",
        "crcl_10_29": "500 mg IV mỗi 12 giờ",
        "crcl_lt_10": "500 mg IV mỗi 24 giờ; nếu lọc máu, dùng sau phiên lọc theo phác đồ bệnh viện",
        "warnings": [
            "Cần chỉnh liều khi CrCl ≤50 mL/phút.",
            "Nguy cơ độc thần kinh/co giật tăng khi suy thận, bệnh lý thần kinh trung ương hoặc quá liều.",
            "Trong ICU/sepsis, cân nhắc truyền kéo dài để tối ưu thời gian trên MIC nếu phác đồ bệnh viện cho phép.",
            "Không bao phủ MRSA, Enterococcus faecium, Stenotrophomonas.",
        ],
    },
    "Piperacillin/Tazobactam": {
        "crcl_gt_50": "4.5 g IV mỗi 6 giờ; ICU thường ưu tiên truyền kéo dài 3–4 giờ nếu phác đồ cho phép",
        "crcl_30_50": "4.5 g IV mỗi 8 giờ hoặc 3.375 g IV mỗi 6–8 giờ tùy ổ nhiễm/mức độ nặng",
        "crcl_10_29": "3.375 g IV mỗi 8 giờ hoặc 2.25 g IV mỗi 6–8 giờ tùy phác đồ",
        "crcl_lt_10": "2.25 g IV mỗi 8–12 giờ; nếu lọc máu, cần liều bổ sung sau lọc theo phác đồ bệnh viện",
        "warnings": [
            "Cần chỉnh liều theo CrCl; cân nhắc truyền kéo dài trong nhiễm nặng/ICU.",
            "Có tải natri đáng kể; thận trọng ở suy tim, phù phổi cấp, ESRD/quá tải dịch.",
            "Phối hợp Vancomycin có thể làm tăng nguy cơ AKI trong một số quần thể.",
            "Không bao phủ ESBL đáng tin trong nhiễm khuẩn nặng nếu nguy cơ ESBL cao; cân nhắc carbapenem theo phác đồ.",
        ],
    },
    "Vancomycin": {
        "crcl_gt_50": "Loading 20–25 mg/kg IV nếu nhiễm nặng; duy trì thường 15–20 mg/kg IV mỗi 8–12 giờ, chỉnh theo AUC/TDM",
        "crcl_30_50": "Loading 20–25 mg/kg IV nếu nhiễm nặng; duy trì 15–20 mg/kg IV mỗi 24 giờ hoặc theo nồng độ/AUC",
        "crcl_10_29": "Loading 20–25 mg/kg IV nếu nhiễm nặng; duy trì theo nồng độ, thường kéo dài khoảng cách 24–48 giờ",
        "crcl_lt_10": "Loading 20–25 mg/kg IV nếu nhiễm nặng; liều duy trì theo nồng độ và lịch lọc máu, không dùng lịch cố định",
        "warnings": [
            "Độc thận: cần TDM. Ưu tiên AUC/MIC 400–600 cho nhiễm MRSA nặng nếu bệnh viện có điều kiện.",
            "Nếu chưa có AUC monitoring, theo dõi trough theo protocol bệnh viện; không chỉnh liều duy trì mù ở AKI/ESRD/CRRT.",
            "Tăng nguy cơ độc thận khi phối hợp aminoglycoside, amphotericin B, piperacillin/tazobactam hoặc thuốc độc thận khác.",
            "Theo dõi phản ứng truyền; truyền chậm, thường ≥1 giờ cho mỗi 1 g.",
        ],
    },
    "Ciprofloxacin": {
        "crcl_gt_50": "400 mg IV mỗi 8–12 giờ",
        "crcl_30_50": "400 mg IV mỗi 12 giờ",
        "crcl_10_29": "400 mg IV mỗi 18–24 giờ",
        "crcl_lt_10": "400 mg IV mỗi 24 giờ; nếu lọc máu, dùng sau phiên lọc theo phác đồ bệnh viện",
        "warnings": [
            "Fluoroquinolone: nguy cơ kéo dài QT, xoắn đỉnh, loạn nhịp; kiểm tra ECG/QTc nếu có nguy cơ.",
            "Cảnh báo đỏ nếu rung nhĩ/nhịp nhanh >120 lần/phút hoặc đang dùng Dobutamine/Noradrenaline.",
            "Tương tác chelation với sắt, kẽm, calcium, magnesium, thuốc kháng acid nếu dùng đường uống/ống tiêu hóa.",
            "Không bao phủ Streptococcus pneumoniae tốt bằng levofloxacin; không dùng đơn độc cho viêm phổi nặng nếu không phù hợp.",
        ],
    },
    "Imipenem/Cilastatin": {
        "crcl_gt_50": "500 mg IV mỗi 6 giờ hoặc 1 g IV mỗi 8 giờ tùy ổ nhiễm/mức độ nặng",
        "crcl_30_50": "500 mg IV mỗi 8 giờ hoặc 250–500 mg IV mỗi 6–8 giờ theo phác đồ",
        "crcl_10_29": "250–500 mg IV mỗi 12 giờ",
        "crcl_lt_10": "Thường tránh nếu có lựa chọn khác; nếu bắt buộc, dùng liều giảm mạnh và theo phác đồ thận/lọc máu",
        "warnings": [
            "Nguy cơ co giật cao hơn meropenem, đặc biệt khi suy thận, bệnh CNS, quá liều.",
            "Bắt buộc chỉnh liều theo CrCl.",
            "Không bao phủ MRSA, Enterococcus faecium, Stenotrophomonas.",
            "Thận trọng ở bệnh nhân có tiền sử động kinh hoặc tổn thương não.",
        ],
    },
    "Ceftriaxone": {
        "crcl_gt_50": "2 g IV mỗi 24 giờ cho nhiễm nặng/sepsis; VIÊM MÀNG NÃO: 2 g IV mỗi 12 giờ",
        "crcl_30_50": "2 g IV mỗi 24 giờ; VIÊM MÀNG NÃO: 2 g IV mỗi 12 giờ; thường không cần chỉnh liều theo thận",
        "crcl_10_29": "2 g IV mỗi 24 giờ; VIÊM MÀNG NÃO: 2 g IV mỗi 12 giờ; thường không cần chỉnh liều theo thận",
        "crcl_lt_10": "2 g IV mỗi 24 giờ; VIÊM MÀNG NÃO: 2 g IV mỗi 12 giờ; thường không cần chỉnh liều theo thận/lọc máu",
        "warnings": [
            "Thường không cần chỉnh liều theo thận đơn thuần; thận trọng nếu suy gan nặng kèm suy thận nặng.",
            "Trong viêm màng não mủ, phải dùng liều CNS/meningitis 2 g IV mỗi 12 giờ, không dùng liều q24h thường quy.",
            "Không bao phủ Listeria, Pseudomonas, Acinetobacter, Enterococcus, MRSA.",
            "Nguy cơ bùn mật/ứ mật, đặc biệt khi dùng liều cao hoặc kéo dài.",
            "Luôn kiểm tra tương hợp đường truyền với calcium theo chính sách bệnh viện.",
        ],
    },
    "Ampicillin": {
        "crcl_gt_50": "2 g IV mỗi 4 giờ cho viêm màng não/Listeria; nhiễm khác chỉnh theo ổ nhiễm",
        "crcl_30_50": "2 g IV mỗi 6 giờ; viêm màng não nặng cần hội chẩn dược lâm sàng để tối ưu liều",
        "crcl_10_29": "2 g IV mỗi 8–12 giờ; viêm màng não nặng cần cá thể hóa theo CrCl và đáp ứng",
        "crcl_lt_10": "2 g IV mỗi 12–24 giờ; nếu lọc máu dùng sau phiên lọc theo phác đồ bệnh viện",
        "warnings": [
            "Ampicillin là thuốc chính để bao phủ Listeria monocytogenes trong viêm màng não cộng đồng có yếu tố nguy cơ.",
            "Cần chỉnh liều theo thận; trong viêm màng não, tránh giảm liều quá mức gây thiếu nồng độ DNT.",
            "Theo dõi dị ứng beta-lactam, phát ban, tiêu chảy/C. difficile và tải natri ở bệnh nhân suy tim/CKD.",
            "Nếu dị ứng penicillin nặng và nghi Listeria: cần hội chẩn nhiễm/dược lâm sàng vì lựa chọn thay thế không đơn giản.",
        ],
    },
    "Colistin": {
        "crcl_gt_50": "Colistimethate sodium: loading 9–10 MIU IV x1, sau đó khoảng 4.5 MIU IV mỗi 12 giờ; chỉnh theo protocol địa phương",
        "crcl_30_50": "Loading 9–10 MIU IV x1, sau đó khoảng 3–4.5 MIU/ngày chia 1–2 lần theo CrCl và protocol",
        "crcl_10_29": "Loading 9–10 MIU IV x1, sau đó khoảng 2–3 MIU/ngày hoặc theo TDM/protocol nếu có",
        "crcl_lt_10": "Loading 9–10 MIU IV x1; duy trì theo protocol lọc máu/CRRT, không dùng lịch cố định nếu không có dược lâm sàng",
        "warnings": [
            "Nguy cơ độc thận và độc thần kinh cao; chỉ dùng khi thật cần, thường cho Gram âm đa kháng.",
            "Rất dễ nhầm đơn vị: MIU vs mg CBA vs mg CMS. App phải ghi rõ đơn vị.",
            "Cần hội chẩn nhiễm/dược lâm sàng; cân nhắc phối hợp và kiểm soát nguồn nhiễm.",
            "Theo dõi creatinine, thần kinh cơ, dị cảm, yếu cơ; thận trọng phối hợp thuốc độc thận/ức chế thần kinh cơ.",
        ],
    },
    "Linezolid": {
        "crcl_gt_50": "600 mg IV/PO mỗi 12 giờ",
        "crcl_30_50": "600 mg IV/PO mỗi 12 giờ; thường không cần chỉnh liều theo thận",
        "crcl_10_29": "600 mg IV/PO mỗi 12 giờ; thường không cần chỉnh liều, nhưng theo dõi độc tính huyết học sát hơn",
        "crcl_lt_10": "600 mg IV/PO mỗi 12 giờ; không cần chỉnh liều theo lọc máu, nhưng theo dõi tiểu cầu/lactate",
        "warnings": [
            "Không cần chỉnh liều thận thường quy, nhưng suy thận có thể tăng nguy cơ giảm tiểu cầu khi dùng kéo dài.",
            "Theo dõi CBC, đặc biệt nếu dùng >7–14 ngày, CKD, ICU hoặc dùng thuốc ức chế tủy.",
            "Nguy cơ serotonin syndrome khi phối hợp SSRI/SNRI/MAOI/tramadol; kiểm tra tương tác thuốc.",
            "Dùng kéo dài: nguy cơ bệnh thần kinh ngoại biên/thị giác và nhiễm toan lactic.",
        ],
    },
    "Amikacin": {
        "crcl_gt_50": "15–20 mg/kg IV liều nạp; nhiễm Gram âm nặng thường dùng extended-interval, ví dụ mỗi 24 giờ, chỉnh theo nồng độ",
        "crcl_30_50": "15–20 mg/kg IV liều nạp, sau đó kéo dài khoảng cách liều, thường mỗi 36–48 giờ theo nồng độ",
        "crcl_10_29": "15–20 mg/kg IV liều nạp, sau đó redose theo nồng độ; không dùng lịch cố định nếu nhiễm nặng/AKI",
        "crcl_lt_10": "15–20 mg/kg IV liều nạp nếu thật cần, sau đó redose theo nồng độ và lịch lọc máu; cần dược lâm sàng",
        "warnings": [
            "Aminoglycoside: độc thận và độc tai; cần TDM, thường theo peak/trough hoặc random level tùy chiến lược liều.",
            "Yêu cầu đo trough để tránh tích lũy; với extended-interval cần random level theo nomogram/protocol.",
            "Tránh hoặc dùng rất thận trọng khi CKD/AKI/ESRD, phối hợp vancomycin, amphotericin B, loop diuretic hoặc thuốc độc thận khác.",
            "Theo dõi thính lực/tiền đình nếu dùng kéo dài; trong sepsis thường ưu tiên liều nạp đủ rồi quyết định redose theo nồng độ.",
        ],
    },
}

# Backward-compatible alias used by app.py.
ANTIBIOTIC_DOSING = ANTIBIOTIC_DICT


def get_antibiotic_dose_recommendation(antibiotic_name: str, crcl: float, on_hemodialysis: bool = False) -> dict:
    """Return renal-adjusted dose recommendation for selected antibiotic."""
    data = ANTIBIOTIC_DICT[antibiotic_name]
    band = get_renal_band(crcl, on_hemodialysis)
    labels = {
        "crcl_gt_50": "CrCl > 50 mL/phút",
        "crcl_30_50": "CrCl 30–50 mL/phút",
        "crcl_10_29": "CrCl 10–29 mL/phút",
        "crcl_lt_10": "CrCl <10 mL/phút hoặc lọc máu",
    }
    return {
        "antibiotic": antibiotic_name,
        "renal_label": labels[band],
        "dose_text": data[band],
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
    """Generate patient-specific clinical alerts. severity: error/warning/info."""
    alerts: list[tuple[str, str]] = []
    vasoactive_running = (
        (drug_name not in ["Không dùng vận mạch", "", None] and desired_dose > 0)
        or (inotrope_name not in ["Không dùng inotrope", "", None] and inotrope_dose > 0)
    )

    if antibiotic_name in ["Levofloxacin", "Ciprofloxacin"]:
        has_tachy_or_af = heart_rate >= 110
        has_vasoactive = vasoactive_running

        if has_tachy_or_af and has_vasoactive:
            alerts.append((
                "error",
                "CẢNH BÁO ĐỎ: Fluoroquinolone có nguy cơ kéo dài QT / xoắn đỉnh / loạn nhịp. "
                "Bệnh nhân đang có nhịp nhanh/rung nhĩ và đang dùng vận mạch/inotrope "
                "(ví dụ Noradrenaline/Dobutamine). Kiểm tra ECG/QTc, K⁺, Mg²⁺, thuốc kéo dài QT khác; "
                "cân nhắc lựa chọn khác nếu phù hợp phác đồ và kháng sinh đồ."
            ))
        elif has_tachy_or_af or has_vasoactive:
            alerts.append((
                "warning",
                "Fluoroquinolone có nguy cơ kéo dài QT / xoắn đỉnh / loạn nhịp. "
                "Bệnh nhân có nhịp nhanh/rung nhĩ hoặc đang dùng vận mạch/inotrope. "
                "Nên kiểm tra ECG/QTc, K⁺, Mg²⁺ và tương tác thuốc."
            ))
        else:
            alerts.append((
                "warning",
                "Fluoroquinolone có nguy cơ kéo dài QT, rối loạn đường huyết, tác dụng phụ thần kinh "
                "và bệnh lý gân. Thận trọng ở người già, CKD, bệnh tim nền."
            ))

    if antibiotic_name == "Vancomycin":
        alerts.append((
            "error",
            "Vancomycin: nguy cơ độc thận. Cần TDM. Ưu tiên AUC/MIC 400–600 nếu có điều kiện; "
            "nếu không, theo dõi nồng độ theo protocol bệnh viện.",
        ))
        if crcl < 50 or ckd_any or anuric_ckd or on_hemodialysis:
            alerts.append((
                "error",
                "Bệnh nhân có suy thận/CKD/lọc máu: không dùng liều duy trì vancomycin cố định. "
                "Cần loading dose nếu nhiễm nặng rồi chỉnh theo nồng độ và lịch lọc máu.",
            ))

    if antibiotic_name == "Amikacin":
        alerts.append((
            "error",
            "Amikacin: độc thận/độc tai, bắt buộc TDM. Nên dùng liều nạp đủ rồi redose theo nồng độ, "
            "đặc biệt trong ICU/AKI/ESRD/CRRT.",
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

    if antibiotic_name == "Colistin":
        alerts.append((
            "error",
            "Colistin: kiểm tra đơn vị kê đơn trước khi dùng. Không trộn lẫn MIU, mg CBA và mg CMS. "
            "Nguy cơ độc thận/độc thần kinh cao, cần dược lâm sàng/ID hỗ trợ.",
        ))

    if antibiotic_name == "Linezolid":
        alerts.append((
            "warning",
            "Linezolid: theo dõi CBC/tiểu cầu, tương tác serotonergic và lactate nếu dùng kéo dài hoặc CKD/ICU.",
        ))

    return alerts
