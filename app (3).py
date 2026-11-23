# -*- coding: utf-8 -*-
# Polski Obserwator Budżetowy 7.0 — kompletna aplikacja w jednym pliku Python.
# Uruchom: streamlit run Polski_Obserwator_Budzetowy_7_0_JEDEN_PLIK.py
# Biblioteki (instalacja jednorazowa):
# pip install "streamlit>=1.49,<2" "pandas>=2.2,<3" "numpy>=1.26,<3" "plotly>=5.23,<7" "requests>=2.31,<3" "openpyxl>=3.1,<4"
# Nie potrzeba dodatkowych plików .py, .csv ani .json.
# Wideo jest zdalne (oficjalne osadzenia YouTube i Pexels); COFOG przez API Eurostatu.

import base64
import io
import math
import zlib
import json
import secrets
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import requests
from html import escape
from string import Template

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Losowa czołówka filmowa (nie wymaga żadnych plików assetów).
# Łódź i Warszawa: oficjalnie osadzone filmy lotnicze ich autorów (YouTube).
# Warszawa: szeroka panorama miasta z Varso Tower i PKiN; rejon Ronda ONZ.
# Łódź: prawdziwe lotnicze ujęcia zabudowy centrum; nie używamy już kadru z ulicy.
# Kraków: oryginalny film lotniczy udostępniony przez Pexels.
# Uwaga: odtwarzanie filmów wymaga internetu i zgody przeglądarki na osadzony odtwarzacz.
INTRO_MOVIES = [
    {
        "city": "Warszawa", "location": "Śródmieście · Varso · PKiN · okolice Ronda ONZ",
        "provider": "youtube", "youtube_id": "Q0pEewnkz5Y", "start": 8,
        "poster": "https://i.ytimg.com/vi/Q0pEewnkz5Y/hqdefault.jpg",
        "source": "https://www.youtube.com/watch?v=Q0pEewnkz5Y",
        "credit": "POLAND ON AIR · Margas & Łogusz / YouTube",
    },
    {
        "city": "Łódź", "location": "Śródmieście · centrum z lotu ptaka",
        "provider": "youtube", "youtube_id": "3N2iQiH6LTg", "start": 5,
        "poster": "https://upload.wikimedia.org/wikipedia/commons/7/76/Aerial_photo%2C_%C5%81%C3%B3d%C5%BA_Fabryczna_station_and_City_Gate_2019.jpg",
        "poster_credit": "Zorro2212 / Wikimedia Commons (CC BY-SA)",
        "source": "https://www.youtube.com/watch?v=3N2iQiH6LTg",
        "credit": "Łódź | Lodz | Poland · Aerial Video 4K / YouTube",
    },
    {
        "city": "Kraków", "location": "Śródmieście · widok z drona",
        "provider": "mp4",
        "video": "https://videos.pexels.com/video-files/40494968/17305640_3840_2160_30fps.mp4",
        "poster": "https://images.pexels.com/videos/40494968/krakow-40494968.jpeg?auto=compress&dpr=1&h=750&w=1260",
        "source": "https://www.pexels.com/video/stunning-aerial-view-of-krakow-cityscape-40494968/",
        "credit": "Samuel Burai / Pexels",
    },
]

def intro_pick_city():
    if 'intro_city_index_v6' not in st.session_state:
        st.session_state['intro_city_index_v6'] = secrets.randbelow(len(INTRO_MOVIES))
    item = INTRO_MOVIES[st.session_state['intro_city_index_v6']].copy()
    return item

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
    initial_sidebar_state="collapsed",
)


# =============================================================
# MODUŁ WBUDOWANY 1/2 — SYMULATOR BUDŻETOWY
# Zintegrowany bez zewnętrznych importów Python.
# Nazwy zostały poprzedzone prefiksem sim_ w celu uniknięcia kolizji.
# =============================================================
sim_STATE_BUDGET_SOURCE = 'https://www.gov.pl/web/finanse/sprawozdanie-roczne-za-2025-rok'
sim_PROGRAM_SOURCE = 'https://www.sejm.gov.pl/sejm10.nsf/biuletyn.xsp?documentId=D9C4C95F0E2C8C89C1258E27003FC9DA'
sim_FAMILY_SOURCE = 'https://budzetpanstwa.pl/wydatki/800-plus'
sim_PKW_SOURCE = 'https://sejmsenat2023.pkw.gov.pl/sejmsenat2023/pl'
sim_ZUS_PROGRAMS = [('800plus', 'Świadczenie wychowawcze 800+', 62.9, 'Rodziny z dziećmi', sim_FAMILY_SOURCE, 'część 73, rozdział 85501 — wykonanie państwowe, nie całkowita obsługa JST'), ('senior_extra', '13. i 14. emerytura oraz Mama+ — część ZUS', 26.8, 'Seniorzy i emeryci', sim_PROGRAM_SOURCE, '26,8 mld zł jest częścią kwoty 29,7 mld zł wszystkich wypłat w informacji sejmowej'), ('support', 'Świadczenie wspierające', 8.8, 'Osoby z niepełnosprawnościami', sim_PROGRAM_SOURCE, 'szacunek raportowany w komisji sejmowej; zakres instytucjonalny może różnić się od rozdziału'), ('active_parent', 'Aktywny rodzic', 6.2, 'Rodzice małych dzieci', sim_PROGRAM_SOURCE, 'program 2025'), ('widow', 'Renta wdowia — część ZUS', 3.5, 'Wdowy i wdowcy', sim_PROGRAM_SOURCE, 'tylko część ZUS (całkowita kwota 3,8 mld zł)'), ('maternity', 'Zasiłki macierzyńskie i opiekuńcze', 13.0, 'Rodziny z dziećmi', sim_PROGRAM_SOURCE, 'program 2025'), ('supplement', 'Świadczenie uzupełniające — niezdolność do samodzielnej egzystencji', 2.1, 'Osoby wymagające wsparcia', sim_PROGRAM_SOURCE, 'program 2025'), ('school_start', 'Dobry Start (300+)', 1.4, 'Rodziny z dziećmi', sim_PROGRAM_SOURCE, 'program 2025'), ('parent_contrib', 'Składki za osoby na urlopach rodzicielskich', 4.2, 'Rodzice na urlopach', sim_PROGRAM_SOURCE, 'składki ubezpieczeniowe finansowane przez państwo')]
sim_PARTS = [('29', 'Obrona narodowa — część 29', 'Obrona i bezpieczeństwo'), ('79', 'Obsługa długu SP — część 79', 'Posiadacze długu / płatnicy podatków'), ('82', 'Subwencje ogólne JST — część 82', 'Jednostki samorządu'), ('85', 'Budżety wojewodów — część 85', 'Usługi regionalne'), ('42', 'Sprawy wewnętrzne — część 42', 'Bezpieczeństwo publiczne'), ('46', 'Zdrowie — część 46', 'Użytkownicy ochrony zdrowia')]
sim_EXTRA_PROGRAMS = [('social_help', 'Pomoc społeczna — ujęcie komisji', 8.2, 'Osoby korzystające z pomocy', sim_PROGRAM_SOURCE), ('nursery', 'Opieka nad dziećmi do 3 lat', 0.526, 'Rodzice małych dzieci', sim_PROGRAM_SOURCE), ('for_life', 'Program „Za życiem”', 0.164, 'Rodziny objęte wsparciem', sim_PROGRAM_SOURCE), ('big_family', 'Karta Dużej Rodziny', 0.0083, 'Rodziny wielodzietne', sim_PROGRAM_SOURCE), ('disability_cert', 'Orzekanie o niepełnosprawności i dokumenty', 0.524, 'Osoby z niepełnosprawnościami', sim_PROGRAM_SOURCE)]

def sim_fmt(x: float, d: int=2) -> str:
    return f'{x:,.{d}f}'.replace(',', '#').replace('.', ',').replace('#', ' ')

def sim_calculate(base_income: float, base_spending: float, programs: list[dict], revenues: list[dict], extra_spending: float=0.0) -> dict:
    """Czysta logika: wartości referencyjne programu są w bazie, sumujemy Δ."""
    spending_delta = sum((p['scenariusz'] - p['baza'] for p in programs)) + extra_spending
    revenue_delta = sum((r['scenariusz'] - r['baza'] for r in revenues))
    new_income = base_income + revenue_delta
    new_spend = base_spending + spending_delta
    return {'dochody': new_income, 'wydatki': new_spend, 'wynik': new_income - new_spend, 'wynik_baza': base_income - base_spending, 'delta_wyniku': revenue_delta - spending_delta, 'delta_dochodow': revenue_delta, 'delta_wydatkow': spending_delta}

def sim__control(entry_id: str, label: str, base: float, stakeholder: str, source: str, details: str='', *, step=5, max_percent=200) -> dict:
    c1, c2 = st.columns([3.2, 1], vertical_alignment='center')
    with c1:
        factor = st.slider(label, 0, max_percent, 100, step=step, key='game_' + entry_id, help=details or f'Rzeczywista wartość referencyjna: {sim_fmt(base, 3)} mld zł. Zmiana procentowa jest scenariuszem, nie prognozą.')
    new = round(base * factor / 100, 6)
    with c2:
        st.markdown(f'**{sim_fmt(new, 3)} mld zł**')
        st.caption(f'Baza {sim_fmt(base, 3)} · {factor}%')
    return {'id': entry_id, 'pozycja': label, 'baza': base, 'scenariusz': new, 'delta': new - base, 'interesariusze': stakeholder, 'źródło': source, 'objaśnienia': details, 'zmiana_proc': factor}

