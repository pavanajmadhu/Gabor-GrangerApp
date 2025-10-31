import streamlit as st
import gspread
import json
from google.oauth2.service_account import Credentials
import pandas as pd

st.set_page_config(page_title="Admin Settings — Gabor-Granger", layout="centered")
# ---------------------------
# SIMPLE PASSWORD PROTECTION
# ---------------------------
ADMIN_PASSWORD = st.secrets["admin"]["password"]  # stored securely in Streamlit secrets

st.title("🔒 Admin Login")
password_input = st.text_input("Enter admin password", type="password")

if password_input != ADMIN_PASSWORD:
    st.warning("Enter the correct password to access admin settings.")
    st.stop()

st.title("⚙️ Admin Settings")
st.caption("Configure and monitor your Gabor-Granger survey")

# ---------------------------
# GOOGLE SHEETS CONNECTION
# ---------------------------
@st.cache_resource
def connect_to_gsheet(sheet_name="Gabor Granger Results"):
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
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
st.subheader("📝 Survey Questions (up to 5)")
questions = []
for i in range(5):
    q = st.text_input(f"Question {i+1}", f"Would you buy {product_name} at ₹{{price}}?")
    questions.append(q)

# ---------------------------
# SAVE SETTINGS
# ---------------------------
CONFIG_SHEET_NAME = "Gabor Granger Config"

@st.cache_resource
def connect_to_config_sheet(sheet_name=CONFIG_SHEET_NAME):
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(
            st.secrets["google"]["service_account"],
            scopes=scopes
        )
        client = gspread.authorize(creds)
        sheet = client.open(sheet_name).sheet1
        return sheet
    except Exception as e:
        st.error(f"⚠️ Could not connect to config sheet: {e}")
        return None

config_sheet = connect_to_config_sheet()
if st.button("💾 Save Settings"):
    # --- Save locally to Streamlit session ---
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
    st.success("✅ Settings saved locally and to Google Sheets!")

    # --- NEW PART: also save to Google Sheet for respondents ---
    if config_sheet:
        data = {
            "product_name": product_name,
            "description": description,
            "price_list": json.dumps(price_list),
            "inc_up": inc_up,
            "dec_down": dec_down,
            "random_start": random_start,
            "max_rounds": max_rounds,
            "questions": json.dumps(questions)
        }

        # Clear old config and add the new one
        config_sheet.clear()
        config_sheet.append_row(["Key", "Value"])
        for k, v in data.items():
            config_sheet.append_row([k, str(v)])
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
