import base64
import io
import math
import zlib
from html import escape
from string import Template

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------
# 0. DANE WBUDOWANE W APLIKACJĘ (brak konieczności wgrywania pliku)
# ---------------------------------------------------------
# Publiczne dane budżetowe są zdefiniowane w sekcji REALNE DANE niżej.
# Zastępują historyczny arkusz z wartościami demonstracyjnymi.

# Osadzona panorama z przykładowego projektu – bez zależności od internetu.

# ---------------------------------------------------------
# 1. USTAWIENIA STRONY
# ---------------------------------------------------------
st.set_page_config(
    page_title="Polski Obserwator Budżetowy",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

TAB_1 = "Stan Budżetu"
TAB_2 = "Budżet w kategoriach"


# W nowej sesji zawsze startujemy z jasnym motywem. Użytkownik może
# później przełączyć się na ciemny; przełączanie nie resetuje filtrów.
# Osobny znacznik pozwala przejść na jasny również po aktualizacji kodu
# w już otwartej sesji Streamlit (bez wymuszania go na każdym rerunie).
if not st.session_state.get("_domyslny_motyw_realne_dane_v1", False):
    st.session_state.theme = "light"
    st.session_state._domyslny_motyw_realne_dane_v1 = True

if "current_tab" not in st.session_state:
    st.session_state.current_tab = TAB_1
if "splash_shown" not in st.session_state:
    st.session_state.splash_shown = False


def set_tab(name):
    st.session_state.current_tab = name


def set_theme(name):
    st.session_state.theme = name


# ---------------------------------------------------------
# 2. MOTYWY
# ---------------------------------------------------------
PALETTES = {
    "light": dict(
        scheme="light",
        bg="#F7FAFF",
        text="#0F172A",
        muted="#475569",
        card="rgba(255,255,255,0.12)",
        border="#DCE5F1",
        side="#EFF4FB",
        side_shadow="6px 0 28px rgba(15,23,42,0.12)",
        on_accent="#FFFFFF",
        panel="rgba(255,255,255,0.16)",
        accent="#2563EB",
        inp="rgba(255,255,255,0.78)",
        th="#F1F5F9",
        shadow="0 8px 24px rgba(15,23,42,0.08)",
        map_stroke="rgba(15,23,42,0.16)",
        plot_paper="rgba(255,255,255,0)",
        plot_bg="rgba(255,255,255,0)",
        grid="#DCE5F1",
        template="plotly_white",
        pos="#16A34A",
        neg="#DC2626",
        sidebar_title="#FFFFFF",
        sidebar_text="#F8FAFC",
        sidebar_card="rgba(255,255,255,0.16)",
        sidebar_card_active="rgba(255,255,255,0.26)",
        balance_tint="rgba(254,226,226,0.40)",
        sidebar_border="rgba(255,255,255,0.22)",
    ),
    "dark": dict(
        scheme="dark",
        bg="#0F172A",
        text="#F8FAFC",
        muted="#CBD5E1",
        card="rgba(18,32,53,0.20)",
        border="rgba(255,255,255,0.12)",
        side="#07101F",
        side_shadow="6px 0 28px rgba(0,0,0,0.55)",
        on_accent="#0B1220",
        panel="rgba(15,23,42,0.23)",
        accent="#60A5FA",
        inp="#162235",
        th="#1E293B",
        shadow="0 8px 24px rgba(0,0,0,0.35)",
        map_stroke="rgba(248,250,252,0.16)",
        plot_paper="rgba(0,0,0,0)",
        plot_bg="rgba(0,0,0,0)",
        grid="rgba(255,255,255,0.10)",
        template="plotly_dark",
        pos="#4ADE80",
        neg="#F87171",
        sidebar_title="#FFFFFF",
        sidebar_text="#F8FAFC",
        sidebar_card="rgba(15,23,42,0.28)",
        sidebar_card_active="rgba(255,255,255,0.16)",
        balance_tint="rgba(100,35,46,0.44)",
        sidebar_border="rgba(255,255,255,0.16)",
    ),
}
P = PALETTES[st.session_state.theme]

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


# Logo z dostarczonego załącznika, osadzone bezpośrednio w kodzie.
def logo_img(size=60, fg=None):
    """Własnoręcznie rysowany znak SVG: przezroczyste tło, biały kontur wykresu z koralowym akcentem."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<g fill="none" stroke="#FFFFFF" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M14 61 V17 Q14 12 19 12 H83 V76 Q83 82 77 82 H14" />'
        '<path d="M21 67 L41 45 L54 58 L76 30" />'
        '</g>'
        '<circle cx="77" cy="29" r="6" fill="#FCA5A5" stroke="#FFFFFF" stroke-width="2.8"/>'
        '</svg>'
    )
    uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return (f'<img src="{uri}" width="{size}" height="{size}" '
            f'alt="Polski Obserwator Budżetowy" '
            'style="display:block;width:100%;height:100%;object-fit:contain;filter:drop-shadow(0 1px 4px rgba(15,23,42,.22));">')


def poland_path():
    lon0, lon1, lat0, lat1 = 13.8, 24.4, 48.9, 55.0
    k, sc = math.cos(math.radians(52)), 100
    pts = [((lo - lon0) * k * sc, (lat1 - la) * sc) for lo, la in POLAND]
    w, h = (lon1 - lon0) * k * sc, (lat1 - lat0) * sc
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"
    return d, w, h


def poland_outline_uri(stroke):
    d, w, h = poland_path()
    fill = "rgba(37,99,235,0.030)" if st.session_state.theme == "light" else "rgba(255,255,255,0.025)"
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}">'
        f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="1.9" stroke-linejoin="round"/></svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


# Kontury państw Europy z Natural Earth (uproszczona mapa).
# Geometria zapisana w kodzie – nie wymaga sieci ani geopandas przy uruchomieniu.
EUROPE_OUTLINES_B64 = "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"
POLAND_FILLED_B64 = "eNpFkduRBSAIQ1vZAhwGkIf2cLeB7b+QTfDjfjlHICb4eyxlr7Qj5+dz7Mpd6VfywVkZKgXQByUB8C298pY4wTBTGmKc2VKAZlvfA+naKk0BZyU2Z/ps0ang0W6lwI6BehVoAnKLAXogggJ+RAG462njDPxixko2AEcCgq4bB73lCOiWADjttM6jplSrC52J4ARnUoTDDuqoOCCmrZ2rOjlQCbWsZuyq4kKyZ6aYNMMHknZyPyhDnvScGXRD2t4O4NpW8DWGo4M4Ma6xF1TgkEtEdwL6fVZQWut91vcb//4BYCVd9Q=="


def europe_watermark_uri(theme):
    countries = zlib.decompress(base64.b64decode(EUROPE_OUTLINES_B64)).decode("utf-8")
    poland = zlib.decompress(base64.b64decode(POLAND_FILLED_B64)).decode("utf-8")
    if theme == "dark":
        europe_fill, europe_stroke = "none", "rgba(219,234,254,0.12)"
        poland_fill, poland_stroke = "rgba(248,113,113,0.065)", "rgba(252,165,165,0.19)"
    else:
        europe_fill, europe_stroke = "none", "rgba(30,58,95,0.12)"
        poland_fill, poland_stroke = "rgba(220,38,38,0.065)", "rgba(185,28,28,0.19)"
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1176 1064" preserveAspectRatio="none">'
        f'<path d="{countries}" fill="{europe_fill}" stroke="{europe_stroke}" '
        'stroke-width="1.1" stroke-linejoin="round" fill-rule="evenodd"/>'
        f'<path d="{poland}" fill="{poland_fill}" stroke="{poland_stroke}" '
        'stroke-width="1.6" stroke-linejoin="round" fill-rule="evenodd"/>'
        '</svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


BASE_CSS = Template("""
<style>
.stApp {
    color-scheme: $scheme;
    background-color: $bg !important;
    /* Znak wodny rozciągnięty na cały widoczny obszar strony.
       preserveAspectRatio="none" w SVG usuwa puste marginesy przy ekranach panoramicznych. */
    background-image: url("$map") !important;
    background-repeat: no-repeat !important;
    background-position: center center !important;
    background-size: 100vw 100vh !important;
    background-attachment: fixed !important;
    color: $text !important;
}
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stMainBlockContainer"] { background: transparent !important; }
header[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stHeader"] * { color: $text !important; }
.block-container { padding-top: 1.25rem !important; padding-bottom: 1.0rem !important; max-width: 1540px; }
section[data-testid="stSidebar"] { border-right: 1px solid $border !important; box-shadow: $side_shadow !important; z-index: 50; }
section[data-testid="stSidebar"] > div {
    background:
        linear-gradient(180deg, rgba(37,99,235,0.92) 0%, rgba(59,130,246,0.72) 34%, rgba(255,255,255,0.08) 62%, rgba(255,255,255,0.00) 100%),
        linear-gradient(180deg, rgba(11,32,78,0.42) 0%, rgba(11,32,78,0.10) 55%, rgba(11,32,78,0.00) 100%),
        none bottom center / cover no-repeat,
        $side !important;
}
section[data-testid="stSidebar"] .block-container { padding-top: 1.2rem !important; padding-bottom: 1.2rem !important; }
section[data-testid="stSidebar"] * { color: $sidebar_text; }
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] span { color: $sidebar_text !important; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp label, .stApp li, .stApp [data-testid="stCaptionContainer"] { color: $text !important; }
.side-brand { display:flex; align-items:center; gap:16px; margin-bottom:16px; padding:6px 6px 10px 6px; }
.side-brand .brand-logo { width:78px; height:78px; flex:none; }
.side-brand .brand-title { font-size:1.02rem; line-height:1.08; font-weight:800; color:$sidebar_title; }
.side-brand .brand-title span { display:block; color:$sidebar_title; }
.side-sep { height:1px; background: rgba(255,255,255,0.42); margin: 0 0 16px 0; }
.side-subhead { font-size:0.88rem; font-weight:800; color:$sidebar_text; margin:18px 0 8px 0; display:flex; align-items:center; gap:10px; }
.side-subhead::after { content:""; flex:1; height:1px; background: rgba(255,255,255,0.36); }
.stApp .st-key-btn_podsumowanie button, .stApp .st-key-btn_kategorie button, .stApp .st-key-theme_light button,
.stApp .st-key-theme_dark button, .stApp .st-key-coming_1 button, .stApp .st-key-coming_2 button,
.stApp .st-key-coming_3 button { border-radius: 14px !important; min-height: 54px !important; border: 1px solid $sidebar_border !important; background: $sidebar_card !important; backdrop-filter: blur(4px); box-shadow: none !important; transition: all .18s ease !important; }
.stApp .st-key-btn_podsumowanie button:hover, .stApp .st-key-btn_kategorie button:hover, .stApp .st-key-theme_light button:hover, .stApp .st-key-theme_dark button:hover { transform: translateY(-1px); background: rgba(255,255,255,0.22) !important; border-color: rgba(255,255,255,0.52) !important; }
.stApp .st-key-btn_podsumowanie button p, .stApp .st-key-btn_kategorie button p, .stApp .st-key-theme_light button p,
.stApp .st-key-theme_dark button p, .stApp .st-key-coming_1 button p, .stApp .st-key-coming_2 button p,
.stApp .st-key-coming_3 button p { color: $sidebar_text !important; font-weight: 700 !important; }
.stApp .st-key-btn_podsumowanie [data-testid="stIconMaterial"], .stApp .st-key-btn_kategorie [data-testid="stIconMaterial"],
.stApp .st-key-theme_light [data-testid="stIconMaterial"], .stApp .st-key-theme_dark [data-testid="stIconMaterial"],
.stApp .st-key-coming_1 [data-testid="stIconMaterial"], .stApp .st-key-coming_2 [data-testid="stIconMaterial"],
.stApp .st-key-coming_3 [data-testid="stIconMaterial"] { color: $sidebar_text !important; }
.stApp .st-key-$active_tab button { background: $sidebar_card_active !important; border: 1.4px solid rgba(255,255,255,0.70) !important; box-shadow: 0 10px 18px rgba(37,99,235,0.28) !important; }
.stApp .st-key-$active_theme button { background: rgba(255,255,255,0.22) !important; border: 1.2px solid rgba(255,255,255,0.62) !important; }
.stApp .st-key-coming_1 button, .stApp .st-key-coming_2 button, .stApp .st-key-coming_3 button { opacity: 0.72 !important; }
.stApp .st-key-coming_1 button:disabled, .stApp .st-key-coming_2 button:disabled, .stApp .st-key-coming_3 button:disabled { cursor: not-allowed !important; background: rgba(255,255,255,0.14) !important; }
section[data-testid="stSidebar"] [data-baseweb="select"] > div, section[data-testid="stSidebar"] [data-baseweb="base-input"],
section[data-testid="stSidebar"] [data-baseweb="tag"] { background: rgba(255,255,255,0.12) !important; border-color: rgba(255,255,255,0.26) !important; }
section[data-testid="stSidebar"] [data-baseweb="select"] *, section[data-testid="stSidebar"] [data-baseweb="base-input"] * { color: $sidebar_text !important; fill: $sidebar_text !important; }
.dash-head { display:flex; justify-content:space-between; align-items:flex-start; gap:20px; margin-bottom: 14px; }
.dash-title { font-size:3rem; line-height:1.0; font-weight: 850; letter-spacing:-1.2px; color:$text; }
.dash-sub { font-size:1.0rem; color:$muted; margin-top:6px; }
.dash-chip-row { display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
.dash-chip { display:inline-flex; align-items:center; gap:8px; padding:8px 12px; border-radius:999px; background:$card; border:1px solid $border; box-shadow:$shadow; color:$text; font-size:0.84rem; font-weight:700; }
.dash-chip.small { min-height:44px; padding:0 16px; }
.kpi-card { background:$card; border:1px solid $border; border-radius:18px; box-shadow:$shadow; padding:16px 18px 15px 18px; min-height:180px; position:relative; overflow:hidden; }
.kpi-top { display:flex; align-items:center; gap:14px; }
.kpi-icon { width:52px; height:52px; border-radius:999px; display:grid; place-items:center; font-size:24px; color:white; font-weight:800; flex:none; }
.kpi-headline { font-size:0.94rem; font-weight:700; color:$text; }
.kpi-value { font-size:1.18rem; font-weight:850; line-height:1.15; color:$text; margin:14px 0 6px 0; }
.kpi-trend { font-size:0.90rem; font-weight:800; }
.kpi-desc { font-size:0.85rem; line-height:1.45; color:$muted; margin-top:10px; }
.kpi-spark { margin-top:8px; height:44px; }
.card-box { background:$card; border:1px solid $border; border-radius:18px; box-shadow:$shadow; padding:14px 16px 10px 16px; height:100%; }
.card-title { display:flex; align-items:center; gap:10px; font-size:1.0rem; font-weight:800; color:$text; margin-bottom:8px; }
.card-note { font-size:0.84rem; color:$muted; line-height:1.45; margin: 4px 0 6px 0; }
[data-testid="stPlotlyChart"] { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; }
.tbl-wrap { max-height: 520px; overflow: auto; border: 1px solid $border; border-radius: 16px; background: $card; box-shadow: $shadow; }
table.tbl { border-collapse: collapse; width: 100%; font-size: 0.90rem; }
table.tbl th { position: sticky; top: 0; z-index: 1; background: $th; color: $text; text-align: left; padding: 10px 12px; border-bottom: 2px solid $border; white-space: nowrap; }
table.tbl td { padding: 8px 12px; border-bottom: 1px solid $border; font-weight: 600; color: $text; }
.stApp [data-baseweb="select"] > div, .stApp [data-baseweb="input"], .stApp [data-baseweb="input"] input, .stApp [data-baseweb="base-input"],
.stApp [data-testid="stMultiSelect"] [data-baseweb="select"] > div, .stApp [data-testid="stSelectbox"] [data-baseweb="select"] > div { background: $inp !important; border-color: $border !important; }
.stApp [data-baseweb="select"] *, .stApp [data-testid="stMultiSelect"] *, .stApp [data-testid="stSelectbox"] * { color: $text !important; fill: $muted !important; }

/* Bardziej wyrazisty interfejs */
.kpi-card { min-height: 218px; padding: 17px 18px !important; border-width: 1.4px !important; }
.kpi-value { font-size: 1.42rem !important; margin: 7px 0 4px !important; overflow-wrap: break-word; }
.kpi-headline { font-size: 0.99rem !important; }
.kpi-desc { font-size: 0.88rem !important; color: $text !important; opacity:.86; }
.kpi-trend { font-size: .86rem !important; }
.card-note { font-size: .91rem !important; color: $text !important; opacity:.88; }
.card-title { font-size: 1.09rem !important; }
/* Kolorowe paski u góry kart, zgodne z finansową legendą */
.stApp .kpi-card.income { border-top: 5px solid #16A34A !important; }
.stApp .kpi-card.spending { border-top: 5px solid #DC2626 !important; }
.stApp .kpi-card.balance { border: 1.4px solid $border !important; border-top: 6px solid #F59E0B !important; box-shadow: $shadow !important; }
.stApp .kpi-card.execution { border-top: 5px solid #7C3AED !important; }
/* pasek narzędzi na górze */
.toolbar-note { display:inline-flex; align-items:center; gap:15px; padding:8px 12px; background:$card; border:1px solid $border; border-radius:12px; color:$text; font-size:.89rem; font-weight:650; }
.toolbar-key { display:inline-block; width:11px; height:11px; border-radius:100%; margin-right:5px; }
.financial-balance { background:$card; border:1px solid $border; border-left:7px solid #111111; border-radius:16px; padding:18px 22px; margin:13px 0 17px; box-shadow:$shadow; }
.financial-balance .balance-title { font-size:1.12rem; font-weight:850; color:$text; }
.financial-balance .balance-value { font-size:2.15rem; color:$text; font-weight:850; line-height:1.3; }
.financial-balance .balance-desc { font-size:.96rem; color:$text; line-height:1.6; }
.financial-balance .balance-years { font-size:.85rem; font-weight:750; color:$muted; margin-top:6px; }
/* Roczny trend wyniku budżetu, w stylu miniwykresów pozostałych kafelków. */
.financial-balance .balance-metrics { display:flex; align-items:center; justify-content:space-between; gap:20px; flex-wrap:wrap; }
.financial-balance .balance-figures { flex:1 1 300px; min-width:0; }
.financial-balance .balance-trend { flex:0 1 270px; min-width:180px; max-width:280px; margin-left:auto; }
.financial-balance .balance-trend-label { font-size:.78rem; font-weight:700; color:$muted; margin-bottom:3px; }
.financial-balance .balance-trend .kpi-spark { display:block; width:100%; height:72px; margin:0 !important; }
@media (max-width: 580px) {
  .financial-balance .balance-trend { flex-basis:100%; max-width:100%; margin-left:0; }
  .financial-balance .balance-trend .kpi-spark { height:55px; }
}
/* Historyczne ustawienia panelu bocznego (nadpisane przez gradient na końcu arkusza). */
section[data-testid="stSidebar"] > div {
    background: linear-gradient(180deg, rgba(24,76,163,0.92), rgba(31,89,166,0.65) 47%, rgba(14,44,84,.28)),
                none center bottom / cover no-repeat, $side !important;
}
/* czerwony, widoczny przycisk zwijania oraz rozwijania sidebaru */
.stApp [data-testid="stSidebarCollapseButton"] button,
.stApp [data-testid="stSidebarCollapsedControl"] button,
.stApp [data-testid="stExpandSidebarButton"] button,
.stApp button[data-testid="stExpandSidebarButton"],
.stApp [data-testid="stSidebarCollapseButton"] button {
    color:#FFFFFF !important; background:#DC2626 !important; border:2px solid #FCA5A5 !important;
    box-shadow: 0 0 0 3px rgba(220,38,38,.18), 0 0 22px rgba(220,38,38,.80) !important;
    border-radius:12px !important; height:44px !important; width:44px !important; min-height:44px !important;
    opacity:1 !important; z-index: 9999 !important;
}
.stApp [data-testid="stSidebarCollapseButton"] button *,
.stApp [data-testid="stSidebarCollapsedControl"] button *,
.stApp [data-testid="stExpandSidebarButton"] button * { color:#FFFFFF !important; fill:#FFFFFF !important; stroke:#FFFFFF !important; }
.stApp [data-testid="stSidebarCollapseButton"] button:hover,
.stApp [data-testid="stSidebarCollapsedControl"] button:hover,
.stApp [data-testid="stExpandSidebarButton"] button:hover { background:#B91C1C !important; box-shadow:0 0 26px rgba(220,38,38,1) !important; }
/* Rozciągnięcie panelu pionowo pozwala przenieść sekcję motywu na dół. */
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > [data-testid="stVerticalBlock"],
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] {
    min-height: calc(100vh - 110px) !important; display:flex !important; flex-direction:column !important;
}
/* Przełącznik motywu odseparowany wizualnie od nawigacji */
.stApp .st-key-theme_bottom { margin-top:auto !important; padding:14px 10px !important; border:2px solid rgba(255,255,255,.62) !important; border-radius:14px !important; background:rgba(12,33,72,.46) !important; box-shadow:0 0 20px rgba(255,255,255,.12) !important; }
.stApp .st-key-theme_light button, .stApp .st-key-theme_dark button { min-height:45px !important; }
/* Pasek boczny z niebieskim gradientem. */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #3775C6 0%, #6D9BD6 61%, #B2C9E8 100%) !important;
}
section[data-testid="stSidebar"] > div {
    background: linear-gradient(180deg, rgba(33,98,185,.82) 0%, rgba(64,117,193,.69) 40%, rgba(89,142,207,.31) 62%, rgba(255,255,255,.00) 79%),
                none bottom center / 100% auto no-repeat,
                linear-gradient(180deg, #3473C6 0%, #84AFE0 100%) !important;
    background-attachment: local, local, local !important;
}
.side-brand { gap:12px !important; padding:2px 4px 11px !important; margin-bottom:7px !important; }
.side-brand .brand-logo { width:53px !important; height:53px !important; }
.side-brand .brand-logo img { width:53px !important; height:53px !important; border-radius:9px !important; }
.side-brand .brand-title { font-size:1.19rem !important; line-height:1.10 !important; }
.side-sep { margin-bottom:13px !important; }
.side-subhead { margin-top:13px !important; margin-bottom:8px !important; }
.stApp .st-key-btn_podsumowanie button,
.stApp .st-key-btn_kategorie button {
    border-radius:12px !important;
    min-height:56px !important;
    background:rgba(255,255,255,.16) !important;
    border:1px solid rgba(255,255,255,.22) !important;
    justify-content:flex-start !important;
    padding-left:18px !important;
}
.stApp .st-key-btn_podsumowanie [data-testid="stIconMaterial"],
.stApp .st-key-btn_kategorie [data-testid="stIconMaterial"] {
    color:white !important;
    font-size:1.4rem !important;
}
.stApp .st-key-coming_1 button, .stApp .st-key-coming_2 button, .stApp .st-key-coming_3 button {
    border-radius:12px !important;
    background:rgba(221,231,243,.26) !important;
    opacity:.75 !important;
    min-height:49px !important;
    justify-content:flex-start !important;
}
/* Motyw jest widoczny przed pierwszym przewinięciem zamiast przyklejać się pod ekranem. */
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > [data-testid="stVerticalBlock"],
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] {
    min-height:0 !important;
}
.stApp .st-key-theme_bottom {
    margin-top:13px !important;
    padding:9px 10px !important;
    border:1px solid rgba(255,255,255,.36) !important;
    border-radius:13px !important;
    background:rgba(20,62,128,.35) !important;
    box-shadow:0 3px 16px rgba(23,54,110,.10) !important;
}
.stApp .st-key-theme_bottom .side-subhead { font-size:.87rem !important; }
.stApp .st-key-theme_light button, .stApp .st-key-theme_dark button { min-height:40px !important; }
section[data-testid="stSidebar"] .block-container { padding-top:.65rem !important; padding-bottom:.6rem !important; }

/* Korekty wizualne sidebaru: przejrzysta nawigacja. */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #2D6AB9 0%, #4B89D4 58%, #76A6E1 100%) !important;
}
section[data-testid="stSidebar"] > div {
    background-image:
        linear-gradient(180deg,
            rgba(25,86,169,.88) 0%,
            rgba(38,107,191,.86) 27%,
            rgba(53,124,207,.60) 49%,
            rgba(57,127,199,.24) 65%,
            rgba(15,46,92,.10) 100%),
        none,
        linear-gradient(180deg, #316EBD, #77A7E2) !important;
    background-repeat: no-repeat, no-repeat, no-repeat !important;
    /* Szerokość zdjęcia = szerokość panelu, bez rozciągania w pionie. */
    background-size: 100% 100%, 100% auto, 100% 100% !important;
    background-position: center center, center bottom, center center !important;
    background-attachment: scroll !important;
}
.side-brand {
    align-items:center !important;
    gap:13px !important;
    padding:6px 3px 10px !important;
    margin-bottom:8px !important;
}
.side-brand .brand-logo { width:63px !important; height:63px !important; }
.side-brand .brand-logo img { width:63px !important; height:63px !important; border-radius:0 !important; }
.side-brand .brand-copy { min-width:0; flex:1; }
.side-brand .brand-title { font-size:1.21rem !important; line-height:1.08 !important; letter-spacing:-.2px; }
.side-brand .brand-tagline {
    font-size:.73rem !important;
    line-height:1.3 !important;
    font-weight:650;
    margin-top:5px;
    color:#FFFFFF !important;
    text-shadow:0 1px 5px rgba(13,51,111,.20);
}
.stApp .st-key-btn_podsumowanie button,
.stApp .st-key-btn_kategorie button {
    min-height:59px !important;
    border:1.5px solid rgba(255,255,255,.55) !important;
    background:rgba(225,239,255,.26) !important;
    box-shadow:0 3px 12px rgba(8,43,101,.16), inset 0 1px 0 rgba(255,255,255,.19) !important;
    backdrop-filter: blur(7px) !important;
}
.stApp .st-key-btn_podsumowanie button:hover,
.stApp .st-key-btn_kategorie button:hover {
    background:rgba(235,245,255,.37) !important;
    border-color:rgba(255,255,255,.85) !important;
}
.stApp .st-key-btn_podsumowanie button p,
.stApp .st-key-btn_kategorie button p {
    color:#FFFFFF !important;
    font-size:.94rem !important;
    font-weight:850 !important;
    text-shadow:0 1px 5px rgba(8,43,101,.28);
}
.stApp .st-key-coming_1 button,
.stApp .st-key-coming_2 button,
.stApp .st-key-coming_3 button {
    border:1px solid rgba(255,255,255,.38) !important;
    background:rgba(226,238,250,.24) !important;
    opacity:.80 !important;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.12) !important;
}
.stApp .st-key-coming_1 button p,
.stApp .st-key-coming_2 button p,
.stApp .st-key-coming_3 button p { color:#E6F0FC !important; font-weight:750 !important; }
.stApp .st-key-theme_bottom { margin-top:7px !important; padding:8px 10px !important; }
.stApp .st-key-theme_light button,
.stApp .st-key-theme_dark button {
    background:rgba(226,239,255,.23) !important;
    border:1px solid rgba(255,255,255,.55) !important;
    box-shadow:0 3px 10px rgba(12,44,97,.14) !important;
}

/* wiersz filtrów */
.stApp .st-key-top_filters { border:1px solid $border !important; background:$card !important; border-radius:16px !important; padding:12px 16px !important; margin-bottom:10px !important; }
.stApp .st-key-top_filters label { font-weight:750 !important; font-size:.88rem !important; }


/* Jedna wspólna karta obejmuje tytuł, opis, narzędzia, wykres i legendę.
   Streamlit renderuje Plotly poza st.markdown, dlatego używamy st.container(key=...). */
.stApp .st-key-panel_income,
.stApp .st-key-panel_spending,
.stApp .st-key-panel_trend_budget,
.stApp .st-key-panel_trend_result,
.stApp .st-key-panel_category_main,
.stApp .st-key-panel_category_share,
.stApp .st-key-panel_category_detail,
.stApp .st-key-panel_summary_table,
.stApp .st-key-panel_detail_table {
    background: $card !important;
    border: 1px solid $border !important;
    border-radius: 20px !important;
    box-shadow: $shadow !important;
    backdrop-filter: blur(14px) !important;
    -webkit-backdrop-filter: blur(14px) !important;
    padding: 18px 20px 15px !important;
    margin-bottom: 14px !important;
}
.stApp .st-key-panel_income .card-title,
.stApp .st-key-panel_spending .card-title,
.stApp .st-key-panel_trend_budget .card-title,
.stApp .st-key-panel_trend_result .card-title,
.stApp .st-key-panel_category_main .card-title,
.stApp .st-key-panel_category_share .card-title,
.stApp .st-key-panel_category_detail .card-title {
    margin-bottom: 5px !important;
}
.stApp .st-key-panel_income .card-note,
.stApp .st-key-panel_spending .card-note,
.stApp .st-key-panel_trend_budget .card-note,
.stApp .st-key-panel_trend_result .card-note,
.stApp .st-key-panel_category_main .card-note,
.stApp .st-key-panel_category_share .card-note,
.stApp .st-key-panel_category_detail .card-note {
    margin-bottom: 0 !important;
}
.stApp [data-testid="stPlotlyChart"],
.stApp [data-testid="stPlotlyChart"] > div,
.stApp [data-testid="stPlotlyChart"] .js-plotly-plot,
.stApp [data-testid="stPlotlyChart"] .plot-container {
    background: transparent !important;
    box-shadow: none !important;
    border: none !important;
}
/* Pozostałe elementy głównego dashboardu również przepuszczają tło Polski. */
.stApp .kpi-card,
.stApp .financial-balance,
.stApp .card-box,
.stApp .dash-chip,
.stApp .toolbar-note,
.stApp .tbl-wrap,
.stApp .st-key-top_filters {
    background: $card !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
}


/* Równa wysokość i wspólny układ czterech kart podsumowania. */
.kpi-card {
    height: 100% !important;
    min-height: 330px !important;
    display: flex !important;
    flex-direction: column !important;
    box-sizing: border-box !important;
}
.kpi-card .kpi-top { min-height: 54px; }
.kpi-card .kpi-value { min-height: 42px; margin-top: 11px !important; }
.kpi-card .kpi-trend { min-height: 43px; line-height: 1.35; }
.kpi-card .kpi-spark { width: 100%; flex: 0 0 44px; margin: 6px 0 8px !important; }
.kpi-card .kpi-desc { margin-top: auto !important; min-height: 92px; }
.kpi-card.gdp-ratio { border-top: 5px solid #F59E0B !important; }
.kpi-card.gdp-ratio .kpi-value { color: $text; }
.kpi-card.gdp-ratio.deficit .kpi-value { color: $neg !important; }
.financial-balance .balance-value { font-size: 2.4rem; font-weight: 900; }
@media (max-width: 1100px) {
    .kpi-card { min-height: 300px !important; }
}

/* ===== Uspójnienie przezroczystości wszystkich pól poza sidebarem ===== */
.stApp .kpi-card,
.stApp .card-box,
.stApp .card-shell,
.stApp .dash-chip,
.stApp .toolbar-note,
.stApp .tbl-wrap,
.stApp .st-key-top_filters,
.stApp .st-key-panel_income,
.stApp .st-key-panel_spending,
.stApp .st-key-panel_trend_budget,
.stApp .st-key-panel_trend_result,
.stApp .st-key-panel_category_main,
.stApp .st-key-panel_category_share,
.stApp .st-key-panel_category_detail,
.stApp .st-key-panel_summary_table,
.stApp .st-key-panel_detail_table {
    background: $card !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}

/* Duży wynik budżetu: identyczne tło i delikatny kontur jak pozostałe karty. */
.stApp .financial-balance {
    background: $card !important;
    border: 1px solid $border !important;
    border-left: 7px solid #111111 !important;
    box-shadow: $shadow !important;
    backdrop-filter: blur(8px) !important;
}

/* Realizacja planu: taki sam kafelek jak pozostałe, ale z fioletowym akcentem u góry. */
.stApp .kpi-card.execution {
    border: 1.4px solid $border !important;
    border-top: 5px solid #7C3AED !important;
    box-shadow: $shadow !important;
}
/* Wynik / PKB: standardowa karta z żółtym akcentem u góry. */
.stApp .kpi-card.gdp-ratio {
    border: 1.4px solid $border !important;
    border-top: 5px solid #F59E0B !important;
    box-shadow: $shadow !important;
}

/* Aktywna zakładka – celowo mocniejsza od pozostałych, niezależnie od motywu. */
.stApp .st-key-$active_tab button,
.stApp .st-key-$active_tab button:hover {
    background: rgba(255,255,255,.43) !important;
    border: 2px solid #FFFFFF !important;
    border-left: 6px solid #F87171 !important;
    box-shadow: 0 0 0 2px rgba(255,255,255,.17), 0 8px 24px rgba(13,35,75,.28) !important;
    filter: brightness(1.1);
}
.stApp .st-key-$active_tab button p,
.stApp .st-key-$active_tab button [data-testid="stIconMaterial"] {
    color: #FFFFFF !important;
    font-weight: 900 !important;
}


/* Wersja: Stan Budżetu, bardziej czytelny sidebar i delikatniejsze karty. */
.side-brand { gap:14px !important; align-items:center !important; padding:5px 2px 9px !important; }
.side-brand .brand-logo,
.side-brand .brand-logo img { width:76px !important; height:76px !important; flex-shrink:0; }
.side-brand .brand-copy { min-width:0 !important; }
.side-brand .brand-title { font-size:1.40rem !important; line-height:1.00 !important; letter-spacing:-.35px !important; }
.side-brand .brand-title > span { display:block !important; }
.side-brand .brand-title .brand-polski { color:#FFFFFF !important; font-weight:350 !important; }
.side-brand .brand-title .brand-obserwator { color:#FFFFFF !important; font-weight:900 !important; }
.side-brand .brand-title .brand-budzetowy { color:#FFB8BE !important; font-weight:900 !important; }
.side-brand .brand-tagline { font-size:.75rem !important; font-weight:700 !important; margin-top:6px !important; }

.stApp .st-key-btn_podsumowanie button,
.stApp .st-key-btn_kategorie button {
    min-height:48px !important;
    padding:7px 13px !important;
    border-radius:11px !important;
}
.stApp .st-key-btn_podsumowanie button p,
.stApp .st-key-btn_kategorie button p { font-size:.88rem !important; }
.stApp .st-key-coming_1 button,
.stApp .st-key-coming_2 button,
.stApp .st-key-coming_3 button { min-height:42px !important; border-radius:11px !important; }
.stApp .st-key-coming_1 button p,
.stApp .st-key-coming_2 button p,
.stApp .st-key-coming_3 button p { font-size:.81rem !important; }

/* Motyw: mniej prześwitów, mocniejsza ramka i czytelne przyciski. */
.stApp .st-key-theme_bottom {
    background:rgba(11,38,90,.82) !important;
    border:1.5px solid rgba(255,255,255,.73) !important;
    box-shadow:0 7px 20px rgba(7,27,66,.29) !important;
    backdrop-filter:blur(10px) !important;
}
.stApp .st-key-theme_light button,
.stApp .st-key-theme_dark button {
    background:rgba(255,255,255,.26) !important;
    border:1px solid rgba(255,255,255,.68) !important;
}

/* Zachowaj spójny stopień przezroczystości także na wspólnych panelach wykresów. */
.stApp .kpi-card,
.stApp .financial-balance,
.stApp .card-box,
.stApp .card-shell,
.stApp .dash-chip,
.stApp .toolbar-note,
.stApp .tbl-wrap,
.stApp .st-key-top_filters,
.stApp .st-key-panel_income,
.stApp .st-key-panel_spending,
.stApp .st-key-panel_trend_budget,
.stApp .st-key-panel_trend_result,
.stApp .st-key-panel_category_main,
.stApp .st-key-panel_category_share,
.stApp .st-key-panel_category_detail,
.stApp .st-key-panel_summary_table,
.stApp .st-key-panel_detail_table { background:$card !important; }

/* Ikona strzałki filtra kategorii zamiast kwadratu powodowanego przez globalne fill. */
.stApp .st-key-filter_type_top [data-baseweb="select"] > div { position:relative !important; padding-right:42px !important; }
.stApp .st-key-filter_type_top [data-baseweb="select"] svg { display:none !important; }
.stApp .st-key-filter_type_top [data-baseweb="select"] > div::after {
    content:"⌄";
    position:absolute;
    right:15px;
    top:50%;
    transform:translateY(-57%);
    font-size:1.75rem;
    line-height:1;
    font-weight:600;
    color:$text;
    pointer-events:none;
}


/* ===== OSTATNIE POPRAWKI UI: 2026-11-08 ===== */
/* Większy znak, czytelny trzywierszowy tytuł, lekkie hasło. */
.side-brand { gap: 12px !important; align-items: center !important; padding-top: 5px !important; }
.side-brand .brand-logo,
.side-brand .brand-logo img { width: 88px !important; height: 88px !important; flex: 0 0 88px !important; }
.side-brand .brand-copy { min-width: 0 !important; }
.side-brand .brand-title { font-size: 1.29rem !important; line-height: 1.06 !important; }
.side-brand .brand-tagline {
    font-size: .78rem !important;
    font-weight: 400 !important;
    line-height: 1.35 !important;
    letter-spacing: .01em !important;
    color: rgba(255,255,255,.94) !important;
    margin-top: 8px !important;
}

/* Oddziel panel motywu od przycisków 'W przygotowaniu' i dodaj białe szkło. */
.stApp .st-key-theme_bottom {
    margin-top: 25px !important;
    padding: 13px 13px 14px !important;
    border: 1px solid rgba(255,255,255,.82) !important;
    border-radius: 17px !important;
    background: rgba(255,255,255,.82) !important;
    box-shadow: 0 7px 20px rgba(9,29,70,.19) !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
}
.stApp .st-key-theme_bottom .side-subhead,
.stApp .st-key-theme_bottom .side-subhead::before,
.stApp .st-key-theme_bottom [data-testid="stMarkdownContainer"] p {
    color: #14264A !important;
}
.stApp .st-key-theme_bottom .side-subhead::after { background: rgba(20,38,74,.22) !important; }
.stApp .st-key-theme_bottom .st-key-theme_light button,
.stApp .st-key-theme_bottom .st-key-theme_dark button {
    min-height: 39px !important;
    background: rgba(232,239,251,.93) !important;
    color: #14264A !important;
    border: 1px solid rgba(35,68,123,.34) !important;
    box-shadow: 0 2px 5px rgba(15,23,42,.06) !important;
}
.stApp .st-key-theme_bottom .st-key-theme_light button p,
.stApp .st-key-theme_bottom .st-key-theme_dark button p,
.stApp .st-key-theme_bottom .st-key-theme_light [data-testid="stIconMaterial"],
.stApp .st-key-theme_bottom .st-key-theme_dark [data-testid="stIconMaterial"] {
    color: #14264A !important;
    fill: #14264A !important;
}
/* Pasek filtrów: lekka powierzchnia pod każdym polem. */
.stApp .st-key-top_filters .filter-legend,
.stApp .st-key-top_filters .filter-empty-state,
.stApp .st-key-top_filters .st-key-filter_year_popover button,
.stApp .st-key-top_filters .st-key-filter_type_top [data-baseweb="select"] > div {
    background: rgba(225,236,253,.28) !important;
    border: 1px solid rgba(96,125,172,.25) !important;
    border-radius: 12px !important;
    box-shadow: inset 0 1px 2px rgba(22,47,88,.025) !important;
}

/* ===== Projekt: bardziej przezroczysty panel motywu i wspólna wysokość logotypu ===== */
.side-brand {
    display:flex !important;
    align-items:flex-start !important;
    gap:12px !important;
    padding:7px 2px 11px !important;
    margin-bottom:10px !important;
}
.side-brand .brand-logo,
.side-brand .brand-logo img {
    width:93px !important;
    height:93px !important;
    flex:0 0 93px !important;
    display:block !important;
    object-fit:contain !important;
    border-radius:0 !important;
}
.side-brand .brand-copy {
    display:flex !important;
    flex-direction:column !important;
    flex:1 1 auto !important;
    min-width:0 !important;
    align-self:flex-start !important;
}
.side-brand .brand-title {
    font-size:1.53rem !important;
    line-height:1.14 !important;
    letter-spacing:-.35px !important;
    margin:0 !important;
    padding:0 !important;
    min-height:93px !important;
    display:flex !important;
    flex-direction:column !important;
    justify-content:space-between !important;
}
.side-brand .brand-title span { display:block !important; }
.side-brand .brand-tagline {
    display:block !important;
    width:100% !important;
    max-width:100% !important;
    box-sizing:border-box !important;
    font-weight:400 !important;
    font-size:.79rem !important;
    line-height:1.32 !important;
    margin-top:8px !important;
    text-align:left !important;
    color:rgba(255,255,255,.96) !important;
}
/* Biel z dużo większą przezroczystością: 82% -> 28%. */
.stApp .st-key-theme_bottom {
    background:rgba(255,255,255,.28) !important;
    border:1px solid rgba(255,255,255,.46) !important;
    box-shadow:0 6px 18px rgba(7,26,66,.09) !important;
    backdrop-filter:blur(6px) !important;
    -webkit-backdrop-filter:blur(6px) !important;
}
.stApp .st-key-theme_bottom .side-subhead,
.stApp .st-key-theme_bottom [data-testid="stMarkdownContainer"] p {
    color:#FFFFFF !important;
    text-shadow:0 1px 3px rgba(12,39,81,.4) !important;
}
.stApp .st-key-theme_bottom .side-subhead::after {
    background:rgba(255,255,255,.48) !important;
}
.stApp .st-key-theme_bottom .st-key-theme_light button,
.stApp .st-key-theme_bottom .st-key-theme_dark button {
    background:rgba(255,255,255,.63) !important;
    color:#152C55 !important;
    border:1px solid rgba(255,255,255,.82) !important;
}
.stApp .st-key-theme_bottom .st-key-theme_light button p,
.stApp .st-key-theme_bottom .st-key-theme_dark button p,
.stApp .st-key-theme_bottom .st-key-theme_light [data-testid="stIconMaterial"],
.stApp .st-key-theme_bottom .st-key-theme_dark [data-testid="stIconMaterial"] {
    color:#152C55 !important;
    fill:#152C55 !important;
    text-shadow:none !important;
}

/* Panel boczny: czysty, pełnowymiarowy niebieski gradient bez fotografii. */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div {
    background-color: #326DB8 !important;
    background-image: linear-gradient(160deg,
        #194C9C 0%,
        #2767B6 30%,
        #4084CE 64%,
        #76ADE4 100%) !important;
    background-repeat: no-repeat !important;
    background-size: cover !important;
    background-position: center center !important;
}
/* W starszych motywach panorama była renderowana jako pseudoelement. */
section[data-testid="stSidebar"] > div::before {
    content: none !important;
    display: none !important;
    background: none !important;
}
/* Znak wodny Europy: w całym obszarze głównej strony, bez wpływu na animację. */
.stApp {
    background-image: url("$map") !important;
    background-repeat: no-repeat !important;
    background-size: 100% 100% !important;
    background-position: center center !important;
    background-attachment: fixed !important;
}

</style>
""")

st.markdown(BASE_CSS.substitute(**P, map=europe_watermark_uri(st.session_state.theme), active_tab="btn_podsumowanie" if st.session_state.current_tab == TAB_1 else "btn_kategorie", active_theme="theme_light" if st.session_state.theme == "light" else "theme_dark"), unsafe_allow_html=True)

# ---------------------------------------------------------
# ANIMACJA STARTOWA: KONTUR POLSKI I OTWIERANE DRZWI
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
.b-light { font-weight: 300; letter-spacing: -0.5px; color: $muted; }
.b-red { color: #DC2626; }

#splash-overlay {
    position: fixed; inset: 0; z-index: 999999; pointer-events: none;
    animation: splashGone 3.6s linear forwards;
}
#splash-overlay .door { position: absolute; top: 0; bottom: 0; width: 50%; overflow: hidden; background: $bg; }
#splash-overlay .door-l { left: 0; animation: doorL 3.6s cubic-bezier(.77,0,.18,1) forwards; }
#splash-overlay .door-r { right: 0; animation: doorR 3.6s cubic-bezier(.77,0,.18,1) forwards; }
#splash-overlay .door-bg {
    position: absolute; top: 0; width: 100vw; height: 100vh;
    background-color: $bg; background-image: none !important;
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
#splash-overlay .splash-logo { width: 112px; height: 112px; margin: 0 auto 22px auto; animation: logoIn 0.8s cubic-bezier(.34,1.56,.64,1) 0.3s both; }
#splash-overlay .splash-title { font-size: 3.2rem; font-weight: 800; color: $text; letter-spacing: -1.2px; line-height: 1.05; animation: titleUp 0.6s ease 0.7s both; }
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
      <div class="splash-title"><span class="b-light">Polski</span> Obserwator <span class="b-red">Budżetowy</span></div>
      <div class="splash-sub">Finanse publiczne bez niedomówień · Wczytywanie danych…</div>
      <div class="splash-bar-track"><div class="splash-bar-fill"></div></div>
    </div>
  </div>
</div>
""")
    st.markdown(
        SPLASH.substitute(
            **P, logo=logo_img(112),
            outline_d=_d, vbw=f"{_w:.0f}", vbh=f"{_h:.0f}",
        ),
        unsafe_allow_html=True,
    )


GREEN, RED = (16, 185, 129), (239, 68, 68)
color_map_typ = {"Dochody": "#10B981", "Wydatki": "#EF4444"}
FONT = "Inter, Segoe UI, Roboto, Helvetica, Arial, sans-serif"
TRACE_OPACITY = 0.88


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgba(c, a):
    return f"rgba({c[0]},{c[1]},{c[2]},{a:.2f})"


def pl(x, d=1):
    if pd.isna(x):
        return "–"
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")


def get_measure_col(m):
    return "Wykonanie_mld_PLN" if m == "Wykonanie" else "Plan_mld_PLN"


def style_fig(fig, legend_top=False, h=None):
    fig.update_layout(template=P["template"], height=h or 300, paper_bgcolor=P["plot_paper"], plot_bgcolor=P["plot_bg"], font=dict(color=P["text"], family=FONT), margin=dict(l=6, r=6, t=10, b=6), separators=", ")
    fig.update_xaxes(gridcolor=P["grid"], zerolinecolor=P["grid"], griddash="dot", showline=False)
    fig.update_yaxes(gridcolor=P["grid"], zerolinecolor=P["grid"], griddash="dot", showline=False)
    if legend_top:
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)", title_text=""))
    return fig


def modern_lines(fig):
    for tr in fig.data:
        col = getattr(getattr(tr, "line", None), "color", None) or "#64748B"
        tr.update(line=dict(shape="spline", smoothing=0.85, width=3.0, color=col), fill="tozeroy", fillcolor=rgba(hex_rgb(col), 0.10), marker=dict(size=10, color=col, line=dict(width=2.2, color=P["bg"])), cliponaxis=False, opacity=TRACE_OPACITY)
    fig.update_layout(hovermode="x unified")
    return fig


def show_fig(fig):
    st.plotly_chart(fig, use_container_width=True, theme=None, config={"displayModeBar": False})


def render_table(df, sort_cols, ascending):
    if df.empty:
        return
    d = df.sort_values(sort_cols, ascending=ascending).reset_index(drop=True)
    head = "".join(f"<th>{escape(str(c).replace('_', ' '))}</th>" for c in d.columns)
    rows = []
    for _, r in d.iterrows():
        tds = []
        for c in d.columns:
            v = r[c]
            if c == "Rok":
                txt, al = escape(str(v)), "left"
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                txt, al = pl(v) + ("%" if "Procent" in c or "%" in c else ""), "right"
            else:
                txt, al = escape(str(v)), "left"
            tds.append(f'<td style="text-align:{al};">{txt}</td>')
        rows.append("<tr>" + "".join(tds) + "</tr>")
    st.markdown('<div class="tbl-wrap"><table class="tbl"><thead><tr>' + head + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>', unsafe_allow_html=True)


def metric_delta_text(actual, plan):
    if plan == 0:
        return "brak porównania do planu", P["muted"]
    delta = actual - plan
    pct = abs(delta) / abs(plan) * 100 if plan else 0
    if delta > 0:
        return f"▲ o {pl(abs(delta))} mld zł względem planu ({pl(pct)}%)", P["pos"]
    if delta < 0:
        return f"▼ o {pl(abs(delta))} mld zł względem planu ({pl(pct)}%)", P["neg"]
    return "• zgodnie z planem", P["muted"]


def citizen_desc(kind, actual, plan, extra=None):
    if kind == "dochody":
        return "To łączna kwota pieniędzy, które państwo rzeczywiście zebrało z podatków, opłat i innych źródeł. " + f"W porównaniu z planem różnica wynosi {pl(actual - plan)} mld zł."
    if kind == "wydatki":
        return "To suma środków wydanych przez państwo na jego zadania – m.in. bezpieczeństwo, edukację, zdrowie i administrację. " + f"W porównaniu z planem różnica wynosi {pl(actual - plan)} mld zł."
    if kind == "wynik":
        return "Dodatni wynik oznacza nadwyżkę – państwo zebrało więcej środków, niż wydało w analizowanym okresie." if actual >= 0 else "Ujemny wynik oznacza deficyt – państwo wydało więcej środków, niż zebrało w analizowanym okresie."
    if kind == "wykonanie":
        return (
            "Wskaźnik pokazuje, jaki procent łącznego planu dochodów i wydatków "
            "został faktycznie zrealizowany w wybranych latach. "
            f"Łączne wykonanie wyniosło {pl(extra or 0)}% planu."
        )
    return ""


def spark_svg(values, stroke):
    vals = [float(v) for v in values if pd.notna(v)] or [0, 0, 0, 0]
    mn, mx = min(vals), max(vals)
    span = (mx - mn) or 1.0
    coords = []
    for i, v in enumerate(vals):
        x = 8 + i * (180 / max(len(vals) - 1, 1))
        y = 42 - ((v - mn) / span) * 30
        coords.append((x, y))
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    area = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords + [(coords[-1][0], 44), (coords[0][0], 44)])
    return '<svg viewBox="0 0 200 48" class="kpi-spark" xmlns="http://www.w3.org/2000/svg"><polyline points="' + area + '" fill="' + stroke + '22" stroke="none"/><polyline points="' + path + '" fill="none" stroke="' + stroke + '" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def kpi_card(title, value, delta_text, delta_color, description, icon_html, icon_bg, spark_values=None, kind=""):
    """Jednoliniowy HTML; Streamlit nie interpretuje fragmentów jako Markdown-code."""
    spark = spark_svg(spark_values or [], icon_bg) if spark_values is not None else ""
    return (
        f'<div class="kpi-card {kind}">'
        f'<div class="kpi-top"><div class="kpi-icon" style="background:{icon_bg}">{icon_html}</div>'
        f'<div class="kpi-headline">{escape(str(title))}</div></div>'
        f'<div class="kpi-value">{escape(str(value))}</div>'
        f'<div class="kpi-trend" style="color:{delta_color}">{escape(str(delta_text))}</div>'
        + spark + f'<div class="kpi-desc">{escape(str(description))}</div></div>'
    )


def section_header(title, subtitle=None, years_text=""):
    chips = [f'<span class="dash-chip"><span>🗓️</span><span>{escape(years_text)}</span></span>', '<span class="dash-chip"><span>👁️</span><span>Polski Obserwator Budżetowy</span></span>']
    subtitle_html = f'<div class="dash-sub">{escape(subtitle)}</div>' if subtitle else ''
    return '<div class="dash-head"><div>' + f'<div class="dash-title">{escape(title)}</div>{subtitle_html}<div class="dash-chip-row">{"".join(chips)}</div></div>' + f'<div class="dash-chip small">{escape(years_text or "Analiza")}</div></div>'


def donut_chart(df, typ, measure_col, hole_title):
    part = df[df["Typ_Pozycji"] == typ].groupby("Kategoria_Główna")[measure_col].sum().reset_index().sort_values(measure_col, ascending=False)
    if part.empty:
        return None
    fig = px.pie(part, names="Kategoria_Główna", values=measure_col, hole=0.62, color_discrete_sequence=(["#16A34A", "#22C55E", "#86EFAC", "#15803D", "#BBF7D0"] if typ == "Dochody" else ["#DC2626", "#EF4444", "#F87171", "#991B1B", "#FCA5A5"]))
    fig.update_traces(textinfo="none", hovertemplate="%{label}<br>%{value:.1f} mld zł<br>%{percent:.1%}<extra></extra>", marker=dict(line=dict(color=P["bg"], width=2)))
    fig.update_layout(annotations=[dict(text=hole_title, x=0.5, y=0.5, showarrow=False, font=dict(size=15, color=P["text"], family=FONT))], showlegend=True, legend=dict(orientation="v", x=1.0, y=0.5, xanchor="left", yanchor="middle", font=dict(size=11)), margin=dict(l=10, r=10, t=10, b=10))
    return style_fig(fig, h=300)


def trend_chart(df_trend, measure, result_mode=False):
    col = get_measure_col(measure)
    if result_mode:
        piv = df_trend.pivot(index="Rok", columns="Typ_Pozycji", values=col).fillna(0)
        piv["Wynik_mld_PLN"] = piv.get("Dochody", 0) - piv.get("Wydatki", 0)
        piv = piv.reset_index()
        fig = px.line(piv, x="Rok", y="Wynik_mld_PLN", markers=True)
        fig.update_traces(line_color="#F59E0B")
        modern_lines(fig)
        fig.add_hline(y=0, line_dash="dash", line_color=P["muted"])
    else:
        fig = px.line(df_trend, x="Rok", y=col, color="Typ_Pozycji", markers=True, color_discrete_map=color_map_typ)
        modern_lines(fig)
    fig.update_traces(mode="lines+markers+text", texttemplate="%{y:.1f} mld", textposition="top center")
    fig.update_xaxes(type="category")
    return style_fig(fig, legend_top=not result_mode, h=300)


def summary_message(d_wyk, w_wyk, wynik_wyk, pct_d, pct_w):
    balance = "nadwyżką" if wynik_wyk >= 0 else "deficytem"
    return f"W analizowanym okresie państwo zebrało {pl(d_wyk)} mld zł dochodów i wydało {pl(w_wyk)} mld zł. Bilans zamknął się {balance} w wysokości {pl(wynik_wyk)} mld zł. Dochody zrealizowano na poziomie {pl(pct_d)}% planu, a wydatki na poziomie {pl(pct_w)}% planu."


# ---------------------------------------------------------
# 5. REALNE DANE: Ministerstwo Finansów 2022–2025
# ---------------------------------------------------------
# Roczne wykonanie: oficjalne SPRAWOZDANIA ROCZNE MF, kwoty w mld zł.
# Wyłącznie dochody/wydatki BUDŻETU PAŃSTWA (bez budżetu środków UE).
# Dokładność sum ogólnych: 0,1 mln zł (0,0001 mld zł).
# Plany oraz wybrane pozycje podatkowe i części budżetowe: publikacja
# MF/dane.gov.pl opracowana w serwisie budzetpanstwa.pl. Kwoty tych
# składowych są tam prezentowane po zaokrągleniu do 0,1 mld zł.
# Kategoria "Pozostałe" = urzędowa suma roczna minus wymienione składniki,
# więc nie jest dodatkową, fikcyjną pozycją budżetu.

SOURCES_MF = {
    2022: "https://www.gov.pl/web/finanse/sprawozdanie-roczne-za-2022-rok",
    2023: "https://www.gov.pl/web/finanse/sprawozdanie-roczne-za-2023-rok",
    2024: "https://www.gov.pl/web/finanse/sprawozdanie-roczne-za-2024-rok",
    2025: "https://www.gov.pl/web/finanse/sprawozdanie-roczne-za-2025-rok",
}

SOURCES_DETAIL = {
    rok: {
        "dochody": f"https://budzetpanstwa.pl/budzet/{rok}/dochody",
        "wydatki": f"https://budzetpanstwa.pl/budzet/{rok}/wydatki",
    }
    for rok in SOURCES_MF
}

# total income plan, executed; total spending plan, executed (mld PLN)
ANNUAL_TOTALS = {
    2022: {"income_plan": 491.9, "income_actual": 504.8208,
           "spend_plan": 521.8, "spend_actual": 517.3989},
    2023: {"income_plan": 601.4, "income_actual": 573.9579,
           "spend_plan": 693.4, "spend_actual": 659.5865},
    2024: {"income_plan": 626.1, "income_actual": 623.2398,
           "spend_plan": 866.4, "spend_actual": 834.2425},
    2025: {"income_plan": 632.8, "income_actual": 594.5244,
           "spend_plan": 921.6, "spend_actual": 870.1906},
}

# Kwoty częściowe — najważniejsze dochody podatkowe (plan, wykonanie).
# MF/dane.gov.pl przez budzetpanstwa.pl; mld zł, zaokrąglone do 0,1 mld.
INCOME_COMPONENTS = {
    2022: {"VAT": (237.4, 230.4), "Akcyza": (79.1, 79.8),
           "CIT": (53.9, 70.1), "PIT": (69.4, 68.1)},
    2023: {"VAT": (272.9, 244.3), "Akcyza": (83.8, 84.8),
           "CIT": (77.6, 67.9), "PIT": (83.6, 91.7)},
    2024: {"VAT": (293.5, 287.7), "Akcyza": (90.3, 90.3),
           "CIT": (58.6, 60.2), "PIT": (97.7, 97.6)},
    2025: {"VAT": (349.5, 321.6), "Akcyza": (98.1, 92.5),
           "CIT": (70.7, 63.7), "PIT": (31.7, 28.8)},
}

# Największe CZĘŚCI budżetowe. Kod oznacza część, nie dział klasyfikacji.
# Celowo nie przypisujemy tym kwotom szerszych dziedzin (np. 'całe zdrowie').
SPENDING_PART_NAMES = {
    "73": "Zakład Ubezpieczeń Społecznych (część 73)",
    "29": "Obrona narodowa (część 29)",
    "79": "Obsługa długu Skarbu Państwa (część 79)",
    "82": "Subwencje ogólne dla JST (część 82)",
    "85": "Województwa (część 85)",
    "42": "Sprawy wewnętrzne (część 42)",
    "46": "Zdrowie (część 46)",
}

# Plan, wykonanie (mld PLN, zaokrąglone do 0,1 mld PLN).
SPENDING_COMPONENTS = {
    2022: {"73": (81.2, 75.6), "29": (57.1, 57.1),
           "79": (26.0, 32.7), "82": (72.2, 74.9),
           "85": (51.0, 60.4), "42": (26.7, 28.4), "46": (14.9, 15.5)},
    2023: {"73": (114.4, 105.4), "29": (97.1, 97.1),
           "79": (62.0, 61.7), "82": (99.6, 99.7),
           "85": (34.8, 43.2), "42": (32.1, 36.2), "46": (14.2, 15.2)},
    2024: {"73": (180.5, 171.3), "29": (117.5, 115.5),
           "79": (66.5, 65.8), "82": (119.7, 119.7),
           "85": (39.7, 55.0), "42": (42.9, 44.3), "46": (28.6, 29.8)},
    2025: {"73": (197.5, 180.5), "29": (123.5, 118.6),
           "79": (75.5, 72.8), "82": (49.4, 50.8),
           "85": (41.3, 58.6), "42": (47.8, 48.0), "46": (37.2, 46.1)},
}


def _budget_row(rok, typ, category, code, name, part, plan, actual, source):
    return {
        "Rok": int(rok),
        "Typ_Pozycji": typ,
        "Kategoria_Główna": category,
        "Kod_Działu": code,
        "Nazwa_Kategorii_Szczegółowa": name,
        "Część_Budżetowa": part,
        "Plan_mld_PLN": round(float(plan), 4),
        "Wykonanie_mld_PLN": round(float(actual), 4),
        "Źródło_Sprawozdawcze": source,
    }


@st.cache_data
def load_data():
    records = []
    for rok, totals in ANNUAL_TOTALS.items():
        detail_source = "MF / dane.gov.pl; rozbicie: budzetpanstwa.pl"
        income_plans = 0.0
        income_actuals = 0.0
        for tax, (plan, actual) in INCOME_COMPONENTS[rok].items():
            category = (
                "Podatki pośrednie (VAT/Akcyza)"
                if tax in ("VAT", "Akcyza") else "Podatki dochodowe (PIT/CIT)"
            )
            records.append(_budget_row(
                rok, "Dochody", category, tax,
                {"VAT": "Podatek od towarów i usług (VAT)",
                 "Akcyza": "Podatek akcyzowy",
                 "CIT": "Podatek dochodowy od osób prawnych (CIT)",
                 "PIT": "Podatek dochodowy od osób fizycznych (PIT)"}[tax],
                "Dochody podatkowe", plan, actual, detail_source,
            ))
            income_plans += plan
            income_actuals += actual
        # Suma kategorii = oficjalne dochody. Wartości resztowe wynikają z różnicy.
        records.append(_budget_row(
            rok, "Dochody", "Pozostałe dochody (podatki, inne i UE)",
            "INNE", "Pozostałe wpływy poza VAT, akcyzą, PIT i CIT",
            "Pozostałe dochody podatkowe, niepodatkowe i środki UE",
            totals["income_plan"] - income_plans,
            totals["income_actual"] - income_actuals,
            f"MF {rok}: różnica do wykonania rocznego (zawiera także zaokrąglenia)",
        ))

        spend_plans = 0.0
        spend_actuals = 0.0
        for code, (plan, actual) in SPENDING_COMPONENTS[rok].items():
            part_name = SPENDING_PART_NAMES[code]
            records.append(_budget_row(
                rok, "Wydatki", part_name, code, part_name,
                part_name, plan, actual, detail_source,
            ))
            spend_plans += plan
            spend_actuals += actual
        records.append(_budget_row(
            rok, "Wydatki", "Pozostałe części budżetowe",
            "INNE", "Pozostałe części budżetu państwa",
            "Różne części nieuwzględnione powyżej",
            totals["spend_plan"] - spend_plans,
            totals["spend_actual"] - spend_actuals,
            f"MF {rok}: różnica do wykonania rocznego (zawiera także zaokrąglenia)",
        ))

    df = pd.DataFrame.from_records(records)
    if (df[["Plan_mld_PLN", "Wykonanie_mld_PLN"]] < 0).any().any():
        raise ValueError("Niespójny podział rocznych kwot budżetu")
    for rok, totals in ANNUAL_TOTALS.items():
        d = df[df["Rok"] == rok].groupby("Typ_Pozycji")[["Plan_mld_PLN", "Wykonanie_mld_PLN"]].sum()
        checks = [
            (d.loc["Dochody", "Plan_mld_PLN"], totals["income_plan"]),
            (d.loc["Dochody", "Wykonanie_mld_PLN"], totals["income_actual"]),
            (d.loc["Wydatki", "Plan_mld_PLN"], totals["spend_plan"]),
            (d.loc["Wydatki", "Wykonanie_mld_PLN"], totals["spend_actual"]),
        ]
        if any(abs(float(got) - float(expected)) > 1e-6 for got, expected in checks):
            raise ValueError(f"Suma kategorii nie zgadza się z MF dla {rok}")
    df["Procent_Wykonania"] = (
        df["Wykonanie_mld_PLN"] / df["Plan_mld_PLN"].replace(0, float("nan")) * 100
    )
    df["Odchylenie_mld_PLN"] = df["Wykonanie_mld_PLN"] - df["Plan_mld_PLN"]
    return df

# Nominalny PKB Polski w cenach bieżących (mld zł), po rewizji GUS 06.10.2026.
# Źródło: GUS, „Produkt krajowy brutto: zaktualizowany szacunek za 2025 r.”,
# tabela „Produkt krajowy brutto (ceny bieżące)”.
# https://stat.gov.pl/obszary-tematyczne/rachunki-narodowe/roczne-rachunki-narodowe/produkt-krajowy-brutto-zaktualizowany-szacunek-za-2025-r-,19,1.html
PKB_NOMINALNY_MLD = {
    2022: 3100.850,
    2023: 3415.274,
    2024: 3669.531,
    2025: 3915.394,
}

df_raw = load_data()
if df_raw.empty:
    st.error("Nie udało się wczytać wbudowanych danych budżetowych.")
    st.stop()

lata_dostepne = sorted(df_raw["Rok"].unique().tolist())

with st.sidebar:
    st.markdown(
        f'<div class="side-brand">'
        f'<div class="brand-logo">{logo_img(88)}</div>'
        f'<div class="brand-copy"><div class="brand-title"><span class="brand-polski">Polski</span><span class="brand-obserwator">Obserwator</span><span class="brand-budzetowy">Budżetowy</span></div>'
        f'<div class="brand-tagline">Finanse publiczne bez niedomówień</div></div>'
        f'</div><div class="side-sep"></div>',
        unsafe_allow_html=True,
    )
    st.button(TAB_1, key="btn_podsumowanie", icon=":material/home:", use_container_width=True, on_click=set_tab, args=(TAB_1,))
    st.button(TAB_2, key="btn_kategorie", icon=":material/bar_chart:", use_container_width=True, on_click=set_tab, args=(TAB_2,))
    st.markdown('<div class="side-subhead">W przygotowaniu</div>', unsafe_allow_html=True)
    st.button("Twój rachunek od państwa", key="coming_1", icon=":material/account_balance:", disabled=True, help="In progress", use_container_width=True)
    st.button("Finanse samorządów", key="coming_2", icon=":material/groups:", disabled=True, help="In progress", use_container_width=True)
    st.button("Zaawansowana analityka", key="coming_3", icon=":material/monitoring:", disabled=True, help="In progress", use_container_width=True)
    with st.container(key="theme_bottom"):
        st.markdown('<div class="side-subhead" style="margin-top:0;">Motyw aplikacji</div>', unsafe_allow_html=True)
        tc1, tc2 = st.columns(2, gap="small")
        with tc1:
            st.button("Jasny", key="theme_light", icon=":material/light_mode:", use_container_width=True, on_click=set_theme, args=("light",))
        with tc2:
            st.button("Ciemny", key="theme_dark", icon=":material/dark_mode:", use_container_width=True, on_click=set_theme, args=("dark",))


# ---------------------------------------------------------
# FILTRY: jeden wyrównany panel, z czytelnym zakresem lat.
# Lata są wybierane w rozwijanym oknie; na pasku widoczny jest
# wynik wyboru, np. 2022–2025 (lub lista lat nieciągłych).
# ---------------------------------------------------------
def opis_zakresu_lat(lata):
    lata = sorted({int(rok) for rok in lata})
    if not lata:
        return "Wybierz lata"
    if len(lata) == 1:
        return str(lata[0])
    if lata == list(range(lata[0], lata[-1] + 1)):
        return f"{lata[0]}–{lata[-1]}"
    return ", ".join(str(rok) for rok in lata)


def przywroc_wszystkie_lata():
    st.session_state.filter_years_top = list(lata_dostepne)


def wyczysc_typ_pozycji():
    st.session_state.filter_type_top = "Wszystkie"


if "filter_years_top" not in st.session_state:
    st.session_state.filter_years_top = list(lata_dostepne)

# Stan filtra jest przechowywany niezależnie od zakładki.
# Przycisk po prawej zawsze pokazuje aktualny wybór lat.
st.markdown(
    """
    <style>
    .stApp .st-key-top_filters {
        border: 1px solid rgba(37,99,235,0.30) !important;
        border-left: 4px solid #2563EB !important;
        background: linear-gradient(105deg, rgba(219,234,254,0.25), rgba(255,255,255,0.09)) !important;
        box-shadow: 0 10px 25px rgba(37,99,235,0.08) !important;
        border-radius: 20px !important;
        padding: 14px 18px 12px !important;
        backdrop-filter: blur(16px);
    }
    .stApp .st-key-top_filters [data-testid="stHorizontalBlock"] {
        align-items: flex-start !important;
    }
    .stApp .filter-field-label {
        min-height: 24px;
        line-height: 24px;
        font-size: 0.88rem;
        font-weight: 800;
        margin: 0 0 7px 0;
        letter-spacing: 0.01em;
    }
    .stApp .filter-legend {
        height: 46px;
        display: flex;
        align-items: center;
        gap: 18px;
        border-radius: 12px;
        border: 1px solid rgba(100,116,139,0.20);
        background: rgba(255,255,255,0.13);
        padding: 0 16px;
        font-size: 0.90rem;
        font-weight: 760;
        white-space: nowrap;
    }
    .stApp .filter-legend .toolbar-key {
        width: 12px; height: 12px; vertical-align: -1px;
    }
    .stApp .st-key-filter_year_popover button {
        height: 46px !important;
        min-height: 46px !important;
        border-radius: 12px !important;
        background: rgba(255,255,255,0.18) !important;
        border: 1px solid rgba(100,116,139,0.27) !important;
        font-weight: 800 !important;
        font-size: 0.98rem !important;
        box-shadow: none !important;
    }
    .stApp .st-key-filter_year_popover button:hover {
        border-color: #3B82F6 !important;
        background: rgba(191,219,254,0.20) !important;
    }
    .stApp .st-key-filter_type_top [data-baseweb="select"] > div {
        min-height: 46px !important;
        border-radius: 12px !important;
        border: 1px solid rgba(100,116,139,0.27) !important;
        background: rgba(255,255,255,0.15) !important;
        box-shadow: none !important;
    }
    /* Przywrócenie prawidłowego wyglądu ikon zamiast kwadratów. */
    .stApp .st-key-top_filters [data-baseweb="select"] svg {
        display: inline-block !important;
        width: 17px !important; height: 17px !important;
        color: inherit !important;
        fill: currentColor !important;
        stroke: currentColor !important;
    }
    .stApp .st-key-top_filters [data-testid="stPopover"] button svg {
        width: 18px !important; height: 18px !important;
    }
    .stApp .filter-empty-state {
        height:46px; border: 1px solid rgba(100,116,139,0.18);
        border-radius:12px; padding: 12px 14px;
        font-weight:650; opacity:0.85;
    }
    /* Precyzyjny chevron CSS zamiast kwadratowego glifu/ikony BaseWeb. */
    .stApp .st-key-filter_type_top [data-baseweb="select"] { position: relative !important; }
    .stApp .st-key-filter_type_top [data-baseweb="select"] > div {
        padding-right: 39px !important;
        background: rgba(225,236,253,.28) !important;
        border-color: rgba(96,125,172,.25) !important;
    }
    .stApp .st-key-filter_type_top [data-baseweb="select"] svg,
    .stApp .st-key-filter_type_top [data-baseweb="select"] [data-baseweb="icon"] {
        display: none !important;
    }
    .stApp .st-key-filter_type_top [data-baseweb="select"]::after {
        content: "";
        position: absolute;
        right: 20px;
        top: 46%;
        width: 9px;
        height: 9px;
        transform: translateY(-50%) rotate(45deg);
        border-right: 2px solid #465B7B;
        border-bottom: 2px solid #465B7B;
        border-radius: 1px;
        pointer-events: none;
        z-index: 4;
    }
    .stApp .st-key-top_filters .filter-empty-state,
    .stApp .st-key-top_filters .filter-legend {
        background: rgba(225,236,253,.28) !important;
        border-color: rgba(96,125,172,.25) !important;
    }
    .stApp .st-key-filter_year_popover button {
        background: rgba(225,236,253,.28) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.container(key="top_filters"):
    # Ten sam układ kolumn w obu zakładkach = wyrównane elementy.
    kol_typ, kol_legenda, kol_lata = st.columns([1.50, 1.15, 1.55], gap="medium")

    with kol_typ:
        st.markdown('<div class="filter-field-label">Typy pozycji budżetowych</div>', unsafe_allow_html=True)
        if st.session_state.current_tab == TAB_2:
            opcje_typow = ["Wszystkie"] + sorted(df_raw["Typ_Pozycji"].unique().tolist())
            wybrany_typ = st.selectbox(
                "Typy pozycji budżetowych", options=opcje_typow,
                label_visibility="collapsed", key="filter_type_top",
            )
        else:
            wybrany_typ = "Wszystkie"
            st.markdown('<div class="filter-empty-state">Wszystkie pozycje</div>', unsafe_allow_html=True)

    with kol_legenda:
        st.markdown('<div class="filter-field-label">Oznaczenia</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="filter-legend">'
            '<span><span class="toolbar-key" style="background:#16A34A"></span> Dochody</span>'
            '<span><span class="toolbar-key" style="background:#DC2626"></span> Wydatki</span>'
            '</div>',
            unsafe_allow_html=True,
        )

    with kol_lata:
        st.markdown('<div class="filter-field-label">Uwzględniane lata</div>', unsafe_allow_html=True)
        with st.container(key="filter_year_popover"):
            with st.popover(f"{opis_zakresu_lat(st.session_state.filter_years_top)}   ⌄", use_container_width=True):
                st.markdown("**Wybierz lata do analizy**")
                st.multiselect(
                    "Lata", options=lata_dostepne,
                    key="filter_years_top", label_visibility="collapsed",
                    placeholder="Wybierz co najmniej jeden rok",
                )
                st.button(
                    "✕ Usuń filtr lat (pokaż wszystkie)",
                    key="reset_years_top",
                    use_container_width=True,
                    on_click=przywroc_wszystkie_lata,
                    help="Przywróć wszystkie dostępne lata",
                )
                st.caption("Aby usunąć pojedynczy rok, kliknij × przy jego nazwie.")

    wybrane_lata = sorted(st.session_state.filter_years_top)
    if not wybrane_lata:
        st.warning("Wybierz co najmniej jeden rok w rozwijanym filtrze lat.")
        st.stop()

wybrane_lata = sorted(wybrane_lata)
df_filtered = df_raw[df_raw["Rok"].isin(wybrane_lata)].copy()
if wybrany_typ != "Wszystkie":
    df_filtered = df_filtered[df_filtered["Typ_Pozycji"] == wybrany_typ].copy()
lata_str = ", ".join(str(y) for y in wybrane_lata)

if st.session_state.current_tab == TAB_1:
    df_lata = df_raw[df_raw["Rok"].isin(wybrane_lata)].copy()
    doch = df_lata[df_lata["Typ_Pozycji"] == "Dochody"]
    wyd = df_lata[df_lata["Typ_Pozycji"] == "Wydatki"]
    d_plan, d_wyk = doch["Plan_mld_PLN"].sum(), doch["Wykonanie_mld_PLN"].sum()
    w_plan, w_wyk = wyd["Plan_mld_PLN"].sum(), wyd["Wykonanie_mld_PLN"].sum()
    wynik_wyk = d_wyk - w_wyk
    pct_d = (d_wyk / d_plan * 100) if d_plan > 0 else 0
    pct_w = (w_wyk / w_plan * 100) if w_plan > 0 else 0
    # Ważone wykonanie planu, zamiast średniej arytmetycznej dwóch odsetków.
    avg_exec = (d_wyk + w_wyk) / (d_plan + w_plan) * 100 if (d_plan + w_plan) else 0.0
    lata_bez_pkb = [int(rok) for rok in wybrane_lata if int(rok) not in PKB_NOMINALNY_MLD]
    pkb_suma = sum(PKB_NOMINALNY_MLD.get(int(rok), 0.0) for rok in wybrane_lata)
    # Dla zakresu lat dzielimy sumę wyników budżetowych przez sumę rocznego PKB.
    # To relacja budżetu państwa, NIE deficyt całego sektora instytucji rządowych i samorządowych.
    wynik_do_pkb = (wynik_wyk / pkb_suma * 100) if pkb_suma > 0 and not lata_bez_pkb else None
    roczny_bilans = (
        df_lata.groupby(["Rok", "Typ_Pozycji"])["Wykonanie_mld_PLN"].sum()
        .unstack(fill_value=0)
    )
    trend_pkb = [
        ((float(roczny_bilans.loc[rok].get("Dochody", 0)) - float(roczny_bilans.loc[rok].get("Wydatki", 0)))
         / PKB_NOMINALNY_MLD[rok] * 100)
        for rok in sorted(int(y) for y in wybrane_lata)
        if rok in PKB_NOMINALNY_MLD and rok in roczny_bilans.index
    ]
    trend = df_lata.groupby(["Rok", "Typ_Pozycji"])[["Plan_mld_PLN", "Wykonanie_mld_PLN"]].sum().reset_index()
    spark_income = trend[trend["Typ_Pozycji"] == "Dochody"]["Wykonanie_mld_PLN"].tolist()
    spark_exp = trend[trend["Typ_Pozycji"] == "Wydatki"]["Wykonanie_mld_PLN"].tolist()
    piv_tmp = trend.pivot(index="Rok", columns="Typ_Pozycji", values="Wykonanie_mld_PLN").fillna(0)
    spark_res = (piv_tmp.get("Dochody", 0) - piv_tmp.get("Wydatki", 0)).tolist()
    # Roczny trend wykonania obu stron budżetu (faktyczne dane z każdego roku).
    roczne_realizacje = (
        df_lata.groupby("Rok")[["Plan_mld_PLN", "Wykonanie_mld_PLN"]].sum().sort_index()
    )
    spark_exec = [
        float(w / p) * 100 if p else 0.0
        for p, w in zip(roczne_realizacje["Plan_mld_PLN"], roczne_realizacje["Wykonanie_mld_PLN"])
    ]
    dt1, dc1 = metric_delta_text(d_wyk, d_plan)
    dt2, dc2 = metric_delta_text(w_wyk, w_plan)
    dt3, dc3 = ("▲ nadwyżka" if wynik_wyk >= 0 else "▼ deficyt", P["pos"] if wynik_wyk >= 0 else P["neg"])
    dt4 = f"Dochody: {pl(pct_d)}% | Wydatki: {pl(pct_w)}%"
    # Najważniejszy wskaźnik — osobny wyróżniony blok z latami i sposobem obliczenia.
    opis_wyniku = ("deficyt: państwo wydało więcej, niż zebrało" if wynik_wyk < 0
                   else "nadwyżka: państwo zebrało więcej, niż wydało")
    st.markdown(
        '<div class="financial-balance">'
        '<div class="balance-title">⚖ Ogólny wynik budżetu państwa</div>'
        '<div class="balance-metrics"><div class="balance-figures">'
        f'<div class="balance-value" style="color:{P["neg"] if wynik_wyk < 0 else P["pos"]}">{pl(wynik_wyk)} mld zł</div>'
        f'<div class="balance-years">Uwzględnione lata: {escape(lata_str)}</div>'
        '</div><div class="balance-trend">'
        '<div class="balance-trend-label">Trend rocznego wyniku budżetu (mld zł)</div>'
        + spark_svg(spark_res, P["neg"] if wynik_wyk < 0 else P["pos"])
        + '</div></div>'
        + f'<div class="balance-desc"><strong>Co to oznacza?</strong> {escape(opis_wyniku)}. '
        f'Wynik obliczamy jako <strong>dochody minus wydatki</strong>: '
        f'{pl(d_wyk)} mld zł − {pl(w_wyk)} mld zł = {pl(wynik_wyk)} mld zł. '
        'Gdy zaznaczysz więcej niż jeden rok, najpierw sumujemy dochody ze wszystkich wybranych lat '
        'i wydatki ze wszystkich tych lat, a następnie odejmujemy wydatki od dochodów. '
        'Nie jest to wynik pojedynczego roku ani średnia roczna.</div></div>',
        unsafe_allow_html=True)

    # Kafelki KPI: jeden, spójny HTML, bez bloków kodu i nadpisywania.
    c1, c2, c3, c4 = st.columns(4, gap="medium")
    with c1:
        st.markdown(kpi_card("Dochody budżetu", f"{pl(d_wyk)} mld zł", dt1, P["pos"], citizen_desc("dochody", d_wyk, d_plan), "↥", "#16A34A", spark_income, kind="income"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Wydatki budżetu", f"{pl(w_wyk)} mld zł", dt2, P["neg"], citizen_desc("wydatki", w_wyk, w_plan), "↧", "#DC2626", spark_exp, kind="spending"), unsafe_allow_html=True)
    with c3:
        if wynik_do_pkb is not None:
            relacja_txt = f"{pl(wynik_do_pkb, 2)}% PKB"
            relacja_podpis = "Deficyt w relacji do PKB" if wynik_wyk < 0 else "Nadwyżka w relacji do PKB"
            relacja_opis = (
                f"W latach {opis_zakresu_lat(wybrane_lata)} suma wyników budżetu państwa "
                f"wyniosła {pl(wynik_wyk)} mld zł, a suma nominalnego PKB {pl(pkb_suma)} mld zł. "
                "Wskaźnik = wynik / suma PKB × 100. Źródło PKB: GUS."
            )
        else:
            relacja_txt = "Brak danych PKB"
            relacja_podpis = "Nie można obliczyć wskaźnika"
            relacja_opis = "Brak nominalnego PKB GUS dla wszystkich wybranych lat."
        st.markdown(
            kpi_card(
                "Wynik budżetu / PKB", relacja_txt, relacja_podpis,
                P["neg"] if wynik_wyk < 0 else P["pos"], relacja_opis,
                "％", "#F59E0B", trend_pkb, kind="gdp-ratio deficit" if wynik_wyk < 0 else "gdp-ratio surplus"
            ),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(kpi_card("Realizacja planu", f"{pl(avg_exec)}%", dt4, P["text"], citizen_desc("wykonanie", avg_exec, avg_exec, extra=avg_exec), "↗", "#7C3AED", spark_exec, kind="execution"), unsafe_allow_html=True)
    st.markdown(f'<div class="card-box" style="margin-top:12px; margin-bottom:14px;"><div class="card-title">🛈 Co oznaczają te dane?</div><div class="card-note">{escape(summary_message(d_wyk, w_wyk, wynik_wyk, pct_d, pct_w))}</div></div>', unsafe_allow_html=True)
    p1, p2 = st.columns(2, gap="medium")
    with p1:
        with st.container(key="panel_income"):
            st.markdown('<div class="card-title">🟢 Struktura dochodów budżetu</div><div class="card-note">Wykres pokazuje, z jakich głównych źródeł pochodzą pieniądze budżetu państwa.</div>', unsafe_allow_html=True)
            fig = donut_chart(df_lata, "Dochody", "Wykonanie_mld_PLN", f"{pl(d_wyk)}\nmld zł")
            if fig is not None:
                show_fig(fig)
    with p2:
        with st.container(key="panel_spending"):
            st.markdown('<div class="card-title">🔴 Wydatki według części budżetowych</div><div class="card-note">Wykres pokazuje, w których częściach budżetu państwa ujęto wydatki (np. ZUS, obronność, obsługa długu). To nie jest pełny podział wydatków całego sektora publicznego.</div>', unsafe_allow_html=True)
            fig = donut_chart(df_lata, "Wydatki", "Wykonanie_mld_PLN", f"{pl(w_wyk)}\nmld zł")
            if fig is not None:
                show_fig(fig)
    if 2025 in wybrane_lata:
        st.caption(
            "Uwaga dotycząca porównywania PIT: od 2025 r. zmieniły się zasady udziału "
            "samorządów we wpływach z PIT. Niższe wpływy PIT w samym budżecie państwa "
            "nie oznaczają analogicznego spadku wpływów podatkowych w całej Polsce. "
            "[Wyjaśnienie MF](https://www.gov.pl/web/finanse/szacunkowe-wykonanie-budzetu-panstwa-w-2025-r)."
        )
    t1, t2 = st.columns(2, gap="medium")
    with t1:
        with st.container(key="panel_trend_budget"):
            st.markdown('<div class="card-title">📈 Trend dochodów i wydatków</div><div class="card-note">Porównanie zmian w czasie pomaga zobaczyć, czy budżet rośnie i jak zmienia się jego skala.</div>', unsafe_allow_html=True)
            show_fig(trend_chart(trend, "Wykonanie", result_mode=False))
    with t2:
        with st.container(key="panel_trend_result"):
            st.markdown('<div class="card-title">🧮 Trend wyniku budżetowego</div><div class="card-note">Jeżeli linia jest poniżej zera, oznacza to deficyt. Powyżej zera widoczna jest nadwyżka.</div>', unsafe_allow_html=True)
            show_fig(trend_chart(trend, "Wykonanie", result_mode=True))
    df_sum = df_lata.groupby(["Rok", "Typ_Pozycji"])[["Plan_mld_PLN", "Wykonanie_mld_PLN", "Odchylenie_mld_PLN"]].sum().reset_index()
    df_sum["% Wykonania"] = df_sum["Wykonanie_mld_PLN"] / df_sum["Plan_mld_PLN"].replace(0, float("nan")) * 100
    with st.container(key="panel_summary_table"):
        st.markdown('<div class="card-title">📋 Zbiorcza tabela bilansu</div>', unsafe_allow_html=True)
        render_table(df_sum, ["Typ_Pozycji", "Rok"], [True, True])
else:
    if df_filtered.empty:
        st.warning("Brak danych spełniających wybrane kryteria filtrowania.")
    else:
        st.markdown('<div class="card-box" style="margin-bottom:14px;"><div class="card-title">🧭 Jak czytać ten widok?</div><div class="card-note">Dochody są rozbite według podatków, a wydatki według części budżetowych. Wartości w podkategoriach zaokrąglono do 0,1 mld zł; „Pozostałe” to różnica do oficjalnych sum MF. Możesz zawężać analizę do wybranych lat i typów pozycji budżetowych.</div></div>', unsafe_allow_html=True)
        col_c1, col_c2 = st.columns(2, gap="medium")
        with col_c1:
            with st.container(key="panel_category_main"):
                st.markdown('<div class="card-title">📊 Struktura kategorii głównych</div><div class="card-note">Im dłuższy słupek, tym większa kwota w danej kategorii.</div>', unsafe_allow_html=True)
                miara_k1 = st.radio("Wskaźnik:", ["Wykonanie", "Plan"], horizontal=True, key="radio_kat1")
                col_mk1 = get_measure_col(miara_k1)
                df_kat = df_filtered.groupby(["Kategoria_Główna", "Typ_Pozycji"])[col_mk1].sum().reset_index()
                df_kat["Etykieta"] = df_kat["Kategoria_Główna"].astype(str) + " (" + df_kat["Typ_Pozycji"] + ")"
                fig = px.bar(df_kat, y="Etykieta", x=col_mk1, color="Typ_Pozycji", orientation="h", color_discrete_map=color_map_typ, labels={col_mk1: f"{miara_k1} (mld zł)", "Etykieta": "", "Typ_Pozycji": "Typ"})
                style_fig(fig, legend_top=True, h=420)
                show_fig(fig)
        with col_c2:
            with st.container(key="panel_category_share"):
                st.markdown('<div class="card-title">🧩 Udział kategorii z podziałem</div><div class="card-note">Wykres kołowy pokazuje udział poszczególnych kategorii w łącznych dochodach lub wydatkach.</div>', unsafe_allow_html=True)
                miara_k2 = st.radio("Wskaźnik: ", ["Wykonanie", "Plan"], horizontal=True, key="radio_kat2")
                col_mk2 = get_measure_col(miara_k2)
                typ_pie = st.segmented_control("Zakres wykresu:", options=["Dochody", "Wydatki"], default="Dochody", key="seg_pie")
                fig_pie = donut_chart(df_filtered, typ_pie, col_mk2, typ_pie)
                if fig_pie is not None:
                    show_fig(fig_pie)
        with st.container(key="panel_category_detail"):
            st.markdown('<div class="card-title">📚 Podział szczegółowy pozycji</div><div class="card-note">Wykres pomaga zidentyfikować najbardziej kosztowne lub najbardziej dochodowe pozycje w budżecie.</div>', unsafe_allow_html=True)
            miara_k3 = st.radio("Wskaźnik:  ", ["Wykonanie", "Plan"], horizontal=True, key="radio_kat3")
            col_mk3 = get_measure_col(miara_k3)
            df_sz = df_filtered.groupby(["Nazwa_Kategorii_Szczegółowa", "Typ_Pozycji"])[["Plan_mld_PLN", "Wykonanie_mld_PLN"]].sum().reset_index().sort_values(["Typ_Pozycji", col_mk3], ascending=[True, False])
            fig = px.bar(df_sz, x="Nazwa_Kategorii_Szczegółowa", y=col_mk3, color="Typ_Pozycji", color_discrete_map=color_map_typ, labels={col_mk3: f"{miara_k3} (mld zł)", "Nazwa_Kategorii_Szczegółowa": "", "Typ_Pozycji": "Typ"})
            fig.update_xaxes(categoryorder="array", categoryarray=df_sz["Nazwa_Kategorii_Szczegółowa"].tolist(), tickangle=-45)
            style_fig(fig, legend_top=True, h=360)
            show_fig(fig)
        with st.container(key="panel_detail_table"):
            st.markdown('<div class="card-title">📋 Zestawienie danych</div>', unsafe_allow_html=True)
            cols_to_show = ["Rok", "Typ_Pozycji", "Kategoria_Główna", "Nazwa_Kategorii_Szczegółowa", "Część_Budżetowa", "Plan_mld_PLN", "Wykonanie_mld_PLN", "Procent_Wykonania", "Odchylenie_mld_PLN"]
            render_table(df_filtered[[c for c in cols_to_show if c in df_filtered.columns]].copy(), ["Typ_Pozycji", "Wykonanie_mld_PLN"], [True, False])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_filtered.to_excel(writer, index=False, sheet_name="Dane_Przefiltrowane")
        st.download_button(label="Pobierz przefiltrowane dane (.xlsx)", data=output.getvalue(), file_name="Raport_Finansowy_Dane.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ---------------------------------------------------------
# 6. JAWNE ŹRÓDŁA I METODOLOGIA
# ---------------------------------------------------------
st.caption(
    "Dane rzeczywiste (wykonanie) za lata 2022–2025: Ministerstwo Finansów. "
    "Sumy dochodów i wydatków pochodzą z rocznych sprawozdań MF; podkategorie "
    "podatkowe i największe części budżetowe — z prezentacji danych MF/dane.gov.pl "
    "w serwisie budzetpanstwa.pl (zaokrąglenie do 0,1 mld zł). "
    "Ostatni rok: 2025, wykonanie roczne; brak sztucznie prognozowanych liczb."
)
with st.expander("Źródła danych i sposób obliczeń"):
    st.markdown("**Wykonanie budżetu państwa — roczne sprawozdania Ministerstwa Finansów:**")
    for rok, url in SOURCES_MF.items():
        st.markdown(f"- [{rok}: roczne sprawozdanie MF]({url})")
    st.markdown("**Szczegółowe dochody i wydatki (zestawienia na podstawie danych MF):**")
    for rok, urls in SOURCES_DETAIL.items():
        st.markdown(f"- {rok}: [dochody]({urls['dochody']}) · [wydatki według części budżetowych]({urls['wydatki']})")
    st.markdown(
        "- **Dochody / wydatki / deficyt:** roczne kwoty wykonane budżetu państwa (nie całego sektora finansów publicznych).\n"
        "- **Wynik budżetu:** dochody minus wydatki; przy kilku latach sumowane są kwoty z wybranych lat.\n"
        "- **Wynik / PKB:** suma wyników budżetu / suma nominalnego PKB GUS z wybranych lat × 100.\n"
        "- **Plan:** wartości ustawowe/po nowelizacji prezentowane z dokładnością do 0,1 mld zł.\n"
        "- **Podkategorie:** opublikowane kwoty są zaokrąglone do 0,1 mld zł. „Pozostałe” "
        "oznacza pozostałe, niewymienione pozycje oraz nieznaczne różnice wynikające z zaokrągleń; "
        "nie jest to prognoza ani oddzielna część budżetu.\n"
        "- **Wydatki:** wykres pokazuje największe *części budżetowe* (np. część 73 ZUS), "
        "a nie funkcjonalne działy klasyfikacji."
    )
    st.markdown(
        "PKB nominalny: [GUS, szacunek zaktualizowany 6.10.2026](https://publikacje.new.stat.gov.pl/portal-publikacje/produkt-krajowy-brutto-zaktualizowany-szacunek-za-2025-r)."
    )
