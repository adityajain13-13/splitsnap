\# SplitSnap



AI bill-splitting chatbot. Upload a restaurant receipt photo, chat to

split items between friends, and get the summary by email.



Live app: https://splitsnap-aditya.streamlit.app



\## What it does

\- Reads a receipt photo using Gemini (vision)

\- Splits items and totals through chat

\- Emails the final summary



\## Run locally

1\. git clone https://github.com/adityajain13-13/splitsnap.git

2\. cd splitsnap

3\. python -m venv venv

4\. venv\\Scripts\\activate

5\. pip install -r requirements.txt

6\. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`

&#x20;  and fill in your own keys

7\. streamlit run app.py



\## Tech

Python, Streamlit, Google Gemini API, Gmail SMTP

