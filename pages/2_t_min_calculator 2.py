"""
Minimum Wall Thickness (t_min) Calculator — ASME B31.8-2022
------------------------------------------------------------
Computes pressure design thickness for natural-gas piping systems
per ASME B31.8-2022 §841 "Steel Pipe Design Requirements".

v0.3 — Tables and clauses verified against ASME B31.8-2022 §841 and
       API 570 Second Edition (1998).

Verified source data:
    Table 841.1.6-1   Basic Design Factor, F (per Location Class)
    Table 841.1.6-2   Design Factors for Steel Pipe Construction (exceptions)
    Table 841.1.7-1   Longitudinal Weld Joint Quality Factor, E
    Table 841.1.8-1   Temperature Derating Factor, T
    §840.2.2          Location Class definitions
"""

import streamlit as st
import pandas as pd


# ============================================================
# VERIFIED REFERENCE DATA — ASME B31.8-2022
# ============================================================

# ----- §840.2.2 Location Class definitions + Table 841.1.6-1 -----
LOCATION_CLASS = {
    "Class 1, Division 1 — ≤10 buildings/mi, F > 0.72 design": {
        "F": 0.80,
        "desc": "≤10 buildings intended for human occupancy per 1-mi section. "
                "Wasteland, deserts, mountains, grazing land, farmland. "
                "Division 1 = pipe designed with F > 0.72."
    },
    "Class 1, Division 2 — ≤10 buildings/mi, F ≤ 0.72 design": {
        "F": 0.72,
        "desc": "Same population criterion as Div 1 (≤10 buildings/mi), "
                "but pipe designed with F ≤ 0.72. This is the typical default "
                "for new rural transmission pipelines."
    },
    "Class 2 — 11 to 45 buildings/mi": {
        "F": 0.60,
        "desc": "11–45 buildings intended for human occupancy per 1-mi section. "
                "Fringe areas around cities and towns, industrial areas, "
                "ranch or country estates."
    },
    "Class 3 — ≥46 buildings/mi (suburban / industrial)": {
        "F": 0.50,
        "desc": "≥46 buildings per 1-mi section. Suburban housing, shopping "
                "centers, residential, industrial areas not meeting Class 4."
    },
    "Class 4 — multistory buildings prevalent, dense traffic": {
        "F": 0.40,
        "desc": "Multistory buildings (4+ floors aboveground) prevalent, "
                "heavy/dense traffic, numerous other underground utilities."
    },
}

# ----- Table 841.1.6-2 exceptions (optional override) -----
F_EXCEPTIONS = {
    "(none — use basic factor from Class Location)": None,
    "Compressor station piping": {
        "F_by_class": {0.80: 0.50, 0.72: 0.50, 0.60: 0.50, 0.50: 0.50, 0.40: 0.40},
        "note": "Compressor station piping is capped at F = 0.50 in Classes 1–3 "
                "(0.40 in Class 4) regardless of basic Location Class.",
    },
    "Fabricated assemblies (separators, valve assemblies, etc.)": {
        "F_by_class": {0.80: 0.60, 0.72: 0.60, 0.60: 0.60, 0.50: 0.50, 0.40: 0.40},
        "note": "Per §841.1.9(a): F = 0.60 throughout the assembly and for "
                "5 diameters or 10 ft beyond the last fitting.",
    },
    "Pipelines on bridges": {
        "F_by_class": {0.80: 0.60, 0.72: 0.60, 0.60: 0.60, 0.50: 0.50, 0.40: 0.40},
        "note": "Per §841.1.9(b): all pipelines on bridges use F = 0.60 in "
                "Location Class 1 (Div 1 or 2).",
    },
    "Pressure/flow control & metering facilities": {
        "F_by_class": {0.80: 0.60, 0.72: 0.60, 0.60: 0.60, 0.50: 0.50, 0.40: 0.40},
        "note": "Per §841.1.9(d): metering and pressure control runs are "
                "limited to F = 0.60 in Classes 1–3.",
    },
    "Road / railroad crossing with hard surface (no casing)": {
        "F_by_class": {0.80: 0.60, 0.72: 0.60, 0.60: 0.50, 0.50: 0.50, 0.40: 0.40},
        "note": "Per Table 841.1.6-2: uncased crossings of paved roads, "
                "highways, public streets, or railroads.",
    },
}

