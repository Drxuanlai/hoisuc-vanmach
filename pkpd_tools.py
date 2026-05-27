import math


def calculate_vanco_auc_2level(
    dose_mg: float,
    infusion_time_hr: float,
    tau_hr: float,
    peak_mg_l: float,
    trough_mg_l: float,
    time_peak_after_start_hr: float,
    time_trough_after_start_hr: float,
    mic_mg_l: float = 1.0,
) -> dict:
    """1-compartment, first-order, 2-level vancomycin AUC24/MIC estimator."""
    if dose_mg <= 0 or infusion_time_hr <= 0 or tau_hr <= 0:
        raise ValueError("Dose, infusion time và tau phải > 0")
    if peak_mg_l <= 0 or trough_mg_l <= 0:
        raise ValueError("Peak và trough phải > 0")
    if peak_mg_l <= trough_mg_l:
        raise ValueError("Peak phải lớn hơn trough")
    if time_trough_after_start_hr <= time_peak_after_start_hr:
        raise ValueError("Thời điểm trough phải sau thời điểm peak")
    if mic_mg_l <= 0:
        raise ValueError("MIC phải > 0")

    delta_t = time_trough_after_start_hr - time_peak_after_start_hr
    ke = math.log(peak_mg_l / trough_mg_l) / delta_t
    half_life_hr = 0.693 / ke

    time_after_infusion_end_hr = time_peak_after_start_hr - infusion_time_hr
    if time_after_infusion_end_hr < 0:
        raise ValueError("Peak nên lấy sau khi kết thúc truyền")

    c_end_infusion = peak_mg_l * math.exp(ke * time_after_infusion_end_hr)
    accumulation_factor = 1 - math.exp(-ke * tau_hr)
    infusion_factor = 1 - math.exp(-ke * infusion_time_hr)
    vd_l = (dose_mg * infusion_factor) / (ke * infusion_time_hr * c_end_infusion * accumulation_factor)
    cl_l_hr = ke * vd_l
    auc_tau_mg_h_l = dose_mg / cl_l_hr
    auc24_mg_h_l = auc_tau_mg_h_l * (24 / tau_hr)
    auc24_mic = auc24_mg_h_l / mic_mg_l

    if auc24_mic < 400:
        level = "LOW"
        interpretation = "Dưới đích AUC/MIC 400–600: nguy cơ dưới liều nếu nhiễm MRSA nặng."
    elif auc24_mic <= 600:
        level = "TARGET"
        interpretation = "Trong đích AUC/MIC 400–600 cho nhiễm MRSA nặng."
    else:
        level = "HIGH"
        interpretation = "Trên đích AUC/MIC 400–600: tăng nguy cơ độc thận."

    return {
        "ke_hr": ke,
        "half_life_hr": half_life_hr,
        "c_end_infusion_mg_l": c_end_infusion,
        "vd_l": vd_l,
        "cl_l_hr": cl_l_hr,
        "auc_tau_mg_h_l": auc_tau_mg_h_l,
        "auc24_mg_h_l": auc24_mg_h_l,
        "auc24_mic": auc24_mic,
        "level": level,
        "interpretation": interpretation,
    }


def estimate_vanco_daily_dose_for_target_auc(current_daily_dose_mg: float, current_auc24: float, target_auc24: float = 500.0) -> float:
    """Linear proportional daily-dose estimate: new TDD = current TDD × target AUC/current AUC."""
    if current_daily_dose_mg <= 0 or current_auc24 <= 0 or target_auc24 <= 0:
        raise ValueError("Các giá trị phải > 0")
    return current_daily_dose_mg * target_auc24 / current_auc24


def colistin_cba_mg_to_miu(cba_mg: float) -> float:
    """mg CBA -> MIU. Prototype convention: 1 MIU ≈ 30 mg CBA."""
    if cba_mg < 0:
        raise ValueError("cba_mg không được âm")
    return cba_mg / 30.0


def colistin_miu_to_cba_mg(miu: float) -> float:
    """MIU -> mg CBA. Prototype convention: 1 MIU ≈ 30 mg CBA."""
    if miu < 0:
        raise ValueError("miu không được âm")
    return miu * 30.0


def colistin_cba_mg_to_cms_mg(cba_mg: float) -> float:
    """mg CBA -> mg CMS. Common approximation: 1 mg CBA ≈ 2.67 mg CMS."""
    if cba_mg < 0:
        raise ValueError("cba_mg không được âm")
    return cba_mg * 2.67


def colistin_cms_mg_to_cba_mg(cms_mg: float) -> float:
    """mg CMS -> mg CBA."""
    if cms_mg < 0:
        raise ValueError("cms_mg không được âm")
    return cms_mg / 2.67


def convert_colistin_units(value: float, from_unit: str) -> dict:
    """Convert between MIU, mg CBA, and mg CMS."""
    if value < 0:
        raise ValueError("Giá trị không được âm")
    if from_unit == "MIU":
        miu = value
        cba_mg = colistin_miu_to_cba_mg(miu)
        cms_mg = colistin_cba_mg_to_cms_mg(cba_mg)
    elif from_unit == "mg CBA":
        cba_mg = value
        miu = colistin_cba_mg_to_miu(cba_mg)
        cms_mg = colistin_cba_mg_to_cms_mg(cba_mg)
    elif from_unit == "mg CMS":
        cms_mg = value
        cba_mg = colistin_cms_mg_to_cba_mg(cms_mg)
        miu = colistin_cba_mg_to_miu(cba_mg)
    else:
        raise ValueError("from_unit phải là 'MIU', 'mg CBA', hoặc 'mg CMS'")
    return {"MIU": miu, "mg CBA": cba_mg, "mg CMS": cms_mg}