def sim_waterfall(p: dict, palette: dict):
    fig = go.Figure(go.Waterfall(x=['Wynik budżetu 2025', 'Zmiana dochodów', 'Zmiana wydatków (minus)', 'Wynik scenariusza'], measure=['absolute', 'relative', 'relative', 'total'], y=[p['wynik_baza'], p['delta_dochodow'], -p['delta_wydatkow'], 0], text=[sim_fmt(p['wynik_baza']), sim_fmt(p['delta_dochodow']), sim_fmt(-p['delta_wydatkow']), sim_fmt(p['wynik'])], textposition='outside', connector={'line': {'color': palette['muted']}}, increasing={'marker': {'color': '#10B981'}}, decreasing={'marker': {'color': '#FB7185'}}, totals={'marker': {'color': '#6478EF'}}))
    fig.update_layout(template=palette['template'], height=440, showlegend=False, margin=dict(l=6, r=9, t=25, b=15), yaxis_title='mld zł', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

# =============================================================
# GRA 5.0 — ZAPROJEKTUJ BUDŻET
# Proces prowadzony w 4 krokach. W modelu 14 jawnych parametrów:
# 10 wydatkowych (w tym dwa dla 800+) i 4 dochodowe.
# Żadna kwota nie jest dopisywana do bazy po raz drugi.
# =============================================================
def sim_game_defaults():
    return {
        'game5_800_amount': 800,
        'game5_800_coverage': 100,
        'game5_senior': 100,
        'game5_disability': 100,
        'game5_active_parent': 100,
        'game5_defence': 100,
        'game5_health': 100,
        'game5_local': 100,
        'game5_internal': 100,
        'game5_province': 100,
        'game5_VAT': 23,
        'game5_PIT': 12,
        'game5_CIT': 19,
        'game5_Akcyza': 0,
    }


def sim_game_reset():
    # Wywoływane jako callback PRZED renderowaniem widżetów, nie w środku.
    st.session_state['game5_memory'] = sim_game_defaults().copy()
    st.session_state['game5_config'] = {
        'goal': 'Zmniejszyć deficyt',
        'constraint': 'Nie pogarszaj wyniku budżetu 2025',
    }
    for k in list(st.session_state):
        if k.startswith('game5_ui_'):
            del st.session_state[k]
    st.session_state['game5_step'] = 0
    st.session_state['game5_conditions'] = False
    st.session_state['game5_method'] = False


def sim_game_sync(key):
    # "game5_ui_*" to tymczasowe wartości widżetów Streamlit.
    # Prawdziwa pamięć modelu jest oddzielna i nie znika między krokami.
    st.session_state.setdefault('game5_memory', sim_game_defaults().copy())
    st.session_state['game5_memory'][key] = st.session_state['game5_ui_' + key]


def sim_game_sync_config(key):
    st.session_state.setdefault('game5_config', {})
    st.session_state['game5_config'][key] = st.session_state['game5_ui_' + key]


def sim_game_value(key):
    return float(st.session_state.get('game5_memory', {}).get(key, sim_game_defaults()[key]))


def sim_game_state(annual, spending_parts, incomes):
    """Czysty rachunek różnicowy, niezależny od aktywnego kroku formularza."""
    income = float(annual['income_actual'])
    spend = float(annual['spend_actual'])
    part73 = float(spending_parts['73'][1])
    other_parts_sum = sum(float(v[1]) for k, v in spending_parts.items() if k != '73')
    assert part73 >= 62.9 + 26.8 + 8.8 + 6.2, 'Niespójna baza części 73.'
    assert spend >= part73 + other_parts_sum, 'Niespójne części budżetowe.'

    def item(key, label, base, group, kind, note, source):
        factor = sim_game_value('game5_' + key) / 100
        new = round(base * factor, 7)
        return {'id': key, 'pozycja': label, 'baza': base, 'scenariusz': new,
                'delta': new - base, 'interesariusze': group, 'typ': kind,
                'objaśnienia': note, 'źródło': source}

    # Kwota programu 800+ i 3 inne wyróżnione programy stanowią podpozycje
    # części 73; pozostała część 73 jest stała (nie jest osobną dźwignią).
    new_800 = round(62.9 * (sim_game_value('game5_800_amount') / 800)
                    * (sim_game_value('game5_800_coverage') / 100), 7)
    programs = [{'id': '800plus', 'pozycja': 'Świadczenie wychowawcze 800+',
                 'baza': 62.9, 'scenariusz': new_800, 'delta': new_800 - 62.9,
                 'interesariusze': 'Rodziny pobierające świadczenie',
                 'typ': 'Wydatki', 'źródło': sim_FAMILY_SOURCE,
                 'objaśnienia': 'Mechaniczne proporcjonalne przeliczenie kwoty świadczenia i zakresu wypłat.'}]
    for key, label, base, group in [
        ('senior', '13. i 14. emerytura i Mama+ (część ZUS)', 26.8, 'Emeryci i seniorzy'),
        ('disability', 'Świadczenie wspierające', 8.8, 'Osoby z niepełnosprawnościami'),
        ('active_parent', 'Aktywny rodzic', 6.2, 'Rodzice małych dzieci'),
    ]:
        programs.append(item(key, label, base, group, 'Wydatki',
                             'Uproszczona zmiana finansowania programu, bez skutków wtórnych.', sim_PROGRAM_SOURCE))
    for key, part, label, group in [
        ('defence', '29', 'Obrona narodowa — część 29', 'Sektor obronności'),
        ('health', '46', 'Ochrona zdrowia — część 46', 'Pacjenci i świadczeniodawcy'),
        ('local', '82', 'Subwencje ogólne JST — część 82', 'Samorządy i użytkownicy usług'),
        ('internal', '42', 'Sprawy wewnętrzne — część 42', 'Usługi publiczne i bezpieczeństwo'),
        ('province', '85', 'Budżety wojewodów — część 85', 'Usługi administracji terenowej'),
    ]:
        programs.append(item(key, label, float(spending_parts[part][1]), group,
                             'Wydatki', 'Wyłącznie wskazana część budżetowa; nie cała dziedzina COFOG.',
                             sim_STATE_BUDGET_SOURCE))
    # Podatki: stawki referencyjne 2025, wyłącznie liniowa statyka.
    # Udziały 60/55/75/80% są *założeniami modelu*, nie ustaleniami MF.
    # Nie wszystkie dochody VAT/PIT/CIT podlegają zmienianym stawkom.
    tax_defs = (
        ('VAT', 'VAT · stawka podstawowa', 23, 0.60, 'Konsumenci i przedsiębiorstwa',
         'Stawka podstawowa 23%; stawki obniżone 8% i 5% pozostają bez zmian.'),
        ('PIT', 'PIT · pierwszy próg skali', 12, 0.55, 'Podatnicy PIT według skali',
         'Zmiana stawki pierwszego progu skali PIT; drugi próg 32% i ulgi bez zmian.'),
        ('CIT', 'CIT · stawka podstawowa', 19, 0.75, 'Spółki płacące CIT',
         'Zmiana podstawowej stawki 19%; preferencyjna 9% bez zmian.'),
        ('Akcyza', 'Akcyza · zmiana stawek wyrobów', 0, 0.80, 'Konsumenci wyrobów akcyzowych',
         'Nie istnieje jedna stawka akcyzy; suwak oznacza proporcjonalną zmianę zestawu stawek.'),
    )
    revenues = []
    for key, label, reference, affected_fraction, group, explanation in tax_defs:
        receipt = float(incomes[key][1])
        chosen = sim_game_value('game5_' + key)
        if key == 'Akcyza':
            multiplier = 1.0 + (chosen / 100.0) * affected_fraction
            change_txt = f'{chosen:+.0f}% względem taryf bazowych'
        else:
            multiplier = 1.0 + (chosen - reference) / reference * affected_fraction
            change_txt = f'{reference:.0f}% → {chosen:.0f}% ({chosen-reference:+.0f} pp)'
        new_receipt = max(0.0, round(receipt * multiplier, 7))
        revenues.append({'id': key, 'pozycja': label, 'baza': receipt,
            'scenariusz': new_receipt, 'delta': new_receipt - receipt,
            'interesariusze': group, 'typ': 'Dochody', 'źródło': 'https://podatki.gov.pl',
            'objaśnienia': explanation + f' Przyjęto {affected_fraction*100:.0f}% dochodów reagujących liniowo; bez zmiany bazy i zachowań.',
            'parametr_baza': reference, 'parametr_scenariusz': chosen,
            'parametr_opis': change_txt, 'udzial_modelu': affected_fraction})
    result = sim_calculate(income, spend, programs, revenues)
    # Obliczenie wpływu każdej dźwigni na wynik: dodatni wynik -> mniejszy deficyt.
    for p in programs:
        p['wplyw_na_wynik'] = -p['delta']
    for r in revenues:
        r['wplyw_na_wynik'] = r['delta']
    return result, programs, revenues


def sim_game_lever(key, label, base, *, min_val=60, max_val=150, step=5, helptext=''):
    """Kontrolka pokazuje stopę finansowania oraz kwoty przed/po i zmianę."""
    col_left, col_right = st.columns([4, 1.65], gap='medium', vertical_alignment='center')
    base_pct = int(sim_game_value('game5_' + key))
    with col_left:
        st.slider(label + ' · % kwoty bazowej', min_val, max_val, base_pct, step=step,
                  key='game5_ui_game5_' + key, on_change=sim_game_sync, args=('game5_' + key,),
                  help=helptext or '100% = wykonanie 2025. Przykład: 110% to 10% więcej środków.')
    factor = sim_game_value('game5_' + key) / 100
    delta = base * (factor-1)
    with col_right:
        st.markdown(f'<div class="game5-value">{sim_fmt(base * factor, 2)} <small>mld zł</small>'
                    f'<span>Przed: {sim_fmt(base, 2)} mld zł · {base_pct-100:+.0f}%</span>'
                    f'<span>Zmiana: {sim_fmt(delta,2)} mld zł</span></div>', unsafe_allow_html=True)


def sim_game_tax_lever(key, title, base_receipt, *, low, high, ref, unit, explanation):
    """Pokazuje dokładnie stawkę/taryfę przed i po; bez fikcyjnej jednolitej akcyzy."""
    current = int(sim_game_value('game5_' + key))
    lhs, rhs = st.columns([4, 1.65], vertical_alignment='center', gap='medium')
    with lhs:
        st.slider(title, low, high, current, step=1,
                  key='game5_ui_game5_' + key, on_change=sim_game_sync, args=('game5_' + key,),
                  help=explanation)
        st.caption(explanation)
    # Odczyt tej samej formuły co w modelu: brak rozbieżności między panelem a wynikiem.
    share = {'VAT': .60, 'PIT': .55, 'CIT': .75, 'Akcyza': .80}[key]
    if key == 'Akcyza':
        multiplier = 1 + share*current/100
        ref_label = 'Taryfy bazowe (0%)'
        change_label = f'{current:+.0f}% stawek'
    else:
        multiplier = 1 + share*(current-ref)/ref
        ref_label = f'Stawka: {ref}% → {current}%'
        change_label = f'{current-ref:+d} pp'
    changed_receipt = max(0, base_receipt*multiplier)
    with rhs:
        st.markdown(f'<div class="game5-value">{sim_fmt(changed_receipt,2)} <small>mld zł</small>'
                    f'<span>{ref_label} · {change_label}</span>'
                    f'<span>Wpływy 2025: {sim_fmt(base_receipt,2)} mld zł; Δ {sim_fmt(changed_receipt-base_receipt,2)} mld zł</span>'
                    '</div>', unsafe_allow_html=True)


def sim_game_next(step):
    st.session_state['game5_step'] = step
    st.rerun()


# 2025, MF: państwowy dług publiczny 1 913,5 mld PLN (49,1% PKB);
# PIB 3 894,0 mld wg wstępnego odniesienia MF (II 2026), EDP 2 335,2 mld.
SIM_PDP_2025 = 1913.5
SIM_EDP_2025 = 2335.2
SIM_GDP_2025 = 3894.0
SIM_DEBT_SOURCE = 'https://www.gov.pl/web/finanse/zadluzenie-sektora-finansow-publicznych'
SIM_CONST_SOURCE = 'https://www.prezydent.pl/prawo/konstytucja-rp/rozdzial-x-finanse-publiczne'
SIM_LAW_SOURCE = 'https://eli.gov.pl/api/acts/DU/2024/1530/text.html'


def sim_debt_projection(delta_balance, base_pdp=SIM_PDP_2025, gdp=SIM_GDP_2025,
                        base_edp=SIM_EDP_2025):
    """Ilustracja jednego roku: tylko zmiana finansowania, bez dynamiki długu.

    Poprawa salda o x -> mniej nowego długu o x. Bazowy stan na koniec 2025,
    nie jest to prognoza przyszłej rzeczywistej relacji do PKB.
    """
    pdp = max(0.0, base_pdp - delta_balance)
    edp = max(0.0, base_edp - delta_balance)
    ratio = pdp / gdp * 100
    eu_ratio = edp / gdp * 100
    return {
        'dług_krajowy_mld': pdp, 'dług_eu_mld': edp, 'pkb_mld': gdp,
        'pdp_pct': ratio, 'edp_pct': eu_ratio,
        'ustawowy_55_przekroczony': ratio > 55,
        'konstytucyjny_60_przekroczony': ratio > 60,
        'eu_60_referencja_przekroczona': eu_ratio > 60,
        'margines_55_mld': 0.55*gdp - pdp,
        'margines_60_mld': 0.60*gdp - pdp,
    }


def sim_debt_thresholds(result):
    d = sim_debt_projection(result['delta_wyniku'])
    a,b,c = st.columns(3)
    a.metric('PDP — scenariusz', f'{sim_fmt(d["pdp_pct"],2)}% PKB',
             f'{sim_fmt(d["dług_krajowy_mld"]-SIM_PDP_2025,2)} mld zł wobec końca 2025')
    b.metric('Margines do 55% PKB', f'{sim_fmt(d["margines_55_mld"],1)} mld zł')
    c.metric('Margines do 60% PKB', f'{sim_fmt(d["margines_60_mld"],1)} mld zł')
    # pasek jest wizualnym przelicznikiem wskaźnika; 100% wskazuje 65% PKB, nie zgodność.
    st.progress(min(1.0, max(0.0, d['pdp_pct']/65)),
        text=f'Relacja długu krajowego do PKB: {sim_fmt(d["pdp_pct"],2)}% '
             '(progi 55% ustawowy i 60% konstytucyjny)')
    if d['konstytucyjny_60_przekroczony']:
        st.error('**Przekroczono w modelu limit konstytucyjny 60% PKB** (art. 216 ust. 5).')
    else:
        st.success('**Nie przekroczono w modelu limitu konstytucyjnego 60% PKB** (art. 216 ust. 5).')
    if d['ustawowy_55_przekroczony']:
        st.warning('**Przekroczono w modelu próg ostrożnościowy 55% PKB** — procedury określa ustawa o finansach publicznych.')
    else:
        st.info('**Nie przekroczono w modelu progu ostrożnościowego 55% PKB** (ustawa o finansach publicznych).')
    st.markdown(f'**Unijna wartość referencyjna zadłużenia (EDP):** '
        f'{sim_fmt(d["edp_pct"],2)}% PKB — '
        f'{"powyżej" if d["eu_60_referencja_przekroczona"] else "nie powyżej"} 60% PKB. '
        'EDP jest inną miarą niż krajowy dług objęty art. 216 Konstytucji.')
    st.caption('**Ważne:** model dodaje wyłącznie zmianę finansowania budżetu państwa do stanu długu '
        'na koniec 2025 r., przy stałym nominalnym PKB 2025. Nie prognozuje wzrostu, inflacji, '
        'kursów, zadłużenia funduszy, konsolidacji, przepływów i zmian innych niż decyzje w grze. '
        'Nie rozstrzyga prawnej zgodności rzeczywistej ustawy budżetowej. '
        'Próg 3% deficytu całego sektora GG UE nie jest progiem konstytucyjnym dla budżetu państwa. '
        'Art. 220 ust. 2 dodatkowo zakazuje pokrywania deficytu przez zobowiązanie w NBP.')
    st.markdown(f'Źródła: [MF — zadłużenie 2025]({SIM_DEBT_SOURCE}) · '
                f'[Konstytucja RP]({SIM_CONST_SOURCE}) · [Ustawa o finansach publicznych]({SIM_LAW_SOURCE}).')

def sim_show_game(palette: dict, annual: dict, spending_parts: dict, incomes: dict):
    if 'game5_memory' not in st.session_state:
        st.session_state['game5_memory'] = sim_game_defaults().copy()
    if 'game5_config' not in st.session_state:
        st.session_state['game5_config'] = {
            'goal': 'Zmniejszyć deficyt',
            'constraint': 'Nie pogarszaj wyniku budżetu 2025',
        }
    if 'game5_step' not in st.session_state:
        st.session_state['game5_step'] = 0
    step = int(st.session_state['game5_step'])
    result, programs, revenues = sim_game_state(annual, spending_parts, incomes)
    base_balance = float(annual['income_actual'] - annual['spend_actual'])
    income_base = float(annual['income_actual'])
    expense_base = float(annual['spend_actual'])

    st.markdown('<div class="portal-kicker">INTERAKTYWNE LABORATORIUM · DLA DZIENNIKARZY I ANALITYKÓW</div>'
                '<div class="portal-title">Zaprojektuj budżet</div>'
                '<div class="portal-lead">Cztery proste kroki: ustal zasady, zdecyduj o wydatkach, '
                'zaprojektuj dochody i zobacz skutki. Każdy suwak przelicza budżet na żywo.</div>',
                unsafe_allow_html=True)

    stages = [('01', 'Zasady gry'), ('02', 'Wydatki'), ('03', 'Dochody'), ('04', 'Twój wynik')]
    labels = []
    for ix, (no, label) in enumerate(stages):
        css = 'done' if ix < step else ('active' if ix == step else 'pending')
        labels.append(f'<div class="game5-stage {css}"><span>{no}</span><strong>{label}</strong></div>')
    st.markdown('<div class="game5-progress">' + ''.join(labels) + '</div>', unsafe_allow_html=True)

    with st.container(key='game5_live'):
        a, b, c, d = st.columns([1, 1, 1, 1], gap='medium')
        a.metric('Dochody po zmianach', f"{sim_fmt(result['dochody'], 1)} mld zł",
                 f"{result['delta_dochodow']:+.2f} mld zł")
        b.metric('Wydatki po zmianach', f"{sim_fmt(result['wydatki'], 1)} mld zł",
                 f"{result['delta_wydatkow']:+.2f} mld zł", delta_color='inverse')
        c.metric('Wynik po zmianach', f"{sim_fmt(result['wynik'], 1)} mld zł",
                 f"{result['delta_wyniku']:+.2f} mld zł")
        d.metric('Zmienione pozycje',
                 f"{sum(abs(x['delta']) > 1e-5 for x in (programs + revenues))} z 13 pozycji")

    if step == 0:
        with st.container(key='game5_panel'):
            st.markdown('### 1. Ustal warunki wstępne')
            st.markdown('Projektowanie opieramy na **wykonaniu budżetu państwa w 2025 r.** '
                        'To pozwala sprawdzić skutki na jednej, porównywalnej bazie. '
                        'Zmiany nie oznaczają automatycznej zmiany ustaw ani zachowań gospodarczych.')
            c1, c2, c3 = st.columns(3)
            c1.metric('Dochody bazowe', f'{sim_fmt(income_base, 1)} mld zł')
            c2.metric('Wydatki bazowe', f'{sim_fmt(expense_base, 1)} mld zł')
            c3.metric('Wynik bazowy', f'{sim_fmt(base_balance, 1)} mld zł')
            st.markdown('#### Wybierz cel swojej rozgrywki')
            st.radio('Cel projektowania', ['Zmniejszyć deficyt', 'Wzmocnić wybrane programy',
                      'Sprawdzić własny pomysł'], horizontal=True,
                      index=['Zmniejszyć deficyt', 'Wzmocnić wybrane programy',
                             'Sprawdzić własny pomysł'].index(st.session_state['game5_config']['goal']),
                      key='game5_ui_goal', on_change=sim_game_sync_config, args=('goal',),
                      help='Cel jest drogowskazem, a nie automatyczną zmianą danych.')
            st.markdown('#### Wybierz ograniczenie budżetowe')
            st.selectbox('Warunek finansowy',
                         ['Nie pogarszaj wyniku budżetu 2025',
                          'Dopuszczam pogorszenie wyniku do 10 mld zł',
                          'Dopuszczam pogorszenie wyniku do 25 mld zł',
                          'Scenariusz swobodny (bez limitu)'],
                         index=['Nie pogarszaj wyniku budżetu 2025',
                                'Dopuszczam pogorszenie wyniku do 10 mld zł',
                                'Dopuszczam pogorszenie wyniku do 25 mld zł',
                                'Scenariusz swobodny (bez limitu)'].index(
                                    st.session_state['game5_config']['constraint']),
                         key='game5_ui_constraint', on_change=sim_game_sync_config,
                         args=('constraint',))
            st.markdown('#### Potwierdź założenia metodologiczne')
            st.checkbox('Rozumiem, że model liczy roczne zmiany nominalne, a nie prognozuje PKB lub inflacji.',
                        key='game5_method')
            st.checkbox('Rozumiem, że budżet państwa nie obejmuje wszystkich wydatków sektora publicznego.',
                        key='game5_conditions')
            ready = st.session_state.get('game5_method') and st.session_state.get('game5_conditions')
            if not ready:
                st.info('Aby rozpocząć, zaznacz oba potwierdzenia. Pozostałe 3 kroki zostaną odblokowane.')
            if st.button('Rozpocznij projektowanie budżetu  →', type='primary',
                         disabled=not ready, use_container_width=True, key='game5_begin'):
                sim_game_next(1)

    elif step == 1:
        with st.container(key='game5_panel'):
            st.markdown('### 2. Wybierz, na co przeznaczysz pieniądze')
            st.info('Masz **10 regulowanych parametrów wydatkowych**. Dla pozostałych pozycji zakładamy '
                    'brak zmian. Suwak 100% oznacza wykonanie 2025 r. Kwoty po prawej są wyliczane automatycznie.')
            st.markdown('#### A. Program 800+ — z osobnymi parametrami')
            c1, c2 = st.columns([1.6, 1.4], gap='large')
            with c1:
                amount = st.slider('Miesięczne świadczenie na dziecko (zł)', 0, 1600,
                                   int(sim_game_value('game5_800_amount')), 50,
                                   key='game5_ui_game5_800_amount', on_change=sim_game_sync,
                                   args=('game5_800_amount',),
                                   help='Zmienia jedynie kwotę programu 800+. To nie jest prognoza zachowań rodzin.')
            with c2:
                coverage = st.slider('Zakres wypłat względem roku bazowego (%)', 0, 120,
                                     int(sim_game_value('game5_800_coverage')), 5,
                                     key='game5_ui_game5_800_coverage', on_change=sim_game_sync,
                                     args=('game5_800_coverage',),
                                     help='100% oznacza liczbę wypłat równoważną 2025 r., nie udział dzieci w populacji.')
            p800 = next(x for x in programs if x['id'] == '800plus')
            st.markdown(f'<div class="game5-example"><b>800+ w Twoim budżecie:</b> '
                        f'<strong>{sim_fmt(p800["scenariusz"], 2)} mld zł</strong>'
                        f'<span>Zmiana: {p800["delta"]:+.2f} mld zł · '
                        f'Rodzina z 2 uprawnionymi dziećmi: {2*amount*12:,.0f} zł rocznie</span></div>'.replace(',', ' '),
                        unsafe_allow_html=True)
            st.markdown('#### B. Trzy wybrane programy społeczne')
            sim_game_lever('senior', '13. i 14. emerytura + Mama+ (część ZUS)', 26.8,
                           helptext='Kwota z informacji komisji sejmowej dla części ZUS.')
            sim_game_lever('disability', 'Świadczenie wspierające', 8.8)
            sim_game_lever('active_parent', 'Program Aktywny rodzic', 6.2)
            st.markdown('#### C. Pięć części budżetowych')
            st.caption('Zmiana dotyczy wskazanej części budżetu, nie całej dziedziny polityki publicznej.')
            for key, part, label in [
                ('defence', '29', 'Obrona narodowa'), ('health', '46', 'Zdrowie'),
                ('local', '82', 'Subwencje dla samorządów'),
                ('internal', '42', 'Sprawy wewnętrzne'),
                ('province', '85', 'Wojewodowie / administracja terenowa')]:
                sim_game_lever(key, label + f' (część {part})', float(spending_parts[part][1]))
            l, r = st.columns(2)
            with l:
                if st.button('← Wróć do założeń', use_container_width=True, key='game5_back1'):
                    sim_game_next(0)
            with r:
                if st.button('Dalej: dochody podatkowe  →', type='primary', use_container_width=True,
                             key='game5_forward2'):
                    sim_game_next(2)

    elif step == 2:
        with st.container(key='game5_panel'):
            st.markdown('### 3. Zmień stawki podatków — konkretne wartości')
            st.info('Podajesz **konkretne parametry podatkowe**. Wartości 2025 są punktem odniesienia, '
                    'a estymacja dochodów to liniowa ilustracja z jawnymi założeniami, nie prognoza Ministerstwa Finansów.')
            sim_game_tax_lever('VAT', 'VAT · podstawowa stawka (%)', float(incomes['VAT'][1]),
                low=18, high=28, ref=23, unit='%',
                explanation='23% to stawka podstawowa w 2025 r. Obniżone 8% i 5% nie są zmieniane; założenie: 60% wpływów VAT reaguje liniowo.')
            sim_game_tax_lever('PIT', 'PIT · stawka pierwszego progu skali (%)', float(incomes['PIT'][1]),
                low=8, high=18, ref=12, unit='%',
                explanation='12% to pierwszy próg skali (do 120 tys. zł), drugi wynosi 32%. Założenie: 55% wpływów PIT reaguje liniowo; kwota wolna bez zmian.')
            sim_game_tax_lever('CIT', 'CIT · stawka podstawowa (%)', float(incomes['CIT'][1]),
                low=14, high=26, ref=19, unit='%',
                explanation='19% to stawka podstawowa CIT; 9% preferencyjna pozostaje stała. Założenie: 75% wpływów CIT reaguje liniowo.')
            sim_game_tax_lever('Akcyza', 'Akcyza · zmiana zestawu stawek (%)', float(incomes['Akcyza'][1]),
                low=-25, high=40, ref=0, unit='%',
                explanation='Akcyza jest zbiorem stawek zależnych od wyrobu, nie jedną stawką. 0% oznacza brak zmian; założenie: 80% wpływów reaguje liniowo.')
            st.caption('VAT 23%, PIT 12%/32%, CIT 19%/9% — historyczne punkty odniesienia. '
                       'W modelu pominięto zmianę popytu, konsumpcji, baz podatkowych, przerzucanie podatków i skutki administracyjne.')
            l, r = st.columns(2)
            with l:
                if st.button('← Wróć do wydatków', use_container_width=True, key='game5_back2'):
                    sim_game_next(1)
            with r:
                if st.button('Przejdź do podsumowania  →', type='primary', use_container_width=True,
                             key='game5_forward3'):
                    sim_game_next(3)

    else:
        with st.container(key='game5_panel'):
            st.markdown('### 4. Sprawdź skutki swojego budżetu')
            constraint = st.session_state['game5_config']['constraint']
            allow = 0 if constraint.startswith('Nie pogarszaj') else (10 if '10 mld' in constraint else
                    (25 if '25 mld' in constraint else None))
            delta = result['delta_wyniku']
            if allow is not None and delta < -allow - 1e-6:
                st.error(f'Nie spełniono wybranego ograniczenia! Wynik pogorszył się '
                         f'o {sim_fmt(-delta, 2)} mld zł; dopuszczalny limit: {allow} mld zł. '
                         'Wróć do suwaków i popraw projekt.')
            elif allow is None:
                st.info('To scenariusz swobodny — bez zadeklarowanego limitu deficytu.')
            else:
                st.success('Twój projekt mieści się w wybranym ograniczeniu finansowym.')
            st.plotly_chart(sim_waterfall(result, palette), use_container_width=True,
                            key='game5_waterfall')
            st.caption('Wynik budżetu = dochody minus wydatki. Poprawa wyniku nie oznacza '
                       'automatycznie wzrostu dobrobytu lub poparcia politycznego.')

            modified = [x for x in programs + revenues if abs(x['delta']) > 1e-6]
            st.markdown('#### Ocena poszczególnych decyzji — koszty, oszczędności i kompromisy')
            if modified:
                for x in sorted(modified, key=lambda y: abs(y['wplyw_na_wynik']), reverse=True):
                    impact = x['wplyw_na_wynik']
                    direction = 'zmniejsza' if impact > 0 else 'zwiększa'
                    if x['typ'] == 'Wydatki':
                        effect = ('Większe środki dla wskazanego obszaru; wymaga wskazania finansowania, '
                                  'może zwiększać dostępność lub skalę świadczeń.' if x['delta'] > 0 else
                                  'Mniej środków dla wskazanego obszaru; konieczna ocena ryzyka ograniczenia '
                                  'świadczeń, usług lub zakresu programu.')
                    else:
                        effect = ('Wyższe szacunkowe wpływy; potencjalny wzrost obciążenia podatkowego '
                                  'wskazanej grupy. Efekty ekonomiczne nie są modelowane.' if x['delta'] > 0 else
                                  'Niższe szacunkowe wpływy; potencjalne zmniejszenie obciążeń podatkowych, '
                                  'ale większa potrzeba finansowania innych pozycji.')
                    rate = (f' · {x["parametr_opis"]}' if x.get('parametr_opis') else '')
                    st.markdown(f'<div class="game6-decision"><b>{escape(x["pozycja"])}{escape(rate)}</b>'
                        f'<span>Wartość bazowa {sim_fmt(x["baza"],2)} → {sim_fmt(x["scenariusz"],2)} mld zł. '
                        f'Zmiana: {sim_fmt(x["delta"],2)} mld zł.</span>'
                        f'<strong>{direction.capitalize()} deficyt o {sim_fmt(abs(impact),2)} mld zł</strong>'
                        f'<p>{escape(effect)} Grupa związana z decyzją: {escape(x["interesariusze"])}.</p></div>',
                        unsafe_allow_html=True)
            else:
                st.info('Projekt nie wprowadza zmian względem roku bazowego 2025.')

            goal = st.session_state['game5_config']['goal']
            if goal == 'Zmniejszyć deficyt':
                met_goal = result['delta_wyniku'] > 0
                st.success('Cel gry „Zmniejszyć deficyt” — osiągnięty w modelu.') if met_goal else st.warning('Cel gry „Zmniejszyć deficyt” — nieosiągnięty w modelu.')
            elif goal == 'Wzmocnić wybrane programy':
                met_goal = any(p['delta'] > 0 for p in programs)
                st.success('Cel gry „Wzmocnić programy” — zwiększono finansowanie wybranych pozycji.') if met_goal else st.warning('Cel gry „Wzmocnić programy” — żadna pozycja nie uzyskała wyższego finansowania.')
            else:
                st.info('Cel gry „Sprawdzić własny pomysł” — interpretuj odchylenia i kompromisy poniżej.')
            st.markdown('#### Wynik sumaryczny Twojego projektu')
            st.markdown(f'Łączna zmiana dochodów: **{sim_fmt(result["delta_dochodow"],2)} mld zł**; '
                        f'łączna zmiana wydatków: **{sim_fmt(result["delta_wydatkow"],2)} mld zł**; '
                        f'zmiana salda: **{sim_fmt(result["delta_wyniku"],2)} mld zł**. '
                        'To księgowy skutek scenariusza, a nie ocena tego, czy polityka jest dobra dla społeczeństwa.')

            st.markdown('#### Konstytucyjne i ustawowe progi zadłużenia')
            sim_debt_thresholds(result)

            with st.expander('Analiza potencjalnych skutków społecznych i źródła badań'):
                st.markdown('Zmiany budżetowe mogą dotykać różnych grup, ale **nie pozwalają wiarygodnie '
                            'wyliczyć zmian poparcia wyborczego**. Wpływ zależy od rozkładu dochodów, wieku, '
                            'preferencji, dostępności usług i wielu czynników. Nie są one parametrami gry.')
                affected = [p for p in programs if abs(p['delta']) > 1e-6]
                for p in affected:
                    st.markdown(f'**{p["pozycja"]}:** {p["interesariusze"]}; '
                                f'zmiana finansowania {sim_fmt(p["delta"],2)} mld zł.')
                st.link_button('PKW — wyniki historyczne, nie prognoza', sim_PKW_SOURCE)

            st.markdown('#### Zachowaj swój projekt')
            full = pd.DataFrame(programs + revenues)
            payload = {'rok_bazowy': 2025, 'cel': st.session_state['game5_config']['goal'],
                       'ograniczenie': constraint, 'saldo': result,
                       'pozycje': programs + revenues,
                       'parametry_uzytkownika': st.session_state['game5_memory'].copy(),
                       'metodologia': 'Model statyczny z 14 parametrami i bez wpływów wtórnych.'}
            left, right = st.columns(2)
            with left:
                st.download_button('Pobierz szczegóły (CSV)',
                                   full.to_csv(index=False).encode('utf-8-sig'),
                                   file_name='projekt_budzetu_2025.csv', mime='text/csv',
                                   use_container_width=True, key='game5_export_csv')
            with right:
                st.download_button('Pobierz projekt i założenia (JSON)',
                                   json.dumps(payload, ensure_ascii=False, indent=2),
                                   file_name='projekt_budzetu_2025.json',
                                   mime='application/json', use_container_width=True,
                                   key='game5_export_json')
            if st.button('← Popraw wcześniejsze decyzje', use_container_width=True,
                         key='game5_revisit'):
                sim_game_next(1)

    with st.expander('Metodologia, źródła i ograniczenia — przeczytaj przed publikacją'):
        st.markdown('**Zakres:** wykonanie budżetu państwa w 2025 r. '
                    '**14 parametrów użytkownika** (2 dla 800+, 3 dla innych programów, '
                    '5 dla części budżetowych, 4 dla wpływów podatkowych). '
                    'Zmiana dźwigni to przyrost/ubytek względem bazy, a nie suma wydatków po raz drugi.')
        st.markdown('**Brak nakładania się kwot w modelu:** 800+, świadczenia dodatkowe '
                    'oraz pozostałe wyróżnione programy zaliczono technicznie do części 73; '
                    'nie dopuszczono suwaka dla całej części 73. '
                    'Części 29, 46, 82, 42, 85 są rozłączne względem tej grupy. '
                    'Pozostałe wydatki i dochody nie są sterowane.')
        st.markdown('**Dane referencyjne:** część kwot programowych pochodzi z informacji '
                    'sejmowych i ma inną szczegółowość niż pozycje wykonania budżetu. '
                    'Podział ma charakter edukacyjnego uproszczenia, a nie nowej oficjalnej klasyfikacji.')
        st.markdown('**Przyjęte udziały reagujących wpływów podatkowych są modelowymi założeniami, nie danymi MF:** '
                    'VAT 60%, PIT 55%, CIT 75%, akcyza 80%. Formuła: '
                    'wpływy po = wpływy 2025 × (1 + udział × zmiana stawki / stawka bazowa); '
                    'dla akcyzy bazą jest % zmiany całego koszyka stawek. Podatki są wielostawkowe, '
                    'dlatego symulacja nie odpowiada precyzyjnemu skutkowi legislacyjnemu.')
        st.markdown('**Model nie symuluje:** zmian prawa, wzrostu cen, kosztów wdrożenia, '
                    'przesunięć między funduszami, elastyczności podatków, zachowań ekonomicznych, '
                    'sondaży, zachowania wyborców ani zmian wyniku wyborów.')
        st.markdown(f'Źródła: [budżet 2025 — MF]({sim_STATE_BUDGET_SOURCE}), '
                    f'[informacja komisji Sejmu]({sim_PROGRAM_SOURCE}), '
                    f'[program 800+]({sim_FAMILY_SOURCE}), [PKW]({sim_PKW_SOURCE}).')
    if step > 0:
        st.button('Resetuj grę i wszystkie suwaki', key='game5_reset',
                  on_click=sim_game_reset)

# =============================================================
# MODUŁ WBUDOWANY 2/2 — EUROSTAT COFOG
# Działa poprzez API Eurostatu; brak obowiązkowych plików danych.
# Nazwy zostały poprzedzone prefiksem cofog_.
# =============================================================
cofog_BASE_URL = 'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/gov_10a_exp'
cofog_BROWSER_URL = 'https://ec.europa.eu/eurostat/databrowser/view/gov_10a_exp/default/table?lang=pl'
cofog_TOP = {'GF01': 'Usługi ogólnopaństwowe', 'GF02': 'Obrona narodowa', 'GF03': 'Porządek i bezpieczeństwo publiczne', 'GF04': 'Sprawy gospodarcze', 'GF05': 'Ochrona środowiska', 'GF06': 'Gospodarka mieszkaniowa i komunalna', 'GF07': 'Ochrona zdrowia', 'GF08': 'Rekreacja, kultura i religia', 'GF09': 'Edukacja', 'GF10': 'Ochrona socjalna'}
cofog_UNITS = {'MIO_NAC': 'mld PLN', 'PC_GDP': '% PKB', 'PC_TOT': '% wydatków sektora'}

def cofog_decode_jsonstat(payload: dict) -> pd.DataFrame:
    """Prawidłowe odczytywanie wielowymiarowych kluczy JSON-stat Eurostatu."""
    ids = payload.get('id', [])
    sizes = payload.get('size', [])
    dimensions = payload.get('dimension', {})
    if not ids or len(ids) != len(sizes):
        raise ValueError('Odpowiedź Eurostatu nie zawiera prawidłowych wymiarów JSON-stat')
    reverse = {}
    labels = {}
    for key in ids:
        cat = dimensions[key]['category']
        idx = cat.get('index', {})
        if isinstance(idx, list):
            reverse[key] = dict(enumerate(idx))
        else:
            reverse[key] = {int(v): str(k) for k, v in idx.items()}
        labels[key] = cat.get('label', {})
    strides = []
    for i in range(len(sizes)):
        strides.append(math.prod(sizes[i + 1:]))
    values = payload.get('value', {})
    iterator = enumerate(values) if isinstance(values, list) else values.items()
    result = []
    for flat_key, value in iterator:
        if value is None:
            continue
        flat = int(flat_key)
        row = {key: reverse[key].get(flat // stride % size, '') for key, size, stride in zip(ids, sizes, strides)}
        if row.get('geo') != 'PL' or row.get('sector') != 'S13' or row.get('na_item') != 'TE':
            continue
        code = row.get('cofog99', '')
        if not code.startswith('GF'):
            continue
        try:
            year = int(row.get('time', row.get('time_period', '')))
        except ValueError:
            continue
        if year < 2016:
            continue
        unit = row.get('unit', '')
        if unit not in cofog_UNITS:
            continue
        amount = float(value)
        if unit == 'MIO_NAC':
            amount /= 1000.0
        result.append({'Rok': year, 'Kod': code, 'Funkcja Eurostatu': labels.get('cofog99', {}).get(code, code), 'Jednostka': unit, 'Wartość': amount, 'Poziom': 'Dział (COFOG 1)' if len(code) == 4 else 'Grupa (COFOG 2)'})
    return pd.DataFrame(result, columns=['Rok', 'Kod', 'Funkcja Eurostatu', 'Jednostka', 'Wartość', 'Poziom'])

def cofog__fetch_unit(unit: str) -> tuple[pd.DataFrame, str]:
    try:
        response = requests.get(cofog_BASE_URL, params={'geo': 'PL', 'sector': 'S13', 'na_item': 'TE', 'unit': unit, 'sinceTimePeriod': '2016', 'lang': 'EN'}, timeout=14, headers={'User-Agent': 'PolskiObserwatorBudzetowy/3.0'})
        response.raise_for_status()
        frame = cofog_decode_jsonstat(response.json())
        if frame.empty:
            return (pd.DataFrame(), f'{unit}: Eurostat nie zwrócił obserwacji')
        return (frame, '')
    except (requests.RequestException, ValueError, KeyError) as ex:
        return (pd.DataFrame(), f'{unit}: {str(ex)[:120]}')

@st.cache_data(ttl=12 * 3600, show_spinner=False)
def cofog_eurostat_data() -> tuple[pd.DataFrame, str]:
    """Sieć odpytywana równolegle; również komunikat o awarii jest cache'owany."""
    frames = []
    problems = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(cofog__fetch_unit, ('MIO_NAC', 'PC_GDP', 'PC_TOT')))
    for frame, error in results:
        if not frame.empty:
            frames.append(frame)
        if error:
            problems.append(error)
    if not frames:
        return (pd.DataFrame(), '; '.join(problems) or 'Eurostat nie odpowiada')
    return (pd.concat(frames, ignore_index=True), '; '.join(problems))

def cofog_fmt_pl(value, precision=1):
    return f'{value:,.{precision}f}'.replace(',', '@').replace('.', ',').replace('@', ' ')

def cofog_show_cofog(palette: dict):
    st.markdown('<div class="portal-kicker">MIĘDZYNARODOWA STATYSTYKA SEKTORA PUBLICZNEGO · ESA 2010</div>\n    <div class="portal-title">Wydatki publiczne według COFOG</div>\n    <div class="portal-lead">10 głównych funkcji państwa i ich grupy szczegółowe · szereg od 2016 roku · Eurostat / S.13</div>', unsafe_allow_html=True)
    st.info('**Inny zakres instytucjonalny:** COFOG obejmuje sektor instytucji rządowych i samorządowych (S.13), a nie tylko budżet państwa. Nie należy dodawać tych wartości do wydatków budżetowych z pozostałych zakładek.')
    data, error = cofog_eurostat_data()
    if not data.empty:
        st.caption('Źródło pobierane bezpośrednio z Eurostat API · gov_10a_exp · S13 · TE · Polska. Tylko wartości opublikowane, bez ekstrapolacji.')
        if error:
            st.caption('Część jednostek nie została pobrana: ' + error)
    if data.empty:
        st.warning('Nie udało się pobrać aktualnych danych Eurostatu. Aplikacja nie pokazuje liczb zastępczych. Sprawdź połączenie z internetem albo zaimportuj wcześniej pobrany CSV z zakładki.')
        if error:
            st.caption(f'Szczegóły: {error}')
        uploaded = st.file_uploader('Importuj wcześniej wyeksportowany CSV z modułu COFOG', type='csv', key='cofog_upload')
        if uploaded is not None:
            try:
                data = pd.read_csv(uploaded)
                expected = {'Rok', 'Kod', 'Funkcja Eurostatu', 'Jednostka', 'Wartość', 'Poziom'}
                if not expected.issubset(data.columns):
                    st.error('CSV powinien zawierać kolumny: ' + ', '.join(sorted(expected)))
                    return
                data['Rok'] = pd.to_numeric(data['Rok'], errors='raise').astype(int)
                data['Wartość'] = pd.to_numeric(data['Wartość'], errors='raise')
                data = data[data['Rok'] >= 2016]
                st.success('Wczytano plik użytkownika — zweryfikuj jego datę i pochodzenie.')
            except Exception as exc:
                st.error(f'Nie można odczytać CSV: {exc}')
                return
        else:
            st.link_button('Otwórz zbiór gov_10a_exp w Eurostacie', cofog_BROWSER_URL)
            return
    available_units = [u for u in cofog_UNITS if u in data['Jednostka'].unique()]
    if not available_units:
        st.error('Brak wymaganych jednostek danych Eurostatu.')
        return
    with st.container(key="top_filters"):
        st.markdown(
            '<div class="filter-topline"><div class="filter-eyebrow">◈ &nbsp; FILTRY COFOG</div>'
            '<div class="filter-subtitle">Wspólny panel wyboru jednostki, roku i szczegółowości.</div></div>',
            unsafe_allow_html=True
        )
        unit_choice, year_choice, view_choice = st.columns([1.3, 1.1, 1.3], vertical_alignment="center")
        with unit_choice:
            unit = st.selectbox('Jednostka', available_units, format_func=lambda x: cofog_UNITS[x], key='cofog_unit')
        d = data[data['Jednostka'] == unit].copy()
        years = sorted(d['Rok'].unique().tolist())
        with year_choice:
            year = st.select_slider('Rok porównania', options=years, value=years[-1], key='cofog_year')
        with view_choice:
            level = st.segmented_control('Stopień szczegółowości', ['10 działów', 'Wszystkie grupy'], default='10 działów', key='cofog_level')
    st.markdown('<div class="visuals-separator">Dane i wizualizacje Eurostatu</div>', unsafe_allow_html=True)
    is_top = level == '10 działów'
    d = d[d['Kod'].str.len().eq(4 if is_top else 6)]
    if d.empty:
        st.warning('W tej jednostce i poziomie szczegółowości brak danych.')
        return
    d['Pozycja'] = d['Kod'] + ' · ' + d['Kod'].map(cofog_TOP).fillna(d['Funkcja Eurostatu'])
    this = d[d['Rok'] == year].sort_values('Wartość', ascending=False)
    prev = d[d['Rok'] == year - 1]
    main = d[(d['Kod'].str.len() == 4) & (d['Rok'] == year)]
    k1, k2, k3 = st.columns(3)
    with k1:
        if is_top:
            st.metric('Funkcje COFOG z obserwacjami', len(this))
        else:
            st.metric('Grupy szczegółowe COFOG', len(this))
    with k2:
        if unit == 'PC_GDP' and is_top:
            st.metric('Wydatki sektora / PKB (suma działów)', cofog_fmt_pl(this['Wartość'].sum()) + ' %')
        elif unit == 'MIO_NAC' and is_top:
            st.metric('Wydatki sektora · suma funkcji', cofog_fmt_pl(this['Wartość'].sum()) + ' mld zł')
        else:
            st.metric('Rok źródłowy', year)
    with k3:
        st.metric('Zakres dostępnych lat', f'{min(years)}–{max(years)}')
    left, right = st.columns([1.15, 0.85], gap='large')
    with left:
        with st.container(key='cofog_panel_rank'):
            st.markdown('#### Struktura wydatków w wybranym roku')
            top = this.head(32).iloc[::-1]
            fig = px.bar(top, y='Pozycja', x='Wartość', orientation='h', color='Wartość', color_continuous_scale='Blues', hover_data=['Kod', 'Funkcja Eurostatu'])
            fig.update_layout(template=palette['template'], height=max(560, len(top) * 27 + 100), coloraxis_showscale=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=5, r=7, t=8, b=30), xaxis_title=cofog_UNITS[unit], yaxis_title='')
            st.plotly_chart(fig, use_container_width=True)
    with right:
        with st.container(key='cofog_panel_trend'):
            st.markdown('#### Historia największych funkcji')
            top_codes = this.head(5)['Kod'].tolist()
            trends = d[d['Kod'].isin(top_codes)]
            fig = px.line(trends, x='Rok', y='Wartość', color='Pozycja', markers=True)
            fig.update_layout(template=palette['template'], height=560, legend_title='', legend=dict(orientation='h', y=-0.28), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=5, r=5, t=8, b=70), yaxis_title=cofog_UNITS[unit])
            st.plotly_chart(fig, use_container_width=True)
    with st.container(key='cofog_panel_heat'):
        st.markdown('#### Mapa zmian w czasie')
        heat = d.pivot_table(index='Pozycja', columns='Rok', values='Wartość', aggfunc='first')
        if len(heat) > 35:
            st.caption('Widok 35 największych grup; pełne dane dostępne poniżej.')
            heat = heat.loc[this.head(35)['Pozycja'].tolist()]
        fig = px.imshow(heat, color_continuous_scale='Blues', aspect='auto', labels={'color': cofog_UNITS[unit], 'x': 'Rok', 'y': 'Funkcja'})
        fig.update_layout(template=palette['template'], height=max(390, 23 * len(heat) + 130), paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=5, r=5, t=10, b=30))
        st.plotly_chart(fig, use_container_width=True)
    st.download_button('Pobierz kompletny szereg COFOG (CSV)',
        data=data.to_csv(index=False).encode('utf-8-sig'),
        file_name='eurostat_cofog_PL_S13_2016_plus.csv', mime='text/csv')
    st.caption("Metodyka: ESA 2010, COFOG 1999, sektor S.13, pozycja TE (całkowite wydatki). Wartości 'MIO_NAC' przeliczone z milionów PLN na miliardy PLN. Rewizje i braki pozostają zgodne z Eurostatem; sumy działów i grup mogą różnić się od zestawień innych metodologii.")
    st.link_button('Źródło, metadane i aktualizacje Eurostatu', cofog_BROWSER_URL)


