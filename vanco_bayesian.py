import math
from typing import Dict, List

import numpy as np
from scipy.optimize import minimize


def estimate_vanco_population_pk(age: float, weight_kg: float, crcl_ml_min: float, is_male: bool = True) -> Dict[str, float]:
    """Simple educational prior: Vd≈0.7 L/kg; CL≈0.75×CrCl converted to L/h."""
    crcl_ml_min = max(crcl_ml_min, 1.0)
    vd_l = max(0.7 * weight_kg, 10.0)
    cl_l_hr = max(0.75 * crcl_ml_min * 0.06, 0.1)
    return {"prior_vd_l": vd_l, "prior_cl_l_hr": cl_l_hr, "prior_ke_hr": cl_l_hr / vd_l}


def simulate_vanco_concentration_1cmt(
    dose_mg: float,
    infusion_time_hr: float,
    tau_hr: float,
    num_doses_given: int,
    sample_time_after_start_hr: float,
    cl_l_hr: float,
    vd_l: float,
) -> float:
    """One-compartment multiple IV infusion concentration prediction."""
    if dose_mg <= 0 or infusion_time_hr <= 0 or tau_hr <= 0:
        raise ValueError("Dose, infusion time, tau phải > 0")
    if cl_l_hr <= 0 or vd_l <= 0:
        raise ValueError("CL và Vd phải > 0")
    if num_doses_given < 1:
        raise ValueError("num_doses_given phải >= 1")

    ke = cl_l_hr / vd_l
    rate_mg_hr = dose_mg / infusion_time_hr
    concentration = 0.0
    for dose_index in range(num_doses_given):
        dose_start = dose_index * tau_hr
        t = sample_time_after_start_hr - dose_start
        if t <= 0:
            continue
        if t <= infusion_time_hr:
            c = (rate_mg_hr / cl_l_hr) * (1 - math.exp(-ke * t))
        else:
            c_end = (rate_mg_hr / cl_l_hr) * (1 - math.exp(-ke * infusion_time_hr))
            c = c_end * math.exp(-ke * (t - infusion_time_hr))
        concentration += c
    return concentration


def vanco_map_bayesian_estimate(
    dose_mg: float,
    infusion_time_hr: float,
    tau_hr: float,
    num_doses_given: int,
    levels: List[Dict[str, float]],
    age: float,
    weight_kg: float,
    crcl_ml_min: float,
    is_male: bool = True,
    mic_mg_l: float = 1.0,
    sigma_level_mg_l: float = 2.0,
    omega_cl_cv: float = 0.30,
    omega_vd_cv: float = 0.30,
) -> Dict[str, float]:
    """Bayesian-like MAP estimator. Educational prototype only; not validated clinical software."""
    if not levels:
        raise ValueError("Cần ít nhất 1 nồng độ Vancomycin")
    if mic_mg_l <= 0:
        raise ValueError("MIC phải > 0")

    prior = estimate_vanco_population_pk(age, weight_kg, crcl_ml_min, is_male)
    prior_cl = prior["prior_cl_l_hr"]
    prior_vd = prior["prior_vd_l"]
    x0 = np.log([prior_cl, prior_vd])

    def objective(x: np.ndarray) -> float:
        cl = math.exp(x[0])
        vd = math.exp(x[1])
        residual_sum = 0.0
        for lvl in levels:
            pred = simulate_vanco_concentration_1cmt(
                dose_mg=dose_mg,
                infusion_time_hr=infusion_time_hr,
                tau_hr=tau_hr,
                num_doses_given=num_doses_given,
                sample_time_after_start_hr=lvl["time_hr"],
                cl_l_hr=cl,
                vd_l=vd,
            )
            obs = lvl["concentration_mg_l"]
            residual_sum += ((obs - pred) / sigma_level_mg_l) ** 2
        prior_penalty_cl = ((math.log(cl / prior_cl)) / omega_cl_cv) ** 2
        prior_penalty_vd = ((math.log(vd / prior_vd)) / omega_vd_cv) ** 2
        return residual_sum + prior_penalty_cl + prior_penalty_vd

    result = minimize(objective, x0, method="Nelder-Mead")
    if not result.success:
        raise RuntimeError("Tối ưu MAP không hội tụ")

    post_cl = math.exp(result.x[0])
    post_vd = math.exp(result.x[1])
    post_ke = post_cl / post_vd
    half_life_hr = 0.693 / post_ke
    daily_dose_mg = dose_mg * (24 / tau_hr)
    auc24 = daily_dose_mg / post_cl
    auc24_mic = auc24 / mic_mg_l

    if auc24_mic < 400:
        level = "LOW"
        interpretation = "AUC/MIC dưới đích 400–600: nguy cơ dưới liều nếu nhiễm MRSA nặng."
    elif auc24_mic <= 600:
        level = "TARGET"
        interpretation = "AUC/MIC trong đích 400–600."
    else:
        level = "HIGH"
        interpretation = "AUC/MIC trên 600: tăng nguy cơ độc thận, cần xem xét giảm liều/kéo dài khoảng cách."

    return {
        "prior_cl_l_hr": prior_cl,
        "prior_vd_l": prior_vd,
        "posterior_cl_l_hr": post_cl,
        "posterior_vd_l": post_vd,
        "posterior_ke_hr": post_ke,
        "half_life_hr": half_life_hr,
        "auc24_mg_h_l": auc24,
        "auc24_mic": auc24_mic,
        "level": level,
        "interpretation": interpretation,
        "objective_value": float(result.fun),
    }


def suggest_vanco_regimen_from_auc(current_dose_mg: float, current_tau_hr: float, current_auc24: float, target_auc24: float = 500.0) -> Dict[str, float]:
    """Linear total daily dose estimate: new TDD = current TDD × target/current AUC."""
    if current_dose_mg <= 0 or current_tau_hr <= 0 or current_auc24 <= 0:
        raise ValueError("Input phải > 0")
    current_tdd = current_dose_mg * (24 / current_tau_hr)
    new_tdd = current_tdd * target_auc24 / current_auc24
    return {"current_total_daily_dose_mg": current_tdd, "suggested_total_daily_dose_mg": new_tdd}
