import time
import smtplib
from email.mime.text import MIMEText

import streamlit as st
from google import genai
from google.genai import types

from prompts import SUMMARY_REQUEST_PROMPT, SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE

MODEL_NAME = "gemini-2.5-flash"
st.set_page_config(page_title="SplitSnap", page_icon="🧾")

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
GMAIL_ADDRESS = st.secrets["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]


@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)


gemini_client = get_gemini_client()


def render_message(message):
    with st.chat_message(message["role"]):
        if message["kind"] == "text":
            st.write(message["content"])
        elif message["kind"] == "image":
            st.image(message["content"])


def add_message(role, kind, content):
    st.session_state.messages.append(
        {"role": role, "kind": kind, "content": content}
    )
    render_message(st.session_state.messages[-1])


def ask_gemini(parts):
    # Returns (ok, text). Retries a few times if Gemini is busy (503).
    last_error = ""
    for attempt in range(3):
        try:
            reply = st.session_state.chat.send_message(parts)
            return True, reply.text
        except Exception as error:
            last_error = str(error)
            if "503" in last_error or "UNAVAILABLE" in last_error:
                time.sleep(3 * (attempt + 1))
                continue
            break
    return False, f"Sorry, something went wrong: {last_error}"


def send_email(to_address, user_name, summary):
    try:
        message = MIMEText(f"Hi {user_name},\n\n{summary}", "plain", "utf-8")
        message["Subject"] = "Your SplitSnap bill summary"
        message["From"] = GMAIL_ADDRESS
        message["To"] = to_address

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(message)
        return True, ""
    except Exception as error:
        return False, str(error)

# ---------- Onboarding ----------
if "onboarded" not in st.session_state:
    st.title("🧾 SplitSnap")
    st.caption("Snap it. Split it. Email yourself the results.")
    with st.form("onboarding_form"):
        name = st.text_input("Your name")
        email = st.text_input(
            "Your email address",
            placeholder="you@gmail.com",
            help="This is where SplitSnap will email your bill summary.",
        )
        submitted = st.form_submit_button("Let's go 🚀")
    if submitted:
        if not name.strip() or not email.strip():
            st.warning("Please fill in both your name and email address.")
        elif "@" not in email or "." not in email.split("@")[-1]:
            st.warning("Please enter a valid email address.")
        else:
            st.session_state.name = name.strip()
            st.session_state.email = email.strip()
            st.session_state.chat = gemini_client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            )
            st.session_state.messages = []
            st.session_state.onboarded = True
            st.rerun()
    st.stop()

# ---------- Chat screen ----------
header_col, button_col = st.columns([5, 2], vertical_alignment="center")

with header_col:
    st.title("🧾 SplitSnap")

with button_col:
    send_disabled = len(st.session_state.messages) <= 2
    send_clicked = st.button(
        "📧 Send to Email", disabled=send_disabled, width="stretch"
    )

if send_clicked:
    with st.spinner("Preparing your summary..."):
        ok, summary = ask_gemini([SUMMARY_REQUEST_PROMPT])
    if not ok:
        st.error(summary)
    else:
        sent, info = send_email(
            st.session_state.email, st.session_state.name, summary
        )
        if sent:
            st.success("Sent! Check your email 📬")
        else:
            st.error(f"Couldn't send that: {info}")

st.caption(
    f"Logged in as {st.session_state.name} - summary goes to {st.session_state.email}"
)

if not st.session_state.messages:
    add_message(
        "assistant",
        "text",
        WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name),
    )
else:
    for message in st.session_state.messages:
        render_message(message)

user_input = st.chat_input(
    "Send a receipt photo, or ask a question",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)

if user_input:
    photo = user_input.files[0] if user_input.files else None
    text = user_input.text
    parts = []

    if photo is not None:
        photo_bytes = photo.getvalue()
        add_message("user", "image", photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))
    if text:
        add_message("user", "text", text)
        parts.append(text)
    elif photo is not None:
        parts.append("Read this receipt. List every item, the tax, and the total.")

    with st.spinner("Reading your bill..."):
        ok, answer = ask_gemini(parts)
    add_message("assistant", "text", answer)
    st.rerun()