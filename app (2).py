import base64
import io
import math
from html import escape
from string import Template

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------
# 0. DANE WBUDOWANE W APLIKACJĘ (brak konieczności wgrywania pliku)
# ---------------------------------------------------------
BUDGET_XLSX_B64 = (
    "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"
)


# ---------------------------------------------------------
# 1. USTAWIENIA STRONY
# ---------------------------------------------------------
st.set_page_config(
    page_title="Monitoring Budżetu",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

TAB_1 = "Podsumowanie budżetu"
TAB_2 = "Budżet w kategoriach"


def detect_default_theme():
    try:
        t = st.context.theme.type
        if t in ("light", "dark"):
            return t
    except Exception:
        pass
    return "light"


if "current_tab" not in st.session_state:
    st.session_state.current_tab = TAB_1
if "theme" not in st.session_state:
    st.session_state.theme = detect_default_theme()
if "splash_shown" not in st.session_state:
    st.session_state.splash_shown = False


def set_tab(name):
    st.session_state.current_tab = name


def set_theme(name):
    st.session_state.theme = name


# ---------------------------------------------------------
# 2. MOTYWY (JEDNO ŹRÓDŁO PRAWDY DLA CSS, WYKRESÓW I TABEL)
# ---------------------------------------------------------
PALETTES = {
    "light": dict(
        scheme="light", bg="#FFFFFF", text="#0F172A", muted="#64748B",
        card="rgba(255,255,255,0.80)", border="#E2E8F0", side="#FFFFFF",
        panel="rgba(241,243,246,0.72)",          # bardzo lekki szary panel z wizualizacjami
        accent="#2563EB",                        # niebieski akcent (przełączniki, nawigacja)
        inp="#FFFFFF", th="#F1F5F9", shadow="0 2px 10px rgba(15,23,42,0.06)",
        map_stroke="rgba(15,23,42,0.16)",
        plot_paper="rgba(255,255,255,0)", plot_bg="rgba(255,255,255,0)",
        grid="#E2E8F0", template="plotly_white",
        pos="#047857", neg="#B91C1C",
    ),
    "dark": dict(
        scheme="dark", bg="#0F172A", text="#F8FAFC", muted="#94A3B8",
        card="rgba(30,41,59,0.78)", border="rgba(255,255,255,0.14)", side="#0B1220",
        panel="rgba(148,163,184,0.10)",
        accent="#60A5FA",
        inp="#1E293B", th="#1E293B", shadow="0 2px 10px rgba(0,0,0,0.35)",
        map_stroke="rgba(248,250,252,0.14)",
        plot_paper="rgba(0,0,0,0)", plot_bg="rgba(0,0,0,0)",
        grid="rgba(255,255,255,0.10)", template="plotly_dark",
        pos="#34D399", neg="#F87171",
    ),
}
P = PALETTES[st.session_state.theme]

# Uproszczony kontur Polski (lon, lat)
POLAND = [
    (14.25, 53.92), (14.45, 53.93), (15.58, 54.18), (16.40, 54.43), (16.85, 54.58),
    (17.55, 54.76), (18.33, 54.83), (18.80, 54.60), (18.55, 54.50), (18.90, 54.38),
    (19.40, 54.37), (19.65, 54.45), (20.50, 54.40), (21.60, 54.33), (22.80, 54.36),
    (23.00, 54.25), (23.50, 53.95), (23.60, 53.50), (23.90, 52.75), (23.60, 52.10),
    (23.55, 51.55), (24.10, 50.85), (23.70, 50.40), (23.00, 49.95), (22.70, 49.60),
    (22.55, 49.08), (21.90, 49.35), (21.10, 49.40), (20.40, 49.40), (19.80, 49.20),
    (19.45, 49.60), (18.85, 49.50), (18.60, 49.75), (18.00, 50.05), (17.70, 50.30),
    (17.20, 50.40), (16.85, 50.20), (16.40, 50.55), (15.90, 50.75), (15.30, 50.85),
    (14.90, 50.87), (15.00, 51.00), (14.95, 51.30), (14.75, 51.55), (14.70, 52.10),
    (14.55, 52.60), (14.65, 52.80), (14.10, 52.85), (14.15, 53.30), (14.35, 53.70),
]


def _logo_markup(radius=22):
    """Minimalistyczne logo: czarna plakietka, białe słupki, ostatni słupek czerwony."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">'
        f'<rect width="100" height="100" rx="{radius}" fill="#0B0B0F"/>'
        '<rect x="22" y="50" width="14" height="26" rx="3" fill="#FFFFFF"/>'
        '<rect x="43" y="38" width="14" height="38" rx="3" fill="#FFFFFF"/>'
        '<rect x="64" y="24" width="14" height="52" rx="3" fill="#DC2626"/>'
        '<rect x="18" y="82" width="64" height="4" rx="2" fill="#FFFFFF"/>'
        f'<rect x="1" y="1" width="98" height="98" rx="{radius - 1}" fill="none" '
        'stroke="rgba(255,255,255,0.28)" stroke-width="2"/>'
        '</svg>'
    )


def logo_img(size=50, radius=22):
    """Logo jako <img> z data-URI - działa niezawodnie (baner, ekran startowy)."""
    uri = "data:image/svg+xml;base64," + base64.b64encode(_logo_markup(radius).encode()).decode()
    return f'<img src="{uri}" width="{size}" height="{size}" alt="logo" style="display:block;">'


def poland_path():
    lon0, lon1, lat0, lat1 = 13.8, 24.4, 48.9, 55.0
    k, sc = math.cos(math.radians(52)), 100
    pts = [((lo - lon0) * k * sc, (lat1 - la) * sc) for lo, la in POLAND]
    w, h = (lon1 - lon0) * k * sc, (lat1 - lat0) * sc
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"
    return d, w, h


def poland_outline_uri(stroke):
    """Sam delikatny kontur Polski (bez wypełnienia), wbudowany SVG."""
    d, w, h = poland_path()
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}">'
        f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="1.6" stroke-linejoin="round"/></svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


# ---------------------------------------------------------
# 3. CSS
# ---------------------------------------------------------
BASE_CSS = Template("""
<style>
.stApp {
    color-scheme: $scheme;
    background-color: $bg !important;
    background-image: url("$map") !important;
    background-repeat: no-repeat !important;
    background-position: center center !important;
    background-size: auto 82vh !important;
    background-attachment: fixed !important;
    color: $text !important;
}
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stMainBlockContainer"] {
    background: transparent !important;
}
header[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stHeader"] * { color: $text !important; }
.block-container { padding-top: 2.0rem !important; padding-bottom: 1rem !important; max-width: 1500px; }

/* Panel boczny */
section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div { background: $side !important; }
section[data-testid="stSidebar"] { border-right: 1px solid $border !important; }

/* Teksty */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp label, .stApp li,
.stApp [data-testid="stCaptionContainer"] { color: $text !important; }

/* Baner */
.banner {
    display: flex; align-items: center; gap: 16px;
    background: $card; border: 1px solid $border; border-bottom: 4px solid #DC2626;
    border-radius: 14px; padding: 12px 22px; margin-bottom: 12px; box-shadow: $shadow;
}
.banner .logo {
    width: 50px; height: 50px; flex: none; line-height: 0;
    filter: drop-shadow(0 4px 10px rgba(220,38,38,0.30));
}
.banner .logo img { display: block; }
.banner .b-title { font-size: 1.4rem; font-weight: 800; letter-spacing: 0.2px; color: $text; line-height: 1.2; }
.banner .b-sub { font-size: 0.86rem; color: $muted; margin-top: 1px; }
.banner .b-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 7px; }
.banner .b-chip {
    display: inline-flex; align-items: center; gap: 6px; font-size: 0.74rem; font-weight: 600;
    color: $muted; background: $panel; border: 1px solid $border; border-radius: 999px; padding: 3px 10px;
}
.banner .b-dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
.banner .b-tag {
    margin-left: auto; font-size: 0.78rem; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; color: #DC2626; border: 1px solid #DC2626;
    border-radius: 999px; padding: 4px 12px; align-self: center;
}