TAB_1 = "Stan Budżetu"
TAB_2 = "Budżet w kategoriach"
TAB_3 = "Finanse samorządów"
TAB_4 = "Zaprojektuj budżet"
TAB_5 = "Eurostat COFOG"


# W nowej sesji zawsze startujemy z jasnym motywem. Użytkownik może
# później przełączyć się na ciemny; przełączanie nie resetuje filtrów.
# Osobny znacznik pozwala przejść na jasny również po aktualizacji kodu
# w już otwartej sesji Streamlit (bez wymuszania go na każdym rerunie).
if not st.session_state.get("_domyslny_motyw_realne_dane_v1", False):
    st.session_state.theme = "light"
    st.session_state._domyslny_motyw_realne_dane_v1 = True

if "current_tab" not in st.session_state:
    st.session_state.current_tab = TAB_1
elif st.session_state.current_tab == "Symulator budżetu":
    st.session_state.current_tab = TAB_4
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
        card="rgba(255,255,255,0.87)",
        border="#DCE5F1",
        side="#EFF4FB",
        side_shadow="6px 0 28px rgba(15,23,42,0.12)",
        on_accent="#FFFFFF",
        panel="rgba(255,255,255,0.85)",
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
        card="rgba(18,32,53,0.87)",
        border="rgba(255,255,255,0.12)",
        side="#07101F",
        side_shadow="6px 0 28px rgba(0,0,0,0.55)",
        on_accent="#0B1220",
        panel="rgba(15,23,42,0.85)",
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