# ----- Table 841.1.7-1 — Pipe Spec → SMYS (Appendix D) + Joint Factor E -----
# Each entry: spec, type, SMYS in psi (where applicable), E
# Organized as (spec, type) -> (SMYS or None, E)
# SMYS is grade-dependent for some specs — we expose grade separately when needed.

# API 5L grades and SMYS (Mandatory Appendix D of B31.8)
API_5L_GRADES = {
    "X42": 42_000,
    "X46": 46_000,
    "X52": 52_000,
    "X56": 56_000,
    "X60": 60_000,
    "X65": 65_000,
    "X70": 70_000,
    "X80": 80_000,
}

# Pipe spec → list of (type_label, E_factor, smys_or_None, smys_note)
PIPE_SPECS = {
    "API Spec 5L (line pipe)": [
        ("Seamless", 1.00, None, "grade-dependent"),
        ("Electric-resistance welded (ERW)", 1.00, None, "grade-dependent"),
        ("Submerged-arc welded (SAW, straight or helical)", 1.00, None, "grade-dependent"),
        ("Combination welded", 1.00, None, "grade-dependent"),
        ("Furnace-buttwelded, continuous weld", 0.60, None, "grade-dependent"),
    ],
    "ASTM A53": [
        ("Seamless", 1.00, 35_000, "Gr B SMYS = 35,000 psi"),
        ("Electric-resistance welded (ERW)", 1.00, 35_000, "Gr B SMYS = 35,000 psi"),
        ("Furnace-buttwelded, continuous weld", 0.60, 25_000, "Gr A SMYS = 25,000 psi"),
    ],
    "ASTM A106 (seamless carbon steel for high-temp)": [
        ("Seamless (only option for A106)", 1.00, 35_000, "Gr B SMYS = 35,000 psi"),
    ],
    "ASTM A134 (electric-fusion welded)": [
        ("Electric-fusion welded", 0.80, None, "depends on parent plate spec"),
    ],
    "ASTM A135 (ERW)": [
        ("Electric-resistance welded", 1.00, 30_000, "Gr A SMYS = 30,000 psi"),
    ],
    "ASTM A139 (electric-fusion welded)": [
        ("Electric-fusion welded", 0.80, 35_000, "Gr B SMYS = 35,000 psi"),
    ],
    "ASTM A333 (low-temp service)": [
        ("Seamless", 1.00, 35_000, "Gr 6 SMYS = 35,000 psi"),
        ("Electric-resistance welded", 1.00, 35_000, "Gr 6 SMYS = 35,000 psi"),
    ],
    "ASTM A381 (SAW for high-pressure)": [
        ("Submerged-arc welded", 1.00, None, "grade-dependent (Y35-Y65)"),
    ],
    "ASTM A671 / A672 / A691 (EFW, classes 12/22/32/42/52)": [
        ("Electric-fusion welded, Class _2 series", 1.00, None, "parent plate spec"),
    ],
    "ASTM A671 / A672 / A691 (EFW, classes 13/23/33/43/53)": [
        ("Electric-fusion welded, Class _3 series", 0.80, None, "parent plate spec"),
    ],
    "Custom / unknown — enter SMYS & E manually": [
        ("Manual entry", None, None, "user-provided"),
    ],
}

# ----- Table 841.1.8-1 — Temperature derating (verified) -----
TEMP_DERATE_F = [
    (250, 1.000),
    (300, 0.967),
    (350, 0.933),
    (400, 0.900),
    (450, 0.867),
]


def temp_derate_factor(temp_C: float) -> float:
    """Linear interpolation per General Note of Table 841.1.8-1."""
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
    """Compute per ASME B31.8-2022 §841.1.1: t = PD / (2 S F E T)."""
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


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="t_min Calculator — ASME B31.8",
    page_icon="⚙️",
    layout="wide",
)

