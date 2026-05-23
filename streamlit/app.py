import os

import streamlit as st

st.set_page_config(
    page_title="Prophecy",
    page_icon="img/favicon.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

logo_path = "img/prophecy_logo.png"
if os.path.exists(logo_path):
    st.image(logo_path, width=280)
else:
    st.title("Prophecy")

st.markdown(
    """
## Plateforme Prophecy — Nexthope

Deux modules ML unifiés derrière une API unique :

| Module | Description |
|--------|-------------|
| **Réassort** | Prédiction XGBoost 30j, alertes stock, obsolescence |
| **Segmentation** | Segments RFM, profils KMeans, recommandations |

Utilisez le menu latéral pour ouvrir le tableau de bord réassort ou la segmentation clients.
"""
)

api_url = os.environ.get("API_URL", "http://localhost:8000")
st.caption(f"API : `{api_url}` — documentation : [{api_url}/docs]({api_url}/docs)")

col1, col2 = st.columns(2)
with col1:
    st.page_link("pages/1_reassort.py", label="Tableau de bord réassort", icon="📦")
with col2:
    st.page_link("pages/2_segmentation.py", label="Segmentation RFM & profils", icon="👥")
