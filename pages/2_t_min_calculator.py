"""
Minimum Wall Thickness (t_min) Calculator — ASME B31.8
-------------------------------------------------------
Computes pressure design thickness for natural-gas transmission
pipelines per ASME B31.8 §841 "Steel Pipe Design Formula".

v0.2 — Added class location sensitivity chart and inspector notes.
"""

import streamlit as st
import pandas as pd


# ---------- Reference data ----------
SMYS_TABLE = {
    "API 5L X42": 42_000,
    "API 5L X46": 46_000,
    "API 5L X52": 52_000,
    "API 5L X56": 56_000,
    "API 5L X60": 60_000,
    "API 5L X65": 65_000,
    "API 5L X70": 70_000,
    "API 5L X80": 80_000,
    "ASTM A106 Gr B": 35_000,
    "Custom (enter manually)": None,
}

CLASS_LOCATION = {
    "Class 1, Division 2 — desert / rural (F = 0.72)": 0.72,
    "Class 1, Division 1 — special (F = 0.60)": 0.60,
    "Class 2 — fringe / light populated (F = 0.60)": 0.60,
    "Class 3 — suburban / industrial (F = 0.50)": 0.50,
    "Class 4 — dense urban / multi-storey (F = 0.40)": 0.40,
}

CLASS_CHART = [
    ("Class 1 Div 2", 0.72),
    ("Class 1 Div 1", 0.60),
    ("Class 2",       0.60),
    ("Class 3",       0.50),
    ("Class 4",       0.40),
]

JOINT_FACTOR = {
    "Seamless (E = 1.00)": 1.00,
    "ERW – modern, post-1970 (E = 1.00)": 1.00,
    "Submerged Arc Weld – SAW (E = 1.00)": 1.00,
    "Furnace butt weld – legacy (E = 0.60)": 0.60,
}

TEMP_DERATE_F = [
    (250, 1.000),
    (300, 0.967),
    (350, 0.933),
    (400, 0.900),
    (450, 0.867),
]


def temp_derate_factor(temp_C: float) -> float:
    temp_F = temp_C * 9.0 / 5.0 + 32.0
    if temp_F <= 250:
        return 1.0
    if temp_F >= 450:
        return 0.867
    for i in range(len(TEMP_DERATE_F) - 1):
        t1, f1 = TEMP_DERATE_F[i]
        t2, f2 = TEMP_DERATE_F[i + 1]
        if t1 <= temp_F <= t2:
            return f1 + (f2 - f1) * (temp_F - t1) / (t2 - t1)
    return 1.0


def calc_tmin(P_psig, D_in, S_psi, F, E, T, corrosion_in, mill_tol_pct):
    t_design = (P_psig * D_in) / (2.0 * S_psi * F * E * T)
    t_required = t_design + corrosion_in
    t_nominal = t_required / (1.0 - mill_tol_pct / 100.0)
    return {
        "t_design_in": t_design,
        "t_required_in": t_required,
        "t_nominal_in": t_nominal,
        "t_design_mm": t_design * 25.4,
        "t_required_mm": t_required * 25.4,
        "t_nominal_mm": t_nominal * 25.4,
    }


# ---------- Page config ----------
st.set_page_config(
    page_title="t_min Calculator — ASME B31.8",
    page_icon="⚙️",
    layout="wide",
)