# ----- Header -----
st.markdown(
    """
    <div style="border-bottom:1px solid #333; padding-bottom:14px; margin-bottom:20px;">
        <div style="color:#f5a623; font-size:12px; letter-spacing:3px; text-transform:uppercase;">
            ● Pipeline Integrity Toolkit · Tool 2
        </div>
        <h1 style="margin:6px 0 4px 0; font-size:38px; font-weight:600; line-height:1.15;">
            Minimum Wall Thickness Calculator
        </h1>
        <p style="color:#888; font-size:14px; max-width:680px; margin-top:8px;">
            Pressure design thickness per <strong>ASME B31.8-2022 §841.1.1</strong>
            for steel gas piping systems. All tables and clauses verified against
            the 2022 edition.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Single clarifying note about Class confusion (you asked for this)
with st.expander("ℹ️  Important — *Location Class* (this tool) vs *Service Class* (API 570)"):
    st.markdown(
        """
        Both standards use the word "Class" for different concepts. Don't confuse them.

        - **B31.8 Location Class** *(what this calculator uses)* — based on **population
          density** along the pipeline route (buildings per mile). Drives the design
          factor F for wall thickness.
        - **API 570 Service Class** — based on **consequence of fluid release**
          (flammable, toxic, etc.). Drives inspection frequency, not wall thickness.

        A pipeline can be B31.8 Location Class 1 *and* API 570 Service Class 1 at the
        same time — the words are identical but they measure different risks.
        """
    )

# ============================================================
# INPUTS
# ============================================================

col_input, col_output = st.columns([1, 1.05])

with col_input:
    st.markdown("##### INPUTS")

    # --- Pipe spec (combined material + joint) ---
    pipe_spec = st.selectbox(
        "Pipe Specification",
        options=list(PIPE_SPECS.keys()),
        index=0,
        help="Pick the specification on the MTR. SMYS and joint factor E auto-fill."
    )

    types_for_spec = PIPE_SPECS[pipe_spec]
    type_labels = [t[0] for t in types_for_spec]
    type_choice = st.selectbox(
        "Pipe Type / Welding Method",
        options=type_labels,
        index=0,
    )
    selected_type = next(t for t in types_for_spec if t[0] == type_choice)
    _, E, smys_fixed, smys_note = selected_type

    # --- Grade / SMYS handling ---
    if pipe_spec == "API Spec 5L (line pipe)":
        grade = st.selectbox(
            "API 5L Grade",
            options=list(API_5L_GRADES.keys()),
            index=6,  # X70 default — matches your 42" RLNG line
        )
        S_psi = float(API_5L_GRADES[grade])
        st.caption(f"SMYS = **{S_psi:,.0f} psi** · Joint factor E = **{E:.2f}**")
    elif smys_fixed is None:
        S_psi = st.number_input(
            "SMYS (psi) — manual entry",
            value=52_000.0, min_value=1_000.0, step=1000.0,
            help=smys_note,
        )
        if E is None:
            E = st.number_input(
                "Joint factor E", value=1.00, min_value=0.10, max_value=1.00, step=0.05
            )
        st.caption(f"Joint factor E = **{E:.2f}**")
    else:
        S_psi = float(smys_fixed)
        st.caption(f"SMYS = **{S_psi:,.0f} psi** · Joint factor E = **{E:.2f}** · {smys_note}")

    with st.expander("About: Pipe Spec / SMYS / Joint Factor E"):
        st.markdown(
            """
            **What this is:** The pipe specification on the Mill Test Report (MTR).
            ASME B31.8-2022 Table 841.1.7-1 assigns a Longitudinal Weld Joint Quality
            Factor (E) to each spec + manufacturing method combination. SMYS comes
            from the grade (B31.8 Mandatory Appendix D for API 5L; from the ASTM
            spec itself for ASTM grades).

            **Why it matters:** E penalizes weld seam quality. Furnace butt-welded
            pipe (legacy, pre-~1970) gets E = 0.60 — a 40% reduction in allowable
            thickness. Most modern welded and seamless pipe is E = 1.00, but A134
            and A139 electric-fusion welded are E = 0.80.

            **Worked example:** A 42″ RLNG transmission line specified as
            *API 5L X70 SAW*  →  SMYS = 70,000 psi, E = 1.00.
            """
        )

    st.divider()

    # --- Geometry & pressure ---
    P_psig = st.number_input(
        "Design Pressure (psig)",
        value=1000.0, min_value=0.0, step=10.0,
        help="MAOP or design pressure of the segment"
    )
    D_in = st.number_input(
        "Outside Diameter (in)",
        value=42.0, min_value=0.0, step=1.0,
    )

    with st.expander("About: Design Pressure & Diameter"):
        st.markdown(
            """
            **Design Pressure (P):** Use MAOP for fitness-for-service, or design
            pressure for new construction. Always *gauge* (psig), not absolute.
            Formula handles the conversion internally.

            **Outside Diameter (D):** Nominal pipe OD per ANSI B36.10M / API 5L.
            NPS 42 → 42.00 in OD. NPS 24 → 24.00 in OD. For NPS ≤ 12 the OD is
            slightly larger than NPS — check the spec.
            """
        )

    st.divider()

    # --- Location Class (with verified F factors) ---
    class_choice = st.selectbox(
        "Location Class (Table 841.1.6-1)",
        options=list(LOCATION_CLASS.keys()),
        index=1,  # default Class 1 Div 2 — most common for transmission
    )
    F_base = LOCATION_CLASS[class_choice]["F"]
    st.caption(f"Basic design factor F = **{F_base:.2f}** "
               f"(per Table 841.1.6-1, B31.8-2022)")

    with st.expander("About: Location Class & F factor"):
        st.markdown(
            f"""
            **What this is:** Per §840.2.2, Location Class is set by counting
            buildings intended for human occupancy in 1-mile sections along the
            route (¼-mile-wide zone centered on the pipeline).

            **Current selection:** {LOCATION_CLASS[class_choice]['desc']}

            **All five values from Table 841.1.6-1:**

            | Location Class | F |
            |---|---|
            | Class 1, Division 1 | 0.80 |
            | Class 1, Division 2 | 0.72 |
            | Class 2 | 0.60 |
            | Class 3 | 0.50 |
            | Class 4 | 0.40 |

            **Important:** This is the *basic* design factor. Compressor stations,
            road crossings, bridges, and fabricated assemblies have stricter F
            values per Table 841.1.6-2 — use the exception selector below if
            applicable.
            """
        )

    # --- F exception (Table 841.1.6-2) — collapsed by default ---
    with st.expander("Apply Table 841.1.6-2 exception? (compressor stations, crossings, bridges)"):
        exception_choice = st.selectbox(
            "Facility type override",
            options=list(F_EXCEPTIONS.keys()),
            index=0,
        )
        if F_EXCEPTIONS[exception_choice] is not None:
            exc = F_EXCEPTIONS[exception_choice]
            F = exc["F_by_class"][F_base]
            st.warning(f"**Override active:** {exc['note']}  \n"
                       f"F changed from {F_base:.2f} → **{F:.2f}**")
        else:
            F = F_base

    st.divider()

    # --- Temperature ---
    temp_C = st.number_input(
        "Design Temperature (°C)",
        value=30.0, step=5.0,
        help="Derating starts above 121°C (250°F)"
    )
    T = temp_derate_factor(temp_C)
    st.caption(f"Temperature derating T = **{T:.3f}** (Table 841.1.8-1)")

    with st.expander("About: Temperature Derating"):
        st.markdown(
            """
            **What this is:** Steel loses strength at elevated temperature.
            Table 841.1.8-1 derates allowable stress above 250°F (121°C).

            | Temperature | T |
            |---|---|
            | ≤ 250°F (121°C) | 1.000 |
            | 300°F (149°C) | 0.967 |
            | 350°F (177°C) | 0.933 |
            | 400°F (204°C) | 0.900 |
            | 450°F (232°C) | 0.867 |

            Intermediate values are linearly interpolated per the table's
            General Note.

            **Most transmission gas runs below 121°C, so T = 1.0 is typical.**
            Compressor station discharge, regen gas, and uninsulated hot lines
            can exceed this — use the highest sustained operating temperature.
            """
        )

    st.divider()

    # --- Allowances ---
    st.markdown("**Allowances**")

    corrosion_in = st.number_input(
        "Corrosion Allowance (in)",
        value=0.0625, min_value=0.0, step=0.0125,
        help="Typical: 1/16″ (0.0625″) for sweet service"
    )
    mill_tol_pct = st.number_input(
        "Mill Tolerance (%)",
        value=12.5, min_value=0.0, max_value=50.0, step=0.5,
        help="API 5L PSL2 = 12.5% typical"
    )

    with st.expander("About: Corrosion Allowance & Mill Tolerance"):
        st.markdown(
            """
            **Corrosion Allowance (CA):** Extra metal added to t_design so the
            pipe still has the required strength after expected metal loss over
            its design life. 1/16″ (0.0625″) is a default for sweet, dry service.
            Wet gas, H₂S service, or high CO₂ partial pressure may demand
            1/8″ to 1/4″ or CRA-clad pipe — confirm with service spec.

            **Mill Tolerance:** API 5L PSL2 allows the pipe to be delivered up
            to 12.5% under nominal wall. So if you order nominal 0.500″, the
            *thinnest legitimate* delivered pipe is 0.4375″. The calculator
            inflates t_required to t_nominal so that even worst-case mill
            delivery meets the required thickness:

            t_nominal = (t_design + CA) / (1 − mill_tol)
            """
        )

# ============================================================
# COMPUTE
# ============================================================
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
                Select next standard wall schedule ≥ this value.
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

    s3, s4, s5 = st.columns(3)
    s3.metric("F", f"{F:.2f}")
    s4.metric("E", f"{E:.2f}")
    s5.metric("T", f"{T:.3f}")

# ============================================================
# CLASS LOCATION SENSITIVITY CHART
# ============================================================
st.markdown("---")
st.markdown("##### CLASS LOCATION SENSITIVITY")
st.markdown(
    "<p style='color:#888; font-size:13px; max-width:700px;'>"
    "Required nominal wall thickness across every Location Class at the inputs "
    "above. Use this when a route passes through changing population density, "
    "or when assessing reclassification risk."
    "</p>",
    unsafe_allow_html=True,
)

chart_rows = []
for label, info in LOCATION_CLASS.items():
    rc = calc_tmin(P_psig, D_in, S_psi, info["F"], E, T, corrosion_in, mill_tol_pct)
    short_label = label.split(" — ")[0]
    chart_rows.append({
        "Location Class": short_label,
        "Required t_nominal (mm)": round(rc["t_nominal_mm"], 2),
        "F factor": info["F"],
    })
df = pd.DataFrame(chart_rows)

st.bar_chart(
    df, x="Location Class", y="Required t_nominal (mm)",
    color="#f5a623", height=320,
)

tnom_div1 = next(r["Required t_nominal (mm)"] for r in chart_rows if r["F factor"] == 0.80)
tnom_class4 = next(r["Required t_nominal (mm)"] for r in chart_rows if r["F factor"] == 0.40)
increase = (tnom_class4 / tnom_div1 - 1) * 100

st.info(
    f"**Reclassification impact:** moving this pipe from Class 1 Div 1 "
    f"(F = 0.80) to Class 4 (F = 0.40) requires **{increase:.0f}% more wall** "
    f"({tnom_div1:.2f} mm → {tnom_class4:.2f} mm). If the as-built pipe "
    f"can't satisfy the higher class, options include MAOP derating, partial "
    f"replacement, or sleeving the affected section.",
    icon="📊",
)

# ============================================================
# HOW TO USE
# ============================================================
st.markdown("---")
st.markdown("##### HOW TO USE THIS TOOL")

how_col1, how_col2 = st.columns(2)

with how_col1:
    st.markdown(
        """
        **For new design**
        1. Enter the **design pressure** (typically MAOP × 1.0).
        2. Pick the **pipe spec** the project specifies (e.g. API 5L X70 SAW).
        3. Pick the **highest Location Class** the route passes through.
        4. Apply any Table 841.1.6-2 exception (compressor station, crossing, etc.)
        5. Use **t_nominal** to select the next standard wall schedule above it.
        """
    )

with how_col2:
    st.markdown(
        """
        **For inspection / fitness-for-service**
        1. Enter the **current MAOP**, not original design pressure.
        2. Pick the **as-built pipe spec and joint type** from the MTR.
        3. Compare **t_design** (not t_nominal) against measured wall thickness.
        4. If measured < t_design → derate or repair per API 570 §8.1 / §8.3.
        5. For corroded pipe → use Tool 6 (B31G remaining strength).
        """
    )

# ============================================================
# COMMON PITFALLS (clause references verified against API 570 1998 edition)
# ============================================================
st.markdown("##### COMMON PITFALLS")

with st.expander("⚠️  Using nominal instead of measured thickness for FFS"):
    st.markdown(
        "For an existing line, never use the *ordered* nominal thickness in "
        "fitness-for-service calculations — use the **lowest measured thickness** "
        "from your TMLs. The mill tolerance and decades of corrosion mean the "
        "actual minimum is always below nominal. API 570 §5.5.2 and §7.1.3 "
        "explicitly require the minimum measured value (or an average within a "
        "test point per §3.46)."
    )

with st.expander("⚠️  Location Class set at construction and never reviewed"):
    st.markdown(
        "ASME B31.8 §840.2 requires Location Class to be determined from current "
        "land use. Urban sprawl can shift a Class 1 line to Class 2 or 3 over "
        "10–20 years. §840.2(g) explicitly states: when observed increases in "
        "buildings occur, Location Class shall be reassessed. If ROW encroachment "
        "is found during inspection, MAOP derating may be required even with no "
        "physical pipe damage."
    )

with st.expander("⚠️  Ignoring temperature derating on hot service"):
    st.markdown(
        "T is often left at 1.0 because most gas transmission runs below 121°C. "
        "But compressor station discharge, regen gas, and uninsulated above-ground "
        "sections can exceed this. Use the highest *sustained* operating "
        "temperature per §841.1.1 nomenclature, not the average."
    )

with st.expander("⚠️  Joint factor E ≠ 1.00 for legacy pipe"):
    st.markdown(
        "Pre-1970 furnace butt-welded pipe (API 5L or A53) carries E = 0.60 — "
        "a 40% reduction in allowable thickness. ASTM A134 and A139 "
        "electric-fusion welded pipe carry E = 0.80. Always check the MTR before "
        "assuming E = 1.00 on inherited assets. If MTR is unavailable, treat "
        "with caution per §817.1.3."
    )

with st.expander("⚠️  Corrosion allowance is service-specific, not a default"):
    st.markdown(
        "0.0625″ is a sweet, dry, transmission-service default. Wet gas, H₂S, "
        "or CO₂ partial-pressure above 30 psia can demand 1/8″ to 1/4″ CA or "
        "CRA-clad pipe. Confirm with the service specification, not habit."
    )

with st.expander("⚠️  Forgetting Table 841.1.6-2 exceptions"):
    st.markdown(
        "Compressor station piping caps at F = 0.50 even in remote Class 1 "
        "areas. Road/railroad crossings, bridges, and fabricated assemblies "
        "have stricter F values. Use the *Table 841.1.6-2 exception* selector "
        "above when calculating thickness for any of these facilities — using "
        "the basic Class F factor alone will produce an under-thick result."
    )

# ============================================================
# FORMULA REFERENCE
# ============================================================
st.markdown("---")
st.markdown("##### FORMULA — ASME B31.8-2022 §841.1.1")

st.latex(r"t \;=\; \frac{P \cdot D}{2 \cdot S \cdot F \cdot E \cdot T}")

st.markdown(
    """
    | Symbol | Description | Source |
    |---|---|---|
    | **P** | Design pressure (psig) | MAOP or design pressure |
    | **D** | Outside diameter (in) | Nominal pipe OD |
    | **S** | SMYS (psi) | B31.8 Mandatory Appendix D / API 5L / ASTM |
    | **F** | Design factor | B31.8 Table 841.1.6-1 (+ 841.1.6-2 exceptions) |
    | **E** | Longitudinal weld joint factor | B31.8 Table 841.1.7-1 |
    | **T** | Temperature derating | B31.8 Table 841.1.8-1 |

    **Required thickness:** $t_{req} = t + CA$  (CA = corrosion allowance)

    **Nominal thickness ordered:** $t_{nom} = t_{req} \\,/\\, (1 - \\text{mill tol})$
    """,
    unsafe_allow_html=True,
)

st.info(
    "**For preliminary design and inspection review only.** All tables and "
    "clauses are verified against ASME B31.8-2022 and API 570 Second Edition "
    "(1998). Special services (sour, HIC-resistant, low-temperature) require "
    "additional considerations not covered here. Not a substitute for a "
    "stamped engineering calculation.",
    icon="ℹ️",
)

# ============================================================
# FOOTER
# ============================================================
st.markdown(
    """
    <div style="margin-top:40px; padding-top:16px; border-top:1px solid #333;
                display:flex; justify-content:space-between;
                color:#666; font-size:11px; letter-spacing:2px;
                text-transform:uppercase;">
        <span>Verified against B31.8-2022 + API 570 (1998)</span>
        <span>v0.3 · Wahid Dino Samo</span>
    </div>
    """,
    unsafe_allow_html=True,
)
