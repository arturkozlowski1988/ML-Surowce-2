"""
Analysis view for the AI Supply Assistant.
Shows historical production data analysis with charts and purchaser panel.
Enhanced with MVVM ViewModels and responsive components.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Dict, Any, Optional

# Import ViewModels
from src.viewmodels import AnalysisViewModel, AnalysisSummary

# Import components
from src.gui.components import (
    ProgressIndicator,
    apply_responsive_styles,
    metric_card,
    info_card,
    responsive_columns
)


def render_analysis_view(
    db,
    product_map: Dict[int, str],
    sorted_product_ids: list,
    start_date,
    end_date,
    prepare_time_series,
    fill_missing_weeks
):
    """
    Renders the historical data analysis view with MVVM architecture.
    
    Args:
        db: DatabaseConnector instance
        product_map: Dict mapping TowarId -> DisplayName
        sorted_product_ids: List of product IDs sorted by usage
        start_date: Filter start date
        end_date: Filter end date
        prepare_time_series: Preprocessing function
        fill_missing_weeks: Preprocessing function
    """
    st.subheader("📊 Analiza Historyczna Produkcji")
    
    # Initialize ViewModel (cached in session state)
    vm = _get_or_create_viewmodel(db, prepare_time_series, fill_missing_weeks)
    
    # Load data with progress
    if not _load_data_with_viewmodel(vm):
        st.warning("Brak danych historycznych z produkcji.")
        return
    
    # Apply date filter
    vm.apply_date_filter(start_date, end_date)
    
    # Render metrics
    _render_metrics(vm, db)
    
    # Visualization
    st.subheader("Trend zużycia")
    
    # Get filtered data
    df_filtered = vm.analysis_state.df_filtered
    if df_filtered is None or df_filtered.empty:
        st.warning("Brak danych w wybranym zakresie dat.")
        return
    
    # Product Selection with Names - SORTED by Usage
    hist_ids = df_filtered['TowarId'].unique()
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
    
    fig = px.line(chart_data, x='Date', y='Quantity', color='ProductLabel', title="Zużycie w czasie")
    st.plotly_chart(fig, use_container_width=True)
    
    # --- Purchaser View (Usage & BOM) ---
    _render_purchaser_panel(db, product_map, selected_ids)
    
    # Data Preview with lazy loading
    with st.expander("Podgląd surowych danych"):
        df_full = vm.analysis_state.df_historical
        if df_full is not None:
            st.dataframe(df_full.head(100))
            if len(df_full) > 100:
                st.caption(f"Wyświetlono 100 z {len(df_full)} rekordów. Użyj filtrów dat aby zawęzić zakres.")


def _get_or_create_viewmodel(db, prepare_time_series, fill_missing_weeks) -> AnalysisViewModel:
    """Get ViewModel from session state or create new one."""
    cache_key = "analysis_viewmodel"
    
    if cache_key not in st.session_state:
        st.session_state[cache_key] = AnalysisViewModel(
            db=db,
            prepare_time_series=prepare_time_series,
            fill_missing_weeks=fill_missing_weeks
        )
    
    return st.session_state[cache_key]


def _load_data_with_viewmodel(vm: AnalysisViewModel) -> bool:
    """Load data using ViewModel with progress indicator."""
    # Check if already loaded
    if vm.analysis_state.df_historical is not None:
        return True
    
    # Load with progress
    progress = st.progress(0, text="Łączenie z bazą danych...")
    
    try:
        progress.progress(20, text="Pobieranie danych historycznych...")
        import time
        start_time = time.time()
        
        success = vm.load_all_data(force_refresh=False)
        
        if success:
            duration = time.time() - start_time
            n_records = len(vm.analysis_state.df_historical) if vm.analysis_state.df_historical is not None else 0
            progress.progress(100, text=f"Pobrano {n_records} rekordów w {duration:.1f}s")
        else:
            progress.progress(100, text="Błąd ładowania danych")
        
        time.sleep(0.3)
        progress.empty()
        
        return success
        
    except Exception as e:
        progress.progress(100, text=f"Błąd: {e}")
        return False


def _render_metrics(vm: AnalysisViewModel, db) -> None:
    """Render metrics row using ViewModel summary."""
    summary = vm.analysis_state.summary
    
    col1, col2, col3 = st.columns(3)
    
    if summary:
        col1.metric("Całkowite Zużycie (okres)", f"{summary.total_quantity:,.0f}")
        col2.metric("Aktywne Surowce", summary.total_products)
        
        # Trend indicator
        trend_icons = {
            'up': '📈',
            'down': '📉',
            'stable': '➡️'
        }
        trend_icon = trend_icons.get(summary.trend_direction, '➡️')
        col3.metric("Trend", f"{trend_icon} {summary.trend_direction.title()}")
    else:
        # Fallback to direct calculation if no summary
        df_filtered = vm.analysis_state.df_filtered
        if df_filtered is not None and not df_filtered.empty:
            total_qty = df_filtered['Quantity'].sum()
            total_products = df_filtered['TowarId'].nunique()
            col1.metric("Całkowite Zużycie (okres)", f"{total_qty:,.0f}")
            col2.metric("Aktywne Surowce", total_products)
    
    # Show query performance if diagnostics available
    stats = db.get_diagnostics_stats()
    if stats.get('total_queries', 0) > 0:
        avg_time = stats.get('avg_duration', 0) * 1000
        col3.metric("Śr. czas zapytania", f"{avg_time:.0f} ms")


def _render_purchaser_panel(db, product_map: Dict[int, str], selected_ids: list):
    """Renders the purchaser context panel with optimized loading."""
    st.divider()
    st.subheader("🛒 Panel Zakupowca: Kontekst Produkcyjny")
    
    if len(selected_ids) == 1:
        sel_id = int(selected_ids[0])
        
        # Use columns for parallel visual loading
        col_u1, col_u2 = st.columns([2, 3])
        
        with col_u1:
            st.markdown(f"**Gdzie używany jest surowiec: {product_map.get(sel_id, str(sel_id))}?**")
            
            with st.spinner("Analizowanie powiązań..."):
                df_usage = db.get_product_usage_stats(sel_id)
            
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
                fig_usage.update_layout(
                    yaxis={'categoryorder': 'total ascending'}, 
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                st.plotly_chart(fig_usage, use_container_width=True)
                
                # Product Selector for BOM
                code_to_id = dict(zip(df_usage['FinalProductCode'], df_usage['FinalProductId']))
                final_product_options = dict(zip(df_usage['FinalProductCode'], df_usage['FinalProductName']))
                
                selected_final_code = st.selectbox(
                    "🔍 Sprawdź skład wyrobu (BOM):", 
                    list(final_product_options.keys()),
                    format_func=lambda x: f"{final_product_options[x]} ({x})"
                )
            else:
                st.info("Brak bezpośredniego użycia w zleceniach produkcyjnych (Typ 1/2).")
                selected_final_code = None
                final_product_options = {}
                code_to_id = {}

        with col_u2:
            if not df_usage.empty and selected_final_code:
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
