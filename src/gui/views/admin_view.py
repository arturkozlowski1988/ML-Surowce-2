"""
Admin Panel View.
Provides user management interface for administrators.
"""

import streamlit as st
from typing import Optional


def render_admin_view():
    """
    Renders the admin panel for user management.
    Only accessible by admin users.
    """
    from src.security.auth import get_auth_manager, UserRole
    from src.gui.views.login_view import get_current_user
    
    # Check permissions
    user = get_current_user()
    if not user or not user.get('can_manage_users'):
        st.error("🚫 Brak uprawnień do zarządzania użytkownikami")
        return
    
    st.subheader("👥 Zarządzanie Użytkownikami")
    
    auth = get_auth_manager()
    
    # Current users table
    st.markdown("### Lista użytkowników")
    
    users = auth.get_all_users()
    
    if users:
        # Create display data
        user_data = []
        for u in users:
            role_display = "🔑 Administrator" if u.role == "admin" else "📊 Zakupowiec"
            user_data.append({
                "Użytkownik": u.username,
                "Nazwa": u.display_name or u.username,
                "Rola": role_display
            })
        
        st.dataframe(user_data, use_container_width=True)
    else:
        st.info("Brak użytkowników")
    
    st.markdown("---")
    
    # Tabs for operations
    tab1, tab2, tab3 = st.tabs(["➕ Dodaj użytkownika", "🔑 Zmień hasło", "🗑️ Usuń użytkownika"])
    
    with tab1:
        _render_add_user_form(auth)
    
    with tab2:
        _render_change_password_form(auth, users)
    
    with tab3:
        _render_delete_user_form(auth, users, user['username'])


def _render_add_user_form(auth):
    """Renders form to add new user."""
    from src.security.auth import UserRole
    
    st.markdown("#### Dodaj nowego użytkownika")
    
    with st.form("add_user_form"):
        new_username = st.text_input(
            "Nazwa użytkownika",
            placeholder="np. jan.kowalski"
        )
        
        new_display_name = st.text_input(
            "Imię i nazwisko",
            placeholder="np. Jan Kowalski"
        )
        
        new_password = st.text_input(
            "Hasło",
            type="password",
            placeholder="Minimum 6 znaków"
        )
        
        new_password_confirm = st.text_input(
            "Potwierdź hasło",
            type="password"
        )
        
        new_role = st.selectbox(
            "Rola",
            options=["purchaser", "admin"],
            format_func=lambda x: "📊 Zakupowiec" if x == "purchaser" else "🔑 Administrator"
        )
        
        if st.form_submit_button("➕ Dodaj użytkownika", use_container_width=True):
            # Validation
            if not new_username:
                st.error("⚠️ Wprowadź nazwę użytkownika")
            elif len(new_password) < 6:
                st.error("⚠️ Hasło musi mieć minimum 6 znaków")
            elif new_password != new_password_confirm:
                st.error("⚠️ Hasła nie są identyczne")
            else:
                role_enum = UserRole.ADMIN if new_role == "admin" else UserRole.PURCHASER
                success = auth.create_user(
                    username=new_username,
                    password=new_password,
                    role=role_enum,
                    display_name=new_display_name or new_username
                )
                
                if success:
                    st.success(f"✅ Użytkownik '{new_username}' został utworzony")
                    st.rerun()
                else:
                    st.error(f"❌ Użytkownik '{new_username}' już istnieje")


def _render_change_password_form(auth, users):
    """Renders form to change user password."""
    st.markdown("#### Zmień hasło użytkownika")
    
    if not users:
        st.info("Brak użytkowników")
        return
    
    with st.form("change_password_form"):
        usernames = [u.username for u in users]
        selected_user = st.selectbox("Użytkownik", usernames)
        
        new_pass = st.text_input("Nowe hasło", type="password")
        new_pass_confirm = st.text_input("Potwierdź nowe hasło", type="password")
        
        if st.form_submit_button("🔑 Zmień hasło", use_container_width=True):
            if len(new_pass) < 6:
                st.error("⚠️ Hasło musi mieć minimum 6 znaków")
            elif new_pass != new_pass_confirm:
                st.error("⚠️ Hasła nie są identyczne")
            else:
                if auth.change_password(selected_user, new_pass):
                    st.success(f"✅ Hasło dla '{selected_user}' zostało zmienione")
                else:
                    st.error("❌ Nie udało się zmienić hasła")


def _render_delete_user_form(auth, users, current_username):
    """Renders form to delete user."""
    st.markdown("#### Usuń użytkownika")
    
    # Filter out current user (can't delete yourself)
    deletable_users = [u for u in users if u.username != current_username]
    
    if not deletable_users:
        st.info("Brak użytkowników do usunięcia (nie możesz usunąć siebie)")
        return
    
    with st.form("delete_user_form"):
        usernames = [u.username for u in deletable_users]
        user_to_delete = st.selectbox("Użytkownik do usunięcia", usernames)
        
        st.warning("⚠️ Ta operacja jest nieodwracalna!")
        
        confirm = st.checkbox("Potwierdzam usunięcie użytkownika")
        
        if st.form_submit_button("🗑️ Usuń użytkownika", use_container_width=True):
            if not confirm:
                st.error("⚠️ Potwierdź usunięcie zaznaczając checkbox")
            else:
                if auth.delete_user(user_to_delete):
                    st.success(f"✅ Użytkownik '{user_to_delete}' został usunięty")
                    st.rerun()
                else:
                    st.error("❌ Nie można usunąć ostatniego administratora")
