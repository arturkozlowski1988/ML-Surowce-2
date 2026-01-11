## 2024-05-23 - Icon-only buttons in Streamlit
**Learning:** Streamlit's `st.button` supports a `help` parameter which renders as a tooltip and is accessible to screen readers as a description. This is critical for icon-only buttons where the label is just an emoji.
**Action:** Always add `help="..."` to `st.button` when the label is not descriptive text (e.g., emojis or single characters).
