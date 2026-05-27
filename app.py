import streamlit as st

from shock_logic import (
    calculate_fluid_volume,
    classify_shock_multilabel,
    detect_mixed_shock,
    interpret_fluid_responsiveness,
    fluid_strategy_for_mixed_shock,
)
from vasopressor_logic import (
    VASOPRESSOR_PRESETS,
    calculate_infusion_rate,
    suggest_noradrenaline_dose,
    choose_vasopressor_preset_for_rate,
)
from inotrope_logic import (
    INOTROPE_PRESETS,
    suggest_inotrope,
)
from antibiotic_logic import (
    assess_mdr_risk,
    antibiotic_timing_advice,
    infer_specific_resistance_risks,
    recommend_antibiotic_coverage,
    suggest_likely_pathogens,
)
from antibiotic_presets_local import ANTIBIOTIC_PROTOCOLS
from antibiotic_dosing import (
    ANTIBIOTIC_DOSING,
    calculate_crcl,
    choose_weight_for_cg,
    generate_antibiotic_clinical_alerts,
    get_antibiotic_dose_recommendation,
)

# ============================================================
# Shock Resuscitation Mini-App By DR.XuanLai
# Main Streamlit UI
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
age_years = st.sidebar.number_input("Tuổi (năm)", min_value=0.0, max_value=120.0, value=68.0, step=1.0)
sex = st.sidebar.selectbox("Giới tính", ["Nam", "Nữ"], index=0)
is_male = sex == "Nam"
height_cm = st.sidebar.number_input("Chiều cao (cm)", min_value=50.0, max_value=230.0, value=165.0, step=1.0)
serum_creatinine = st.sidebar.number_input("Creatinine máu (mg/dL)", min_value=0.1, max_value=20.0, value=1.5, step=0.1)

cg_weight, cg_weight_method, bmi, ibw = choose_weight_for_cg(
    weight_kg=weight_kg,
    height_cm=height_cm,
    is_male=is_male,
)
calculated_crcl = calculate_crcl(
    age=age_years,
    weight=cg_weight,
    is_male=is_male,
    serum_creatinine=serum_creatinine,
)
st.sidebar.info(
    f"CrCl Cockcroft-Gault: {calculated_crcl:.1f} mL/phút\n\n"
    f"BMI: {bmi:.1f} kg/m²\n\n"
    f"IBW: {ibw:.1f} kg\n\n"
    f"Cân nặng dùng tính CrCl: {cg_weight:.1f} kg ({cg_weight_method})"
)

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

