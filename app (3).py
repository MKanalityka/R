# -*- coding: utf-8 -*-
"""Tymczasowy test diagnostyczny Streamlit Cloud; nie jest częścią Obserwatora."""
import sys
from datetime import datetime, timezone

import streamlit as st

st.set_page_config(page_title='Diagnostyka Streamlit', page_icon='🧪', layout='centered')
st.title('✅ Streamlit działa')
st.success('Jeśli widzisz ten komunikat, przeglądarka odbiera widżety z serwera Streamlit.')
st.write('Python:', sys.version.split()[0])
st.write('Streamlit:', st.__version__)
st.write('Czas uruchomienia serwera (UTC):', datetime.now(timezone.utc).isoformat(timespec='seconds'))
st.write('Kliknij przycisk, aby sprawdzić połączenie WebSocket:')
if st.button('Test połączenia'):
    st.success('Kliknięcie dotarło do serwera.')

