import streamlit as st
import gspread
import json
from google.oauth2.service_account import Credentials
import pandas as pd

st.set_page_config(page_title="Admin Settings — Gabor-Granger", layout="centered")

st.title("⚙️ Admin Settings")
st.caption("Configure and monitor your Gabor-Granger survey")

# ---------------------------
# GOOGLE SHEETS CONNECTION
# ---------------------------
@st.cache_resource
def connect_to_gsheet(sheet_name="Gabor Granger Results"):
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/spreadsheets.readonly"]
        creds = Credentials.from_service_account_info(
            st.secrets["google"]["service_account"],
            scopes=scopes
        )
        client = gspread.authorize(creds)
        sheet = client.open(sheet_name).sheet1
        return sheet
    except Exception as e:
        st.error(f"⚠️ Could not connect to Google Sheets: {e}")
        return None

sheet = connect_to_gsheet()

# ---------------------------
# SURVEY CONFIGURATION
# ---------------------------
st.subheader("🧾 Survey Configuration")

product_name = st.text_input("Product name", "Eggs")
description = st.text_area("Product description", "Farm-fresh eggs, high in protein and nutrition.")

price_list_input = st.text_input("Price list (comma-separated)", "5,6,7,8,9,10,11,12")
price_list = [float(p.strip()) for p in price_list_input.split(",") if p.strip()]
inc_up = st.number_input("Increase increment (₹)", value=1.0, step=0.5)
dec_down = st.number_input("Decrease decrement (₹)", value=0.5, step=0.5)
random_start = st.checkbox("Start at random price", value=True)
max_rounds = st.number_input("Max price questions per respondent", 1, 10, 5)

# ---------------------------
# MULTIPLE QUESTIONS (UP TO 8)
# ---------------------------
st.subheader("📝 Survey Questions (up to 8)")
questions = []
for i in range(8):
    q = st.text_input(f"Question {i+1}", f"Would you buy {product_name} at ₹{{price}}?")
    questions.append(q)

# ---------------------------
# SAVE SETTINGS
# ---------------------------
if st.button("💾 Save Settings"):
    st.session_state['settings'] = {
        "product_name": product_name,
        "description": description,
        "price_list": price_list,
        "inc_up": inc_up,
        "dec_down": dec_down,
        "random_start": random_start,
        "max_rounds": max_rounds,
        "questions": questions
    }
    st.success("✅ Settings saved! Respondents can now visit the 'Questionnaire' page.")

# ---------------------------
# ADMIN DASHBOARD
# ---------------------------
st.markdown("---")
st.subheader("📊 Responses Dashboard")

if sheet:
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if df.empty:
            st.info("No responses yet.")
        else:
            st.dataframe(df)
            st.download_button("⬇️ Download CSV", df.to_csv(index=False), "responses.csv", "text/csv")
    except Exception as e:
        st.error(f"Error reading Google Sheet: {e}")