/* Kafelki KPI - jednakowa wysokość */
.kpi {
    background: $card; border: 1px solid $border; border-radius: 12px;
    padding: 10px 14px; height: 100px; box-shadow: $shadow;
    display: flex; flex-direction: column; justify-content: center; gap: 3px;
    overflow: hidden;
}
.kpi .k-label { font-size: 0.70rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; color: $muted; }
.kpi .k-value { font-size: 1.38rem; font-weight: 800; color: $text; line-height: 1.15; white-space: nowrap; }
.kpi .k-sub { font-size: 0.76rem; color: $muted; }

/* Panele z wizualizacjami - bardzo lekki, półprzezroczysty szary */
[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
    background: $panel !important; border: 1px solid $border !important;
    border-radius: 12px !important; box-shadow: $shadow !important;
}
.sec-title { font-size: 1.05rem; font-weight: 700; color: $text; margin: 2px 0 4px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sec-plain { font-size: 1.05rem; font-weight: 700; color: $text; margin: 10px 0 6px 0; }

/* Każda wizualizacja: lekka ramka + delikatne, transparentne wypełnienie (jak kafelki KPI) */
[data-testid="stPlotlyChart"] {
    background: $card !important; border: 1px solid $border !important;
    border-radius: 12px !important; box-shadow: $shadow !important;
    padding: 8px 6px 4px 6px !important; box-sizing: border-box;
}

/* Legenda kategorii - kompaktowe chipy w poziomym układzie, stała wysokość (wyrównanie paneli) */
.legend-wrap {
    display: flex; flex-wrap: wrap; align-items: center; align-content: center; gap: 6px 8px;
    background: $card; border: 1px solid $border; border-radius: 12px; box-shadow: $shadow;
    padding: 8px 12px; margin-top: 0; height: 76px; box-sizing: border-box; overflow-y: auto;
}
.legend-wrap .lg-grouplabel { font-size: 0.72rem; font-weight: 800; letter-spacing: 0.3px; margin-right: 2px; }
.legend-wrap .lg-chip {
    display: inline-flex; align-items: center; gap: 5px; font-size: 0.74rem; font-weight: 600;
    color: $text; background: $panel; border: 1px solid $border; border-radius: 999px; padding: 3px 9px 3px 6px;
}
.legend-wrap .lg-dot { width: 10px; height: 10px; border-radius: 3px; flex: none; }
.legend-wrap .lg-sep { width: 1px; align-self: stretch; background: $border; margin: 0 2px; }

/* Pola formularzy (w tym panel filtrowania w sidebarze) - zawsze zgodne z aktualnym motywem */
.stApp [data-baseweb="select"] > div, .stApp [data-baseweb="input"],
.stApp [data-baseweb="input"] input, .stApp [data-baseweb="base-input"],
.stApp [data-testid="stFileUploaderDropzone"],
.stApp [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
.stApp [data-testid="stSelectbox"] [data-baseweb="select"] > div,
.stApp [data-testid="stTextInput"] input,
.stApp [data-testid="stNumberInput"] input {
    background: $inp !important; border-color: $border !important;
}
.stApp [data-baseweb="select"] *, .stApp [data-testid="stFileUploaderDropzone"] *,
.stApp [data-testid="stMultiSelect"] *, .stApp [data-testid="stSelectbox"] * {
    color: $text !important; fill: $muted !important;
}
.stApp [data-baseweb="select"] span[data-baseweb="tag"] {
    background: rgba(37,99,235,0.18) !important; border: 1px solid $accent !important;
}
.stApp [data-baseweb="select"] span[data-baseweb="tag"] * { color: $text !important; fill: $text !important; }
.stApp [data-testid="stMultiSelect"] svg, .stApp [data-testid="stSelectbox"] svg { fill: $muted !important; }
/* Listy rozwijane (portal poza .stApp) - także podążają za motywem */
[data-baseweb="popover"] ul, [data-baseweb="popover"] li, [data-baseweb="menu"],
[data-baseweb="popover"] [role="listbox"], [data-baseweb="popover"] [role="option"] {
    background: $inp !important; color: $text !important;
}
[data-baseweb="popover"] [aria-selected="true"] { background: rgba(37,99,235,0.16) !important; }
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] [role="option"]:hover { background: rgba(37,99,235,0.10) !important; }

/* Zwykłe przyciski */
.stApp button[data-testid^="stBaseButton"] { background: $inp !important; border: 1px solid $border !important; }
.stApp button[data-testid^="stBaseButton"] p { color: $text !important; }

/* Ikony zwijania / rozwijania panelu bocznego - zawsze kontrastowe względem motywu */
.stApp [data-testid="stSidebarCollapseButton"] [data-testid^="stBaseButton"],
.stApp [data-testid="stSidebarCollapsedControl"] [data-testid^="stBaseButton"],
.stApp [data-testid="stExpandSidebarButton"],
.stApp [data-testid="stExpandSidebarButton"] [data-testid^="stBaseButton"] {
    background: transparent !important; border: none !important; box-shadow: none !important;
}
.stApp [data-testid="stSidebarCollapseButton"] *,
.stApp [data-testid="stSidebarCollapsedControl"] *,
.stApp [data-testid="stExpandSidebarButton"] *,
.stApp [data-testid="stSidebarHeader"] [data-testid="stIconMaterial"],
header[data-testid="stHeader"] [data-testid="stIconMaterial"] {
    color: $text !important; fill: $text !important;
}
.stApp [data-testid="stSidebarCollapseButton"] [data-testid^="stBaseButton"]:hover,
.stApp [data-testid="stExpandSidebarButton"]:hover { background: rgba(37,99,235,0.10) !important; }

/* Box przełącznika motywu w panelu bocznym */
section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid $border !important; border-radius: 12px !important;
    background: $card !important; padding: 4px 2px !important;
}
.theme-label { font-size: 0.74rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: $muted; margin-bottom: 4px; }

