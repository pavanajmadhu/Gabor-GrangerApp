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
# ---------------------------
# RESPONDENT FLOW (with pre-questions + improved Gabor logic)
# ---------------------------

PRE_QUESTIONS = [
    "Do you currently use similar products?",
    "Would you recommend this product to others?",
    "Do you care about eco-friendly packaging?",
    "Do you check price before quality while buying?",
    "Would you switch brands if offered better price?"
]

if 'session_id' not in st.session_state:
    st.session_state.session_id = None
    st.session_state.stage = "pre"   # stages: pre → gabor → done
    st.session_state.pre_answers = {}
    st.session_state.pre_index = 0
    st.session_state.sequence = []
    st.session_state.timestamps = []
    st.session_state.rounds = 0
    st.session_state.current_price = None
    st.session_state.completed = False

# ---------------------------
# START BUTTON
# ---------------------------
if not st.session_state.session_id:
    if st.button("Start Questionnaire"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.stage = "pre"
        st.session_state.pre_answers = {}
        st.session_state.pre_index = 0
        st.rerun()

# ---------------------------
# STAGE 1 — PRELIMINARY QUESTIONS
# ---------------------------
elif st.session_state.stage == "pre":
    q_index = st.session_state.pre_index
    if q_index < len(PRE_QUESTIONS):
        question = PRE_QUESTIONS[q_index]
        st.subheader(f"Question {q_index + 1} of {len(PRE_QUESTIONS)}")
        st.markdown(f"### {question}")
        col1, col2 = st.columns(2)
        yes = col1.button("✅ Yes")
        no = col2.button("❌ No")

        if yes or no:
            st.session_state.pre_answers[question] = "Yes" if yes else "No"
            st.session_state.pre_index += 1
            st.rerun()
    else:
        # Move to Gabor stage
        st.session_state.stage = "gabor"
        if settings['random_start']:
            st.session_state.current_price = random.choice(settings['price_list'])
        else:
            st.session_state.current_price = settings['price_list'][0]
        st.rerun()

# ---------------------------
# STAGE 2 — GABOR-GRANGER TEST (from 2nd code)
# ---------------------------
elif st.session_state.stage == "gabor" and not st.session_state.completed:
    st.subheader(settings['product_name'])
    st.write(settings['description'])

    price = st.session_state.current_price
    st.markdown(f"### Would you buy this product at **₹{price:.2f}** ?")

    col1, col2 = st.columns(2)
    yes = col1.button("✅ Yes, I would buy")
    no = col2.button("❌ No, I wouldn’t")

    if yes or no:
        answer = "Yes" if yes else "No"
        st.session_state.sequence.append((price, answer))
        st.session_state.timestamps.append(datetime.utcnow().isoformat())
        st.session_state.rounds += 1

        # Stop if max rounds reached
        if st.session_state.rounds >= settings['max_rounds']:
            st.session_state.completed = True
            st.session_state.stage = "done"
        else:
            next_price = adaptive_next_price(
                st.session_state.sequence,
                settings['inc_up'],
                settings['dec_down']
            )
            if next_price:
                st.session_state.current_price = next_price
            else:
                st.session_state.current_price = (
                    price + settings['inc_up']
                    if answer == "Yes"
                    else max(0, price - settings['dec_down'])
                )
        st.rerun()

# ---------------------------
# STAGE 3 — SUBMIT RESULTS
# ---------------------------
elif st.session_state.stage == "done":
    st.success("✅ Thank you! Your responses are recorded.")
    seq = st.session_state.sequence
    timestamps = st.session_state.timestamps

    yes_prices = [p for p, a in seq if a == "Yes"]
    final_price = max(yes_prices) if yes_prices else min([p for p, _ in seq])

    record = {
        "Respondent_ID": st.session_state.session_id,
        "Timestamp_Final": datetime.utcnow().isoformat(),
        "Product_Name": settings['product_name'],
        "Pre_Questions_JSON": json.dumps(st.session_state.pre_answers),
        "Sequence_JSON": json.dumps(seq),
        "Timestamps_JSON": json.dumps(timestamps),
        "Final_Price": final_price,
        "Total_Rounds": st.session_state.rounds
    }

    sheet.append_row(list(record.values()), value_input_option="USER_ENTERED")
    st.balloons()
    st.write("**Your final estimated willingness-to-pay price:** ₹", final_price)
    st.json(record)

    if st.button("Start new respondent"):
        for key in ['session_id', 'stage', 'pre_answers', 'pre_index', 'sequence',
                    'timestamps', 'rounds', 'current_price', 'completed']:
            st.session_state.pop(key, None)
        st.rerun()
