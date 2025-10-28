import streamlit as st

st.set_page_config(page_title="Gabor-Granger Survey", layout="centered")

st.title("💰 Gabor-Granger Pricing Survey")
st.markdown("""
Welcome to the **Gabor-Granger interactive pricing survey** platform.

This app helps you test consumers’ willingness to pay by adapting product prices dynamically.

### How to use:
1. Go to the **Admin Settings** page and configure your product, price list, and increments.
2. Share the **Questionnaire** page link with respondents.
3. View and download all collected responses from the Admin dashboard.

---
""")

st.info("Use the sidebar → 'Admin Settings' to set up your survey.")