# ---------- Header ----------
st.markdown(
    """
    <div style="border-bottom:1px solid #333; padding-bottom:14px; margin-bottom:24px;">
        <div style="color:#f5a623; font-size:12px; letter-spacing:3px; text-transform:uppercase;">
            ● Pipeline Integrity Toolkit · Tool 2
        </div>
        <h1 style="margin:6px 0 4px 0; font-size:38px; font-weight:600; line-height:1.15;">
            Minimum Wall Thickness Calculator
        </h1>
        <p style="color:#888; font-size:14px; max-width:680px; margin-top:8px;">
            Pressure design thickness per <strong>ASME B31.8 §841</strong> for
            steel gas transmission pipelines. Outputs design, required, and
            nominal wall thicknesses with corrosion allowance and mill tolerance.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Layout ----------
col_input, col_output = st.columns([1, 1.1])

with col_input:
    st.markdown("##### INPUTS")

    P_psig = st.number_input("Design Pressure (psig)",
        value=1000.0, min_value=0.0, step=10.0,
        help="MAOP or design pressure of the segment")
    D_in = st.number_input("Outside Diameter (in)",
        value=42.0, min_value=0.0, step=1.0,
        help="Nominal outside diameter (NPS)")

    material = st.selectbox("Material / Grade",
        options=list(SMYS_TABLE.keys()), index=6,
        help="SMYS auto-fills from API 5L. Choose Custom to enter manually.")
    if SMYS_TABLE[material] is None:
        S_psi = st.number_input("SMYS (psi) — manual entry",
            value=52_000.0, min_value=1_000.0, step=1000.0)
    else:
        S_psi = float(SMYS_TABLE[material])
        st.caption(f"SMYS = **{S_psi:,.0f} psi**")

    class_choice = st.selectbox("Class Location (Design Factor F)",
        options=list(CLASS_LOCATION.keys()), index=0,
        help="ASME B31.8 §840.2 — based on population density along pipeline")
    F = CLASS_LOCATION[class_choice]

    joint_choice = st.selectbox("Longitudinal Joint Type (E)",
        options=list(JOINT_FACTOR.keys()), index=0)
    E = JOINT_FACTOR[joint_choice]

    temp_C = st.number_input("Design Temperature (°C)",
        value=30.0, step=5.0,
        help="Derating starts above 121°C (250°F)")
    T = temp_derate_factor(temp_C)
    st.caption(f"Temperature derating factor T = **{T:.3f}**")

    st.divider()
    st.markdown("**Allowances**")

    corrosion_in = st.number_input("Corrosion Allowance (in)",
        value=0.0625, min_value=0.0, step=0.0125,
        help="Typical: 1/16″ (0.0625″) for sweet service")
    mill_tol_pct = st.number_input("Mill Tolerance (%)",
        value=12.5, min_value=0.0, max_value=50.0, step=0.5,
        help="API 5L PSL2 typically 12.5%")

# ---------- Compute ----------
r = calc_tmin(P_psig, D_in, S_psi, F, E, T, corrosion_in, mill_tol_pct)

with col_output:
    st.markdown("##### RESULT")

    st.markdown(
        f"""
        <div style="border:1px solid rgba(245,166,35,0.4);
                    background: linear-gradient(135deg, rgba(245,166,35,0.08), transparent);
                    border-radius:10px; padding:24px;">
            <div style="color:#f5a623; font-size:11px; letter-spacing:3px;
                        text-transform:uppercase;">
                Nominal Wall Thickness Required
            </div>
            <div style="font-family:'JetBrains Mono', monospace; font-size:48px;
                        font-weight:600; color:#ffe9b0; margin-top:6px;
                        line-height:1.1;">
                {r['t_nominal_in']:.4f} <span style="font-size:24px; color:#bba">in</span>
            </div>
            <div style="font-family:'JetBrains Mono', monospace; font-size:24px;
                        color:#ffe9b0; margin-top:2px;">
                {r['t_nominal_mm']:.2f} <span style="font-size:16px; color:#999">mm</span>
            </div>
            <div style="color:#888; font-size:12px; margin-top:10px;">
                Includes corrosion allowance and mill tolerance.
                Select next standard wall thickness ≥ this value.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    s1, s2 = st.columns(2)
    s1.metric("Pressure Design (t)", f"{r['t_design_in']:.4f} in",
              f"{r['t_design_mm']:.2f} mm")
    s2.metric("Required (t + CA)", f"{r['t_required_in']:.4f} in",
              f"{r['t_required_mm']:.2f} mm")

    s3, s4 = st.columns(2)
    s3.metric("Design Factor F", f"{F:.2f}")
    s4.metric("Temp Factor T", f"{T:.3f}")

# ==================================================================
# CLASS LOCATION SENSITIVITY CHART
# ==================================================================
st.markdown("---")
st.markdown("##### CLASS LOCATION SENSITIVITY")
st.markdown(
    "<p style='color:#888; font-size:13px; max-width:700px;'>"
    "Required nominal wall thickness at the inputs above, evaluated across "
    "every class location. Use this when a route passes through changing "
    "population density, or when assessing reclassification risk per "
    "<strong>API 570 §6.2.5</strong> and <strong>B31.8 §840.2</strong>."
    "</p>",
    unsafe_allow_html=True,
)

chart_rows = []
for label, F_class in CLASS_CHART:
    rc = calc_tmin(P_psig, D_in, S_psi, F_class, E, T, corrosion_in, mill_tol_pct)
    chart_rows.append({
        "Class Location": label,
        "Required t_nominal (mm)": round(rc["t_nominal_mm"], 2),
        "F factor": F_class,
    })
df = pd.DataFrame(chart_rows)

st.bar_chart(
    df,
    x="Class Location",
    y="Required t_nominal (mm)",
    color="#f5a623",
    height=320,
)

tnom_class1 = next(r["Required t_nominal (mm)"] for r in chart_rows if r["F factor"] == 0.72)
tnom_class4 = next(r["Required t_nominal (mm)"] for r in chart_rows if r["F factor"] == 0.40)
increase = (tnom_class4 / tnom_class1 - 1) * 100

st.info(
    f"**Reclassification impact:** moving this pipe from Class 1 Div 2 to Class 4 "
    f"requires **{increase:.0f}% more wall thickness** "
    f"({tnom_class1:.2f} mm → {tnom_class4:.2f} mm). "
    f"If the as-built pipe cannot satisfy the higher class, options per API 570 / B31.8 "
    f"include MAOP derating, partial replacement, or sleeving the affected section.",
    icon="📊",
)

# ==================================================================
# HOW TO USE — inspector grade, not textbook
# ==================================================================
st.markdown("---")
st.markdown("##### HOW TO USE THIS TOOL")

how_col1, how_col2 = st.columns(2)

with how_col1:
    st.markdown(
        """
        **For new design**
        1. Enter the **design pressure** (typically MAOP × 1.0).
        2. Pick the **highest class location** the route passes through — design for the worst case.
        3. Pick the **material grade** the project specifies.
        4. Use the **t_nominal** value to select the next standard wall schedule above it.
        5. Cross-check against ANSI B36.10M / API 5L pipe data sheets.
        """
    )

with how_col2:
    st.markdown(
        """
        **For inspection / fitness-for-service**
        1. Enter the **current MAOP**, not the original design pressure.
        2. Pick the **as-built material and joint type**.
        3. Compare **t_design** (not t_nominal) against measured wall thickness.
        4. If measured < t_design → derate pressure or repair per API 570 §8.
        5. For corroded pipe, use Tool 6 (B31G remaining strength) instead.
        """
    )

# ==================================================================
# COMMON PITFALLS
# ==================================================================
st.markdown("##### COMMON PITFALLS")

with st.expander("⚠️  Using nominal instead of measured thickness for FFS", expanded=False):
    st.markdown(
        "For an existing line, never use the *ordered* nominal thickness in fitness-for-service "
        "calculations — use the **lowest measured thickness** from your CMLs/TMLs. The mill tolerance "
        "and decades of corrosion mean the actual minimum is always below nominal. "
        "API 570 §7.2 explicitly requires the minimum measured value."
    )

with st.expander("⚠️  Class location was set at construction and never reviewed"):
    st.markdown(
        "ASME B31.8 §840.2.2 requires periodic class location review. Urban sprawl can shift a Class 1 "
        "line to Class 2 or 3 over 10–20 years. If you find encroachment during ROW inspection, the line "
        "may need MAOP derating even if no physical damage exists. This is a frequent NCR finding in audits."
    )

with st.expander("⚠️  Ignoring temperature derating on hot service"):
    st.markdown(
        "The T factor is often left at 1.0 because most gas transmission runs below 121 °C. "
        "But compressor station discharge piping, regen gas lines, and uninsulated southern-climate "
        "above-ground sections can exceed this. Use the highest sustained operating temperature, not the average."
    )

with st.expander("⚠️  Joint factor for legacy pipe is not always 1.0"):
    st.markdown(
        "Pipe manufactured before ~1970 may have furnace butt-welded longitudinal seams (E = 0.60), "
        "drastically reducing allowable thickness. Always check the mill test report (MTR) before assuming "
        "E = 1.0 on inherited assets. If MTR is unavailable, B31.8 Appendix N gives guidance."
    )

with st.expander("⚠️  Corrosion allowance is service-specific, not a universal 1/16″"):
    st.markdown(
        "0.0625″ is a sweet, dry, transmission-service default. Wet gas, H₂S service, or CO₂ partial-pressure "
        "above 30 psia can demand 1/8″ to 1/4″ CA, or specification of CRA-clad pipe. Confirm CA with the "
        "service specification, not habit."
    )

# ==================================================================
# FORMULA REFERENCE
# ==================================================================
st.markdown("---")
st.markdown("##### FORMULA — ASME B31.8 §841")

st.latex(r"t \;=\; \frac{P \cdot D}{2 \cdot S \cdot F \cdot E \cdot T}")

st.markdown(
    """
    | Symbol | Description | Source |
    |---|---|---|
    | **P** | Design pressure (psig) | MAOP or design pressure |
    | **D** | Outside diameter (in) | Nominal pipe OD |
    | **S** | SMYS (psi) | API 5L Table 6 |
    | **F** | Design factor | B31.8 §840.2 — class location |
    | **E** | Longitudinal joint factor | B31.8 Table 841.1.7-1 |
    | **T** | Temperature derating | B31.8 Table 841.1.8-1 |

    **Required thickness:** $t_{req} = t + CA$    (CA = corrosion allowance)

    **Nominal thickness ordered:** $t_{nom} = t_{req} \\,/\\, (1 - \\text{mill tol})$
    """,
    unsafe_allow_html=True,
)

st.info(
    "**For preliminary design and inspection review only.** "
    "Verify against the current edition of ASME B31.8. "
    "Special services (sour, HIC, low-temperature) require additional considerations "
    "not covered here. Not a substitute for a stamped engineering calculation.",
    icon="ℹ️",
)

# ---------- Footer ----------
st.markdown(
    """
    <div style="margin-top:40px; padding-top:16px; border-top:1px solid #333;
                display:flex; justify-content:space-between;
                color:#666; font-size:11px; letter-spacing:2px;
                text-transform:uppercase;">
        <span>For preliminary engineering use only</span>
        <span>v0.2 · Wahid Dino Samo</span>
    </div>
    """,
    unsafe_allow_html=True,
)