# Sześć precyzyjnie odsuniętych konturów Polski (obliczonych offline).
# Głębokości 0 / 3.6 / 7.2 / 10.8 / 14.4 / 18.0 px nie krzyżują się.
# Obrysy są wbudowane w kod — nie wymagają biblioteki shapely ani plików SVG.
LOGO_SIX_CONTOURS = (
    'M 9.09,22.85 L 9.92,25.80 L 8.25,31.18 L 7.83,37.23 L 12.43,37.90 L 11.59,40.59 L 13.26,54.70 L 14.93,58.07 L 15.35,62.10 L 14.51,63.85 L 22.86,65.46 L 27.04,68.15 L 30.80,72.85 L 33.72,70.16 L 37.89,71.51 L 40.40,74.87 L 45.41,78.90 L 47.50,82.26 L 52.50,80.92 L 55.43,86.30 L 60.44,83.61 L 66.28,83.61 L 72.96,84.28 L 78.39,87.91 L 79.64,80.92 L 82.15,76.21 L 87.99,70.16 L 91.33,64.11 L 86.74,54.70 L 87.16,47.31 L 89.66,38.57 L 86.32,22.44 L 82.15,18.41 L 80.48,16.93 L 70.46,17.33 L 54.17,15.72 L 52.09,16.80 L 47.91,16.66 L 44.99,15.05 L 47.08,13.70 L 43.15,10.61 L 36.64,11.55 L 20.19,19.35 L 9.09,22.85 Z',
    'M 13.51,25.55 L 11.66,34.15 L 14.53,34.98 L 15.89,36.93 L 15.29,40.81 L 16.81,53.76 L 18.39,57.06 L 18.82,60.65 L 24.49,62.25 L 29.30,65.35 L 31.20,67.59 L 34.15,66.59 L 39.67,68.38 L 49.14,78.09 L 53.92,77.61 L 56.88,81.43 L 59.73,80.08 L 66.28,80.01 L 73.67,80.75 L 75.82,81.86 L 79.14,74.23 L 85.07,68.01 L 87.27,64.01 L 83.14,54.87 L 83.61,46.71 L 85.93,38.51 L 82.92,24.17 L 79.70,21.05 L 54.89,19.40 L 52.34,20.39 L 47.46,20.23 L 42.41,17.56 L 41.44,14.50 L 37.60,15.05 L 21.78,22.58 L 13.51,25.55 Z',
    'M 15.69,31.49 L 18.12,33.50 L 19.36,35.95 L 19.00,41.02 L 20.37,52.82 L 22.14,57.81 L 26.12,59.04 L 32.20,63.13 L 35.26,63.13 L 41.46,65.25 L 50.64,73.96 L 54.70,74.06 L 58.34,76.72 L 73.52,77.10 L 76.53,71.71 L 83.22,63.91 L 79.62,55.76 L 80.06,46.11 L 82.21,38.44 L 79.53,25.89 L 77.82,24.24 L 69.72,24.50 L 55.60,23.09 L 52.59,23.98 L 47.00,23.80 L 40.91,20.98 L 38.70,18.53 L 16.71,28.24 L 15.69,31.49 Z',
    'M 20.48,30.71 L 23.06,35.98 L 22.70,41.24 L 23.92,51.88 L 25.26,54.92 L 33.32,59.38 L 43.24,62.12 L 51.75,70.15 L 55.80,70.63 L 59.66,72.84 L 71.47,73.27 L 73.72,69.46 L 79.15,63.77 L 75.95,55.20 L 76.51,45.51 L 78.48,38.37 L 76.17,27.91 L 69.36,28.08 L 56.22,26.76 L 52.84,27.57 L 46.55,27.38 L 42.69,26.12 L 37.55,22.86 L 20.48,30.71 Z',
    'M 25.80,32.59 L 27.98,52.00 L 34.46,55.80 L 45.02,59.00 L 53.01,66.53 L 56.90,67.20 L 60.86,69.21 L 69.43,69.45 L 74.81,63.09 L 72.35,55.36 L 72.96,44.91 L 74.76,38.31 L 73.12,31.64 L 56.68,30.42 L 53.09,31.16 L 46.09,30.95 L 42.17,29.87 L 36.97,27.00 L 25.80,32.59 Z',
    'M 30.10,34.54 L 30.99,49.40 L 35.64,52.28 L 46.80,55.87 L 54.39,63.03 L 61.93,65.61 L 67.58,65.67 L 70.47,62.39 L 68.76,55.53 L 69.41,44.31 L 71.03,38.24 L 70.30,35.29 L 57.09,34.08 L 45.64,34.52 L 36.88,31.13 L 30.10,34.54 Z',
 )


