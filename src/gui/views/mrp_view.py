"""
MRP View - Material Requirements Planning GUI
AI Supply Assistant - Phase 2

This view provides:
- Production simulation ("What-If")
- BOM visualization with color-coded shortages
- Smart alerts dashboard
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional


def render_mrp_view(
    db,
    product_map: Dict[int, str],
    sorted_product_ids: List[int],
    warehouse_ids: List[int] = None
):
    """
    Renders the MRP Lite view with production simulation and alerts.
    
    Args:
        db: DatabaseConnector instance
        product_map: Mapping of product IDs to display names
        sorted_product_ids: List of product IDs for dropdown
        warehouse_ids: Optional warehouse filter
    """
    
    st.header("🏭 MRP Lite - Symulator Produkcji")
    
    # Initialize services lazily
    from src.services.mrp_simulator import MRPSimulator
    from src.services.alerts import SmartAlerts
    
    mrp = MRPSimulator(db)
    alerts = SmartAlerts(db)
    
    # Create tabs
    tab1, tab2 = st.tabs(["🔍 Symulacja Produkcji", "⚠️ Krytyczne Braki"])
    
    # === TAB 1: Production Simulation ===
    with tab1:
        render_simulation_tab(db, mrp, product_map, sorted_product_ids, warehouse_ids)
    
    # === TAB 2: Critical Alerts ===
    with tab2:
        render_alerts_tab(alerts, warehouse_ids)


def render_simulation_tab(
    db, 
    mrp, 
    product_map: Dict[int, str],
    sorted_product_ids: List[int],
    warehouse_ids: List[int] = None
):
    """Renders the production simulation tab."""
    
    # [U4] Dashboard statystyk CTI
    render_cti_dashboard(db)
    
    st.subheader("📊 Symulacja 'Co-Jeśli'")
    st.markdown("""
    Sprawdź, czy masz wystarczające surowce do wyprodukowania określonej ilości wyrobu.
    Analiza uwzględnia **stany magazynowe**, **zamienniki** oraz **czasy dostaw**.
    """)
    
    # Get products with technology (BOM)
    df_tech = db.get_products_with_technology()
    
    if df_tech.empty:
        st.warning("⚠️ Brak produktów z zdefiniowaną technologią (BOM)")
        return
    
    # Create product options with display names
    tech_product_map = {
        row['FinalProductId']: f"{row['Name']} ({row['Code']})"
        for _, row in df_tech.iterrows()
    }
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_product_id = st.selectbox(
            "Wybierz wyrób do produkcji",
            options=list(tech_product_map.keys()),
            format_func=lambda x: tech_product_map.get(x, str(x)),
            key="mrp_product_select"
        )
    
    with col2:
        target_quantity = st.number_input(
            "Ilość do wyprodukowania",
            min_value=1,
            max_value=100000,
            value=100,
            step=10,
            key="mrp_quantity"
        )
    
    # Buttons row
    col_btn1, col_btn2 = st.columns([1, 2])
    
    analyze_ai = False
    
    with col_btn1:
        run_sim = st.button("🚀 Uruchom Symulację", type="primary", key="mrp_simulate")
    
    with col_btn2:
        analyze_ai = st.button("🤖 Pełna Analiza AI + Rekomendacje", key="mrp_analyze_ai")
    
    if run_sim or analyze_ai:
        with st.spinner("Analizuję BOM, stany, dostawy i zamienniki..."):
            # Use advanced simulation with delivery times
            if analyze_ai:
                # Full AI analysis
                llm_result = mrp.analyze_with_llm(
                    product_id=selected_product_id,
                    quantity=target_quantity,
                    warehouse_ids=warehouse_ids
                )
                result = llm_result['simulation_result']
                st.markdown(llm_result['analysis'])
                
                if llm_result.get('llm_recommendation'):
                    st.markdown("---")
                    st.subheader("🤖 Rekomendacja Lokalnego LLM")
                    st.info(llm_result['llm_recommendation'])
                
            else:
                # Standard simulation with delivery
                result = mrp.simulate_production_with_delivery(
                    product_id=selected_product_id,
                    quantity=target_quantity,
                    warehouse_ids=warehouse_ids
                )
        
        if 'error' in result and not analyze_ai:
            st.error(f"❌ {result['error']}")
            return
            
        if not analyze_ai: # If analyze_ai is true, we already showed markdown
            # Display results
            st.markdown("---")
            
            # Status banner
            if result['can_produce']:
                st.success(f"✅ **MOŻLIWA PRODUKCJA** {target_quantity} szt.")
            else:
                st.error(f"⚠️ **BRAKI SUROWCÓW** - Maksymalnie: {result['max_producible']:.0f} szt.")
                if result.get('max_delivery_time', 0) > 0:
                    st.warning(f"⏰ Najdłuższy czas dostawy braków: **{result['max_delivery_time']} dni**")
            
            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Cel produkcji", f"{target_quantity} szt.")
            
            with col2:
                st.metric("Max. możliwa", f"{result['max_producible']:.0f} szt.",
                         delta=f"{result['max_producible'] - target_quantity:.0f}" 
                         if result['max_producible'] < target_quantity else None,
                         delta_color="inverse")
            
            with col3:
                shortage_count = len(result['shortages'])
                st.metric("Braki surowców", shortage_count,
                         delta=f"{shortage_count} pozycji" if shortage_count > 0 else None,
                         delta_color="inverse")
                
            with col4:
                earliest = result.get('earliest_production_date')
                if earliest:
                    st.metric("Start produkcji", str(earliest)[:10])
            
            # Limiting factor with Smart Substitutes [U3]
            if result['limiting_factor'] and not result['can_produce']:
                lf = result['limiting_factor']
                st.warning(f"""
                **Czynnik ograniczający (bottleneck):**  
                🔴 **{lf['ingredient_name']}** ({lf['ingredient_code']})  
                Stan: {lf['current_stock']:.2f} | Potrzeba: {lf['quantity_required']:.2f} | 
                Max produkcja: {lf['max_producible']:.0f} szt.
                """)
                
                # Show safe substitutes for bottleneck
                if lf.get('ingredient_id'):
                    subs = db.get_smart_substitutes(lf['ingredient_id'], 
                                                  lf['quantity_required'] - lf['current_stock'],
                                                  warehouse_ids)
                    if not subs.empty:
                        valid_subs = subs[subs['IsAllowed'] == 1]
                        if not valid_subs.empty:
                            st.info(f"💡 **Dostępne zamienniki:** {', '.join(valid_subs['SubstituteCode'].tolist())}")

            # BOM Table with color coding
            st.subheader("📋 Lista Materiałów (BOM)")
            
            bom_df = result['bom']
            if not bom_df.empty:
                cols = ['IngredientCode', 'IngredientName', 'QuantityRequired', 'CurrentStock', 'Shortage', 'Status']
                if 'DeliveryTime_Days' in bom_df.columns:
                    cols.append('DeliveryTime_Days')
                
                display_df = bom_df[cols].copy()
                
                new_cols = ['Kod', 'Nazwa', 'Potrzeba', 'Stan', 'Różnica', 'Status']
                if 'DeliveryTime_Days' in bom_df.columns:
                    new_cols.append('Dostawa (dni)')
                
                display_df.columns = new_cols
                
                # Apply styling
                def color_status(val):
                    if val == 'OK': return 'background-color: #90EE90'
                    elif val == 'BRAK': return 'background-color: #FFD700'
                    elif val == 'KRYTYCZNY': return 'background-color: #FF6B6B'
                    return ''
                
                styled_df = display_df.style.map(color_status, subset=['Status']).format({
                    'Potrzeba': '{:.2f}', 'Stan': '{:.2f}', 'Różnica': '{:+.2f}'
                })
                
                st.dataframe(styled_df, use_container_width=True, height=400)
                
                # Export shortages
                csv = bom_df[bom_df['Shortage'] < 0].to_csv(index=False)
                st.download_button("📥 Eksportuj braki do CSV", csv, 
                                 f"braki_{selected_product_id}_{target_quantity}.csv", "text/csv")


def render_alerts_tab(alerts, warehouse_ids: List[int] = None):
    """Renders the critical alerts dashboard tab."""
    
    st.subheader("⚠️ Dashboard Krytycznych Braków")
    st.markdown("""
    Automatyczna analiza stanów magazynowych na podstawie średniego zużycia tygodniowego.
    """)
    
    # Refresh button
    if st.button("🔄 Odśwież Alerty", key="refresh_alerts"):
        st.rerun()
    
    # Get summary first
    summary = alerts.get_shortage_summary()
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🔴 Krytyczne", summary['critical_count'])
    with col2:
        st.metric("🟡 Niskie", summary['low_count'])
    with col3:
        st.metric("🟢 OK", summary['ok_count'])
    with col4:
        st.metric("⚪ Brak użycia", summary['no_usage_count'])
    
    st.markdown("---")
    
    # Get detailed shortages
    with st.spinner("Analizuję stany magazynowe..."):
        shortages_df = alerts.get_critical_shortages(warehouse_ids=warehouse_ids)
    
    if shortages_df.empty:
        st.success("✅ Brak krytycznych braków magazynowych!")
        return
    
    # Display table with filtering
    status_filter = st.multiselect(
        "Filtruj wg statusu",
        options=['KRYTYCZNY', 'NISKI'],
        default=['KRYTYCZNY', 'NISKI'],
        key="alert_status_filter"
    )
    
    filtered_df = shortages_df[shortages_df['Status'].isin(status_filter)]
    
    if filtered_df.empty:
        st.info("Brak alertów dla wybranego filtra")
        return
    
    # Color-coded table
    def color_alert_status(val):
        if val == 'KRYTYCZNY':
            return 'background-color: #FF6B6B; color: white; font-weight: bold'
        elif val == 'NISKI':
            return 'background-color: #FFD700; color: black'
        return ''
    
    display_columns = ['Code', 'Name', 'StockLevel', 'AvgWeeklyUsage', 
                      'DaysOfStock', 'Status']
    
    styled_df = filtered_df[display_columns].style.map(
        color_alert_status, subset=['Status']
    ).format({
        'StockLevel': '{:.1f}',
        'AvgWeeklyUsage': '{:.2f}'
    })
    
    st.dataframe(styled_df, use_container_width=True, height=400)
    
    # Export
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        "📥 Eksportuj alerty do CSV",
        csv,
        "alerty_magazynowe.csv",
        "text/csv"
    )
    
    # AI Explanation section
    st.markdown("---")
    st.subheader("🤖 Wyjaśnienie AI")
    
    if st.button("Generuj wyjaśnienie przyczyn braków", key="ai_explain_alerts"):
        ai_context = alerts.generate_ai_context(filtered_df)
        st.markdown(ai_context)
        st.info("💡 Skopiuj powyższy kontekst do AI Asystenta dla szczegółowej analizy.")

def render_cti_dashboard(db):
    """Renders high-level CTI production statistics [U4]."""
    try:
        stats = db.get_production_dashboard_stats()
        
        st.subheader("📊 Panel Produkcyjny CTI")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📦 Aktywne Zlecenia", 
                     stats['orders']['total'], 
                     help="Łączna liczba zleceń w okresie")
        with col2:
            st.metric("⚠️ Dokumenty Braków", 
                     stats['shortages']['active_docs'],
                     f"{stats['shortages']['total_items']} pozycji")
        with col3:
            st.metric("🛠️ Technologie", 
                     stats['technologies']['active'],
                     f"z {stats['technologies']['total']} total")
        with col4:
            st.metric("⚙️ Zasoby", 
                     stats['resources']['total'])
            
        st.markdown("---")
    except Exception as e:
        st.warning(f"Nie udało się załadować panelu CTI: {e}")


