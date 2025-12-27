import streamlit as st
import pandas as pd
import os
import urllib.parse
from src.db_connector import DatabaseConnector
from src.preprocessing import prepare_time_series, fill_missing_weeks


# Page Config
st.set_page_config(
    page_title="AI Supply Assistant",
    page_icon="🏭",
    layout="wide"
)

# Title
st.title("🏭 AI Supply Assistant (Produkcja by CTI)")

# Sidebar
with st.sidebar:
    st.markdown("### 📦 Konfiguracja")
    
    # Connection Status
    if "db_status" not in st.session_state:
        st.session_state["db_status"] = False

    # Connection Wizard / Settings
    with st.expander("🔌 Ustawienia Połączenia"):
        st.caption("Jeśli połączenie z .env nie działa, wprowadź dane ręcznie.")
        manual_server = st.text_input("Server", value="DESKTOP-JHQ03JE\SQL")
        manual_db = st.text_input("Database", value="cdn_test")
        manual_user = st.text_input("User", value="sa")
        manual_pass = st.text_input("Password", type="password")
        
        if st.button("Połącz Ręcznie"):
            conn_str = f"mssql+pyodbc://{manual_user}:{urllib.parse.quote_plus(manual_pass)}@{manual_server}/{manual_db}?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"
            try:
                # Update Env Var for this session
                os.environ['DB_CONN_STR'] = conn_str
                # Re-init connector
                db_conn = DatabaseConnector()
                if db_conn.test_connection():
                    st.session_state["db_status"] = True
                    st.success("Połączono!")
                    st.rerun()
                else:
                    st.error("Nieudane połączenie.")
            except Exception as e:
                st.error(f"Błąd: {e}")

    # Auto-connect if not connected
    if not st.session_state["db_status"]:
        try:
            db_conn = DatabaseConnector()
            if db_conn.test_connection():
                st.session_state["db_status"] = True
        except:
            pass

    if st.session_state["db_status"]:
        st.success("🟢 Utworzono połączenie z bazą")
    else:
        st.error("🔴 Błąd połączenia z bazą")
    
    st.divider()
    app_mode = st.selectbox("Wybierz tryb:", 
        ["Analiza Danych", "Predykcja", "AI Assistant (GenAI)"]
    )
    
    st.markdown("---")
    st.caption("v1.0.0 | Produkcja by CTI")

# Logic
@st.cache_resource
def get_db_connection():
    # Force reload v2 - Invalidating cache for new DB methods
    return DatabaseConnector()