def logo_svg():
    """Wektorowy znak marki: dokładnie sześć topograficznych obrysów Polski."""
    colors = ("#EFFAFF", "#CCEDFF", "#A6DEFF", "#72C8FF", "#448DF2", "#F9BA6F")
    strokes = ("1.75", "1.65", "1.65", "1.60", "1.65", "1.85")
    lines = [
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{stroke}" '
        'stroke-linejoin="round" stroke-linecap="round"/>'
        for d, color, stroke in zip(LOGO_SIX_CONTOURS, colors, strokes)
    ]
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
            'role="img" aria-label="Sześć koncentrycznych konturów Polski">'
            + "".join(lines) + '</svg>')


def logo_img(size=60, fg=None):
    """Wstawia sześciokonturowe logo jako samodzielny obraz SVG w kodzie Pythona."""
    uri = "data:image/svg+xml;base64," + base64.b64encode(logo_svg().encode("utf-8")).decode("ascii")
    return (f'<img src="{uri}" width="{size}" height="{size}" '
            'alt="Polska — sześć koncentrycznych konturów" '
            'style="display:block;width:100%;height:100%;object-fit:contain;'
            'filter:drop-shadow(0 4px 16px rgba(84,187,255,.28));">')


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
        europe_fill, europe_stroke = "none", "rgba(219,234,254,0.075)"
        poland_fill, poland_stroke = "rgba(248,113,113,0.035)", "rgba(252,165,165,0.095)"
    else:
        europe_fill, europe_stroke = "none", "rgba(30,58,95,0.075)"
        poland_fill, poland_stroke = "rgba(220,38,38,0.035)", "rgba(185,28,28,0.105)"
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


/* Obserwator 2.0 — nowocześniejsze, wyraźniejsze karty i typografia. */
.stApp .block-container { max-width: 1640px; padding-top: 1.5rem !important; }
.stApp .dash-title { font-size: clamp(2.0rem, 3vw, 3.2rem); letter-spacing:-.055em; }
.stApp .kpi-card { min-height:280px !important; border-radius:22px !important; padding:20px 21px !important; }
.stApp .kpi-value { font-size: clamp(1.24rem, 1.7vw, 1.8rem) !important; }
.stApp .kpi-desc { min-height:0; margin-top:14px !important; }
.stApp .financial-balance { border-radius:23px; padding:22px 26px; }
.stApp .st-key-panel_income, .stApp .st-key-panel_spending,
.stApp .st-key-panel_trend_budget, .stApp .st-key-panel_trend_result,
.stApp .st-key-panel_category_main, .stApp .st-key-panel_category_share,
.stApp .st-key-panel_category_detail, .stApp .st-key-panel_summary_table,
.stApp .st-key-panel_detail_table, .stApp .st-key-panel_yoy,
.stApp .st-key-panel_debt, .stApp .st-key-panel_jst_map,
.stApp .st-key-panel_jst_ranking, .stApp .st-key-panel_jst_table {
    background:$card !important; border:1px solid $border !important;
    border-radius:22px !important; box-shadow:$shadow !important;
    padding:19px 22px 16px !important; margin-bottom:16px !important;
    backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px);
}
.stApp .st-key-top_filters { background:$card !important; border-radius:21px !important;
  padding:18px 20px !important; box-shadow:$shadow !important; border:1px solid $border !important; }
.stApp .st-key-top_filters [data-testid="stSegmentedControl"] { margin-top:3px !important; }
.stApp .st-key-top_filters [data-testid="stSlider"],
.stApp .st-key-top_filters [data-testid="stSelectSlider"] { padding-top:5px; }
.stApp .st-key-top_filters [data-testid="stWidgetLabel"] p { font-weight:750 !important; }
.stApp .st-key-btn_samorzady button { min-height:52px !important; background:rgba(225,239,255,.26) !important;
  border:1.5px solid rgba(255,255,255,.55) !important; justify-content:flex-start !important;
  border-radius:11px !important; padding-left:16px !important; }
