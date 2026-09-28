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


def poland_outline_uri(stroke):
    """Sam delikatny kontur Polski (bez wypełnienia), wbudowany SVG."""
    lon0, lon1, lat0, lat1 = 13.8, 24.4, 48.9, 55.0
    k, sc = math.cos(math.radians(52)), 100
    pts = [((lo - lon0) * k * sc, (lat1 - la) * sc) for lo, la in POLAND]
    w, h = (lon1 - lon0) * k * sc, (lat1 - lat0) * sc
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"
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
.block-container { padding-top: 3.2rem !important; max-width: 1500px; }

/* Panel boczny */
section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div { background: $side !important; }
section[data-testid="stSidebar"] { border-right: 1px solid $border !important; }

/* Teksty */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp label, .stApp li,
.stApp [data-testid="stCaptionContainer"] { color: $text !important; }

/* Baner */
.banner {
    display: flex; align-items: center; gap: 18px;
    background: $card; border: 1px solid $border; border-bottom: 4px solid #DC2626;
    border-radius: 14px; padding: 18px 26px; margin-bottom: 18px; box-shadow: $shadow;
}
.banner .logo {
    width: 54px; height: 54px; border-radius: 12px; flex: none;
    background: linear-gradient(135deg, #EF4444, #B91C1C);
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 4px 14px rgba(220,38,38,0.35);
}
.banner .b-title { font-size: 1.6rem; font-weight: 800; letter-spacing: 0.2px; color: $text; line-height: 1.2; }
.banner .b-sub { font-size: 0.92rem; color: $muted; margin-top: 2px; }
.banner .b-tag {
    margin-left: auto; font-size: 0.78rem; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; color: #DC2626; border: 1px solid #DC2626;
    border-radius: 999px; padding: 4px 12px;
}

/* Kafelki KPI - jednakowa wysokość */
.kpi {
    background: $card; border: 1px solid $border; border-radius: 12px;
    padding: 14px 16px; height: 128px; box-shadow: $shadow;
    display: flex; flex-direction: column; justify-content: center; gap: 4px;
    overflow: hidden;
}
.kpi .k-label { font-size: 0.74rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; color: $muted; }
.kpi .k-value { font-size: 1.55rem; font-weight: 800; color: $text; line-height: 1.15; white-space: nowrap; }
.kpi .k-sub { font-size: 0.82rem; color: $muted; }

/* Panele z wizualizacjami - bardzo lekki, półprzezroczysty szary */
[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
    background: $panel !important; border: 1px solid $border !important;
    border-radius: 12px !important; box-shadow: $shadow !important;
}
.sec-title { font-size: 1.05rem; font-weight: 700; color: $text; margin: 2px 0 4px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sec-plain { font-size: 1.1rem; font-weight: 700; color: $text; margin: 18px 0 8px 0; }

/* Każda wizualizacja: lekka ramka + delikatne, transparentne wypełnienie (jak kafelki KPI) */
[data-testid="stPlotlyChart"] {
    background: $card !important; border: 1px solid $border !important;
    border-radius: 12px !important; box-shadow: $shadow !important;
    padding: 8px 6px 4px 6px !important; box-sizing: border-box;
}

/* Legenda obok wykresu udziału */
.legend-box {
    background: $card; border: 1px solid $border; border-radius: 12px; box-shadow: $shadow;
    padding: 12px 14px; margin-top: 8px;
}
.legend-box .lg-title { font-size: 0.74rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: $muted; margin-bottom: 8px; }
.legend-box .lg-row { display: flex; align-items: center; gap: 8px; font-size: 0.92rem; font-weight: 600; color: $text; margin: 6px 0; }
.legend-box .lg-dot { width: 14px; height: 14px; border-radius: 3px; flex: none; }
.legend-box .lg-note { font-size: 0.78rem; color: $muted; margin-top: 10px; line-height: 1.3; }

/* Objaśnienie raportu w banerze */
.banner .b-desc { font-size: 0.84rem; color: $muted; margin-top: 8px; line-height: 1.45; max-width: 980px; }
.banner .b-desc b { color: $text; }

/* Pola formularzy */
.stApp [data-baseweb="select"] > div, .stApp [data-baseweb="input"],
.stApp [data-baseweb="input"] input, .stApp [data-baseweb="base-input"],
.stApp [data-testid="stFileUploaderDropzone"] { background: $inp !important; border-color: $border !important; }
.stApp [data-baseweb="select"] *, .stApp [data-testid="stFileUploaderDropzone"] * { color: $text !important; }
.stApp [data-baseweb="select"] span[data-baseweb="tag"] { background: rgba(220,38,38,0.18) !important; }
[data-baseweb="popover"] ul, [data-baseweb="popover"] li, [data-baseweb="menu"] { background: $inp !important; color: $text !important; }

/* Zwykłe przyciski */
.stApp button[data-testid^="stBaseButton"] { background: $inp !important; border: 1px solid $border !important; }
.stApp button[data-testid^="stBaseButton"] p { color: $text !important; }

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
</style>
""")
btn = 'button[data-testid^="stBaseButton"]'
st.markdown(
    NAV_CSS.substitute(
        all_btn=_sel(NAV_KEYS, btn), all_p=_sel(NAV_KEYS, "button p"),
        act_btn=_sel(active_keys, btn), act_p=_sel(active_keys, "button p"),
        inact_btn=_sel(inactive_keys, btn), inact_p=_sel(inactive_keys, "button p"),
        inact_hover=_sel(inactive_keys, btn + ":hover"),
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
CHART_H = 400
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


def style_fig(fig, legend_top=False):
    fig.update_layout(
        template=P["template"], height=CHART_H,
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
def load_data(uploaded_file=None):
    file_path = uploaded_file if uploaded_file is not None else "Model_Budzet_Panstwa_Analiza.xlsx"
    try:
        df = pd.read_excel(file_path, sheet_name="Dane_Szczegolowe")
    except Exception as e:
        st.error(f"Błąd podczas wczytywania danych z pliku: {e}")
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
        st.button("Jasny", key="theme_light", use_container_width=True,
                  on_click=set_theme, args=("light",))
    with tc2:
        st.button("Ciemny", key="theme_dark", use_container_width=True,
                  on_click=set_theme, args=("dark",))

st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.header("Panel filtrowania")

uploaded_file = st.sidebar.file_uploader("Wgraj własny plik Excel (.xlsx)", type=["xlsx"])
df_raw = load_data(uploaded_file)

# ---------------------------------------------------------
# 7. BANER
# ---------------------------------------------------------
LOGO = (
    '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<rect x="3" y="12" width="4" height="9" rx="1" fill="#FFFFFF"/>'
    '<rect x="10" y="7" width="4" height="14" rx="1" fill="#FFFFFF"/>'
    '<rect x="17" y="3" width="4" height="18" rx="1" fill="#FFFFFF"/></svg>'
)
st.markdown(
    f'<div class="banner"><div class="logo">{LOGO}</div>'
    '<div style="min-width:0;"><div class="b-title">Monitoring Budżetu</div>'
    '<div class="b-sub">Raport wykonania budżetu – analiza wieloletnia planu i wykonania</div>'
    '<div class="b-desc">Raport porównuje <b>plan</b> z <b>wykonaniem</b> dochodów i wydatków budżetu w ujęciu '
    'wieloletnim (wartości w mld PLN). <b>Zielony</b> oznacza dochody, <b>czerwony</b> – wydatki; '
    'intensywność koloru rośnie wraz z wartością. <b>Wynik budżetowy</b> = dochody − wydatki '
    '(nadwyżka lub deficyt), a <b>% wykonania</b> = wykonanie / plan. Zakładka „Podsumowanie budżetu” '
    'pokazuje bilans i trendy, a „Budżet w kategoriach” – strukturę i szczegółowy podział pozycji. '
    'Lata i typ pozycji wybierzesz w panelu bocznym.</div></div>'
    '<div class="b-tag">Raport analityczny</div></div>',
    unsafe_allow_html=True,
)

if df_raw.empty:
    st.info("Upewnij się, że plik `Model_Budzet_Panstwa_Analiza.xlsx` jest w katalogu roboczym, lub wgraj plik w panelu bocznym.")
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

st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

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

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

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
            with st.container(border=True):
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
                style_fig(fig, legend_top=True)
                show_fig(fig)

        # --- Udział kategorii z podziałem (sunburst: typ -> kategoria) ---
        with col_c2:
            with st.container(border=True):
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
                    style_fig(fig)
                    fig.update_layout(showlegend=False)

                    legend_rows = "".join(
                        f'<div class="lg-row"><span class="lg-dot" style="background:'
                        f'{rgba(TYPE_RGB.get(t, (100, 116, 139)), MAX_ALPHA)};"></span>{escape(str(t))}</div>'
                        for t in sorted(df_u["Typ_Pozycji"].unique())
                    )
                    sb_chart, sb_legend = st.columns([4, 1], gap="small")
                    with sb_chart:
                        show_fig(fig)
                    with sb_legend:
                        st.markdown(
                            '<div class="legend-box"><div class="lg-title">Legenda</div>'
                            + legend_rows
                            + '<div class="lg-note">Ciemniejszy odcień = większy udział kategorii w danym typie.</div></div>',
                            unsafe_allow_html=True,
                        )

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

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
            fig.update_layout(height=460)
            show_fig(fig)

        # --- Tabela ---
        st.markdown('<div class="sec-plain">Zestawienie danych</div>', unsafe_allow_html=True)
        cols_to_show = ["Rok", "Typ_Pozycji", "Kategoria_Główna", "Nazwa_Kategorii_Szczegółowa", "Część_Budżetowa",
                        "Plan_mld_PLN", "Wykonanie_mld_PLN", "Procent_Wykonania", "Odchylenie_mld_PLN"]
        cols_present = [c for c in cols_to_show if c in df_filtered.columns]
        render_table(df_filtered[cols_present].copy(), ["Typ_Pozycji", "Wykonanie_mld_PLN"], [True, False])

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_filtered.to_excel(writer, index=False, sheet_name="Dane_Przefiltrowane")
        st.download_button(
            label="Pobierz przefiltrowane dane (.xlsx)",
            data=output.getvalue(),
            file_name="Raport_Finansowy_Dane.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