# Override an toàn cho ESRD/CKD nặng hoặc vô niệu kèm phù phổi cấp khi MAP không thấp.
# Trong phenotype này, không nên chỉ nói "bolus nhỏ"; ưu tiên xử trí quá tải dịch/suy hô hấp và source control.
if (anuric_ckd or ckd_any) and pulmonary_edema and map_mmHg >= 65:
    strategy_level = "RED"
    strategy_text = (
        "CKD/ESRD hoặc vô niệu kèm phù phổi cấp và MAP hiện không thấp. "
        "Không bolus dịch. Ưu tiên oxy/NIV nếu phù hợp, POCUS tim-phổi, "
        "cân nhắc lọc máu/siêu lọc cấp cứu nếu quá tải dịch nặng, kháng sinh sớm nếu nghi nhiễm khuẩn "
        "và tìm source control."
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
# Module 5: Vasopressor calculator - only when clinically indicated
# ============================================================

st.header("5. Vận mạch: chỉ bật khi có tụt huyết áp/sốc cần nâng MAP")

# Mặc định: không đề xuất vận mạch nếu MAP đang cao/bình thường.
# Lactate cao một mình KHÔNG phải chỉ định norepinephrine nếu MAP đã 195 mmHg.
vasopressor_indication = map_mmHg < 65
manual_vasopressor_override = False

# Giá trị mặc định để phần summary không lỗi khi module bị tắt.
drug_name = "Không dùng vận mạch"
total_drug_mg = 0.0
final_volume_ml = 0.0
desired_dose = 0.0
vasopressor_result = {
    "total_drug_mg": 0.0,
    "total_drug_mcg": 0.0,
    "final_concentration_mcg_ml": 0.0,
    "required_mcg_min": 0.0,
    "pump_rate_ml_hour": 0.0,
}

if map_mmHg >= 90:
    st.success(
        f"MAP hiện tại {map_mmHg:.0f} mmHg: không có chỉ định gợi ý vận mạch để nâng MAP. "
        "Nếu bệnh nhân đang phù phổi cấp/tăng huyết áp, ưu tiên xử trí suy hô hấp, giảm tiền tải/hậu tải, lợi tiểu/giãn mạch theo phác đồ và tìm nguyên nhân lactate tăng."
    )
    manual_vasopressor_override = st.checkbox(
        "Vẫn mở máy tính vận mạch thủ công",
        value=False,
        key="manual_vasopressor_override_high_map",
    )
elif 65 <= map_mmHg < 90:
    st.info(
        f"MAP hiện tại {map_mmHg:.0f} mmHg: chưa có chỉ định tự động dùng norepinephrine. "
        "Có thể mở máy tính nếu đang chuẩn bị vận mạch trong bối cảnh tụt HA động học hoặc sau an thần/đặt nội khí quản."
    )
    manual_vasopressor_override = st.checkbox(
        "Mở máy tính vận mạch thủ công",
        value=False,
        key="manual_vasopressor_override_mid_map",
    )
else:
    st.error(
        f"MAP hiện tại {map_mmHg:.0f} mmHg < 65: có chỉ định đánh giá vận mạch nếu tụt HA dai dẳng hoặc không thể bù dịch an toàn."
    )

show_vasopressor_calculator = vasopressor_indication or manual_vasopressor_override

if show_vasopressor_calculator:
    suggested_ne_dose, ne_reason = suggest_noradrenaline_dose(
        map_mmHg=map_mmHg,
        lactate=lactate,
        cardiogenic_active=cardiogenic_active,
        fluid_overload_risk=fluid_overload_risk,
    )
    recommended_preset_name, recommended_preset, all_ne_rates = choose_vasopressor_preset_for_rate(weight_kg, suggested_ne_dose)

    if vasopressor_indication:
        st.info("Gợi ý tự động: " + ne_reason)
    else:
        st.warning(
            "Đang mở máy tính thủ công dù MAP không thấp. App sẽ không xem đây là khuyến cáo dùng vận mạch."
        )

    with st.expander("Xem bảng tốc độ bơm theo các nồng độ Noradrenaline ở liều gợi ý", expanded=False):
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

    st.write(
        f"Nhu cầu thuốc: **{vasopressor_result['required_mcg_min']:.2f} mcg/phút** "
        f"ở bệnh nhân **{weight_kg:.1f} kg**, liều **{desired_dose:.3f} mcg/kg/phút**."
    )
    st.info("Công thức: mL/giờ = liều mcg/kg/phút × cân nặng kg × 60 ÷ nồng độ sau pha mcg/mL.")

    if drug_name == "Noradrenaline" and map_mmHg < 65:
        st.warning(
            "MAP < 65 mmHg. Noradrenaline thường là vận mạch đầu tay trong sốc nhiễm khuẩn; "
            "ưu tiên đường truyền trung tâm nếu có. Nếu dùng ngoại biên, cần theo dõi thoát mạch sát theo phác đồ bệnh viện."
        )

# ============================================================
# Module 6: Inotrope decision support and calculator
# ============================================================

st.header("6. Inotrope: chỉ bật khi có low-output phenotype phù hợp")

# Dữ kiện sàng lọc, không tự động bắt dùng inotrope.
ef_reduced = severe_hfrEF or cardiogenic_active
cold_hypoperfusion = st.checkbox("Chi lạnh / CRT kéo dài / mottling", value=False, key="ino_cold_screen")
persistent_lactate = lactate > 4
rapid_af = heart_rate >= 120
low_vti_or_low_co = st.checkbox("VTI/CO thấp trên POCUS/monitor", value=False, key="ino_low_co_screen")
rv_failure = st.checkbox("Nghi suy thất phải / tăng áp phổi", value=False, key="ino_rv_failure_screen")
ischemia_concern = st.checkbox("Nghi thiếu máu cơ tim cấp", value=False, key="ino_ischemia_screen")

# Với MAP rất cao, nhất là phù phổi cấp/tăng HA, dobutamine thường không phải hướng mặc định.
# App chỉ mở tính liều nếu có low CO xác nhận hoặc bác sĩ override.
hypertensive_state = map_mmHg >= 90
inotrope_indication = (
    (map_mmHg < 65 and (ef_reduced or low_vti_or_low_co or cold_hypoperfusion))
    or (65 <= map_mmHg < 90 and low_vti_or_low_co and cold_hypoperfusion)
)

manual_inotrope_override = False

# Giá trị mặc định để summary không lỗi.
inotrope_rec = {
    "need_inotrope": False,
    "level": "BLUE",
    "drug": "Không dùng inotrope",
    "dose": 0.0,
    "preset": "Dobutamine 250 mg/50 mL",
    "text": "Không có chỉ định tự động gợi ý inotrope.",
    "warnings": [],
}
inotrope_name = "Không dùng inotrope"
ino_total_drug_mg = 0.0
ino_final_volume_ml = 0.0
inotrope_dose = 0.0
inotrope_result = {
    "total_drug_mg": 0.0,
    "total_drug_mcg": 0.0,
    "final_concentration_mcg_ml": 0.0,
    "required_mcg_min": 0.0,
    "pump_rate_ml_hour": 0.0,
}

if hypertensive_state:
    st.success(
        f"MAP {map_mmHg:.0f} mmHg: không tự động gợi ý dobutamine/inotrope. "
        "Nếu là phù phổi cấp do tăng huyết áp, ưu tiên oxy/NIV, giảm tiền tải-hậu tải, lợi tiểu/giãn mạch theo phác đồ, kiểm soát thiếu máu cơ tim/loạn nhịp và tìm nguyên nhân lactate tăng."
    )
    if low_vti_or_low_co:
        st.warning(
            "Có nhập VTI/CO thấp: đây là tình huống đặc biệt. Chỉ cân nhắc inotrope khi đã đánh giá huyết động đầy đủ và có theo dõi sát."
        )
    manual_inotrope_override = st.checkbox(
        "Vẫn mở máy tính inotrope thủ công",
        value=False,
        key="manual_inotrope_override_high_map",
    )
elif inotrope_indication:
    st.warning(
        "Có dữ kiện gợi ý low-output phenotype. App sẽ mở phần gợi ý inotrope và tính tốc độ bơm."
    )
else:
    st.info(
        "Chưa đủ dữ kiện để mở inotrope tự động. Có thể mở thủ công nếu đã có bằng chứng low cardiac output."
    )
    manual_inotrope_override = st.checkbox(
        "Mở máy tính inotrope thủ công",
        value=False,
        key="manual_inotrope_override_normal_map",
    )

show_inotrope_calculator = inotrope_indication or manual_inotrope_override

if show_inotrope_calculator:
    norepi_running_or_planned = st.checkbox("Đang/chuẩn bị chạy Noradrenaline", value=map_mmHg < 65, key="ino_norepi")
    map_supported = st.checkbox("MAP đã/đang được hỗ trợ bằng vận mạch", value=map_mmHg >= 60 or norepi_running_or_planned, key="ino_map_supported")

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

    if not inotrope_indication:
        st.warning("Đang mở máy tính thủ công. App không xem đây là khuyến cáo tự động dùng inotrope.")

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

st.header("7. Cảnh báo liều cao và nguyên nhân sốc kháng trị")

if not show_vasopressor_calculator and not show_inotrope_calculator:
    st.info("Không có vận mạch/inotrope đang được tính trong app, nên ẩn checklist liều cao để giảm rối mắt.")
    high_dose_red_flags = False
else:
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

    with st.expander("Checklist cần xem lại khi cần vận mạch/inotrope liều cao", expanded=False):
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
    infection_with_organ_dysfunction = possible_sepsis and (lactate >= 2 or urine_output_ml_kg_h < 0.5 or spo2 < 90)
    septic_shock_for_abx = possible_sepsis and map_mmHg < 65
    high_risk_infection_for_abx = possible_sepsis and (septic_shock_for_abx or lactate >= 4 or infection_with_organ_dysfunction)

    # Phân tầng timing kháng sinh rõ ràng hơn:
    # - Septic shock: nghi nhiễm khuẩn + MAP < 65.
    # - High-risk sepsis: nghi nhiễm khuẩn + lactate >= 4 nhưng MAP không thấp.
    # Lactate cao một mình không tạo chỉ định vận mạch, nhưng vẫn là dấu hiệu nặng cần kháng sinh sớm nếu xác suất nhiễm khuẩn cao.
    st.subheader("8.1. Thời điểm dùng kháng sinh")

    septic_shock = (
        possible_sepsis
        and map_mmHg < 65
    )

    high_risk_sepsis = (
        possible_sepsis
        and lactate >= 4
        and map_mmHg >= 65
    )

    possible_sepsis_without_shock = (
        possible_sepsis
        and not septic_shock
        and not high_risk_sepsis
    )

    if septic_shock:
        timing_text = (
            "Septic shock: dùng kháng sinh phổ rộng càng sớm càng tốt, lý tưởng trong 1 giờ. "
            "Lấy cấy trước nếu không làm trì hoãn."
        )
        st.error(timing_text)

    elif high_risk_sepsis:
        timing_text = (
            "Khả năng nhiễm khuẩn cao kèm lactate tăng/giảm tưới máu mô nhưng MAP hiện chưa thấp. "
            "Không gọi là septic shock nếu MAP ≥ 65 mmHg, nhưng vẫn cần dùng kháng sinh sớm nếu xác suất nhiễm khuẩn cao. "
            "Lấy cấy trước nếu không làm trì hoãn."
        )
        st.warning(timing_text)

    elif possible_sepsis_without_shock:
        timing_text = (
            "Nghi sepsis nhưng chưa sốc: đánh giá nhanh khả năng nhiễm khuẩn, lấy cấy phù hợp "
            "và dùng kháng sinh sớm nếu xác suất nhiễm khuẩn cao."
        )
        st.info(timing_text)

    else:
        timing_text = (
            "Chưa đủ dữ kiện nhiễm khuẩn rõ. Tiếp tục đánh giá và tránh lạm dụng kháng sinh nếu xác suất nhiễm khuẩn thấp."
        )
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
            "CrCl Cockcroft-Gault dùng chỉnh liều (mL/phút)",
            min_value=0.0,
            max_value=200.0,
            value=float(round(calculated_crcl, 1)),
            step=1.0,
            key="abx_egfr",
        )
        on_hemodialysis_for_dosing = st.checkbox(
            "Đang lọc máu chu kỳ / chỉnh liều theo lịch lọc máu",
            value=anuric_ckd,
            key="abx_on_hemodialysis_for_dosing",
        )

    st.caption(
        f"CrCl tự tính theo Cockcroft-Gault từ tuổi, giới, cân nặng và creatinine. "
        f"Cân nặng dùng tính: {cg_weight:.1f} kg ({cg_weight_method}). "
        "Có thể chỉnh tay nếu ESRD/lọc máu, phù nhiều, cụt chi, AKI hoặc creatinine không ổn định."
    )

    current_protocol = ANTIBIOTIC_PROTOCOLS.get(infection_focus, ANTIBIOTIC_PROTOCOLS["Chưa rõ ổ nhiễm"])

    culture_options = [
        "Cấy máu 2 bộ",
        "Cấy nước tiểu",
        "Cấy đàm / hút đàm",
        "Cấy dịch vô khuẩn / dịch ổ bụng / màng phổi",
        "Cấy catheter nếu nghi liên quan",
        "Cấy mô/dịch mủ sâu nếu có",
    ]
    suggested_cultures = [item for item in culture_options if any(item.lower().split(" /")[0] in c.lower() for c in current_protocol["cultures"])]
    if "Cấy máu 2 bộ" in current_protocol["cultures"] and "Cấy máu 2 bộ" not in suggested_cultures:
        suggested_cultures.insert(0, "Cấy máu 2 bộ")
    if infection_focus == "Nhiễm khuẩn tiết niệu phức tạp / Pyelonephritis" and "Cấy nước tiểu" not in suggested_cultures:
        suggested_cultures.append("Cấy nước tiểu")
    if infection_focus == "Viêm phổi cộng đồng nặng" and "Cấy đàm / hút đàm" not in suggested_cultures:
        suggested_cultures.append("Cấy đàm / hút đàm")
    if infection_focus == "Nhiễm khuẩn ổ bụng" and "Cấy dịch vô khuẩn / dịch ổ bụng / màng phổi" not in suggested_cultures:
        suggested_cultures.append("Cấy dịch vô khuẩn / dịch ổ bụng / màng phổi")
    if infection_focus == "Nhiễm khuẩn huyết liên quan catheter" and "Cấy catheter nếu nghi liên quan" not in suggested_cultures:
        suggested_cultures.append("Cấy catheter nếu nghi liên quan")

    source_control_needed = infection_focus in [
        "Nhiễm khuẩn ổ bụng",
        "Da - mô mềm nặng",
        "Nhiễm khuẩn tiết niệu phức tạp / Pyelonephritis",
        "Nhiễm khuẩn huyết liên quan catheter",
    ]

    st.subheader("8.3. Bệnh phẩm và source control")
    st.info("Mục này được thu gọn vì đa số thao tác cấy là checklist cơ bản. App chỉ nhắc nhanh theo ổ nhiễm và không làm rối giao diện.")

    st.write("**Gợi ý nhanh theo ổ nhiễm:** " + "; ".join(suggested_cultures))

    with st.expander("Mở checklist cấy bệnh phẩm chi tiết", expanded=False):
        st.write("**Bệnh phẩm app gợi ý theo ổ nhiễm đang chọn:**")
        for culture_item in current_protocol["cultures"]:
            st.write(f"- {culture_item}")

        selected_cultures = st.multiselect(
            "Checklist cấy cần thực hiện/đã thực hiện",
            options=culture_options,
            default=suggested_cultures,
            key="abx_cultures_" + infection_focus,
        )

        source_control_needed = st.checkbox(
            "Cần đánh giá kiểm soát nguồn nhiễm",
            value=source_control_needed,
            key="abx_source_control_" + infection_focus,
        )

    if high_risk_infection_for_abx:
        st.error("Nhiễm khuẩn nặng/septic shock/high-risk sepsis: không trì hoãn kháng sinh để chờ cấy nếu việc lấy cấy gây chậm trễ đáng kể.")

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

    inferred_risks = infer_specific_resistance_risks(
        infection_focus=infection_focus,
        community_or_hospital=community_or_hospital,
        recent_hospitalization=recent_hospitalization,
        recent_antibiotics=recent_antibiotics,
        prior_mdr=prior_mdr,
        nursing_home=nursing_home,
        hemodialysis=hemodialysis,
        immunosuppression=immunosuppression,
        invasive_device=invasive_device,
        prior_colonization_unknown=prior_colonization_unknown,
    )

    st.write("**App tự suy luận nguy cơ mở rộng phổ từ checklist:**")
    auto_cols = st.columns(4)
    auto_cols[0].metric("MRSA", "Có" if inferred_risks["mrsa_risk"] else "Không rõ")
    auto_cols[1].metric("Pseudomonas", "Có" if inferred_risks["pseudomonas_risk"] else "Không rõ")
    auto_cols[2].metric("ESBL", "Có" if inferred_risks["esbl_risk"] else "Không rõ")
    auto_cols[3].metric("Candida", "Có" if inferred_risks["candida_risk"] else "Không rõ")

    with st.expander("Xem lý do app suy luận nguy cơ"):
        for risk_name, reason_list in inferred_risks["reasons"].items():
            meaningful_reasons = [r for r in reason_list if "Tiền sử vi sinh chưa rõ" not in r]
            if meaningful_reasons:
                st.write(f"**{risk_name}:**")
                for reason in meaningful_reasons:
                    st.write(f"- {reason}")

    st.write("Bác sĩ có thể override nếu có dữ liệu vi sinh/antibiogram cụ thể:")
    col_cov1, col_cov2, col_cov3, col_cov4 = st.columns(4)
    with col_cov1:
        mrsa_risk = st.checkbox("Bao phủ MRSA", value=inferred_risks["mrsa_risk"], key="abx_mrsa")
    with col_cov2:
        pseudomonas_risk = st.checkbox("Bao phủ Pseudomonas", value=inferred_risks["pseudomonas_risk"], key="abx_pseudomonas")
    with col_cov3:
        esbl_risk = st.checkbox("Bao phủ ESBL", value=inferred_risks["esbl_risk"], key="abx_esbl")
    with col_cov4:
        candida_risk = st.checkbox("Bao phủ Candida/nấm xâm lấn", value=inferred_risks["candida_risk"], key="abx_candida")

    if mdr_risk:
        st.warning("Có yếu tố nguy cơ MDR: " + ", ".join(mdr_factors))
    elif prior_colonization_unknown:
        st.info("Chưa có yếu tố MDR rõ, nhưng tiền sử vi sinh chưa đầy đủ. Cần kiểm tra hồ sơ cấy cũ nếu có.")
    else:
        st.success("Chưa ghi nhận yếu tố nguy cơ MDR rõ.")

    likely_pathogens = suggest_likely_pathogens(
        infection_focus=infection_focus,
        community_or_hospital=community_or_hospital,
        mrsa_risk=mrsa_risk,
        pseudomonas_risk=pseudomonas_risk,
        esbl_risk=esbl_risk,
        candida_risk=candida_risk,
    )

    st.subheader("8.5. Tác nhân có khả năng và gợi ý coverage")
    st.write("**Tác nhân/nhóm tác nhân cần nghĩ tới:**")
    for pathogen in likely_pathogens:
        st.write(f"- {pathogen}")

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

    st.subheader("8.6. Chọn kháng sinh cụ thể để xem liều và cảnh báo")

    selected_antibiotic = st.selectbox(
        "Chọn kháng sinh cụ thể để xem liều và cảnh báo",
        list(ANTIBIOTIC_DOSING.keys()),
        index=0,
        key="abx_specific_drug",
    )

    dose_rec = get_antibiotic_dose_recommendation(
        antibiotic_name=selected_antibiotic,
        crcl=egfr,
        on_hemodialysis=on_hemodialysis_for_dosing,
    )

    col_dose1, col_dose2, col_dose3 = st.columns(3)
    with col_dose1:
        st.metric("Kháng sinh", dose_rec["antibiotic"])
    with col_dose2:
        st.metric("Nhóm chức năng thận", dose_rec["renal_label"])
    with col_dose3:
        st.metric("CrCl dùng tính liều", f"{egfr:.1f} mL/phút")

    st.info(f"**Liều gợi ý tham khảo:** {dose_rec['dose_text']}")

    st.write("**Cảnh báo nền của thuốc:**")
    for warning in dose_rec["warnings"]:
        st.warning(warning)

    clinical_alerts = generate_antibiotic_clinical_alerts(
        antibiotic_name=selected_antibiotic,
        heart_rate=heart_rate,
        drug_name=drug_name,
        inotrope_name=inotrope_name,
        desired_dose=desired_dose,
        inotrope_dose=inotrope_dose,
        crcl=egfr,
        on_hemodialysis=on_hemodialysis_for_dosing,
        ckd_any=ckd_any,
        anuric_ckd=anuric_ckd,
        pulmonary_edema=pulmonary_edema,
    )

    if clinical_alerts:
        st.write("**Cảnh báo cá thể hóa theo dữ kiện trong app:**")
        for severity, message in clinical_alerts:
            if severity == "error":
                st.error(message)
            elif severity == "warning":
                st.warning(message)
            else:
                st.info(message)

    st.subheader("8.7. Stewardship và review sau 24–48–72 giờ")
    st.write("- Đánh giá lại chẩn đoán nhiễm khuẩn khi có diễn tiến lâm sàng, hình ảnh học và kết quả cấy.")
    st.write("- Xuống thang kháng sinh khi có kháng sinh đồ hoặc khi xác suất MDR thấp.")
    st.write("- Ngưng kháng sinh nếu xác suất nhiễm khuẩn thấp và có chẩn đoán thay thế phù hợp.")
    st.write("- Chỉnh liều theo eGFR/CrCl, cân nặng, mức độ nặng, lọc máu và khuyến cáo dược lâm sàng.")

    antibiotic_summary_lines.append(f"- Kháng sinh: đã bật module; ổ nhiễm nghi ngờ: {infection_focus}; bối cảnh: {community_or_hospital}")
    antibiotic_summary_lines.append(f"- Timing: {timing_text}")
    antibiotic_summary_lines.append("- Bệnh phẩm gợi ý: " + "; ".join(selected_cultures))
    antibiotic_summary_lines.append("- Tác nhân cần nghĩ: " + "; ".join(likely_pathogens[:6]))
    antibiotic_summary_lines.append("- Coverage chính: " + "; ".join(antibiotic_recommendation["coverage"][:5]))
    antibiotic_summary_lines.append("- Gợi ý nhóm: " + "; ".join(antibiotic_recommendation["suggestions"][:4]))
    antibiotic_summary_lines.append(
        f"- Kháng sinh cụ thể: {selected_antibiotic}; CrCl {egfr:.1f} mL/phút; "
        f"liều tham khảo: {dose_rec['dose_text']}"
    )

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

