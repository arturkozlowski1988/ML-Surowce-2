"""
Login View for Streamlit Application.
Provides user authentication interface.
"""

import streamlit as st
from typing import Callable, Optional


def render_login_view(on_login_success: Optional[Callable] = None) -> bool:
    """
    Renders the login form.
    
    Args:
        on_login_success: Callback to call after successful login
        
    Returns:
        True if user is logged in
    """
    from src.security.auth import get_auth_manager
    
    # Check if already logged in
    if st.session_state.get('authenticated', False):
        return True
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("# 🔐 Logowanie")
        st.markdown("---")
        
        # Login form
        with st.form("login_form"):
            username = st.text_input(
                "Nazwa użytkownika",
                placeholder="np. admin",
                key="login_username"
            )
            
            password = st.text_input(
                "Hasło",
                type="password",
                placeholder="••••••••",
                key="login_password"
            )
            
            submitted = st.form_submit_button("🔓 Zaloguj", use_container_width=True)
            
            if submitted:
                if not username or not password:
                    st.error("⚠️ Wprowadź nazwę użytkownika i hasło")
                else:
                    auth = get_auth_manager()
                    user = auth.authenticate(username, password)
                    
                    if user:
                        # Store user info in session
                        st.session_state['authenticated'] = True
                        st.session_state['user'] = {
                            'username': user.username,
                            'role': user.role,
                            'display_name': user.display_name or user.username,
                            'can_change_database': user.can_change_database(),
                            'can_access_wizard': user.can_access_wizard(),
                            'can_manage_users': user.can_manage_users()
                        }
                        
                        st.success(f"✅ Zalogowano jako: {user.display_name or user.username}")
                        
                        if on_login_success:
                            on_login_success()
                        
                        st.rerun()
                    else:
                        st.error("❌ Nieprawidłowa nazwa użytkownika lub hasło")
        
        # Info about default credentials
        with st.expander("ℹ️ Pierwsze logowanie"):
            st.info("""
            **Domyślne dane logowania:**
            - Użytkownik: `admin`
            - Hasło: `admin123`
            
            ⚠️ Zmień hasło po pierwszym zalogowaniu!
            """)
    
    return False


def logout():
    """Logs out the current user."""
    keys_to_clear = ['authenticated', 'user']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]


def get_current_user() -> Optional[dict]:
    """
    Returns current logged-in user info.
    
    Returns:
        Dict with user info or None if not logged in
    """
    if st.session_state.get('authenticated', False):
        return st.session_state.get('user')
    return None


def require_auth() -> bool:
    """
    Checks if user is authenticated.
    Use at the start of protected views.
    
    Returns:
        True if authenticated, False otherwise
    """
    return st.session_state.get('authenticated', False)


def require_role(role: str) -> bool:
    """
    Checks if current user has specific role.
    
    Args:
        role: Required role (e.g., 'admin')
        
    Returns:
        True if user has the role
    """
    user = get_current_user()
    if user is None:
        return False
    return user.get('role') == role
