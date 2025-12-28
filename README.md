# 💬 Chatbot template

A simple Streamlit app that shows how to build a chatbot using OpenAI's GPT-3.5.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://chatbot-template.streamlit.app/)

### How to run it on your own machine

1. Install the requirements

   ```
   $ pip install -r requirements.txt
   ```

2. Run the app

   ```
   $ streamlit run streamlit_app.py
   ```

### Version badge visibility

The app hides the version badge from users by default and only shows it in admin mode.

- Env flag (server-side):

```
$ CPQ_SHOW_VERSION=1 streamlit run streamlit_app.py
```

- Optional admin code: set `CPQ_ADMIN_CODE` (or `ADMIN_CODE` in `st.secrets`) and append `?admin=CODE` to the URL to enable admin mode on demand:

```
$ CPQ_ADMIN_CODE=abc123 streamlit run streamlit_app.py
# Open http://localhost:8501/?admin=abc123
```

### Debug traces (optional)

Enable lightweight debug messages in the sidebar during AI steps:

```
$ CPQ_DEBUG=1 streamlit run streamlit_app.py
# Or open with: http://localhost:8501/?debug=1
```