.stApp .st-key-btn_samorzady button p { color:#FFFFFF !important; font-size:.90rem !important; font-weight:850 !important; }
.stApp .st-key-btn_samorzady [data-testid="stIconMaterial"] {color:#FFF !important;}
.stApp .st-key-$active_tab button { border-left:6px solid #FB7185 !important; }
.stApp .st-key-filter_year_preset button { font-weight:750 !important; }
.stApp [data-testid="stDownloadButton"] button { border-radius:12px; }
.insight-strip { display:flex;flex-wrap:wrap;gap:9px;margin:10px 0 18px; }
.insight-pill {display:inline-flex;gap:8px;align-items:center;padding:8px 12px;
  border:1px solid $border;border-radius:999px;background:$card;color:$text;font-weight:700;font-size:.84rem;}
@media(max-width:780px) { .stApp .kpi-card { min-height:0 !important; } }
</style>
""")

st.markdown(BASE_CSS.substitute(**P, map=europe_watermark_uri(st.session_state.theme), active_tab=("btn_podsumowanie" if st.session_state.current_tab == TAB_1 else ("btn_kategorie" if st.session_state.current_tab == TAB_2 else "btn_samorzady")), active_theme="theme_light" if st.session_state.theme == "light" else "theme_dark"), unsafe_allow_html=True)

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
    fig.update_layout(template=P["template"], height=h or 420, paper_bgcolor=P["plot_paper"], plot_bgcolor=P["plot_bg"], font=dict(color=P["text"], family=FONT), margin=dict(l=6, r=6, t=10, b=6), separators=", ")
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
# 5. REALNE DANE: wykonanie 2016–2025 (MF / dane.gov.pl)
# ---------------------------------------------------------
# Wyłącznie BUDŻET PAŃSTWA, nie cały sektor finansów publicznych.
# 2016–2021: sumy na podstawie zbiorów MF w opracowaniu budzetpanstwa.pl,
# dokładność 0,1 mld zł; 2022–2025: oficjalne wykonanie MF, 0,0001 mld zł.
# Plany oraz wybrane pozycje podatkowe i części budżetowe: publikacja
# MF/dane.gov.pl opracowana w serwisie budzetpanstwa.pl. Kwoty tych
# składowych są tam prezentowane po zaokrągleniu do 0,1 mld zł.
# Kategoria "Pozostałe" = urzędowa suma roczna minus wymienione składniki,
# więc nie jest dodatkową, fikcyjną pozycją budżetu.

# Historyczne sumy i rozbicie: https://budzetpanstwa.pl/budzet/{rok}
# Serwis niezależny; prezentuje dane źródłowe MF/dane.gov.pl (zbiór 163 i 1179).
SOURCES_HISTORICAL = {r: f"https://budzetpanstwa.pl/budzet/{r}" for r in range(2016, 2022)}

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
    for rok in range(2016, 2026)
}

# total income plan, executed; total spending plan, executed (mld PLN)
ANNUAL_TOTALS = {
    # Zestawienie budzetpanstwa.pl, plan ustawowy i wykonanie (mld zł),
    # dokładność publikacji: 0,1 mld zł; nie są to wymyślone wartości.
    2016: {"income_plan": 313.8, "income_actual": 314.7, "spend_plan": 368.5, "spend_actual": 360.8},
    2017: {"income_plan": 325.4, "income_actual": 350.4, "spend_plan": 384.8, "spend_actual": 375.8},
    2018: {"income_plan": 355.7, "income_actual": 380.0, "spend_plan": 397.2, "spend_actual": 390.5},
    2019: {"income_plan": 387.7, "income_actual": 400.5, "spend_plan": 416.2, "spend_actual": 414.3},
    2020: {"income_plan": 398.7, "income_actual": 419.8, "spend_plan": 508.0, "spend_actual": 504.8},
    2021: {"income_plan": 483.0, "income_actual": 494.8, "spend_plan": 523.5, "spend_actual": 521.2},
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
    # Plan i wykonanie czterech podatków, mld zł; budzetpanstwa.pl/budzet/<rok>.
    2016: {"VAT": (128.7,126.6), "Akcyza": (64.1,65.7), "CIT": (26.1,26.4), "PIT": (46.9,48.2)},
    2017: {"VAT": (143.5,156.8), "Akcyza": (69.0,68.3), "CIT": (29.8,29.8), "PIT": (51.0,52.7)},
    2018: {"VAT": (166.0,174.9), "Akcyza": (70.0,72.1), "CIT": (32.4,34.6), "PIT": (55.5,59.6)},
    2019: {"VAT": (179.6,180.9), "Akcyza": (73.0,72.4), "CIT": (34.8,40.0), "PIT": (64.3,65.4)},
    2020: {"VAT": (170.0,184.6), "Akcyza": (68.4,71.8), "CIT": (38.5,41.3), "PIT": (64.1,63.8)},
    2021: {"VAT": (214.5,215.7), "Akcyza": (75.5,75.8), "CIT": (49.5,52.4), "PIT": (71.3,73.6)},
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
    # Najważniejsze części budżetowe: plan ustawowy, wykonanie (mld zł).
    2016: {"73": (53.8,54.4), "29": (35.5,34.7), "79": (31.8,32.1), "82": (53.0,53.0), "85": (39.4,50.8), "42": (20.2,20.2), "46": (4.5,5.6)},
    2017: {"73": (52.0,50.1), "29": (36.9,36.2), "79": (29.8,29.6), "82": (54.3,54.3), "85": (48.6,57.8), "42": (20.4,21.7), "46": (4.9,7.2)},
    2018: {"73": (56.5,48.6), "29": (40.3,41.8), "79": (30.7,29.5), "82": (56.4,56.4), "85": (50.1,58.6), "42": (20.5,21.4), "46": (5.1,8.1)},
    2019: {"73": (60.4,58.1), "29": (44.0,43.4), "79": (29.2,27.3), "82": (60.8,61.8), "85": (49.4,67.0), "42": (21.5,24.6), "46": (5.4,8.4)},
    2020: {"73": (57.4,54.4), "29": (52.0,51.4), "79": (29.1,29.3), "82": (66.7,67.0), "85": (71.7,78.2), "42": (24.6,24.4), "46": (5.2,6.1)},
    2021: {"73": (62.6,44.3), "29": (58.1,57.1), "79": (26.0,26.0), "82": (82.1,82.3), "85": (73.6,78.8), "42": (27.0,28.3), "46": (12.9,16.0)},
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
# Archiwalny PKB nominalny: GUS, 2016–2017 z korekty za 2019;
# 2018–2021 z rachunków narodowych 2018–2021; rewizje powodują
# nieznaczne różnice pomiędzy historycznymi edycjami publikacji.
PKB_NOMINALNY_MLD = {
    2016: 1863.487, 2017: 1989.835,
    2018: 2126.506, 2019: 2288.492,
    2020: 2337.672, 2021: 2631.302,
    2022: 3100.850,
    2023: 3415.274,
    2024: 3669.531,
    2025: 3915.394,
}

# Obsługa długu Skarbu Państwa: wykonanie, części budżetowej 79, w mld zł.
DEBT_SERVICE_MLD = {
    2016:32.1, 2017:29.6, 2018:29.5, 2019:27.3, 2020:29.3,
    2021:26.0, 2022:32.7, 2023:61.7, 2024:65.8, 2025:72.8,
}

# Regionalne agregaty z serwisu budzetpanstwa.pl/samorzady/wojewodztwo/<slug>.
# Wszystkie JST przypisane do województwa: gminy, powiaty, miasta i samorząd
# wojewódzki. 2025, wykonanie; kwoty dochodów i wydatków 0,1 mld,
# wynik dokładniejszy (0,1 mln zł). NIE SĄ TO KWOTY BUDŻETU WOJEWODY.
# Koordynaty to orientacyjne punkty na mapie, nie granice województw.
# Nazwa; slug; dochody; wydatki; wynik mln PLN; liczba JST; lon; lat.
REGIONAL_JST_2025 = [
    ("dolnośląskie", "dolnoslaskie", 37.4,37.5,-93.7,196,16.9,51.1),
    ("kujawsko-pomorskie", "kujawsko-pomorskie",24.5,24.4,100.9,164,18.4,53.15),
    ("lubelskie", "lubelskie",23.6,23.5,118.3,234,22.6,51.25),
    ("lubuskie", "lubuskie",11.9,12.1,-131.1,95,15.45,52.2),
    ("łódzkie", "lodzkie",28.3,28.5,-196.6,199,19.45,51.75),
    ("małopolskie", "malopolskie",39.8,40.5,-709.9,203,20.0,49.93),
    ("mazowieckie", "mazowieckie",76.0,75.8,210.8,352,21.05,52.15),
    ("opolskie", "opolskie",11.1,11.1,4.5,83,17.92,50.62),
    ("podkarpackie", "podkarpackie",25.5,25.3,137.9,182,22.05,49.98),
    ("podlaskie", "podlaskie",14.9,14.7,210.6,134,23.0,53.08),
    ("pomorskie", "pomorskie",30.5,30.1,408.9,140,18.55,54.05),
    ("śląskie", "slaskie",50.4,50.2,152.8,185,19.15,50.35),
    ("świętokrzyskie", "swietokrzyskie",14.2,14.0,185.4,116,20.75,50.77),
    ("warmińsko-mazurskie", "warminsko-mazurskie",16.9,16.6,282.7,136,20.55,53.77),
    ("wielkopolskie", "wielkopolskie",42.0,41.3,695.7,258,17.35,52.45),
    ("zachodniopomorskie", "zachodniopomorskie",21.1,20.6,441.5,132,15.58,53.48),
]

@st.cache_data
def load_jst_regions():
    df = pd.DataFrame(REGIONAL_JST_2025, columns=[
        "Województwo", "Slug", "Dochody_mld", "Wydatki_mld",
        "Wynik_mln", "Liczba_JST", "Lon", "Lat",
    ])
    df["Wynik_mld"] = df["Wynik_mln"] / 1000
    df["Źródło"] = df["Slug"].map(
        lambda s: f"https://budzetpanstwa.pl/samorzady/wojewodztwo/{s}"
    )
    if len(df)!=16 or df["Liczba_JST"].sum()!=2809:
        raise ValueError("Zestawienie JST musi obejmować 16 regionów i 2809 jednostek")
    return df

def jst_map(df, metric):
    """Interaktywna mapa punktowa z polskim konturem (bez zewnętrznych kafelków)."""
    field = {"Dochody":"Dochody_mld", "Wydatki":"Wydatki_mld", "Wynik":"Wynik_mld"}[metric]
    d = df.copy()
    # Względny rozmiar: w trybie wyniku używamy wartości bezwzględnej.
    val = d[field].abs() if metric=="Wynik" else d[field]
    d["Marker"] = 16 + 36 * ((val / max(float(val.max()), 0.01)) ** 0.5)
    d["Odcień"] = [P["pos"] if v>=0 else P["neg"] for v in d["Wynik_mln"]]
    path_x = [p[0] for p in POLAND] + [POLAND[0][0]]
    path_y = [p[1] for p in POLAND] + [POLAND[0][1]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=path_x, y=path_y, mode="lines", fill="toself",
        fillcolor="rgba(37,99,235,0.08)" if P["scheme"]=="light" else "rgba(96,165,250,.10)",
        line=dict(color=P["accent"], width=1.8), hoverinfo="skip", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=d["Lon"], y=d["Lat"], mode="markers+text", text=d["Województwo"],
        textposition="top center", textfont=dict(color=P["text"],size=10),
        customdata=d[["Dochody_mld","Wydatki_mld","Wynik_mln","Liczba_JST"]].to_numpy(),
        hovertemplate=("<b>%{text}</b><br>Dochody: %{customdata[0]:.1f} mld zł"
                       "<br>Wydatki: %{customdata[1]:.1f} mld zł"
                       "<br>Wynik: %{customdata[2]:.1f} mln zł"
                       "<br>Liczba JST: %{customdata[3]:.0f}<extra></extra>"),
        marker=dict(size=d["Marker"], color=d["Odcień"], opacity=.76,
                    line=dict(color=P["bg"],width=1.7)), showlegend=False,
    ))
    fig.update_xaxes(range=[13.7,24.5], visible=False, fixedrange=False, showgrid=False)
    fig.update_yaxes(range=[48.7,55.15], visible=False, fixedrange=False, showgrid=False,
                     scaleanchor="x", scaleratio=1.6)
    fig.update_layout(template=P["template"], height=520,
                      margin=dict(l=8,r=8,t=16,b=8),
                      paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family=FONT,color=P["text"]))
    return fig

df_raw = load_data()
if df_raw.empty:
    st.error("Nie udało się wczytać wbudowanych danych budżetowych.")
    st.stop()

lata_dostepne = sorted(df_raw["Rok"].unique().tolist())

# ---------------------------------------------------------
# NAWIGACJA 4.0 — ROZBUDOWANY, STAŁY BANER / TABS Z DOLNĄ LINIĄ
# ---------------------------------------------------------
active_key = {TAB_1: "nav_overview", TAB_2: "nav_categories", TAB_3: "nav_regions",
              TAB_4: "nav_game", TAB_5: "nav_cofog"}.get(st.session_state.current_tab, "nav_overview")

# Ostatnia warstwa stylów nadpisuje starszy CSS zachowany dla kompatybilności wykresów.
site_css = f"""
<style>
section[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"], [data-testid="stExpandSidebarButton"] {{ display:none!important; }}
[data-testid="stAppViewContainer"] > .main, [data-testid="stMain"] {{width:100%!important;margin:0!important}}
header[data-testid="stHeader"] {{height:0!important;min-height:0!important;display:none!important}}
.stApp .block-container {{max-width:2100px!important;width:100%!important;
  padding:202px clamp(18px,3.2vw,82px) 82px!important;}}
/* Górna belka jest nieruchoma, a pod nią przewija się wyłącznie strona. */
.stApp .st-key-site_nav {{
  position:fixed!important;inset:0 0 auto 0!important;z-index:9990!important;
  background:linear-gradient(109deg,#08172e 0%,#102a50 37%,#19549a 72%,#0e397d 100%)!important;
  border-bottom:1px solid rgba(147,210,255,.26)!important;
  box-shadow:0 17px 60px rgba(2,19,44,.34)!important;
  padding:9px clamp(17px,3.3vw,78px) 0!important;
  color:white!important;backdrop-filter:blur(22px)!important;
  overflow:visible!important;
}}
.stApp .st-key-site_nav::before {{content:"";position:absolute;inset:0 0 auto 0;height:4px;
  background:linear-gradient(90deg,#44b8ff,#7e98ff,#47e7d1 75%,#ffce73);opacity:.96;}}
.stApp .st-key-site_nav > div {{max-width:2100px!important;margin:0 auto!important;}}
.stApp .st-key-site_nav [data-testid="stHorizontalBlock"] {{gap:clamp(6px,1.35vw,18px)!important;}}
.nav-brand {{display:flex;align-items:center;gap:19px;min-height:96px;padding:4px 0 8px;}}
.nav-brand-icon {{width:96px;height:92px;flex:0 0 96px;background:transparent!important;
 border:0!important;box-shadow:none!important;border-radius:0!important;padding:0!important;}}
.nav-brand-copy {{min-width:0;display:flex;flex-direction:column;gap:5px;}}
.nav-brand-name {{font-size:clamp(1.3rem,2.45vw,2.38rem);line-height:1.02;
  letter-spacing:-.055em;font-weight:900;color:#fff;text-shadow:0 2px 12px rgba(1,22,43,.25);}}
.nav-brand-tagline {{font-size:clamp(.76rem,1vw,.98rem);line-height:1.2;font-weight:720;
  color:#cbe7ff;letter-spacing:.065em;}}
.nav-meta {{display:flex;flex-direction:column;align-items:flex-end;justify-content:center;gap:6px;
  color:#dceeff;text-transform:uppercase;font-weight:750;font-size:.65rem;letter-spacing:.11em;}}
.nav-meta strong {{background:rgba(105,197,255,.15);color:#a8efff;border:1px solid rgba(110,216,255,.32);
  font-size:.70rem;padding:7px 11px;border-radius:999px;white-space:nowrap;}}
.nav-separator {{height:1px;width:100%;margin:0 0 0;background:linear-gradient(90deg,rgba(148,202,255,.08),rgba(148,202,255,.25),rgba(148,202,255,.08));}}
/* Pięć zakładek leży na samym dolnym brzegu baneru. */
.stApp .st-key-site_nav .st-key-nav_tabs [data-testid="stHorizontalBlock"] {{align-items:stretch!important;gap:clamp(1px,.7vw,13px)!important;}}
.stApp .st-key-site_nav .st-key-nav_tabs button {{width:100%!important;min-height:60px!important;
  position:relative!important;overflow:visible!important;
  color:#c8dbf4!important;background:transparent!important;border:0!important;
  border-radius:11px 11px 0 0!important;box-shadow:none!important;
  padding:13px 5px 14px!important;transition:background .22s,color .22s!important;}}
.stApp .st-key-site_nav .st-key-nav_tabs button p {{color:inherit!important;font-size:clamp(.77rem,.89vw,.99rem)!important;
  font-weight:800!important;line-height:1.15!important;white-space:nowrap!important;letter-spacing:.003em;}}
.stApp .st-key-site_nav .st-key-nav_tabs button::after {{content:"";position:absolute;
  bottom:-1px;left:9%;right:9%;height:4px;border-radius:6px 6px 0 0;
  background:linear-gradient(90deg,#53e4ff,#79acff);box-shadow:0 0 14px rgba(83,211,255,.68);
  transform:scaleX(0);transform-origin:50% 50%;opacity:0;
  transition:transform .22s ease,opacity .22s ease;}}
.stApp .st-key-site_nav .st-key-nav_tabs button:hover {{background:rgba(130,203,255,.13)!important;color:#fff!important;}}
.stApp .st-key-site_nav .st-key-nav_tabs button:hover::after {{transform:scaleX(1);opacity:.95;}}
.stApp .st-key-site_nav .st-key-nav_tabs .st-key-{active_key} button {{background:linear-gradient(180deg,rgba(100,197,255,.10),rgba(100,197,255,.22))!important;color:#fff!important;}}
.stApp .st-key-site_nav .st-key-nav_tabs .st-key-{active_key} button::after {{transform:scaleX(1);opacity:1;}}
/* Przełącznik motywu: świadomie wyróżniony ciepłym kolorem. */
.stApp .st-key-site_nav .st-key-nav_theme button {{min-height:42px!important;width:auto!important;max-width:180px!important;margin-left:auto!important;
  color:#18243b!important;background:linear-gradient(115deg,#ffe09b,#ffbe66 50%,#ff9577)!important;
  border:1px solid rgba(255,248,213,.78)!important;border-radius:12px!important;padding:6px 12px!important;
  box-shadow:0 4px 15px rgba(247,158,81,.22),inset 0 1px 0 rgba(255,255,255,.6)!important;
  white-space:nowrap!important;transition:transform .20s,box-shadow .20s!important;}}
.stApp .st-key-site_nav .st-key-nav_theme button p {{color:#152540!important;font-size:.76rem!important;font-weight:850!important;}}
.stApp .st-key-site_nav .st-key-nav_theme button:hover {{transform:translateY(-2px)!important;
  box-shadow:0 8px 30px rgba(255,190,102,.52)!important;}}
/* Panel filtrów jest wyraźnie oddzieloną poziomą konsolą nad wykresami. */
.stApp .st-key-top_filters {{background:{P['card']}!important;
  border:1px solid {P['border']}!important;
  border-top:4px solid {P['accent']}!important;
  border-radius:25px!important;padding:17px 24px 16px!important;
  box-shadow:0 16px 44px rgba(16,35,69,.13)!important;margin:6px 0 20px!important;
  backdrop-filter:blur(20px)!important;}}
.stApp .st-key-top_filters [data-testid="stHorizontalBlock"] {{align-items:center!important;gap:18px!important;}}
.stApp .st-key-top_filters label {{font-size:.84rem!important;font-weight:800!important;}}
.stApp .st-key-top_filters [data-testid="stSegmentedControl"] {{min-height:45px!important;}}
.stApp .st-key-top_filters [data-testid="stSegmentedControl"] button {{border-radius:12px!important;}}
.filter-topline {{display:flex;align-items:center;justify-content:space-between;gap:12px;
  padding:0 0 13px;margin:0 0 12px;border-bottom:1px solid {P['border']};}}
.filter-eyebrow {{text-transform:uppercase;letter-spacing:.15em;font-size:.72rem;font-weight:920;color:{P['accent']};}}
.filter-subtitle {{font-size:.83rem;font-weight:600;color:{P['muted']};}}
.filter-mini-label {{font-size:.77rem;font-weight:780;color:{P['muted']};padding-top:5px;}}
.filter-selected-pill {{background:linear-gradient(125deg,{P['accent']}16,{P['accent']}0a);
 border:1px solid {P['border']};border-radius:16px;padding:10px 14px;text-align:center;}}
.filter-selected-pill b {{display:block;font-weight:920;font-size:1.24rem;color:{P['text']};}}
.filter-selected-pill small {{font-size:.70rem;color:{P['muted']};font-weight:750;}}
.visuals-separator {{display:flex;align-items:center;gap:17px;margin:19px 0 18px;
 font-weight:900;letter-spacing:.18em;font-size:.71rem;color:{P['muted']};text-transform:uppercase;}}
.visuals-separator::before,.visuals-separator::after {{content:"";height:1px;flex:1;
 background:linear-gradient(90deg,transparent,{P['border']});}}
.visuals-separator::after {{transform:rotate(180deg);}}
.portal-kicker {{text-transform:uppercase;font-size:.74rem;letter-spacing:.17em;color:{P['accent']};font-weight:850;margin:12px 0 12px;}}
.portal-title {{font-size:clamp(2rem,3.35vw,3.45rem);font-weight:880;letter-spacing:-.055em;line-height:1.07;color:{P['text']};}}
.portal-lead {{font-size:1.02rem;color:{P['muted']};margin:10px 0 21px;max-width:1150px;}}
.stApp .dash-title {{font-size:clamp(2.1rem,3.4vw,3.7rem)!important;letter-spacing:-.06em!important;}}
.stApp .kpi-card {{min-height:255px!important;border-radius:24px!important;border:1px solid {P['border']}!important;transition:transform .22s,box-shadow .22s!important;}}
.stApp .kpi-card:hover {{transform:translateY(-3px);box-shadow:0 14px 42px rgba(28,62,105,.16)!important;}}
.stApp .card-box,.stApp .financial-balance {{border-radius:23px!important;}}
.stApp .st-key-game_panel_programs,.stApp .st-key-game_panel_parts,
.stApp .st-key-game_panel_revenue,.stApp .st-key-game_panel_waterfall,.stApp .st-key-game_panel_change,
.stApp .st-key-game_panel_electoral,.stApp .st-key-cofog_panel_rank,
.stApp .st-key-cofog_panel_trend,.stApp .st-key-cofog_panel_heat,
.stApp .st-key-cofog_panel_table {{border-radius:22px!important;background:{P['card']}!important;
 border:1px solid {P['border']}!important;box-shadow:{P['shadow']}!important;
 padding:19px 23px 17px!important;margin:9px 0 18px!important;backdrop-filter:blur(14px)!important;}}
.stApp button[kind="primary"] {{border-radius:13px!important;}}
.stApp [data-testid="stMetric"] {{background:{P['card']};border:1px solid {P['border']};border-radius:18px;padding:15px;}}
.stApp [data-testid="stMetricValue"] {{font-weight:830!important;letter-spacing:-.045em;}}
.stApp .stTabs [data-baseweb="tab-list"] {{border-bottom:1px solid {P['border']}!important;gap:6px;}}
.stApp .stTabs button {{border-radius:13px 13px 0 0!important;padding:10px 19px!important;}}
.stApp [data-testid="stAlert"] {{border-radius:16px!important;}}
/* Krok po kroku: nowa gra 5.0 "Zaprojektuj budżet". */
.game5-progress {{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:14px 0 21px;}}
.game5-stage {{display:flex;align-items:center;gap:12px;background:{P['card']};
 border:1px solid {P['border']};border-radius:17px;padding:13px 16px;color:{P['muted']};}}
.game5-stage span {{width:33px;height:33px;border-radius:11px;display:grid;place-items:center;
 font-weight:900;background:{P['th']};flex:0 0 33px;font-size:.82rem;}}
.game5-stage strong {{font-size:.9rem;font-weight:830;}}
.game5-stage.active {{border:1.5px solid #59b5ff;box-shadow:0 6px 19px rgba(45,131,231,.13);
 background:linear-gradient(115deg,rgba(74,158,247,.14),{P['card']});color:{P['text']};}}
.game5-stage.active span {{background:linear-gradient(125deg,#246ac9,#56c3e7);color:#fff;}}
.game5-stage.done span {{background:#0d9d84;color:#fff;}}
.stApp .st-key-game5_live {{border:1px solid {P['border']}!important;border-radius:22px!important;
 background:{P['card']}!important;padding:15px 17px!important;margin:7px 0 20px!important;
 box-shadow:{P['shadow']}!important;}}
.stApp .st-key-game5_panel {{border:1px solid {P['border']}!important;border-radius:25px!important;
 background:{P['card']}!important;padding:24px clamp(18px,3vw,35px)!important;
 margin-bottom:15px!important;box-shadow:{P['shadow']}!important;}}
.stApp .st-key-game5_panel h3 {{margin-top:8px!important;}}
.stApp .st-key-game5_panel h4 {{margin:20px 0 7px!important;font-size:1.05rem!important;}}
.game5-value {{display:flex;flex-direction:column;align-items:flex-end;line-height:1.2;
 color:{P['text']};font-size:1.05rem;font-weight:900;white-space:nowrap;}}
.game5-value small {{font-size:.74rem;font-weight:660;}}
.game5-value span {{color:{P['muted']};font-size:.71rem;font-weight:680;margin-top:5px;}}
.game5-example {{background:linear-gradient(120deg,rgba(44,137,234,.12),rgba(78,187,200,.08));
 border:1px solid rgba(73,149,222,.24);border-radius:18px;padding:14px 18px;
 display:flex;gap:9px;align-items:center;flex-wrap:wrap;color:{P['text']};}}
.game5-example strong {{font-size:1.24rem;}}
.game5-example span {{color:{P['muted']};font-size:.83rem;font-weight:640;}}
@media(max-width:810px){{.game5-progress{{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;}}
 .game5-stage{{padding:10px 9px;gap:7px;}}.game5-stage strong{{font-size:.73rem;}}
 .game5-stage span{{width:26px;height:26px;flex-basis:26px;}}}}
/* Film otwierający jest pełnoekranowy, automatyczny i znika bez przeładowania. */
.intro-overlay {{position:fixed;z-index:100000;inset:0;overflow:hidden;isolation:isolate;
 background:linear-gradient(135deg,#07162b,#0b3152 52%,#235e91);color:white;display:flex;align-items:center;
 animation:intro-close 8.2s linear forwards;}}
.intro-overlay::after {{content:"";position:absolute;inset:0;z-index:1;
 background:linear-gradient(90deg,rgba(2,10,27,.82),rgba(2,10,25,.2) 75%),
 linear-gradient(0deg,rgba(4,15,36,.7),transparent 50%,rgba(4,15,36,.35));}}
/* Film od autora: zdalny player YouTube przyklejony jak pełnoekranowe wideo.
   Zachowujemy zdjęcie lotnicze pod spodem jako zabezpieczenie przed blokadą autoplay. */
.intro-poster {{position:absolute;inset:0;background-position:center 48%;background-repeat:no-repeat;
 background-size:cover;transform:scale(1.05);filter:saturate(1.08) contrast(1.06);}}
.intro-yt-frame {{position:absolute;inset:0;overflow:hidden;pointer-events:none;z-index:0;}}
.intro-yt-frame iframe {{position:absolute;top:50%;left:50%;border:0;pointer-events:none;
 width:max(100vw,177.78vh);height:max(100vh,56.25vw);
 transform:translate(-50%,-50%) scale(1.05);filter:saturate(1.05) contrast(1.04);}}
.intro-logo-row {{display:flex;align-items:center;gap:25px;margin-bottom:18px;}}
.intro-logo {{width:clamp(90px,10vw,136px);height:clamp(90px,10vw,136px);
 flex:none;filter:drop-shadow(0 0 30px rgba(70,178,255,.26));}}
.intro-place {{position:absolute;bottom:32px;left:clamp(22px,5.5vw,110px);
 z-index:4;color:rgba(235,246,255,.87);font-weight:750;letter-spacing:.04em;font-size:.76rem;}}
.intro-place b {{color:white;font-size:.86rem;}}
@media(max-width:760px) {{.intro-logo-row {{gap:10px;margin-bottom:8px;}}
 .intro-logo {{width:88px;height:88px;}}.intro-place {{bottom:68px;font-size:.68rem;}}
 .intro-credit {{bottom:24px!important;left:22px;right:auto!important;font-size:.64rem!important;}}}}
.intro-video {{width:100%;height:100%;position:absolute;inset:0;object-fit:cover;opacity:.98;
 filter:saturate(1.05) contrast(1.06);animation:intro-video-move 8s ease-out both;}}
@keyframes intro-video-move {{0%{{transform:scale(1.03)}}100%{{transform:scale(1.13)}}}}
.intro-credit {{position:absolute;bottom:30px;right:34px;font-size:.72rem;font-weight:600;
 color:#bfd5e6;z-index:3;letter-spacing:.04em;opacity:.8;}}
.intro-credit a {{color:#c2edff!important;text-decoration:none;border-bottom:1px solid rgba(194,237,255,.38);}}
.intro-credit a:hover {{color:#ffffff!important;}}
.intro-pulses {{display:flex;gap:6px;align-items:center;}}
.intro-pulses i {{width:6px;height:6px;display:block;border-radius:50%;background:#83deff;
 animation:intro-dot 1.1s ease-in-out infinite alternate;}}
.intro-pulses i:nth-child(2){{animation-delay:.2s}}
.intro-pulses i:nth-child(3){{animation-delay:.4s}}
@keyframes intro-dot {{to {{opacity:.25;transform:translateY(-4px)}}}}
.intro-content {{position:relative;z-index:2;padding:clamp(25px,7.5vw,150px);width:min(100%,1080px);
 animation:intro-title-reveal .85s ease-out both;}}
@keyframes intro-title-reveal {{from{{opacity:0;transform:translateY(19px)}}to{{opacity:1;transform:translateY(0)}}}}
.intro-badge {{display:inline-flex;align-items:center;gap:12px;border:1px solid rgba(138,213,255,.4);
 background:rgba(20,75,132,.38);border-radius:100px;padding:9px 17px;
 color:#bceaff;font-size:.75rem;font-weight:850;letter-spacing:.16em;}}
.intro-heading {{font-size:clamp(2.6rem,7.6vw,7rem);letter-spacing:-.07em;
 line-height:.98;font-weight:900;margin:27px 0 20px;text-shadow:0 8px 36px rgba(0,0,0,.24);}}
.intro-heading b {{color:#8cecff;}}
.intro-tagline {{font-size:clamp(1rem,1.65vw,1.6rem);font-weight:780;letter-spacing:.07em;color:#d6eeff;}}
.intro-desc {{display:none!important;}}
.intro-loading {{max-width:420px;margin-top:55px;}}
.intro-loading-label {{display:flex;justify-content:space-between;font-size:.75rem;font-weight:780;
 letter-spacing:.13em;color:#c3def6;}}
.intro-loading-track {{height:5px;margin-top:14px;border-radius:20px;overflow:hidden;background:rgba(176,215,255,.19);}}
.intro-loading-progress {{height:100%;width:0;border-radius:20px;background:linear-gradient(90deg,#51cbff,#96e7e7,#fad07e);
 box-shadow:0 0 18px rgba(130,233,255,.6);animation:intro-progress 7.45s ease-in-out forwards;}}
.stApp .st-key-intro_skip {{position:fixed!important;right:clamp(18px,4vw,80px);top:30px;z-index:100001!important;
 animation:intro-hide-skip 8.2s linear forwards;}}
.stApp .st-key-intro_skip button {{color:#fff!important;background:rgba(8,32,69,.58)!important;
 border:1px solid rgba(202,229,253,.42)!important;border-radius:999px!important;padding:9px 18px!important;
 backdrop-filter:blur(12px)!important;}}
.stApp .st-key-intro_skip button p {{font-weight:750!important;color:#fff!important;}}
@keyframes intro-progress {{0%{{width:0}} 16%{{width:17%}} 50%{{width:57%}} 85%{{width:90%}} 100%{{width:100%}}}}
@keyframes intro-close {{0%,86%{{opacity:1;visibility:visible;pointer-events:auto}}100%{{opacity:0;visibility:hidden;pointer-events:none}}}}
@keyframes intro-hide-skip {{0%,85%{{opacity:1;visibility:visible;pointer-events:auto}}100%{{opacity:0;visibility:hidden;pointer-events:none}}}}
@media(max-width:1180px) {{
 .nav-brand-name {{font-size:1.44rem;}}.nav-brand-tagline {{font-size:.76rem;}}
 .nav-meta {{display:none;}}.stApp .st-key-site_nav .st-key-nav_tabs button p {{font-size:.78rem!important;}}
 .stApp .st-key-site_nav .st-key-nav_theme button p {{font-size:.73rem!important;}}
}}
@media(max-width:760px) {{
 .stApp .block-container {{padding:181px 13px 40px!important;}}
 .stApp .st-key-site_nav {{padding:7px 12px 0!important;}}
 .nav-brand {{gap:9px;min-height:77px;padding:0 0 7px;}}
 .nav-brand-icon {{height:57px;width:57px;flex-basis:57px;padding:0;border-radius:0;}}
 .nav-brand-name {{font-size:clamp(.98rem,3.6vw,1.25rem);line-height:1.04;}}
 .nav-brand-tagline {{font-size:clamp(.57rem,2vw,.71rem);letter-spacing:.015em;}}
 .stApp .st-key-site_nav [data-testid="stHorizontalBlock"] {{flex-wrap:nowrap!important;gap:3px!important;}}
 .stApp .st-key-site_nav .st-key-nav_tabs button {{min-height:58px!important;padding:10px 1px!important;}}
 .stApp .st-key-site_nav .st-key-nav_tabs button p {{font-size:clamp(.55rem,2.1vw,.73rem)!important;
   white-space:normal!important;overflow-wrap:break-word!important;}}
 .stApp .st-key-site_nav .st-key-nav_theme button {{min-height:37px!important;padding:4px 8px!important;max-width:145px!important;}}
 .stApp .st-key-site_nav .st-key-nav_theme button p {{font-size:.65rem!important;}}
 .stApp .st-key-top_filters {{padding:14px 14px!important;}}
 .filter-topline {{align-items:start;flex-direction:column;gap:5px;}}
 .intro-heading {{font-size:clamp(2.65rem,11vw,4.3rem);}}
 .intro-content {{padding:26px;}}
 .intro-loading {{margin-top:38px;}}
 .stApp .kpi-card {{min-height:0!important;}}
}}
/* 6.0 — ujednolicone karty wykresów, rozbudowane decyzje gry */
.stApp .st-key-panel_income, .stApp .st-key-panel_spending,
.stApp .st-key-panel_trend_budget, .stApp .st-key-panel_trend_result,
.stApp .st-key-panel_category_main, .stApp .st-key-panel_category_share,
.stApp .st-key-panel_yoy, .stApp .st-key-panel_debt,
.stApp .st-key-panel_jst_map, .stApp .st-key-panel_jst_ranking,
.stApp .st-key-cofog_panel_rank, .stApp .st-key-cofog_panel_trend {{
    min-height: 510px !important; box-sizing: border-box !important;
}}
.stApp .st-key-panel_jst_map, .stApp .st-key-panel_jst_ranking {{min-height:660px!important;}}
.stApp .st-key-cofog_panel_rank,.stApp .st-key-cofog_panel_trend {{min-height:680px!important;}}
.game6-decision {{display:flex;flex-direction:column;gap:9px;padding:20px 24px;
    border:1px solid rgba(111,145,190,.27);border-left:5px solid #478ff7;
    border-radius:18px;background:rgba(127,168,210,.08);margin:11px 0;}}
.game6-decision b {{font-size:1.02rem;letter-spacing:-.02em;}}
.game6-decision span {{font-size:.93rem;opacity:.8;}}
.game6-decision strong {{font-size:1rem;}}
.game6-decision p {{margin:0!important;font-size:.91rem;line-height:1.5;opacity:.84;}}
.stApp [data-testid="stMetric"] {{min-height:110px;}}
.stApp [data-testid="stPlotlyChart"] {{width:100%!important;}}
.stApp .st-key-game5_panel h4 {{margin-top:16px;}}
@media(max-width:1000px) {{
    .stApp .st-key-panel_income,.stApp .st-key-panel_spending,
    .stApp .st-key-panel_trend_budget,.stApp .st-key-panel_trend_result,
    .stApp .st-key-panel_category_main,.stApp .st-key-panel_category_share,
    .stApp .st-key-cofog_panel_rank,.stApp .st-key-cofog_panel_trend {{min-height:0!important;}}
}}
@media(prefers-reduced-motion:reduce) {{
 .intro-overlay,.stApp .st-key-intro_skip {{animation-duration:.15s!important;}}
 .intro-loading-progress {{animation-duration:.15s!important;}}
 .stApp * {{scroll-behavior:auto!important;}}
}}
</style>
"""
st.markdown(site_css, unsafe_allow_html=True)

# Ujęcie miasta wybierane tylko raz na pierwsze otwarcie sesji.
# Wideo jest odtwarzane z oficjalnego serwera autora, bez lokalnych assetów.
if not st.session_state.get("splash_shown", False):
    intro_city = intro_pick_city()
    poster = escape(intro_city['poster'], quote=True)
    city_name = escape(intro_city['city'])
    location_name = escape(intro_city['location'])
    credit = escape(intro_city['credit'])
    video_source = escape(intro_city['source'], quote=True)
    poster_credit = intro_city.get('poster_credit', '')
    # Oba źródła osadzane, a nie pobierane czy dołączane jako osobny asset.
    if intro_city.get('provider') == 'youtube':
        youtube_id = escape(intro_city['youtube_id'], quote=True)
        start_sec = int(intro_city.get('start', 0))
        iframe_src = (
            f'https://www.youtube-nocookie.com/embed/{youtube_id}'
            f'?autoplay=1&mute=1&controls=0&loop=1&playlist={youtube_id}'
            f'&start={start_sec}&playsinline=1&rel=0&iv_load_policy=3&disablekb=1'
        )
        moving_background = (
            '<div class="intro-yt-frame">'
            f'<iframe src="{iframe_src}" title="Panorama miasta {city_name} z lotu ptaka" '
            'referrerpolicy="strict-origin-when-cross-origin" '
            'allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen '
            'tabindex="-1" aria-hidden="true"></iframe></div>'
        )
    else:
        mp4_src = escape(intro_city['video'], quote=True)
        moving_background = (
            '<video class="intro-video" autoplay muted playsinline loop preload="metadata" '
            f'aria-hidden="true" poster="{poster}" src="{mp4_src}"></video>'
        )
    st.markdown(
        '<div class="intro-overlay" aria-label="Ekran startowy Polskiego Obserwatora Budżetowego">'
        f'<div class="intro-poster" style="background-image:url(\'{poster}\')"></div>'
        + moving_background
        + '<div class="intro-content">'
        + f'<div class="intro-logo-row"><div class="intro-logo">{logo_img(136)}</div>'
        + '<div class="intro-badge">ANALITYKA FINANSÓW PUBLICZNYCH</div></div>'
        + '<div class="intro-heading">POLSKI<br><b>OBSERWATOR</b><br>BUDŻETOWY</div>'
        + '<div class="intro-tagline">Dane. Decyzje. Odpowiedzialność.</div>'
        + '<div class="intro-loading"><div class="intro-loading-label">'
        + '<span>PRZYGOTOWUJEMY ANALIZY</span><span class="intro-pulses"><i></i><i></i><i></i></span></div>'
        + '<div class="intro-loading-track"><div class="intro-loading-progress"></div></div></div>'
        + '</div>'
        + f'<div class="intro-place">{city_name} &nbsp;·&nbsp; {location_name}</div>'
        + f'<div class="intro-credit">Film: {credit} · <a target="_blank" rel="noopener noreferrer" href="{video_source}">Źródło</a>'
        + (f' · kadr awaryjny: {escape(poster_credit)}' if poster_credit else '')
        + '</div></div>',
        unsafe_allow_html=True
    )
    with st.container(key="intro_skip"):
        st.button("Pomiń intro →", key="intro_skip_btn", help="Przejdź od razu do analiz")
    st.session_state.splash_shown = True

with st.container(key="site_nav"):
    c_brand, c_badge, c_theme = st.columns([6.25, 1.0, 1.18], gap="medium", vertical_alignment="center")
    with c_brand:
        st.markdown(
            f'<div class="nav-brand"><div class="nav-brand-icon">{logo_img(98)}</div>'
            '<div class="nav-brand-copy">'
            '<div class="nav-brand-name">Polski Obserwator Budżetowy</div>'
            '<div class="nav-brand-tagline">Dane. Decyzje. Odpowiedzialność.</div>'
            '</div></div>', unsafe_allow_html=True
        )
    with c_badge:
        st.markdown('<div class="nav-meta"><strong>2016–2025</strong><span>Finanse publiczne</span></div>', unsafe_allow_html=True)
    with c_theme:
        st.button("☾  Ciemny" if st.session_state.theme == "light" else "☀  Jasny",
                  key="nav_theme", use_container_width=True,
                  help="Przełącz wygląd jasny / ciemny", on_click=set_theme,
                  args=("dark" if st.session_state.theme == "light" else "light",))
    st.markdown('<div class="nav-separator"></div>', unsafe_allow_html=True)
    with st.container(key="nav_tabs"):
        tabs = st.columns([1.7, 1.7, 1.6, 1.85, 1.55], gap="small", vertical_alignment="bottom")
        for slot, label, key, page in zip(
            tabs,
            ["Stan budżetu", "Kategorie wydatków", "Finanse samorządów", "Zaprojektuj budżet", "Eurostat COFOG"],
            ["nav_overview", "nav_categories", "nav_regions", "nav_game", "nav_cofog"],
            [TAB_1, TAB_2, TAB_3, TAB_4, TAB_5],
        ):
            with slot:
                st.button(label, key=key, use_container_width=True, on_click=set_tab, args=(page,))

# ---------------------------------------------------------
# FILTRY 2.0 — szybkie presety i interaktywny zakres lat (2016–2025).
# Nie pokazujemy okresu 2016–2025 przy danych JST, które są z 2025 r.
# ---------------------------------------------------------
def opis_zakresu_lat(lata):
    lata = sorted({int(y) for y in lata})
    if not lata: return "brak lat"
    return str(lata[0]) if len(lata)==1 else f"{lata[0]}–{lata[-1]}"

if st.session_state.current_tab in (TAB_1, TAB_2):
    with st.container(key="top_filters"):
        st.markdown(
            '<div class="filter-topline">'
            '<div class="filter-eyebrow">◈ &nbsp; PANEL FILTRÓW</div>'
            '<div class="filter-subtitle">Zmień zakres, a wszystkie wizualizacje zaktualizują się automatycznie.</div>'
            '</div>', unsafe_allow_html=True
        )
        c_typ, c_preset, c_range, c_summary = st.columns([1.35, 2.65, 1.55, 1.15], gap="medium", vertical_alignment="center")
        with c_typ:
            if st.session_state.current_tab == TAB_2:
                wybrany_typ = st.selectbox(
                    "Rodzaj pozycji", ["Wszystkie", "Dochody", "Wydatki"],
                    key="filter_type_modern",
                )
            else:
                wybrany_typ = "Wszystkie"
                st.markdown('<div class="filter-mini-label">TYP ANALIZY</div>', unsafe_allow_html=True)
                st.markdown("**Dochody i wydatki**")
                st.caption("Dane roczne · wykonanie")
        with c_preset:
            preset = st.segmented_control(
                "Szybki wybór okresu",
                ["Cały okres", "Ostatnie 5 lat", "Ostatni rok", "Własny zakres"],
                key="filter_year_preset", default="Cały okres",
            ) or "Cały okres"
        with c_range:
            if preset == "Własny zakres":
                dolny, gorny = st.select_slider(
                    "Lata od–do", options=lata_dostepne,
                    value=(lata_dostepne[0], lata_dostepne[-1]),
                    key="filter_year_range",
                )
                wybrane_lata = list(range(int(dolny), int(gorny) + 1))
            else:
                ostatni = lata_dostepne[-1]
                wybrane_lata = (lata_dostepne if preset == "Cały okres"
                               else list(range(max(lata_dostepne[0], ostatni-4), ostatni+1))
                               if preset == "Ostatnie 5 lat" else [ostatni])
                st.markdown('<div class="filter-mini-label">ZAKRES CZASOWY</div>', unsafe_allow_html=True)
                st.markdown(f"**{opis_zakresu_lat(wybrane_lata)}**")
        with c_summary:
            st.markdown(
                f'<div class="filter-selected-pill"><small>AKTYWNY OKRES</small>'
                f'<b>{len(wybrane_lata)} {"rok" if len(wybrane_lata) == 1 else "lat"}</b>'
                '</div>', unsafe_allow_html=True
            )
    st.markdown('<div class="visuals-separator">Wizualizacje i wnioski</div>', unsafe_allow_html=True)
    st.markdown(section_header(
        "Stan budżetu" if st.session_state.current_tab == TAB_1 else "Budżet w kategoriach",
        "Wykonanie budżetu państwa · dane nominalne, mld zł · Ministerstwo Finansów",
        opis_zakresu_lat(wybrane_lata)), unsafe_allow_html=True)

else:
    wybrany_typ = "Wszystkie"
    wybrane_lata = lata_dostepne

wybrane_lata = sorted(int(y) for y in wybrane_lata)
df_filtered = df_raw[df_raw["Rok"].isin(wybrane_lata)].copy()
if wybrany_typ != "Wszystkie":
    df_filtered = df_filtered[df_filtered["Typ_Pozycji"]==wybrany_typ].copy()
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
    # Dodatkowe dane i analiza: dynamika rok do roku oraz koszt obsługi długu.
    st.markdown("### Więcej o finansach państwa")
    a_yoy, a_debt = st.columns(2, gap="medium")
    with a_yoy:
        with st.container(key="panel_yoy"):
            st.markdown('<div class="card-title">📊 Dynamika dochodów i wydatków r/r</div>'
                        '<div class="card-note">Zmiana nominalna względem roku poprzedniego; nie jest skorygowana o inflację. Dla pierwszego wybranego roku porównujemy z poprzednim dostępnym rokiem, jeżeli istnieje.</div>',
                        unsafe_allow_html=True)
            pełne = df_raw.groupby(["Rok","Typ_Pozycji"])["Wykonanie_mld_PLN"].sum().unstack().sort_index()
            zmiany = pełne.pct_change(fill_method=None).mul(100).loc[wybrane_lata].reset_index()
            zmiany = zmiany.melt(id_vars="Rok", value_vars=["Dochody","Wydatki"],
                                 var_name="Typ_Pozycji", value_name="Zmiana_rdr")
            zmiany = zmiany.dropna(subset=["Zmiana_rdr"])
            if not zmiany.empty:
                wyk_yoy = px.bar(zmiany,x="Rok",y="Zmiana_rdr",color="Typ_Pozycji",
                                 barmode="group",color_discrete_map=color_map_typ,
                                 labels={"Zmiana_rdr":"Zmiana r/r (%)","Rok":""})
                wyk_yoy.update_xaxes(type="category")
                show_fig(style_fig(wyk_yoy,legend_top=True,h=420))
            else: st.info("Brak wcześniejszego roku do obliczenia dynamiki.")
    with a_debt:
        with st.container(key="panel_debt"):
            st.markdown('<div class="card-title">🏦 Obsługa długu Skarbu Państwa</div>'
                        '<div class="card-note">Wykonanie części budżetowej 79 (mld zł), nie całkowita wielkość długu publicznego.</div>',
                        unsafe_allow_html=True)
            debt = pd.DataFrame([{"Rok":y,"Koszt_mld":DEBT_SERVICE_MLD[y]} for y in wybrane_lata])
            wyk_debt = px.bar(debt,x="Rok",y="Koszt_mld",text="Koszt_mld",
                              labels={"Koszt_mld":"Wykonanie (mld zł)","Rok":""})
            wyk_debt.update_traces(marker_color=P["accent"],texttemplate="%{y:.1f}",textposition="outside")
            wyk_debt.update_xaxes(type="category")
            show_fig(style_fig(wyk_debt,h=310))
    st.caption('Pełny szereg budżetowy pozostaje dostępny w eksporcie danych. '
               'Końcową tabelę zastąpiły wykresy i podsumowania na tej stronie.')
elif st.session_state.current_tab == TAB_3:
    st.markdown(section_header(
        "Finanse samorządów",
        "Mapa dochodów, wydatków i wyniku wszystkich typów JST według województw",
        "Wykonanie 2025"), unsafe_allow_html=True)
    st.info(
        "**Zakres mapy: 2025 r.** Suma gmin, miast na prawach powiatu, powiatów "
        "i samorządów wojewódzkich w każdym regionie. "
        "To nie są wyłącznie budżety urzędów marszałkowskich ani wojewodów. "
        "Transfery między JST mogą powodować podwójne ujęcie kwot."
    )
    jst = load_jst_regions()
    with st.container(key="top_filters"):
        st.markdown(
            '<div class="filter-topline"><div class="filter-eyebrow">◈ &nbsp; FILTRY SAMORZĄDOWE</div>'
            '<div class="filter-subtitle">Wskaźnik steruje mapą i rankingiem; wybór regionu wskazuje źródło danych.</div></div>',
            unsafe_allow_html=True
        )
        jm, jr, js = st.columns([1.7, 1.5, 0.7], vertical_alignment="center")
        with jm:
            wybrana_miara = st.segmented_control(
                "Porównywana wielkość", ["Dochody", "Wydatki", "Wynik"],
                default="Dochody", key="jst_map_metric") or "Dochody"
        with jr:
            wybrany_region = st.selectbox(
                "Województwo — źródło danych", sorted(jst["Województwo"].tolist()),
                key="jst_region_source")
        with js:
            st.markdown('<div class="filter-selected-pill"><small>ROK DANYCH</small><b>2025</b></div>', unsafe_allow_html=True)
    st.markdown('<div class="visuals-separator">Mapa i porównania regionalne</div>', unsafe_allow_html=True)
    j1,j2,j3,j4 = st.columns(4, gap="medium")
    with j1: st.metric("Dochody JST w Polsce", "468,2 mld zł", help="budzetpanstwa.pl: wykonanie za 2025 r.; suma dokładniejszych kwot źródłowych")
    with j2: st.metric("Wydatki JST w Polsce", "466,4 mld zł", help="budzetpanstwa.pl: wykonanie za 2025 r.")
    with j3: st.metric("Wynik budżetów JST", "+1,8 mld zł", help="Zaokrąglony wynik na podstawie dokładniejszych kwot niż wyświetlane sumy")
    with j4: st.metric("Liczba jednostek", "2 809", help="Gminy, miasta na prawach powiatu, powiaty, samorządy wojewódzkie")
    st.markdown('<div class="insight-strip">'
        '<span class="insight-pill">🟢 Zielony: nadwyżka</span>'
        '<span class="insight-pill">🔴 Czerwony: deficyt</span>'
        '<span class="insight-pill">◯ Rozmiar punktu: wartość wskaźnika</span>'
        '</div>', unsafe_allow_html=True)
    map_col, rank_col = st.columns([1.55,1.0],gap="large")
    with map_col:
        with st.container(key="panel_jst_map"):
            st.markdown('<div class="card-title">🗺️ Finanse JST na mapie Polski</div>',unsafe_allow_html=True)
            show_fig(jst_map(jst,wybrana_miara))
            st.caption("Punkty pokazują orientacyjne położenie województw, a nie ich granice. Najedź na punkt, aby sprawdzić wartości i liczbę jednostek.")
    with rank_col:
        with st.container(key="panel_jst_ranking"):
            st.markdown('<div class="card-title">🏅 Ranking regionów</div>',unsafe_allow_html=True)
            kolumna = {"Dochody":"Dochody_mld", "Wydatki":"Wydatki_mld", "Wynik":"Wynik_mld"}[wybrana_miara]
            ranked = jst.sort_values(kolumna,ascending=True)
            fig_ranking = px.bar(
                ranked,x=kolumna,y="Województwo",orientation="h",
                color="Wynik_mln" if wybrana_miara == "Wynik" else None,
                color_continuous_scale=[P["neg"],P["pos"]] if wybrana_miara=="Wynik" else None,
                labels={kolumna:f"{wybrana_miara} (mld zł)"})
            fig_ranking.update_layout(showlegend=False,coloraxis_showscale=False)
            if wybrana_miara != "Wynik": fig_ranking.update_traces(marker_color=P["accent"])
            show_fig(style_fig(fig_ranking,h=560))
    st.download_button("Pobierz dane JST (CSV)",
        data=jst.to_csv(index=False).encode("utf-8-sig"),
        file_name="samorzady_wojewodztwa_2025.csv", mime="text/csv")
    adres = jst.set_index("Województwo").loc[wybrany_region,"Źródło"]
    st.link_button(f"Źródło dla regionu: {wybrany_region}",adres)
    st.caption(
        "Źródło: budzetpanstwa.pl, na podstawie sprawozdań Rb-27S/Rb-28S MF / dane.gov.pl, "
        "zbiór 872. Prezentacja regionów: wartości dochodów i wydatków zaokrąglone "
        "do 0,1 mld zł, wynik do 0,1 mln zł. Dlatego różnica widocznych kwot może nie odpowiadać dokładnie wynikowi. "
        "Mapa i ranking pokazują 2025; dla 2016–2024 nie przypisujemy sztucznych danych regionalnych."
    )
elif st.session_state.current_tab == TAB_4:
    sim_show_game(P, ANNUAL_TOTALS[2025], SPENDING_COMPONENTS[2025], INCOME_COMPONENTS[2025])
elif st.session_state.current_tab == TAB_5:
    cofog_show_cofog(P)
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
                style_fig(fig, legend_top=True, h=440)
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
            style_fig(fig, legend_top=True, h=440)
            show_fig(fig)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_filtered.to_excel(writer, index=False, sheet_name="Dane_Przefiltrowane")
        st.download_button(label="Pobierz przefiltrowane dane (.xlsx)", data=output.getvalue(), file_name="Raport_Finansowy_Dane.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ---------------------------------------------------------
# 6. JAWNE ŹRÓDŁA I METODOLOGIA
# ---------------------------------------------------------
if st.session_state.current_tab in (TAB_1,TAB_2,TAB_3):
    st.caption(
        "Wykonanie budżetu państwa: 2016–2025 (MF / dane.gov.pl). "
        "Sumy 2016–2021 zaokrąglono do 0,1 mld zł według budzetpanstwa.pl; "
        "sumy 2022–2025 pochodzą z rocznych sprawozdań MF. Podkategorie "
        "podatkowe i największe części budżetowe — z prezentacji danych MF/dane.gov.pl "
        "w serwisie budzetpanstwa.pl (zaokrąglenie do 0,1 mld zł). "
        "Finanse JST na mapie: regiony 2025, oparte na sprawozdaniach MF. "
        "Ostatni pełny rok wykonania: 2025; brak sztucznie prognozowanych liczb."
    )
    with st.expander("Źródła danych i sposób obliczeń"):
        st.markdown("**Budżet państwa 2016–2021 — opracowanie danych MF/dane.gov.pl:**")
        for rok, url in SOURCES_HISTORICAL.items():
            st.markdown(f"- [{rok}: roczne zestawienie i źródła na budzetpanstwa.pl]({url})")
        st.markdown("**Budżet państwa 2022–2025 — roczne sprawozdania Ministerstwa Finansów:**")
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
            "PKB nominalny: [GUS, dane historyczne 2016–2019]"
            "(https://stat.gov.pl/files/gfx/portalinformacyjny/pl/defaultaktualnosci/5481/9/6/1/informacja_gus_w_sprawie_skorygowanego_szacunku_pkb_za_2019_r.pdf), "
            "[GUS, rachunki narodowe 2018–2021]"
            "(https://stat.gov.pl/download/gfx/portalinformacyjny/pl/defaultaktualnosci/5481/4/18/1/rachunki_narodowe_wedlug_sektorow_i_podsektorow_instytucjonalnych_w_latach_2018-2021._publikacja_w_formacie_pdf.pdf) "
            "oraz [GUS, rewizja 2025 opublikowana 6.10.2026]"
            "(https://publikacje.new.stat.gov.pl/portal-publikacje/produkt-krajowy-brutto-zaktualizowany-szacunek-za-2025-r). "
            "Dane pochodzą z edycji o różnej dacie rewizji — szeregu PKB nie należy traktować jako w pełni jednolicie zrewidowanego."
        )
        st.markdown(
            "**Finanse samorządowe:** [katalog JST](https://budzetpanstwa.pl/samorzady), "
            "[sprawozdania JST Ministerstwa Finansów](https://www.gov.pl/web/finanse/sprawozdania-budzetowe), "
            "[FinanseJST (BeSTia)](https://finansejst.mf.gov.pl/). "
            "Mapa pokazuje agregację wszystkich jednostek z danego obszaru w 2025 r.; "
            "suma jednostek nie jest skonsolidowanym rachunkiem sektora."
        )