if show_vasopressor_calculator and drug_name != "Không dùng vận mạch" and map_mmHg < 65:
    summary_lines.append(
        f"- Vận mạch: {drug_name}, pha {total_drug_mg:.1f} mg/{final_volume_ml:.0f} mL, "
        f"nồng độ {vasopressor_result['final_concentration_mcg_ml']:.1f} mcg/mL"
    )
    summary_lines.append(
        f"- Liều vận mạch: {desired_dose:.3f} mcg/kg/phút → "
        f"{vasopressor_result['pump_rate_ml_hour']:.2f} mL/giờ"
    )
elif show_vasopressor_calculator and drug_name != "Không dùng vận mạch":
    summary_lines.append(
        f"- Vận mạch: máy tính được mở thủ công; {drug_name}, pha {total_drug_mg:.1f} mg/{final_volume_ml:.0f} mL, "
        f"liều {desired_dose:.3f} mcg/kg/phút → {vasopressor_result['pump_rate_ml_hour']:.2f} mL/giờ. "
        "App không xem đây là chỉ định tự động vì MAP hiện không thấp."
    )
else:
    summary_lines.append(
        "- Vận mạch: chưa có chỉ định nâng MAP bằng vận mạch vì MAP hiện ≥65 mmHg. "
        "Không tự động gợi ý Noradrenaline."
    )

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
