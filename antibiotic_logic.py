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


def infer_specific_resistance_risks(
    infection_focus: str,
    community_or_hospital: str,
    recent_hospitalization: bool,
    recent_antibiotics: bool,
    prior_mdr: bool,
    nursing_home: bool,
    hemodialysis: bool,
    immunosuppression: bool,
    invasive_device: bool,
    prior_colonization_unknown: bool,
) -> dict:
    """
    Tự gợi ý nguy cơ MRSA/Pseudomonas/ESBL/Candida từ ổ nhiễm và yếu tố nguy cơ.
    Đây là gợi ý an toàn để bác sĩ đỡ phải nhớ, không thay thế antibiogram/phác đồ bệnh viện.
    """
    focus_lower = infection_focus.lower()
    hospital_context = community_or_hospital in ["Bệnh viện", "ICU/VAP"]
    severe_context = hospital_context or recent_hospitalization or recent_antibiotics or prior_mdr

    mrsa = False
    pseudomonas = False
    esbl = False
    candida = False

    reasons = {"MRSA": [], "Pseudomonas": [], "ESBL": [], "Candida": []}

    # ESBL/MDR Enterobacterales: rất liên quan ở UTI/ổ bụng khi có KS gần đây, nhập viện, tiền sử MDR.
    if prior_mdr:
        esbl = True
        reasons["ESBL"].append("Tiền sử cấy MDR/ESBL/MRSA/CRE")
    if recent_antibiotics:
        esbl = True
        reasons["ESBL"].append("Dùng kháng sinh trong 90 ngày")
    if recent_hospitalization and ("tiết niệu" in focus_lower or "bụng" in focus_lower or hospital_context):
        esbl = True
        reasons["ESBL"].append("Nhập viện gần đây trong bối cảnh UTI/ổ bụng/nhiễm bệnh viện")
    if nursing_home or hemodialysis:
        esbl = True
        reasons["ESBL"].append("Chăm sóc y tế kéo dài/lọc máu làm tăng nguy cơ Enterobacterales kháng thuốc")

    # Pseudomonas: HAP/VAP, ICU, dụng cụ xâm lấn, sonde/catheter lâu ngày, nhập viện/KS gần đây.
    if "bệnh viện" in focus_lower or "vap" in focus_lower or community_or_hospital == "ICU/VAP":
        pseudomonas = True
        reasons["Pseudomonas"].append("Viêm phổi bệnh viện/ICU/VAP")
    if invasive_device and ("tiết niệu" in focus_lower or hospital_context):
        pseudomonas = True
        reasons["Pseudomonas"].append("Sonde/catheter/dụng cụ xâm lấn lâu ngày")
    if recent_hospitalization or recent_antibiotics:
        if "phổi" in focus_lower or "tiết niệu" in focus_lower or hospital_context:
            pseudomonas = True
            reasons["Pseudomonas"].append("Nhập viện hoặc dùng kháng sinh gần đây")

    # MRSA: viêm phổi bệnh viện/ICU, catheter, tiền sử MRSA/MDR, lọc máu, chăm sóc dài hạn.
    if "bệnh viện" in focus_lower or "vap" in focus_lower or "catheter" in focus_lower:
        mrsa = True
        reasons["MRSA"].append("Ổ nhiễm bệnh viện/VAP/catheter")
    if prior_mdr or hemodialysis or nursing_home:
        mrsa = True
        reasons["MRSA"].append("Tiền sử MDR/chăm sóc y tế kéo dài/lọc máu")

    # Candida: ICU, ổ bụng phức tạp, catheter, suy giảm miễn dịch, KS kéo dài, sốc dai dẳng.
    if immunosuppression:
        candida = True
        reasons["Candida"].append("Suy giảm miễn dịch")
    if recent_antibiotics and ("bụng" in focus_lower or "catheter" in focus_lower or community_or_hospital == "ICU/VAP"):
        candida = True
        reasons["Candida"].append("Kháng sinh gần đây trong bối cảnh ICU/ổ bụng/catheter")
    if invasive_device and ("catheter" in focus_lower or community_or_hospital == "ICU/VAP"):
        candida = True
        reasons["Candida"].append("Catheter/dụng cụ xâm lấn trong bối cảnh nguy cơ cao")

    # Nếu thiếu dữ liệu, không tự bật tất cả; chỉ nhắc kiểm tra vi sinh cũ.
    if prior_colonization_unknown:
        for key in reasons:
            reasons[key].append("Tiền sử vi sinh chưa rõ: cần kiểm tra hồ sơ cấy cũ/antibiogram")

    return {
        "mrsa_risk": mrsa,
        "pseudomonas_risk": pseudomonas,
        "esbl_risk": esbl,
        "candida_risk": candida,
        "reasons": reasons,
    }


def suggest_likely_pathogens(
    infection_focus: str,
    community_or_hospital: str,
    mrsa_risk: bool,
    pseudomonas_risk: bool,
    esbl_risk: bool,
    candida_risk: bool,
) -> list:
    """Gợi ý nhóm tác nhân thường gặp theo ổ nhiễm và nguy cơ mở rộng phổ."""
    focus_lower = infection_focus.lower()
    pathogens = []

    if "tiết niệu" in focus_lower:
        pathogens.extend(["E. coli", "Klebsiella/Enterobacterales", "Proteus spp."])
        if community_or_hospital in ["Bệnh viện", "ICU/VAP"]:
            pathogens.append("Enterococcus trong một số bối cảnh")
    elif "phổi cộng đồng" in focus_lower:
        pathogens.extend(["Streptococcus pneumoniae", "H. influenzae", "Gram âm hô hấp", "Atypical pathogens"])
    elif "phổi bệnh viện" in focus_lower or "vap" in focus_lower:
        pathogens.extend(["Gram âm bệnh viện", "Pseudomonas/Acinetobacter tùy ICU", "S. aureus"])
    elif "bụng" in focus_lower:
        pathogens.extend(["Enterobacterales", "Kỵ khí", "Enterococcus trong một số bối cảnh bệnh viện"])
    elif "da" in focus_lower:
        pathogens.extend(["Streptococcus", "Staphylococcus aureus", "Gram âm/kỵ khí nếu hoại tử/đái tháo đường/vùng tầng sinh môn"])
    elif "catheter" in focus_lower:
        pathogens.extend(["Coagulase-negative staphylococci", "Staphylococcus aureus", "Gram âm bệnh viện", "Candida nếu nguy cơ cao"])
    else:
        pathogens.extend(["Phổi", "Tiết niệu", "Ổ bụng", "Da-mô mềm", "Catheter", "Thần kinh trung ương tùy bệnh cảnh"])

    if pseudomonas_risk:
        pathogens.append("Pseudomonas aeruginosa")
    if mrsa_risk:
        pathogens.append("MRSA")
    if esbl_risk:
        pathogens.append("ESBL Enterobacterales")
    if candida_risk:
        pathogens.append("Candida/nấm xâm lấn trong bối cảnh nguy cơ cao")

    return list(dict.fromkeys(pathogens))


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

