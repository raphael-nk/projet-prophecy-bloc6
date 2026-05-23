import os

import streamlit as st

from dashboard_page import run_dashboard
from reassort_page import _inject_prophecy_styles, run_reassort
from segmentation_page import run_segmentation

st.set_page_config(
    page_title="Prophecy",
    page_icon="img/favicon.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

_inject_prophecy_styles()

dashboard_page = st.Page(
    run_dashboard,
    title="Tableau de bord",
    icon=":material/dashboard:",
    default=True,
)
reassort_page = st.Page(
    run_reassort,
    title="Réassort",
    icon=":material/inventory_2:",
)
segmentation_page = st.Page(
    run_segmentation,
    title="Segmentation RFM & Profils",
    icon=":material/segment:",
)

pg = st.navigation(
    [dashboard_page, reassort_page, segmentation_page],
    position="hidden",
)

logo_path = "img/prophecy_logo.png"
with st.sidebar:
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        st.title("Prophecy")
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    st.page_link(
        dashboard_page,
        label="Tableau de bord",
        icon=":material/dashboard:",
        use_container_width=True,
    )
    st.page_link(
        reassort_page,
        label="Réassort",
        icon=":material/inventory_2:",
        use_container_width=True,
    )
    st.page_link(
        segmentation_page,
        label="Segments Clients",
        icon=":material/segment:",
        use_container_width=True,
    )

pg.run()