/* Tabele HTML */
.tbl-wrap { max-height: 520px; overflow: auto; border: 1px solid $border; border-radius: 12px; background: $panel; box-shadow: $shadow; }
table.tbl { border-collapse: collapse; width: 100%; font-size: 0.88rem; }
table.tbl th {
    position: sticky; top: 0; z-index: 1; background: $th; color: $text; text-align: left;
    padding: 10px 12px; border-bottom: 2px solid $border; white-space: nowrap;
}
table.tbl td { padding: 7px 12px; border-bottom: 1px solid $border; font-weight: 600; }
</style>
""")

st.markdown(BASE_CSS.substitute(**P, map=poland_outline_uri(P["map_stroke"])), unsafe_allow_html=True)

# ---------------------------------------------------------
# 3b. EKRAN STARTOWY (to samo tło co aplikacja; rozsuwa się jak drzwi i odsłania stronę)
# ---------------------------------------------------------
if not st.session_state.splash_shown:
    st.session_state.splash_shown = True

    _d, _w, _h = poland_path()

    SPLASH = Template("""
<style>
@keyframes splashGone { 0%, 99% { visibility: visible; } 100% { visibility: hidden; } }
@keyframes doorL { 0%, 68% { transform: translateX(0); } 100% { transform: translateX(-101%); } }
@keyframes doorR { 0%, 68% { transform: translateX(0); } 100% { transform: translateX(101%); } }
@keyframes contentOut { 0%, 58% { opacity: 1; transform: scale(1); } 72%, 100% { opacity: 0; transform: scale(1.05); } }
@keyframes drawOutline { from { stroke-dashoffset: 1; } to { stroke-dashoffset: 0; } }
@keyframes fillIn { from { fill-opacity: 0; } to { fill-opacity: 0.08; } }
@keyframes logoIn {
    0% { transform: scale(0.4) rotate(-20deg); opacity: 0; }
    60% { transform: scale(1.08) rotate(4deg); opacity: 1; }
    100% { transform: scale(1) rotate(0deg); opacity: 1; }
}
@keyframes titleUp { 0% { transform: translateY(14px); opacity: 0; } 100% { transform: translateY(0); opacity: 1; } }
@keyframes barFill { from { width: 0; } to { width: 100%; } }

#splash-overlay {
    position: fixed; inset: 0; z-index: 999999; pointer-events: none;
    animation: splashGone 3.6s linear forwards;
}
#splash-overlay .door { position: absolute; top: 0; bottom: 0; width: 50%; overflow: hidden; background: $bg; }
#splash-overlay .door-l { left: 0; animation: doorL 3.6s cubic-bezier(.77,0,.18,1) forwards; }
#splash-overlay .door-r { right: 0; animation: doorR 3.6s cubic-bezier(.77,0,.18,1) forwards; }
#splash-overlay .door-bg {
    position: absolute; top: 0; width: 100vw; height: 100vh;
    background-color: $bg; background-image: url("$map");
    background-repeat: no-repeat; background-position: center center; background-size: auto 82vh;
}
#splash-overlay .door-l .door-bg { left: 0; }
#splash-overlay .door-r .door-bg { left: -50vw; }
#splash-overlay .splash-content {
    position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
    animation: contentOut 3.6s ease forwards;
}
#splash-overlay .splash-map { position: absolute; left: 50%; top: 50%; height: 82vh; transform: translate(-50%, -50%); overflow: visible; }
#splash-overlay .splash-map path {
    fill: #DC2626; fill-opacity: 0; stroke: #DC2626; stroke-width: 2.4; stroke-linejoin: round;
    stroke-dasharray: 1; stroke-dashoffset: 1;
    animation: drawOutline 2s ease-out 0.2s forwards, fillIn 1s ease 1.5s forwards;
}
#splash-overlay .splash-inner { position: relative; text-align: center; }
#splash-overlay .splash-logo { width: 92px; height: 92px; margin: 0 auto 20px auto; animation: logoIn 0.8s cubic-bezier(.34,1.56,.64,1) 0.3s both; }
#splash-overlay .splash-title { font-size: 2.1rem; font-weight: 800; color: $text; letter-spacing: 0.3px; animation: titleUp 0.6s ease 0.7s both; }
#splash-overlay .splash-sub { font-size: 0.95rem; color: $muted; margin-top: 6px; animation: titleUp 0.6s ease 0.9s both; }
#splash-overlay .splash-bar-track { width: 220px; height: 4px; border-radius: 999px; background: $border; margin: 24px auto 0 auto; overflow: hidden; animation: titleUp 0.6s ease 1.0s both; }
#splash-overlay .splash-bar-fill { height: 100%; border-radius: 999px; background: #DC2626; animation: barFill 1.9s ease 1.0s forwards; width: 0; }
</style>
<div id="splash-overlay">
  <div class="door door-l"><div class="door-bg"></div></div>
  <div class="door door-r"><div class="door-bg"></div></div>
  <div class="splash-content">
    <svg class="splash-map" viewBox="0 0 $vbw $vbh" xmlns="http://www.w3.org/2000/svg"><path d="$outline_d" pathLength="1"/></svg>
    <div class="splash-inner">
      <div class="splash-logo">$logo</div>
      <div class="splash-title">Monitoring Budżetu</div>
      <div class="splash-sub">Wczytywanie danych budżetowych…</div>
      <div class="splash-bar-track"><div class="splash-bar-fill"></div></div>
    </div>
  </div>