try:
    db = get_db_connection()
    
    # Global Data Fetch
    with st.spinner("Pobieranie danych globalnych..."):
        df_stock = db.get_current_stock()
        # Create a mapping dictionary for ID -> Name
        product_map = {}
        if not df_stock.empty:
            # Ensure TowarId is int
            df_stock['TowarId'] = pd.to_numeric(df_stock['TowarId'], errors='coerce').fillna(0).astype(int)
            # SORTING: The SQL query already sorts by UsageCount DESC, so df_stock is sorted.
            # We preserve this order in dropdowns by using the list of keys from this DF.
            df_stock['DisplayName'] = df_stock['Name'] + " (" + df_stock['Code'] + ")"
            product_map = dict(zip(df_stock['TowarId'], df_stock['DisplayName']))
            
            # Helper list of sorted IDs for dropdowns
            sorted_product_ids = df_stock['TowarId'].tolist()
        else:
             sorted_product_ids = []

    # Sidebar Filters
    with st.sidebar:
        st.header("Filtry")
        # Date Range
        today = pd.Timestamp.now().date()
        start_date = st.date_input("Od daty:", value=today - pd.Timedelta(weeks=26))
        end_date = st.date_input("Do daty:", value=today + pd.Timedelta(weeks=8))
        
    if app_mode == "Analiza Danych":
        st.subheader("📊 Analiza Historyczna Produkcji")
        
        with st.spinner("Pobieranie danych historycznych..."):
            df_hist = db.get_historical_data()
            
        if not df_hist.empty:
            # Preprocessing
            df_clean = prepare_time_series(df_hist)
            # Ensure TowarId is int here too
            df_clean['TowarId'] = pd.to_numeric(df_clean['TowarId'], errors='coerce').fillna(0).astype(int)
            
            df_full = fill_missing_weeks(df_clean)
            
            # Filter by Date
            mask = (df_full['Date'].dt.date >= start_date) & (df_full['Date'].dt.date <= end_date)
            df_filtered = df_full.loc[mask]
            
            # Metrics
            total_qty = df_filtered['Quantity'].sum()
            total_products = df_filtered['TowarId'].nunique()
            
            col1, col2 = st.columns(2)
            col1.metric("Całkowite Zużycie (okres)", f"{total_qty:,.0f}")
            col2.metric("Aktywne Surowce", total_products)
            
            # Visualization
            st.subheader("Trend zużycia")
            
            # Product Selection with Names - SORTED by Usage
            # Use intersection of history IDs and sorted stock IDs to keep order
            hist_ids = df_filtered['TowarId'].unique()
            # Sort hist_ids based on their order in sorted_product_ids (UsageCount)
            # If an ID is not in stock list (rare), append at end
            dropdown_options = [x for x in sorted_product_ids if x in hist_ids]
            remaining_ids = [x for x in hist_ids if x not in sorted_product_ids]
            dropdown_options.extend(remaining_ids)
            
            # Default to TOP 5 for readability
            default_selection = dropdown_options[:5] if len(dropdown_options) >= 5 else dropdown_options
            
            selected_ids = st.multiselect(
                "Wybierz surowce do wykresu (Posortowane wg zużycia):", 
                options=dropdown_options,
                default=default_selection,
                format_func=lambda x: product_map.get(x, str(x))
            )
            
            chart_data = df_filtered if not selected_ids else df_filtered[df_filtered['TowarId'].isin(selected_ids)]
            
            # Map TowarId to product code/name for chart legend
            chart_data = chart_data.copy()
            chart_data['ProductLabel'] = chart_data['TowarId'].map(product_map).fillna(chart_data['TowarId'].astype(str))
            
            import plotly.express as px
            fig = px.line(chart_data, x='Date', y='Quantity', color='ProductLabel', title="Zużycie w czasie")
            st.plotly_chart(fig, use_container_width=True)
            
            # --- UPDATED: Purchaser View (Usage & BOM) ---
            st.divider()
            st.subheader("🛒 Panel Zakupowca: Kontekst Produkcyjny")
            
            if len(selected_ids) == 1:
                sel_id = int(selected_ids[0])
                with st.spinner("Analizowanie powiązań produkcji..."):
                    df_usage = db.get_product_usage_stats(sel_id)
                
                col_u1, col_u2 = st.columns([2, 3])
                
                with col_u1:
                    st.markdown(f"**Gdzie używany jest surowiec: {product_map.get(sel_id, str(sel_id))}?**")
                    if not df_usage.empty:
                        # Bar Chart Small
                        fig_usage = px.bar(
                            df_usage, 
                            x='TotalUsage', 
                            y='FinalProductName', 
                            orientation='h',
                            title=None,
                            height=300
                        )
                        fig_usage.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=0, r=0, t=0, b=0))
                        st.plotly_chart(fig_usage, use_container_width=True)
                        
                        # Product Selector for BOM
                        # Map Code -> ID to facilitate lookup
                        code_to_id = dict(zip(df_usage['FinalProductCode'], df_usage['FinalProductId']))
                        final_product_options = dict(zip(df_usage['FinalProductCode'], df_usage['FinalProductName']))
                        
                        selected_final_code = st.selectbox(
                            "🔍 Sprawdź skład wyrobu (BOM):", 
                            list(final_product_options.keys()),
                            format_func=lambda x: f"{final_product_options[x]} ({x})"
                        )
                    else:
                        st.info("Brak bezpośredniego użycia w zleceniach produkcyjnych (Typ 1/2).")

                with col_u2:
                    if not df_usage.empty and 'selected_final_code' in locals():
                        st.markdown(f"**📦 Struktura Receptury (BOM): {final_product_options[selected_final_code]}**")
                        
                        sel_final_id = int(code_to_id[selected_final_code])
                        
                        with st.spinner("Pobieranie receptury..."):
                             df_bom = db.get_product_bom(sel_final_id)
                        
                        if not df_bom.empty:
                            st.dataframe(
                                df_bom.style.format({'QuantityPerUnit': '{:.4f}'}), 
                                use_container_width=True,
                                hide_index=True
                            )
                            st.caption("Tabela zawiera aktywne składniki technologiczne (Typ 1 i 2).")
                        else:
                            st.warning("Brak zdefiniowanej technologii (BOM) w systemie CTI dla tego wyrobu.")
            
            elif len(selected_ids) > 1:
                st.info("Wybierz pojedynczy surowiec, aby uruchomić Panel Zakupowca.")
            # ----------------------------------
            
            # Data Preview
            with st.expander("Podgląd surowych danych"):
                st.dataframe(df_full.head(100))
        else:
            st.warning("Brak danych historycznych z produkcji.")
            
    elif app_mode == "Predykcja":
        st.subheader("📈 Prognoza Zapotrzebowania")
        
        with st.spinner("Pobieranie i przetwarzanie danych..."):
            df_hist = db.get_historical_data()
            if not df_hist.empty:
                df_clean = prepare_time_series(df_hist)
                df_full = fill_missing_weeks(df_clean)
                
                # Setup Forecaster
                from src.forecasting import Forecaster
                forecaster = Forecaster()
                
                # Select Single Product for detailed view - SORTED
                product_list = [x for x in sorted_product_ids if x in df_full['TowarId'].unique()]
                # Fallback if list empty
                if not product_list: product_list = df_full['TowarId'].unique()

                selected_product = st.selectbox(
                    "Wybierz Surowiec do Prognozy:", 
                    product_list,
                    format_func=lambda x: product_map.get(x, str(x))
                )
                
                # Select Model Type
                model_option = st.selectbox(
                    "Wybierz Model:", 
                    ["Random Forest (Zbalansowany)", "Gradient Boosting (Wysoka Precyzja)", "Exponential Smoothing (Trend/Sezonowość)"]
                )
                
                model_map = {
                    "Random Forest (Zbalansowany)": "rf",
                    "Gradient Boosting (Wysoka Precyzja)": "gb",
                    "Exponential Smoothing (Trend/Sezonowość)": "es"
                }
                
                selected_model_code = model_map[model_option]

                with st.spinner(f"Trenowanie modelu ({model_option}) dla {product_map.get(selected_product, selected_product)}..."):
                    # 1. Baseline
                    df_baseline = forecaster.predict_baseline(df_full)
                    
                    # 2. Advanced Model
                    df_ml = forecaster.train_predict(df_full, model_type=selected_model_code)
                
                # Prepare chart data
                # Historical
                hist_data = df_full[df_full['TowarId'] == selected_product].copy()
                hist_data['Type'] = 'History'
                
                # Forecast Baseline
                base_data = df_baseline[df_baseline['TowarId'] == selected_product].copy()
                base_data['Type'] = 'Forecast (Baseline)'
                base_data = base_data.rename(columns={'Predicted_Qty': 'Quantity'})
                
                # Forecast Advanced
                ml_data = df_ml[df_ml['TowarId'] == selected_product].copy()
                # Rename Model column to identify source
                # ml_data['Model'] already set in forecaster
                ml_data['Type'] = 'Forecast (' + ml_data['Model'] + ')'
                ml_data = ml_data.rename(columns={'Predicted_Qty': 'Quantity'})
                
                # Combine
                combined_df = pd.concat([
                    hist_data[['Date', 'Quantity', 'Type']], 
                    base_data[['Date', 'Quantity', 'Type']],
                    ml_data[['Date', 'Quantity', 'Type']]
                ])
                
                # Apply Date Filter for View
                view_mask = (combined_df['Date'].dt.date >= start_date) & (combined_df['Date'].dt.date <= end_date)
                chart_df = combined_df.loc[view_mask]
                
                import plotly.express as px
                fig = px.line(chart_df, x='Date', y='Quantity', color='Type', 
                              title=f"Prognoza: {product_map.get(selected_product, str(selected_product))}",
                              color_discrete_map={
                                  "History": "royalblue", 
                                  "Forecast (Baseline)": "gray", 
                                  "Forecast (Random Forest)": "orange",
                                  "Forecast (Gradient Boosting)": "darkgreen", 
                                  "Forecast (Exponential Smoothing)": "purple"
                                })
                st.plotly_chart(fig, use_container_width=True)
                
                if selected_model_code == 'rf':
                    st.info("Random Forest: Ensemble drzew decyzyjnych. Dobry balans między dopasowaniem a generalizacją.")
                elif selected_model_code == 'gb':
                    st.info("Gradient Boosting: Uczy się na błędach poprzedników. Często dokładniejszy, ale wolniejszy.")
                elif selected_model_code == 'es':
                    st.info("Exponential Smoothing (Holt-Winters): Modeluje trend i sezonowość bezpośrednio. Dobry dla stabilnych wzorców.")
            else:
                st.warning("Brak danych do prognozowania.")
        
    elif app_mode == "AI Assistant (GenAI)":
        st.subheader("🤖 Inteligentny Asystent Zakupowy")
        
        col_ai_1, col_ai_2 = st.columns(2)
        with col_ai_1:
            ai_source = st.radio("Wybierz Silnik AI:", ["Ollama (Local)", "Google Gemini (Cloud)"])
            
            ollama_model = "llama3.2"
            if "Ollama" in ai_source:
                ollama_model = st.selectbox("Wybierz Model Ollama:", ["llama3.2", "ministral-3:8b"])
        
        # --- MODE SELECTION: RAW MATERIAL vs FINAL PRODUCT ---
        st.markdown("---")
        
        # Security info banner
        if "Gemini" in ai_source:
            st.info("🔒 **Bezpieczeństwo:** Twoje dane są anonimizowane przed wysłaniem do AI (NIP, PESEL, email)")
        
        analysis_mode = st.radio("Tryb Analizy:", ["Analiza Surowca (Anomalie)", "Analiza Wyrobu Gotowego (BOM)"], horizontal=True)
        
        if analysis_mode == "Analiza Surowca (Anomalie)":
            # Use Cached Product List if available or fetch - SORTED
            selected_product_ai = st.selectbox(
                "Wybierz Surowiec do Analizy AI:", 
                sorted_product_ids,
                format_func=lambda x: product_map.get(x, str(x))
            )
            
            if st.button("Generuj Analizę Ekspercką (Surowiec)"):
                with st.spinner("Analizowanie danych i generowanie odpowiedzi..."):
                    # Prepare Context
                    df_hist = db.get_historical_data()
                    df_clean = prepare_time_series(df_hist)
                    df_prod = df_clean[df_clean['TowarId'] == selected_product_ai].copy()
                    
                    if df_prod.empty:
                        st.warning(f"Brak danych historycznych dla produktu: {product_map.get(selected_product_ai, str(selected_product_ai))}. Nie można wygenerować analizy.")
                    else:
                        # Stats - with proper validation
                        last_4_weeks = df_prod['Quantity'].tail(4).tolist()
                        
                        # Validate that we have sufficient data
                        if not last_4_weeks or len(last_4_weeks) < 2:
                            st.warning(f"Niewystarczająca ilość danych historycznych (dostępne: {len(last_4_weeks)} tygodni, wymagane min. 2). Analiza może być niepełna.")
                            avg_consumption = last_4_weeks[0] if last_4_weeks else 0
                        else:
                            avg_consumption = sum(last_4_weeks) / len(last_4_weeks)
                        
                        product_name = product_map.get(selected_product_ai, f"ID {selected_product_ai}")
                        
                        prompt = f"""
                        Jesteś ekspertem ds. łańcucha dostaw. Przeanalizuj sytuację dla surowca: {product_name}.
                        Ostatnie 4 tygodnie zużycia: {last_4_weeks}.
                        Średnie zużycie: {avg_consumption:.2f}.
                        
                        Czy trend jest rosnący czy malejący? Czy sugerujesz zwiększenie zapasów? 
                        Jakie mogą być przyczyny anomalii (jeśli występują)?
                        Odpowiedz krótko i konkretnie w języku polskim.
                        """
                        
                        # Generate Response Logic (Same as before)
                        response_text = ""
                        if "Gemini" in ai_source:
                            from src.ai_engine.gemini_client import GeminiClient
                            from src.ai_engine.anonymizer import DataAnonymizer
                            anonymizer = DataAnonymizer()
                            safe_prompt = anonymizer.anonymize_text(prompt)
                            client = GeminiClient()
                            response_text = client.generate_explanation(safe_prompt)
                        else: # Ollama
                            from src.ai_engine.ollama_client import OllamaClient
                            client = OllamaClient(model_name=ollama_model)
                            response_text = client.generate_explanation(prompt)
                        
                        st.markdown("### 💡 Wnioski AI")
                        st.write(response_text)
                        with st.expander("Pokaż Prompt (Debug)"): st.code(prompt)
                        
        elif analysis_mode == "Analiza Wyrobu Gotowego (BOM)":
             with st.spinner("Pobieranie listy wyrobów gotowych..."):
                 df_tech_prods = db.get_products_with_technology()
             
             if not df_tech_prods.empty:
                 tech_map = dict(zip(df_tech_prods['FinalProductId'], df_tech_prods['Name'] + " (" + df_tech_prods['Code'] + ")"))
                 
                 selected_final_prod_ai = st.selectbox(
                     "Wybierz Wyrób Gotowy do produkcji:",
                     df_tech_prods['FinalProductId'],
                     format_func=lambda x: tech_map.get(x, str(x))
                 )
                 
                 plan_qty = st.number_input("Planowana ilość produkcji (szt):", min_value=1, value=100)
                 
                 if st.button("Generuj Analizę Zakupową (BOM)"):
                     with st.spinner("Pobieranie BOM i generowanie porady..."):
                         df_bom_ai = db.get_bom_with_stock(selected_final_prod_ai)
                         
                         if df_bom_ai.empty:
                             st.warning("Brak zdefiniowanej technologii dla tego wyrobu.")
                         else:
                             # Calculate deficits
                             df_bom_ai['RequiredTotal'] = df_bom_ai['QuantityPerUnit'] * plan_qty
                             df_bom_ai['Deficit'] = df_bom_ai['RequiredTotal'] - df_bom_ai['CurrentStock']
                             df_bom_ai['Status'] = df_bom_ai['Deficit'].apply(lambda x: 'BRAK' if x > 0 else 'OK')
                             
                             # Prepare text summary for AI
                             bom_summary = df_bom_ai[['IngredientName', 'RequiredTotal', 'CurrentStock', 'Status']].to_string(index=False)
                             critical_items = df_bom_ai[df_bom_ai['Status'] == 'BRAK']
                             
                             prompt = f"""
                             Jesteś asystentem zakupowym w fabryce. Planujemy produkcję wyrobu: {tech_map[selected_final_prod_ai]}.
                             Ilość do wyprodukowania: {plan_qty} szt.
                             
                             Oto analiza zapotrzebowania na surowce (BOM vs Magazyn):
                             {bom_summary}
                             
                             Zadanie:
                             1. Wskaż krytyczne braki (co musimy pilnie zamówić?).
                             2. Czy są jakieś ryzyka dla ciągłości produkcji?
                             3. Podaj rekomendację dla działu zakupów.
                             Odpowiedz krótko i konkretnie w języku polskim.
                             """
                             
                             # Generate Response
                             response_text = ""
                             if "Gemini" in ai_source:
                                 from src.ai_engine.gemini_client import GeminiClient
                                 from src.ai_engine.anonymizer import DataAnonymizer
                                 anonymizer = DataAnonymizer()
                                 safe_prompt = anonymizer.anonymize_text(prompt)
                                 client = GeminiClient()
                                 response_text = client.generate_explanation(safe_prompt)
                             else:
                                 from src.ai_engine.ollama_client import OllamaClient
                                 client = OllamaClient(model_name=ollama_model)
                                 response_text = client.generate_explanation(prompt)
                                 
                             st.markdown("### 💡 Raport Zakupowy AI")
                             st.write(response_text)
                             
                             with st.expander("Szczegóły kalkulacji (Tabela)"):
                                 st.dataframe(df_bom_ai.style.applymap(lambda v: 'color: red;' if v == 'BRAK' else 'color: green;', subset=['Status']))
                             with st.expander("Pokaż Prompt (Debug)"): st.code(prompt)
             else:
                 st.info("Brak zdefiniowanych technologii w systemie.")

except Exception as e:
    st.error(f"Błąd krytyczny aplikacji: {e}")

