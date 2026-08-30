"""
Apt Price Tracker - Multi-Page Native Route for 18-Year Regional Big Data & Macro Analysis
"""
import streamlit as st
from macro_page import render_macro_page

st.set_page_config(
    page_title="18개년 지역 빅데이터 & 매크로 분석",
    page_icon="🌐",
    layout="wide"
)

render_macro_page()
