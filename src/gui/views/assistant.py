"""
AI Assistant view for the AI Supply Assistant.
Provides GenAI-powered analysis using Ollama, Google Gemini, or Local LLM (Embedded).
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional
import os
from pathlib import Path
import time

# Project root for absolute path resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
MIN_MODEL_SIZE_MB = 500  # Minimum valid model size in MB


def render_assistant_view(
    db,
    product_map: Dict[int, str],
    sorted_product_ids: list,
    prepare_time_series,
    warehouse_ids: list = None
):
    """
    Renders the AI Assistant view with Raw Material and Final Product analysis modes.
    
    Args:
        db: DatabaseConnector instance
        product_map: Dict mapping TowarId -> DisplayName
        sorted_product_ids: List of product IDs sorted by usage
        prepare_time_series: Preprocessing function
        warehouse_ids: Optional list of warehouse IDs to filter stock
    """
    st.subheader("🤖 Inteligentny Asystent Zakupowy")
    
    # Check Local LLM availability
    local_llm_available, local_llm_status = _check_local_llm()
    
    # AI Engine Selection
    col_ai_1, col_ai_2 = st.columns(2)
    
    with col_ai_1:
        ai_options = ["Ollama (Local Server)", "Google Gemini (Cloud)"]
        
        # Add Local LLM option if available or show info
        if local_llm_available:
            ai_options.insert(0, "🚀 Local LLM (Embedded)")
        
        ai_source = st.radio("Wybierz Silnik AI:", ai_options)
        
        # Model Selection State
        selected_models = []
        comparison_mode = False
        
        if "Local LLM" in ai_source:
            # Scan for valid models (filter out incomplete/corrupt files)
            available_models = []
            incomplete_models = []
            
            if MODELS_DIR.exists():
                for f in MODELS_DIR.glob("*.gguf"):
                    size_mb = f.stat().st_size / (1024**2)
                    if size_mb >= MIN_MODEL_SIZE_MB:
                        available_models.append(f.name)
                    else:
                        incomplete_models.append((f.name, size_mb))
            
            if incomplete_models:
                st.warning(f"⚠️ Niekompletne modele (pomijane): {', '.join([m[0] for m in incomplete_models])}")
            
            if not available_models:
                st.error("Brak poprawnych modeli .gguf w folderze /models! (min. 500MB)")
            else:
                comparison_mode = st.checkbox("🆚 Tryb Porównania (Benchmark)", help="Porównaj odpowiedzi dwóch modeli")
                
                if comparison_mode:
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        model_a = st.selectbox("Model A (Baza)", available_models, index=0, key="model_a")
                        selected_models.append(model_a)
                    with col_m2:
                        # Try to select different second model by default
                        default_idx = 1 if len(available_models) > 1 else 0
                        model_b = st.selectbox("Model B (Challenger)", available_models, index=default_idx, key="model_b")
                        selected_models.append(model_b)
                else:
                    default_model = available_models[0]
                    # Try to preserve selection
                    selected_model = st.selectbox("Wybierz Model:", available_models, index=0)
                    selected_models.append(selected_model)
        
        ollama_model = "llama3.2"
        if "Ollama" in ai_source:
            ollama_model = st.selectbox("Wybierz Model Ollama:", ["llama3.2", "ministral-3:8b"])
    
    with col_ai_2:
        # Show engine status
        st.markdown("**Status silników AI:**")
        
        if local_llm_available:
            st.success(f"🟢 Local LLM: {local_llm_status}")
            
            # Helper to find models
            model_files = list(MODELS_DIR.glob("*.gguf")) if MODELS_DIR.exists() else []
            
            with st.expander("🛠️ Zarządzanie Modelami"):
                st.write(f"Folder modeli: `{MODELS_DIR}`")
                st.write(f"Znaleziono {len(model_files)} plików .gguf")
                for m in model_files:
                    size_gb = m.stat().st_size / (1024**3)
                    status = "✅" if size_gb >= 0.5 else "⚠️ niekompletny"
                    st.code(f"{status} {m.name} ({size_gb:.2f} GB)")
        else:
            st.warning(f"🟡 Local LLM: {local_llm_status}")
            with st.expander("Jak skonfigurować Local LLM?"):
                st.markdown("""
                1. Pobierz model GGUF (np. DeepSeek R1, Mistral)
                2. Umieść w folderze `models/`
                3. Wybierz model w menu po lewej
                """)
        
        # Always show Gemini status
        gemini_configured = _check_gemini_configured()
        if gemini_configured:
            st.success("🟢 Gemini: Skonfigurowany")
        else:
            st.warning("🟡 Gemini: Brak klucza API")
    
    # --- MODE SELECTION: RAW MATERIAL vs FINAL PRODUCT ---
    st.markdown("---")
    
    # Security info banner
    if "Gemini" in ai_source:
        st.info("🔒 **Bezpieczeństwo:** Twoje dane są anonimizowane przed wysłaniem do AI (NIP, PESEL, email)")
    elif "Local LLM" in ai_source:
        st.success("🔒 **Prywatność:** Dane przetwarzane lokalnie - nic nie opuszcza Twojego komputera")
    
    analysis_mode = st.radio(
        "Tryb Analizy:", 
        ["Analiza Surowca (Anomalie)", "Analiza Wyrobu Gotowego (BOM)"], 
        horizontal=True
    )
    
    if analysis_mode == "Analiza Surowca (Anomalie)":
        _render_raw_material_analysis(
            db, product_map, sorted_product_ids, 
            prepare_time_series, ai_source, ollama_model,
            selected_models, comparison_mode
        )
    else:
        _render_final_product_analysis(
            db, ai_source, ollama_model, 
            selected_models, comparison_mode, warehouse_ids
        )


def _check_local_llm() -> tuple:
    """Check if Local LLM is available."""
    try:
        from src.ai_engine.local_llm import check_local_llm_available
        return check_local_llm_available()
    except ImportError:
        return False, "Module not found"
    except Exception as e:
        return False, str(e)


def _check_gemini_configured() -> bool:
    """Check if Gemini API key is configured."""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    return bool(os.getenv('GEMINI_API_KEY'))


def _render_raw_material_analysis(
    db, product_map, sorted_product_ids, 
    prepare_time_series, ai_source, ollama_model,
    selected_models=[], comparison_mode=False
):
    """Renders raw material anomaly analysis."""
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
                st.warning(
                    f"Brak danych historycznych dla produktu: "
                    f"{product_map.get(selected_product_ai, str(selected_product_ai))}. "
                    "Nie można wygenerować analizy."
                )
                return
            
            # Stats - with proper validation
            last_4_weeks = df_prod['Quantity'].tail(4).tolist()
            
            # Validate that we have sufficient data
            if not last_4_weeks or len(last_4_weeks) < 2:
                st.warning(
                    f"Niewystarczająca ilość danych historycznych "
                    f"(dostępne: {len(last_4_weeks)} tygodni, wymagane min. 2). "
                    "Analiza może być niepełna."
                )
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
            
            response_text = _generate_ai_response(prompt, ai_source, ollama_model)
            
            st.markdown("### 💡 Wnioski AI")
            
            if comparison_mode and len(selected_models) == 2:
                # Benchmark Mode
                col_res1, col_res2 = st.columns(2)
                
                with col_res1:
                    st.markdown(f"**Model A: {selected_models[0]}**")
                    with st.spinner(f"Geneowanie (Model A)..."):
                        path_a = str(MODELS_DIR / selected_models[0])
                        resp_a = _generate_ai_response(prompt, ai_source, ollama_model, local_model_path=path_a)
                        st.info(resp_a)
                
                with col_res2:
                    st.markdown(f"**Model B: {selected_models[1]}**")
                    with st.spinner(f"Generowanie (Model B)..."):
                        path_b = str(MODELS_DIR / selected_models[1])
                        resp_b = _generate_ai_response(prompt, ai_source, ollama_model, local_model_path=path_b)
                        st.success(resp_b)
                        
            else:
                # Single Mode
                model_path = str(MODELS_DIR / selected_models[0]) if selected_models else None
                response_text = _generate_ai_response(prompt, ai_source, ollama_model, local_model_path=model_path)
                st.write(response_text)

            with st.expander("Pokaż Prompt (Debug)"):
                st.code(prompt)


def _render_final_product_analysis(
    db, ai_source, ollama_model, 
    selected_models=[], comparison_mode=False, warehouse_ids=None
):
    """Renders final product (BOM) analysis with warehouse filtering."""
    with st.spinner("Pobieranie listy wyrobów gotowych..."):
        df_tech_prods = db.get_products_with_technology()
    
    if df_tech_prods.empty:
        st.info("Brak zdefiniowanych technologii w systemie.")
        return
    
    tech_map = dict(zip(
        df_tech_prods['FinalProductId'], 
        df_tech_prods['Name'] + " (" + df_tech_prods['Code'] + ")"
    ))
    
    selected_final_prod_ai = st.selectbox(
        "Wybierz Wyrób Gotowy do produkcji:",
        df_tech_prods['FinalProductId'],
        format_func=lambda x: tech_map.get(x, str(x))
    )
    
    plan_qty = st.number_input("Planowana ilość produkcji (szt):", min_value=1, value=100)
    
    if st.button("Generuj Analizę Zakupową (BOM)"):
        with st.spinner("Pobieranie BOM i generowanie porady..."):
            # Get BOM with stock for selected warehouses
            df_bom_ai = db.get_bom_with_stock(selected_final_prod_ai, warehouse_ids=warehouse_ids)
            
            if df_bom_ai.empty:
                st.warning("Brak zdefiniowanej technologii dla tego wyrobu.")
                return
            
            # Get warehouse breakdown for AI context (all warehouses)
            df_warehouse_breakdown = db.get_bom_with_warehouse_breakdown(selected_final_prod_ai)
            
            # Calculate deficits
            df_bom_ai['RequiredTotal'] = df_bom_ai['QuantityPerUnit'] * plan_qty
            df_bom_ai['Deficit'] = df_bom_ai['RequiredTotal'] - df_bom_ai['CurrentStock']
            df_bom_ai['Status'] = df_bom_ai['Deficit'].apply(lambda x: 'BRAK' if x > 0 else 'OK')
            
            # Prepare text summary for AI (selected warehouses)
            bom_summary = df_bom_ai[['IngredientName', 'RequiredTotal', 'CurrentStock', 'Status']].to_string(index=False)
            
            # Prepare warehouse breakdown for AI (other warehouses context)
            warehouse_context = ""
            if not df_warehouse_breakdown.empty and warehouse_ids:
                # Group by ingredient and show stock per warehouse
                warehouse_summary = df_warehouse_breakdown.groupby(
                    ['IngredientCode', 'IngredientName', 'MagSymbol']
                )['StockInWarehouse'].sum().reset_index()
                
                if not warehouse_summary.empty:
                    warehouse_context = f"""
            
            UWAGA - Stany na INNYCH magazynach (możliwe do przesunięcia):
            {warehouse_summary.to_string(index=False)}
            """
            
            # Build enhanced prompt with warehouse context
            selected_mag_info = f"(wybrane magazyny: {len(warehouse_ids)})" if warehouse_ids else "(wszystkie magazyny)"
            
            prompt = f"""
            Jesteś asystentem zakupowym w fabryce. Planujemy produkcję wyrobu: {tech_map[selected_final_prod_ai]}.
            Ilość do wyprodukowania: {plan_qty} szt.
            
            Oto analiza zapotrzebowania na surowce (BOM vs Magazyn) {selected_mag_info}:
            {bom_summary}
            {warehouse_context}
            
            Zadanie:
            1. Wskaż krytyczne braki (co musimy pilnie zamówić?).
            2. Jeśli są surowce na innych magazynach - zasugeruj przesunięcie międzymagazynowe.
            3. Czy są jakieś ryzyka dla ciągłości produkcji?
            4. Podaj rekomendację dla działu zakupów.
            Odpowiedz krótko i konkretnie w języku polskim.
            """
            
            st.markdown("### 💡 Raport Zakupowy AI")
            
            if comparison_mode and len(selected_models) == 2:
                # Benchmark Mode
                col_res1, col_res2 = st.columns(2)
                
                with col_res1:
                    st.markdown(f"**Model A: {selected_models[0]}**")
                    with st.spinner(f"Geneowanie (Model A)..."):
                        path_a = str(MODELS_DIR / selected_models[0])
                        resp_a = _generate_ai_response(prompt, ai_source, ollama_model, local_model_path=path_a)
                        st.info(resp_a)
                
                with col_res2:
                    st.markdown(f"**Model B: {selected_models[1]}**")
                    with st.spinner(f"Generowanie (Model B)..."):
                        path_b = str(MODELS_DIR / selected_models[1])
                        resp_b = _generate_ai_response(prompt, ai_source, ollama_model, local_model_path=path_b)
                        st.success(resp_b)
                        
            else:
                # Single Mode
                model_path = str(MODELS_DIR / selected_models[0]) if selected_models else None
                response_text = _generate_ai_response(prompt, ai_source, ollama_model, local_model_path=model_path)
                st.write(response_text)
            
            with st.expander("Szczegóły kalkulacji (Tabela)"):
                st.dataframe(
                    df_bom_ai.style.applymap(
                        lambda v: 'color: red;' if v == 'BRAK' else 'color: green;', 
                        subset=['Status']
                    )
                )
            with st.expander("Pokaż Prompt (Debug)"):
                st.code(prompt)


def _generate_ai_response(prompt: str, ai_source: str, ollama_model: str, local_model_path: Optional[str] = None) -> str:
    """
    Generates AI response using selected engine.
    Handles Gemini, Ollama, and Local LLM with proper error handling.
    """
    try:
        if "Gemini" in ai_source:
            from src.ai_engine.gemini_client import GeminiClient
            from src.ai_engine.anonymizer import DataAnonymizer
            anonymizer = DataAnonymizer()
            safe_prompt = anonymizer.anonymize_text(prompt)
            client = GeminiClient()
            return client.generate_explanation(safe_prompt)
        
        elif "Local LLM" in ai_source:
            from src.ai_engine.local_llm import LocalLLMEngine
            # Use specific model path if provided, else fallback to env/default
            client = LocalLLMEngine(model_path=local_model_path)
            start_t = time.time()
            resp = client.generate_explanation(prompt)
            duration = time.time() - start_t
            return f"{resp}\n\n_(Czas generowania: {duration:.1f}s)_"
        
        else:  # Ollama
            from src.ai_engine.ollama_client import OllamaClient
            client = OllamaClient(model_name=ollama_model)
            return client.generate_explanation(prompt)
            
    except Exception as e:
        return f"Błąd podczas generowania odpowiedzi AI: {str(e)}"
