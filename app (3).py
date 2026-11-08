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
        europe_fill, europe_stroke = "none", "rgba(219,234,254,0.065)"
        poland_fill, poland_stroke = "rgba(248,113,113,0.035)", "rgba(252,165,165,0.10)"
    else:
        europe_fill, europe_stroke = "none", "rgba(30,58,95,0.065)"
        poland_fill, poland_stroke = "rgba(220,38,38,0.035)", "rgba(185,28,28,0.11)"
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1176 1064" preserveAspectRatio="none">'
        f'<path d="{countries}" fill="{europe_fill}" stroke="{europe_stroke}" '
        'stroke-width="1.1" stroke-linejoin="round" fill-rule="evenodd"/>'
        f'<path d="{poland}" fill="{poland_fill}" stroke="{poland_stroke}" '
        'stroke-width="1.6" stroke-linejoin="round" fill-rule="evenodd"/>'
        '</svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def sidebar_panorama_uri():
    # Panorama wydzielona z załączonego przez użytkownika zrzutu; działa offline.
    return "data:image/jpeg;base64,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"


BASE_CSS = Template("""
<style>
:root { --sidebar-photo: url('$sidebar_photo'); }
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
        var(--sidebar-photo) bottom center / cover no-repeat,
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
/* Zdjęcie sidebaru, prawdziwa Warszawa, a nie grafika wygenerowana */
section[data-testid="stSidebar"] > div {
    background: linear-gradient(180deg, rgba(24,76,163,0.92), rgba(31,89,166,0.65) 47%, rgba(14,44,84,.28)),
                var(--sidebar-photo) center bottom / cover no-repeat, $side !important;
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
/* Pasek boczny zgodny z referencyjnym zrzutem: niebieski gradient + panorama */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #3775C6 0%, #6D9BD6 61%, #B2C9E8 100%) !important;
}
section[data-testid="stSidebar"] > div {
    background: linear-gradient(180deg, rgba(33,98,185,.82) 0%, rgba(64,117,193,.69) 40%, rgba(89,142,207,.31) 62%, rgba(255,255,255,.00) 79%),
                var(--sidebar-photo) bottom center / 100% auto no-repeat,
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

/* Korekty wizualne sidebaru: fotografia bez nadmiernego przybliżenia, przejrzysta nawigacja. */
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
        var(--sidebar-photo),
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
</style>
""")

st.markdown(BASE_CSS.substitute(**P, map=europe_watermark_uri(st.session_state.theme), sidebar_photo=sidebar_panorama_uri(), active_tab="btn_podsumowanie" if st.session_state.current_tab == TAB_1 else "btn_kategorie", active_theme="theme_light" if st.session_state.theme == "light" else "theme_dark"), unsafe_allow_html=True)

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
      <div class="splash-title"><span class="b-light">Polski</span> Obserwator <span class="b-red">Finansowy</span></div>
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
        f'<div class="balance-value" style="color:{P["neg"] if wynik_wyk < 0 else P["pos"]}">{pl(wynik_wyk)} mld zł</div>'
        f'<div class="balance-years">Uwzględnione lata: {escape(lata_str)}</div>'
        f'<div class="balance-desc"><strong>Co to oznacza?</strong> {escape(opis_wyniku)}. '
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
