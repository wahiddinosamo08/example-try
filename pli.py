"""
Line Pack Calculator — Natural Gas Pipelines
---------------------------------------------
Computes standard-volume gas inventory inside a transmission pipeline
segment, given operating pressure, temperature, geometry, and gas
compressibility.

Formula (standard volume at base conditions):

    V_std = (pi/4) * D^2 * L * (P / P_b) * (T_b / T) * (1 / Z)

where:
    P_b = 14.696 psia        (base pressure)
    T_b = 519.67 deg R       (base temperature = 60 deg F)
    P, T are absolute units
    Z   = gas compressibility factor (typ. 0.85 - 0.95)

Run locally:
    pip install streamlit
    streamlit run app.py
"""

import math
import streamlit as st

# ---------- Constants ----------
PSI_ATM = 14.696          # psia
T_BASE_R = 519.67         # degrees Rankine (60 deg F)
P_BASE_PSIA = 14.696      # psia
IN_TO_FT = 1.0 / 12.0
KM_TO_FT = 3280.8399


# ---------- Core calculation ----------
def calc_line_pack(diameter_in, length_km, pressure_psig, temperature_C, z):
    """Return a dict with geometric volume, standard volume, MMSCF, and absolutes."""
    D_ft = diameter_in * IN_TO_FT
    L_ft = length_km * KM_TO_FT
    V_geom_ft3 = (math.pi / 4.0) * D_ft * D_ft * L_ft

    P_psia = pressure_psig + PSI_ATM
    T_R = (temperature_C + 273.15) * 1.8   # deg C -> K -> deg R

    V_std_ft3 = V_geom_ft3 * (P_psia / P_BASE_PSIA) * (T_BASE_R / T_R) * (1.0 / z)

    return {
        "V_geom_ft3": V_geom_ft3,
        "V_std_ft3": V_std_ft3,
        "V_std_MMSCF": V_std_ft3 / 1_000_000.0,
        "P_psia": P_psia,
        "T_R": T_R,
    }


# ---------- Page config ----------
st.set_page_config(
    page_title="Line Pack Calculator",
    page_icon="⚙️",
    layout="wide",
)

# ---------- Header ----------
st.markdown(
    """
    <div style="border-bottom:1px solid #333; padding-bottom:14px; margin-bottom:24px;">
        <div style="color:#f5a623; font-size:12px; letter-spacing:3px; text-transform:uppercase;">
            ● Pipeline Integrity Toolkit
        </div>
        <h1 style="margin:6px 0 4px 0; font-size:42px; font-weight:600;">
            Line Pack Calculator
        </h1>
        <p style="color:#888; font-size:14px; max-width:640px;">
            Computes the standard-volume gas inventory inside a natural-gas
            transmission pipeline segment. For preliminary engineering and
            depressurization planning. Verify with AGA-8 for billing-grade work.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Two columns: inputs + result ----------
col_input, col_output = st.columns([1, 1.1])

with col_input:
    st.markdown("##### INPUTS")

    diameter_in = st.number_input(
        "Diameter (in)", value=42.0, min_value=0.0, step=1.0,
        help="Nominal pipe internal diameter"
    )
    length_km = st.number_input(
        "Length (km)", value=100.0, min_value=0.0, step=0.1,
        help="Pipeline segment length"
    )
    pressure_psig = st.number_input(
        "Pressure (psig)", value=830.0, min_value=0.0, step=10.0,
        help="Gauge operating pressure"
    )
    temperature_C = st.number_input(
        "Temperature (°C)", value=30.0, step=1.0,
        help="Flowing gas temperature"
    )
    z = st.number_input(
        "Z-factor", value=0.90, min_value=0.1, max_value=1.5, step=0.01,
        help="Compressibility factor (typ. 0.85–0.95 for transmission)"
    )

# ---------- Compute ----------
r = calc_line_pack(diameter_in, length_km, pressure_psig, temperature_C, z)

with col_output:
    st.markdown("##### RESULT")

    st.markdown(
        f"""
        <div style="border:1px solid rgba(245,166,35,0.4);
                    background: linear-gradient(135deg, rgba(245,166,35,0.08), transparent);
                    border-radius:10px; padding:24px;">
            <div style="color:#f5a623; font-size:11px; letter-spacing:3px;
                        text-transform:uppercase;">
                Line Pack (Standard Volume)
            </div>
            <div style="font-family:'JetBrains Mono', monospace; font-size:56px;
                        font-weight:600; color:#ffe9b0; margin-top:4px;
                        line-height:1.1;">
                {r['V_std_MMSCF']:.2f}
            </div>
            <div style="color:#999; font-size:14px;">MMSCF</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # secondary stats
    s1, s2 = st.columns(2)
    s1.metric("Geometric Volume", f"{r['V_geom_ft3']:,.0f} ft³")
    s2.metric("Standard Volume", f"{r['V_std_ft3']:,.0f} scf")
    s3, s4 = st.columns(2)
    s3.metric("Absolute Pressure", f"{r['P_psia']:.2f} psia")
    s4.metric("Absolute Temperature", f"{r['T_R']:.2f} °R")

# ---------- Formula block ----------
st.markdown("---")
st.markdown("##### FORMULA")

st.latex(
    r"V_{std} \;=\; \frac{\pi}{4} D^2 L \cdot \frac{P}{P_b} \cdot \frac{T_b}{T} \cdot \frac{1}{Z}"
)
st.markdown(
    """
    - **P<sub>b</sub>** = 14.696 psia &nbsp;·&nbsp; **T<sub>b</sub>** = 519.67 °R (60 °F)  
    - **P, T** converted to absolute units internally  
    - **Z** defaults to 0.90 — use AGA-8 or an EOS for precise work  
    - Internal diameter ≈ nominal diameter (no wall-thickness correction)
    """,
    unsafe_allow_html=True,
)

# ---------- Footer ----------
st.markdown(
    """
    <div style="margin-top:40px; padding-top:16px; border-top:1px solid #333;
                display:flex; justify-content:space-between;
                color:#666; font-size:11px; letter-spacing:2px;
                text-transform:uppercase;">
        <span>For preliminary engineering use only</span>
        <span>v0.1 · Wahid Dino Samo</span>
    </div>
    """,
    unsafe_allow_html=True,
)
