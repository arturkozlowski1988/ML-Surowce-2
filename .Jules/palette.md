## 2024-05-22 - [Streamlit Icon-Only Buttons]
**Learning:** Icon-only buttons (like emojis) in Streamlit are inaccessible without a `help` parameter, as they lack descriptive text for screen readers and tooltips for sighted users.
**Action:** Always add `help="Description of action"` to `st.button()` when the label is an emoji or icon.