</div>
""")
    st.markdown(
        SPLASH.substitute(
            **P, map=poland_outline_uri(P["map_stroke"]), logo=logo_img(92, 22),
            outline_d=_d, vbw=f"{_w:.0f}", vbh=f"{_h:.0f}",
        ),
        unsafe_allow_html=True,
    )

# Przyciski małe; aktywny = przezroczysty niebieski
NAV_KEYS = ["btn_podsumowanie", "btn_kategorie", "theme_light", "theme_dark"]
active_keys = [
    "btn_podsumowanie" if st.session_state.current_tab == TAB_1 else "btn_kategorie",
    "theme_light" if st.session_state.theme == "light" else "theme_dark",
]
inactive_keys = [k for k in NAV_KEYS if k not in active_keys]


def _sel(keys, suffix):
    return ",".join(f'.stApp .st-key-{k} {suffix}' for k in keys)


NAV_CSS = Template("""
<style>
$all_btn { min-height: 38px !important; border-radius: 8px !important; transition: all .15s ease-in-out !important; }
$all_p { font-size: 0.92rem !important; font-weight: 700 !important; }
$act_btn {
    background: rgba(37,99,235,0.16) !important;
    border: 1.5px solid $accent !important;
    box-shadow: none !important;
}
$act_p { color: $accent !important; }
$inact_btn { background: transparent !important; border: 1px solid $border !important; }
$inact_p { color: $muted !important; }
$inact_hover { border-color: $accent !important; background: rgba(37,99,235,0.08) !important; }
$act_icon { color: $accent !important; }
$inact_icon { color: $muted !important; }
</style>
""")
btn = 'button[data-testid^="stBaseButton"]'
ico = '[data-testid="stIconMaterial"]'
st.markdown(
    NAV_CSS.substitute(
        all_btn=_sel(NAV_KEYS, btn), all_p=_sel(NAV_KEYS, "button p"),
        act_btn=_sel(active_keys, btn), act_p=_sel(active_keys, "button p"),
        inact_btn=_sel(inactive_keys, btn), inact_p=_sel(inactive_keys, "button p"),
        inact_hover=_sel(inactive_keys, btn + ":hover"),
        act_icon=_sel(active_keys, ico), inact_icon=_sel(inactive_keys, ico),
        border=P["border"], muted=P["muted"], accent=P["accent"],
    ),
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 4. FUNKCJE POMOCNICZE
# ---------------------------------------------------------
GREEN, RED = (16, 185, 129), (239, 68, 68)
TYPE_RGB = {"Dochody": GREEN, "Wydatki": RED}
color_map_typ = {"Dochody": "#10B981", "Wydatki": "#EF4444"}
PCT_COLS = {"Procent_Wykonania", "% Wykonania"}
CHART_H = 300
SUN_H = 260                       # wysokość sunburstu
LEGEND_H = 76                     # wysokość legendy (zgodna z CSS .legend-wrap)
BAR_H = SUN_H + LEGEND_H + 16     # wykres słupkowy = sunburst + odstęp + legenda
CAT_H = 540                       # stała wysokość obu górnych paneli w widoku kategorii
MAX_ALPHA = 0.85      # żaden element wizualizacji nie jest w pełni kryjący
TRACE_OPACITY = 0.85


def rgba(c, a):
    return f"rgba({c[0]},{c[1]},{c[2]},{a:.2f})"


def pl(x, d=1):
    if pd.isna(x):
        return "–"
    return f"{x:,.{d}f}".replace(",", "\u00a0").replace(".", ",")


def get_measure_col(m):
    return "Wykonanie_mld_PLN" if m == "Wykonanie" else "Plan_mld_PLN"


def style_fig(fig, legend_top=False, h=None):
    fig.update_layout(
        template=P["template"], height=h or CHART_H,
        paper_bgcolor=P["plot_paper"], plot_bgcolor=P["plot_bg"],
        font=dict(color=P["text"]), margin=dict(l=10, r=10, t=30, b=10),
        separators=", ",   # przecinek dziesiętny, spacja jako separator tysięcy
    )
    fig.update_xaxes(gridcolor=P["grid"], zerolinecolor=P["grid"])
    fig.update_yaxes(gridcolor=P["grid"], zerolinecolor=P["grid"])
    if legend_top:
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                      xanchor="right", x=1, bgcolor="rgba(0,0,0,0)", title_text=""))
    return fig


def show_fig(fig):
    st.plotly_chart(fig, use_container_width=True, theme=None, config={"displayModeBar": False})


def shade_bars(fig, df, value_col, orientation="v"):
    """Im większa wartość, tym mocniejszy kolor - ale zawsze z przezroczystością."""
    maxes = df.groupby("Typ_Pozycji")[value_col].max().abs().to_dict()
    for tr in fig.data:
        rgb = TYPE_RGB.get(tr.name)
        if rgb is None:
            continue
        mx = maxes.get(tr.name) or 1
        vals = tr.x if orientation == "h" else tr.y
        tr.marker.color = [rgba(rgb, 0.30 + (MAX_ALPHA - 0.30) * min(abs(v) / mx, 1)) for v in vals]
    return fig


def add_type_legend(fig, types, hide_axes=False):
    """Legenda Dochody (zielony) / Wydatki (czerwony) o stałych kolorach.
    Ponieważ słupki mają odcienie zależne od wartości, legenda budowana jest z osobnych znaczników."""
    for tr in fig.data:
        if tr.type == "bar":
            tr.showlegend = False
    for t in types:
        rgb = TYPE_RGB.get(t, (100, 116, 139))
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers", name=str(t), showlegend=True, hoverinfo="skip",
            marker=dict(symbol="square", size=13, color=rgba(rgb, MAX_ALPHA)),
        ))
    if hide_axes:
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
    return fig


def bar_labels(fig, axis):
    """Etykiety danych: wartości liczbowe w mld PLN."""
    fig.update_traces(
        selector=dict(type="bar"),
        texttemplate=f"%{{{axis}:.1f}} mld", textposition="outside", cliponaxis=False,
        textfont=dict(color=P["text"], size=11),
    )
    return fig


def add_type_divider(fig, df, orientation="v"):
    """Linia rozdzielająca dochody od wydatków na wykresach słupkowych.
    orientation='h': wydatki na dole, dochody na górze; 'v': dochody z lewej, wydatki z prawej."""
    counts = df["Typ_Pozycji"].value_counts().to_dict()
    n_d, n_w = counts.get("Dochody", 0), counts.get("Wydatki", 0)
    if n_d == 0 or n_w == 0:
        return fig
    line = dict(line_dash="dash", line_color=P["muted"], line_width=2)
    if orientation == "h":
        y = n_w - 0.5
        fig.add_hline(y=y, **line)
        fig.add_annotation(xref="paper", x=1, yref="y", y=y, text="▲ Dochody", showarrow=False,
                           xanchor="right", yanchor="bottom", font=dict(color=P["pos"], size=11))
        fig.add_annotation(xref="paper", x=1, yref="y", y=y, text="▼ Wydatki", showarrow=False,
                           xanchor="right", yanchor="top", font=dict(color=P["neg"], size=11))
    else:
        x = n_d - 0.5
        fig.add_vline(x=x, **line)
        fig.add_annotation(xref="x", x=x, yref="paper", y=1, text="◄ Dochody", showarrow=False,
                           xanchor="right", yanchor="top", font=dict(color=P["pos"], size=11))
        fig.add_annotation(xref="x", x=x, yref="paper", y=1, text="Wydatki ►", showarrow=False,
                           xanchor="left", yanchor="top", font=dict(color=P["neg"], size=11))
    return fig


def kpi(label, value, sub="", tint=None, value_color=None, border=None):
    bg = f"background: linear-gradient({tint}, {tint}), {P['card']};" if tint else ""
    bd = f"border: 2px solid {border};" if border else ""
    vc = f"color:{value_color};" if value_color else ""
    return (
        f'<div class="kpi" style="{bg}{bd}">'
        f'<div class="k-label">{label}</div>'
        f'<div class="k-value" style="{vc}">{value}</div>'
        f'<div class="k-sub">{sub}</div></div>'
    )


def render_table(df, sort_cols, ascending):
    """Dochody obok dochodów (zielone), wydatki obok wydatków (czerwone);
    im większe Wykonanie, tym mocniejszy kolor."""
    if df.empty:
        return
    LIMIT = 1000
    d = df.sort_values(sort_cols, ascending=ascending).reset_index(drop=True)
    truncated = len(d) > LIMIT
    d = d.head(LIMIT)
    maxes = df.groupby("Typ_Pozycji")["Wykonanie_mld_PLN"].max().abs().to_dict()

    head = "".join(f"<th>{escape(str(c).replace('_', ' '))}</th>" for c in d.columns)
    rows = []
    for _, r in d.iterrows():
        rgb = TYPE_RGB.get(r["Typ_Pozycji"])
        mx = maxes.get(r["Typ_Pozycji"]) or 1
        val = r["Wykonanie_mld_PLN"]
        ratio = 0 if pd.isna(val) else min(abs(val) / mx, 1)
        rstyle = f"background-color:{rgba(rgb, 0.12 + 0.62 * ratio)};color:{P['text']};" if rgb else ""
        tds = []
        for c in d.columns:
            v = r[c]
            if c == "Rok":
                txt, al = escape(str(v)), "left"
            elif c in PCT_COLS:
                txt, al = ("–" if pd.isna(v) else pl(v) + "%"), "right"
            elif pd.api.types.is_number(v) and not isinstance(v, bool):
                txt, al = pl(v), "right"
            else:
                txt, al = escape(str(v)), "left"
            tds.append(f'<td style="text-align:{al};">{txt}</td>')
        rows.append(f'<tr style="{rstyle}">' + "".join(tds) + "</tr>")

    st.markdown(
        '<div class="tbl-wrap"><table class="tbl"><thead><tr>' + head + "</tr></thead><tbody>"
        + "".join(rows) + "</tbody></table></div>",
        unsafe_allow_html=True,
    )
    if truncated:
        st.caption(f"Wyświetlono pierwsze {LIMIT} wierszy. Pełne dane dostępne w eksporcie do Excela.")


# ---------------------------------------------------------
# 5. DANE
# ---------------------------------------------------------
@st.cache_data
def load_data():
    """Dane budżetowe są wbudowane w aplikację (BUDGET_XLSX_B64) i wczytywane
    automatycznie po uruchomieniu — nie trzeba dołączać żadnego pliku."""
    try:
        raw_bytes = base64.b64decode(BUDGET_XLSX_B64)
        df = pd.read_excel(io.BytesIO(raw_bytes), sheet_name="Dane_Szczegolowe")
    except Exception as e:
        st.error(f"Błąd podczas wczytywania wbudowanych danych: {e}")
        return pd.DataFrame()
    df["Plan_mld_PLN"] = pd.to_numeric(df["Plan_mld_PLN"], errors="coerce").fillna(0)
    df["Wykonanie_mld_PLN"] = pd.to_numeric(df["Wykonanie_mld_PLN"], errors="coerce").fillna(0)
    df["Procent_Wykonania"] = df["Wykonanie_mld_PLN"] / df["Plan_mld_PLN"].replace(0, float("nan")) * 100
    df["Odchylenie_mld_PLN"] = df["Wykonanie_mld_PLN"] - df["Plan_mld_PLN"]
    return df


# ---------------------------------------------------------
# 6. PANEL BOCZNY
# ---------------------------------------------------------
with st.sidebar.container(border=True):
    st.markdown('<div class="theme-label">Motyw</div>', unsafe_allow_html=True)
    tc1, tc2 = st.columns(2, gap="small")
    with tc1:
        st.button("Jasny", key="theme_light", icon=":material/light_mode:",
                  use_container_width=True, on_click=set_theme, args=("light",))
    with tc2:
        st.button("Ciemny", key="theme_dark", icon=":material/dark_mode:",
                  use_container_width=True, on_click=set_theme, args=("dark",))

st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.header("Panel filtrowania")

df_raw = load_data()

# ---------------------------------------------------------
# 7. BANER
# ---------------------------------------------------------
st.markdown(
    f'<div class="banner"><div class="logo">{logo_img(50)}</div>'
    '<div style="min-width:0;"><div class="b-title">Monitoring Budżetu</div>'
    '<div class="b-sub">Plan vs. wykonanie dochodów i wydatków budżetu państwa, w mld PLN</div>'
    '<div class="b-chips">'
    f'<span class="b-chip"><span class="b-dot" style="background:{P["pos"]};"></span>Dochody</span>'
    f'<span class="b-chip"><span class="b-dot" style="background:{P["neg"]};"></span>Wydatki</span>'
    '<span class="b-chip">Wynik = Dochody − Wydatki</span>'
    '<span class="b-chip">% wykonania = Wykonanie / Plan</span>'
    '</div></div>'
    '<div class="b-tag">Raport analityczny</div></div>',
    unsafe_allow_html=True,
)

if df_raw.empty:
    st.error("Nie udało się wczytać wbudowanych danych budżetowych.")
    st.stop()

lata_dostepne = sorted(df_raw["Rok"].unique().tolist())
wybrane_lata = st.sidebar.multiselect("Wybierz lata do analizy:", options=lata_dostepne, default=lata_dostepne)
if not wybrane_lata:
    st.warning("Wybierz co najmniej jeden rok w panelu bocznym.")
    st.stop()

# ---------------------------------------------------------
# 8. NAWIGACJA (małe, osobne przyciski)
# ---------------------------------------------------------
n1, n2, _sp = st.columns([1, 1, 4], gap="small")
with n1:
    st.button(TAB_1, key="btn_podsumowanie", use_container_width=True, on_click=set_tab, args=(TAB_1,))
with n2:
    st.button(TAB_2, key="btn_kategorie", use_container_width=True, on_click=set_tab, args=(TAB_2,))

widok = st.session_state.current_tab

if widok == TAB_2:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filtry dla kategorii")
    typy = ["Wszystkie"] + sorted(df_raw["Typ_Pozycji"].unique().tolist())
    wybrany_typ = st.sidebar.selectbox("Typy pozycji budżetowych:", options=typy, index=0)
else:
    wybrany_typ = "Wszystkie"

df_filtered = df_raw[df_raw["Rok"].isin(wybrane_lata)]
if wybrany_typ != "Wszystkie":
    df_filtered = df_filtered[df_filtered["Typ_Pozycji"] == wybrany_typ]

if len(wybrane_lata) == 1:
    lata_str = f"Rok {wybrane_lata[0]}"
    lata_krotko = f"Rok {wybrane_lata[0]}"
else:
    lata_str = f"Lata: {', '.join(map(str, wybrane_lata))}"
    lata_krotko = f"Lata {min(wybrane_lata)}–{max(wybrane_lata)} (suma)"

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# =========================================================
# WIDOK 1: PODSUMOWANIE BUDŻETU
# =========================================================
if widok == TAB_1:
    st.markdown(f'<div class="sec-plain" style="margin-top:4px;">Ogólny bilans finansowy – {escape(lata_str)}</div>',
                unsafe_allow_html=True)

    df_lata = df_raw[df_raw["Rok"].isin(wybrane_lata)]
    doch = df_lata[df_lata["Typ_Pozycji"] == "Dochody"]
    wyd = df_lata[df_lata["Typ_Pozycji"] == "Wydatki"]

    d_plan, d_wyk = doch["Plan_mld_PLN"].sum(), doch["Wykonanie_mld_PLN"].sum()
    w_plan, w_wyk = wyd["Plan_mld_PLN"].sum(), wyd["Wykonanie_mld_PLN"].sum()
    wynik_plan, wynik_wyk = d_plan - w_plan, d_wyk - w_wyk
    pct_d = (d_wyk / d_plan * 100) if d_plan > 0 else 0
    pct_w = (w_wyk / w_plan * 100) if w_plan > 0 else 0

    dodatni = wynik_wyk >= 0
    wynik_rgb = GREEN if dodatni else RED
    wynik_txt = P["pos"] if dodatni else P["neg"]

    k1, k2, k3, k4, k5 = st.columns(5, gap="small")
    k1.markdown(kpi("Dochody (wykonanie)", f"{pl(d_wyk)} mld PLN", f"Plan: {pl(d_plan)} mld PLN",
                    tint=rgba(GREEN, 0.10)), unsafe_allow_html=True)
    k2.markdown(kpi("Wydatki (wykonanie)", f"{pl(w_wyk)} mld PLN", f"Plan: {pl(w_plan)} mld PLN",
                    tint=rgba(RED, 0.10)), unsafe_allow_html=True)
    k3.markdown(kpi(f"Wynik budżetowy · {escape(lata_krotko)}", f"{pl(wynik_wyk)} mld PLN",
                    f"Plan: {pl(wynik_plan)} mld PLN · {'nadwyżka' if dodatni else 'deficyt'}",
                    tint=rgba(wynik_rgb, 0.20), value_color=wynik_txt, border=rgba(wynik_rgb, 0.85)),
                unsafe_allow_html=True)
    k4.markdown(kpi("% wykonania dochodów", f"{pct_d:.1f}%".replace(".", ","), "Wykonanie / plan"),
                unsafe_allow_html=True)
    k5.markdown(kpi("% wykonania wydatków", f"{pct_w:.1f}%".replace(".", ","), "Wykonanie / plan"),
                unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    df_trend = df_lata.groupby(["Rok", "Typ_Pozycji"])[["Plan_mld_PLN", "Wykonanie_mld_PLN"]].sum().reset_index()
    col_t1, col_t2 = st.columns(2, gap="medium")

    with col_t1:
        with st.container(border=True):
            st.markdown('<div class="sec-title">Trend dochodów i wydatków</div>', unsafe_allow_html=True)
            miara_t1 = st.radio("Wskaźnik:", ["Wykonanie", "Plan"], horizontal=True, key="radio_trend1")
            col_m1 = get_measure_col(miara_t1)
            fig = px.line(df_trend, x="Rok", y=col_m1, color="Typ_Pozycji", markers=True,
                          color_discrete_map=color_map_typ,
                          labels={col_m1: f"{miara_t1} (mld PLN)", "Rok": "Rok", "Typ_Pozycji": "Typ"})
            fig.update_traces(line_width=3, marker_size=9, opacity=TRACE_OPACITY,
                              mode="lines+markers+text", texttemplate="%{y:.1f} mld",
                              textposition="top center", textfont=dict(color=P["text"], size=11))
            fig.update_xaxes(type="category")
            style_fig(fig, legend_top=True)
            show_fig(fig)

    with col_t2:
        with st.container(border=True):
            st.markdown('<div class="sec-title">Trend wyniku budżetowego</div>', unsafe_allow_html=True)
            miara_t2 = st.radio("Wskaźnik:", ["Wykonanie", "Plan"], horizontal=True, key="radio_trend2")
            col_m2 = get_measure_col(miara_t2)
            piv = df_trend.pivot(index="Rok", columns="Typ_Pozycji", values=col_m2).fillna(0)
            piv["Wynik_mld_PLN"] = piv.get("Dochody", 0) - piv.get("Wydatki", 0)
            piv = piv.reset_index()
            fig = px.line(piv, x="Rok", y="Wynik_mld_PLN", markers=True,
                          labels={"Wynik_mld_PLN": f"Wynik – {miara_t2.lower()} (mld PLN)", "Rok": "Rok"})
            fig.update_traces(line_color="#EAB308", line_width=4, marker_size=9, opacity=TRACE_OPACITY,
                              mode="lines+markers+text", texttemplate="%{y:.1f} mld",
                              textposition="top center", textfont=dict(color=P["text"], size=11))
            fig.add_hline(y=0, line_dash="dash", line_color="#64748B", annotation_text="Zrównoważenie")
            fig.update_xaxes(type="category")
            style_fig(fig)
            show_fig(fig)

    st.markdown('<div class="sec-plain">Zbiorcza tabela bilansu</div>', unsafe_allow_html=True)
    df_sum = (df_lata.groupby(["Rok", "Typ_Pozycji"])[["Plan_mld_PLN", "Wykonanie_mld_PLN", "Odchylenie_mld_PLN"]]
              .sum().reset_index())
    df_sum["% Wykonania"] = df_sum["Wykonanie_mld_PLN"] / df_sum["Plan_mld_PLN"].replace(0, float("nan")) * 100
    render_table(df_sum, ["Typ_Pozycji", "Rok"], [True, True])

# =========================================================
# WIDOK 2: BUDŻET W KATEGORIACH
# =========================================================
else:
    st.markdown(f'<div class="sec-plain" style="margin-top:4px;">Szczegółowa analiza kategorii – {escape(lata_str)}</div>',
                unsafe_allow_html=True)

    if df_filtered.empty:
        st.warning("Brak danych spełniających wybrane kryteria filtrowania.")
    else:
        col_c1, col_c2 = st.columns(2, gap="medium")

        # --- Struktura kategorii głównych ---
        with col_c1:
            with st.container(border=True, height=CAT_H):
                st.markdown('<div class="sec-title">Struktura kategorii głównych</div>', unsafe_allow_html=True)
                miara_k1 = st.radio("Wskaźnik:", ["Wykonanie", "Plan"], horizontal=True, key="radio_kat1")
                col_mk1 = get_measure_col(miara_k1)

                df_kat = df_filtered.groupby(["Kategoria_Główna", "Typ_Pozycji"])[col_mk1].sum().reset_index()
                df_kat["Etykieta"] = df_kat["Kategoria_Główna"].astype(str) + " (" + df_kat["Typ_Pozycji"] + ")"
                df_kat = df_kat.sort_values(["Typ_Pozycji", col_mk1], ascending=[True, False])
                kolejnosc_y = df_kat["Etykieta"].tolist()[::-1]

                fig = px.bar(df_kat, y="Etykieta", x=col_mk1, color="Typ_Pozycji", orientation="h",
                             color_discrete_map=color_map_typ,
                             labels={col_mk1: f"{miara_k1} (mld PLN)", "Etykieta": "", "Typ_Pozycji": "Typ"})
                fig.update_yaxes(categoryorder="array", categoryarray=kolejnosc_y)
                shade_bars(fig, df_kat, col_mk1, orientation="h")
                bar_labels(fig, "x")
                add_type_divider(fig, df_kat, orientation="h")
                add_type_legend(fig, sorted(df_kat["Typ_Pozycji"].unique()))
                style_fig(fig, legend_top=True, h=BAR_H)
                show_fig(fig)

        # --- Udział kategorii z podziałem (sunburst: typ -> kategoria) ---
        with col_c2:
            with st.container(border=True, height=CAT_H):
                st.markdown('<div class="sec-title">Udział kategorii z podziałem</div>', unsafe_allow_html=True)
                miara_k2 = st.radio("Wskaźnik:", ["Wykonanie", "Plan"], horizontal=True, key="radio_kat2")
                col_mk2 = get_measure_col(miara_k2)

                df_u = df_filtered.groupby(["Typ_Pozycji", "Kategoria_Główna"])[col_mk2].sum().reset_index()
                df_u = df_u[df_u[col_mk2] > 0]

                if df_u.empty:
                    st.info("Brak dodatnich wartości do zaprezentowania.")
                else:
                    ids, labels, parents, values, colors = [], [], [], [], []
                    for typ, grp in df_u.groupby("Typ_Pozycji"):
                        rgb = TYPE_RGB.get(typ, (100, 116, 139))
                        ids.append(str(typ)); labels.append(str(typ)); parents.append("")
                        values.append(float(grp[col_mk2].sum())); colors.append(rgba(rgb, MAX_ALPHA))
                        mx = float(grp[col_mk2].max()) or 1.0
                        for _, r in grp.sort_values(col_mk2, ascending=False).iterrows():
                            ids.append(f"{typ}|{r['Kategoria_Główna']}")
                            labels.append(str(r["Kategoria_Główna"]))
                            parents.append(str(typ))
                            values.append(float(r[col_mk2]))
                            colors.append(rgba(rgb, 0.40 + 0.40 * float(r[col_mk2]) / mx))

                    fig = go.Figure(go.Sunburst(
                        ids=ids, labels=labels, parents=parents, values=values,
                        branchvalues="total", marker=dict(colors=colors, line=dict(color=P["bg"], width=2)),
                        texttemplate="%{label}<br>%{value:.1f} mld",
                        insidetextfont=dict(color="#0F172A"),
                        hovertemplate="%{label}<br>%{value:,.1f} mld PLN<br>%{percentParent:.1%} nadrzędnej<extra></extra>",
                    ))
                    style_fig(fig, h=SUN_H)
                    fig.update_layout(showlegend=False)
                    show_fig(fig)

                    # Legenda pokazuje konkretne pozycje kategorii (nie tylko Dochody/Wydatki),
                    # a kolor każdej pozycji dokładnie odpowiada jej wycinkowi na wykresie.
                    # Kompaktowy poziomy pasek chipów o stałej wysokości (LEGEND_H).
                    chip_groups = []
                    for typ, grp in df_u.groupby("Typ_Pozycji"):
                        rgb = TYPE_RGB.get(typ, (100, 116, 139))
                        mx = float(grp[col_mk2].max()) or 1.0
                        typ_color = P["pos"] if typ == "Dochody" else (P["neg"] if typ == "Wydatki" else P["muted"])
                        chips = "".join(
                            f'<span class="lg-chip"><span class="lg-dot" style="background:'
                            f'{rgba(rgb, 0.40 + 0.40 * float(r[col_mk2]) / mx)};"></span>'
                            f'{escape(str(r["Kategoria_Główna"]))}</span>'
                            for _, r in grp.sort_values(col_mk2, ascending=False).iterrows()
                        )
                        chip_groups.append(
                            f'<span class="lg-grouplabel" style="color:{typ_color};">{escape(str(typ))}:</span>'
                            + chips
                        )

                    st.markdown(
                        '<div class="legend-wrap">'
                        + '<span class="lg-sep"></span>'.join(chip_groups)
                        + '</div>',
                        unsafe_allow_html=True,
                    )

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # --- Podział szczegółowy ---
        with st.container(border=True):
            st.markdown('<div class="sec-title">Podział szczegółowy pozycji</div>', unsafe_allow_html=True)
            miara_k3 = st.radio("Wskaźnik:", ["Wykonanie", "Plan"], horizontal=True, key="radio_kat3")
            col_mk3 = get_measure_col(miara_k3)

            df_sz = (df_filtered.groupby(["Nazwa_Kategorii_Szczegółowa", "Typ_Pozycji"])
                     [["Plan_mld_PLN", "Wykonanie_mld_PLN"]].sum().reset_index()
                     .sort_values(["Typ_Pozycji", col_mk3], ascending=[True, False]))
            fig = px.bar(df_sz, x="Nazwa_Kategorii_Szczegółowa", y=col_mk3, color="Typ_Pozycji",
                         color_discrete_map=color_map_typ,
                         labels={col_mk3: f"{miara_k3} (mld PLN)", "Nazwa_Kategorii_Szczegółowa": "", "Typ_Pozycji": "Typ"})
            fig.update_xaxes(categoryorder="array", categoryarray=df_sz["Nazwa_Kategorii_Szczegółowa"].tolist(),
                             tickangle=-45)
            shade_bars(fig, df_sz, col_mk3, orientation="v")
            bar_labels(fig, "y")
            add_type_divider(fig, df_sz, orientation="v")
            add_type_legend(fig, sorted(df_sz["Typ_Pozycji"].unique()))
            style_fig(fig, legend_top=True)
            fig.update_layout(height=320)
            show_fig(fig)

        # --- Tabela ---
        st.markdown('<div class="sec-plain">Zestawienie danych</div>', unsafe_allow_html=True)
        cols_to_show = ["Rok", "Typ_Pozycji", "Kategoria_Główna", "Nazwa_Kategorii_Szczegółowa", "Część_Budżetowa",
                        "Plan_mld_PLN", "Wykonanie_mld_PLN", "Procent_Wykonania", "Odchylenie_mld_PLN"]
        cols_present = [c for c in cols_to_show if c in df_filtered.columns]
        render_table(df_filtered[cols_present].copy(), ["Typ_Pozycji", "Wykonanie_mld_PLN"], [True, False])

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_filtered.to_excel(writer, index=False, sheet_name="Dane_Przefiltrowane")
        st.download_button(
            label="Pobierz przefiltrowane dane (.xlsx)",
            data=output.getvalue(),
            file_name="Raport_Finansowy_Dane.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
