import streamlit as st
import random
import pandas as pd
import uuid
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="Questionnaire — Gabor-Granger", layout="centered")

# ---------------------------
# CONNECT TO GOOGLE SHEET
# ---------------------------
@st.cache_resource
def connect_to_gsheet(sheet_name="GaborGrangerResponses"):
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(
        json.loads(st.secrets["google"]["service_account"]),
        scopes=scopes
    )
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).sheet1
    return sheet

sheet = connect_to_gsheet()

# ---------------------------
# ADAPTIVE PRICE LOGIC
# ---------------------------
def adaptive_next_price(seq, inc_up, dec_down):
    if len(seq) < 2:
        return None
    last_price, last_answer = seq[-1]
    prev_price, prev_answer = seq[-2]
    if prev_answer == "Yes" and last_answer == "No":
        return round((prev_price + last_price) / 2, 2)
    if prev_answer == "No" and last_answer == "Yes":
        return round((prev_price + last_price) / 2, 2)
    return round(last_price + inc_up, 2) if last_answer == "Yes" else round(max(0, last_price - dec_down), 2)

# ---------------------------
# LOAD SETTINGS
# ---------------------------
settings = st.session_state.get('settings')
if not settings:
    st.warning("⚠️ No survey configuration found. Please ask the admin to set it up first.")
    st.stop()

st.title(f"{settings['product_name']} — Pricing Survey")
st.caption("An adaptive willingness-to-pay questionnaire")

# ---------------------------
# INITIALIZE SESSION
# ---------------------------
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.q_index = 0
    st.session_state.sequence = []
    st.session_state.rounds = 0
    st.session_state.completed = False
    st.session_state.current_price = (
        random.choice(settings['price_list']) if settings['random_start']
        else settings['price_list'][0]
    )

# ---------------------------
# QUESTION FLOW
# ---------------------------
if not st.session_state.completed:
    question_text = settings['questions'][st.session_state.q_index].format(price=st.session_state.current_price)
    st.markdown(f"### {question_text}")

    col1, col2 = st.columns(2)
    yes = col1.button("✅ Yes, I would buy")
    no = col2.button("❌ No, I wouldn’t")

    if yes or no:
        answer = "Yes" if yes else "No"
        st.session_state.sequence.append((st.session_state.current_price, answer))
        st.session_state.rounds += 1

        # Move to next question or adapt price
        if st.session_state.rounds >= settings['max_rounds']:
            st.session_state.q_index += 1
            st.session_state.rounds = 0
            st.session_state.sequence = []

            if st.session_state.q_index >= len(settings['questions']):
                st.session_state.completed = True
            else:
                st.session_state.current_price = (
                    random.choice(settings['price_list'])
                    if settings['random_start']
                    else settings['price_list'][0]
                )
        else:
            next_price = adaptive_next_price(
                st.session_state.sequence,
                settings['inc_up'],
                settings['dec_down']
            )
            st.session_state.current_price = next_price or st.session_state.current_price
        st.rerun()

else:
    st.success("✅ Thank you! Your responses have been recorded.")
    record = {
        "Respondent_ID": st.session_state.session_id,
        "Timestamp": datetime.utcnow().isoformat(),
        "Product_Name": settings['product_name'],
        "Questions": json.dumps(settings['questions']),
        "Responses": json.dumps(st.session_state.sequence)
    }

    try:
        sheet.append_row(list(record.values()), value_input_option="USER_ENTERED")
        st.balloons()
        st.json(record)
    except Exception as e:
        st.error(f"Failed to save to Google Sheets: {e}")

    if st.button("Start a new respondent"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
