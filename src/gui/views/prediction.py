"""
Prediction view for the AI Supply Assistant.
Shows demand forecasting with multiple ML models.
Enhanced with MVVM ViewModels and reusable components.
"""

from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

# Import components
from src.gui.components import (
    ModelTrainingProgress,
    info_card,
)

# Import ViewModels
from src.viewmodels import ModelResult, ModelType, PredictionViewModel


def render_prediction_view(
    db,
    product_map: dict[int, str],
    sorted_product_ids: list,
    start_date,
    end_date,
    prepare_time_series,
    fill_missing_weeks,
    Forecaster,
):
    """
    Renders the prediction/forecasting view with MVVM architecture.

    Args:
        db: DatabaseConnector instance
        product_map: Dict mapping TowarId -> DisplayName
        sorted_product_ids: List of product IDs sorted by usage
        start_date: Filter start date
        end_date: Filter end date
        prepare_time_series: Preprocessing function
        fill_missing_weeks: Preprocessing function
        Forecaster: Forecaster class from src.forecasting
    """
    st.subheader("📈 Prognoza Zapotrzebowania")

    # Initialize ViewModel (cached in session state)
    vm = _get_or_create_viewmodel(db, Forecaster, prepare_time_series, fill_missing_weeks)

    # Load data with progress
    if not _load_data_with_viewmodel(vm):
        st.warning("Brak danych do prognozowania.")
        return

    # Get available products
    available_products = vm.prediction_state.available_products
    product_list = [x for x in sorted_product_ids if x in available_products]
    if not product_list:
        product_list = list(available_products)

    if not product_list:
        st.warning("Brak produktów z wystarczającą ilością danych historycznych.")
        return

    # Two-column layout for inputs
    col_input1, col_input2 = st.columns(2)

    with col_input1:
        selected_product = st.selectbox(
            "Wybierz Surowiec do Prognozy:", product_list, format_func=lambda x: product_map.get(x, str(x))
        )

    with col_input2:
        model_option = st.selectbox(
            "Wybierz Model:",
            [
                ("Random Forest (Zbalansowany)", ModelType.RANDOM_FOREST),
                ("Gradient Boosting (Wysoka Precyzja)", ModelType.GRADIENT_BOOSTING),
                ("Exponential Smoothing (Trend/Sezonowość)", ModelType.EXPONENTIAL_SMOOTHING),
                ("🧠 LSTM Deep Learning (Zaawansowany)", ModelType.LSTM),
            ],
            format_func=lambda x: x[0],
        )

    model_display_name, model_type = model_option

    # Train and get predictions
    result = _train_model_with_progress(vm, selected_product, model_type, model_display_name)

    if result is None or not result.is_valid:
        if result and result.error:
            st.error(f"Błąd modelu: {result.error}")
        return

    # Get combined data for charting
    chart_df = vm.get_combined_forecast_data(selected_product, model_type, start_date=start_date, end_date=end_date)

    if chart_df is not None and not chart_df.empty:
        _render_forecast_chart(chart_df, selected_product, product_map)
        _render_model_metrics(result)
        _render_business_interpretation(result)
        _render_model_info(model_type)


def _get_or_create_viewmodel(db, Forecaster, prepare_time_series, fill_missing_weeks) -> PredictionViewModel:
    """Get ViewModel from session state or create new one."""
    cache_key = "prediction_viewmodel"

    if cache_key not in st.session_state:
        forecaster = Forecaster()
        st.session_state[cache_key] = PredictionViewModel(
            db=db, forecaster=forecaster, prepare_time_series=prepare_time_series, fill_missing_weeks=fill_missing_weeks
        )

    return st.session_state[cache_key]


def _load_data_with_viewmodel(vm: PredictionViewModel) -> bool:
    """Load data using ViewModel with progress indicator."""
    # Check if already loaded
    if vm.prediction_state.df_prepared is not None:
        return True

    # Load with progress
    progress = st.progress(0, text="Pobieranie danych historycznych...")

    try:
        progress.progress(20, text="Łączenie z bazą danych...")
        success = vm.load_data(force_refresh=False)

        if success:
            n_products = len(vm.prediction_state.available_products)
            progress.progress(100, text=f"Załadowano dane dla {n_products} produktów")
        else:
            progress.progress(100, text="Błąd ładowania danych")

        import time

        time.sleep(0.3)
        progress.empty()

        return success

    except Exception as e:
        progress.progress(100, text=f"Błąd: {e}")
        return False


def _train_model_with_progress(
    vm: PredictionViewModel, product_id: int, model_type: ModelType, model_display_name: str
) -> Optional[ModelResult]:
    """Train model with progress indicator."""

    # Check cache first
    cache_key = f"{product_id}_{model_type.value}"
    if cache_key in vm.prediction_state.model_results:
        cached = vm.prediction_state.model_results[cache_key]
        if cached.is_valid:
            return cached

    # Train with progress
    with ModelTrainingProgress.training(model_display_name):
        result = vm.train_model(product_id, model_type, weeks_ahead=4)

    return result


def _render_forecast_chart(chart_df: pd.DataFrame, product_id: int, product_map: dict[int, str]):
    """Render the forecast chart using Plotly."""
    fig = px.line(
        chart_df,
        x="Date",
        y="Quantity",
        color="Type",
        title=f"Prognoza: {product_map.get(product_id, str(product_id))}",
        color_discrete_map={
            "Historical": "royalblue",
            "Forecast": "orange",
            "Forecast (Baseline)": "gray",
            "Forecast (Random Forest)": "orange",
            "Forecast (Gradient Boosting)": "darkgreen",
            "Forecast (Exponential Smoothing)": "purple",
            "Forecast (LSTM (Deep Learning))": "crimson",
        },
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_model_metrics(result: ModelResult):
    """Render model performance metrics with MAPE, RMSE, MAE, R²."""
    if result.metrics:
        # Show 4 metrics in responsive columns
        cols = st.columns(4)

        metrics_display = [
            ("mape", "MAPE", "Średni % błędu prognozy", "%"),
            ("rmse", "RMSE", "Pierwiastek błędu średniokwadratowego", ""),
            ("mae", "MAE", "Średni błąd bezwzględny", ""),
            ("r2", "R²", "Współczynnik determinacji (1.0 = idealny)", ""),
        ]

        for i, (key, label, help_text, suffix) in enumerate(metrics_display):
            if key in result.metrics:
                value = result.metrics[key]
                if suffix == "%":
                    cols[i].metric(label, f"{value:.1f}%", help=help_text)
                elif key == "r2":
                    cols[i].metric(label, f"{value:.3f}", help=help_text)
                else:
                    cols[i].metric(label, f"{value:.2f}", help=help_text)

        # Training time in expander
        if result.training_time_ms > 0:
            st.caption(f"⏱️ Czas treningu: {result.training_time_ms:.0f} ms")


def _render_model_info(model_type: ModelType):
    """Render model explanation with performance tips."""
    info_map = {
        ModelType.RANDOM_FOREST: (
            "**🌲 Random Forest**: Ensemble drzew decyzyjnych. "
            "Dobry balans między dopasowaniem a generalizacją. "
            "⚡ Szybki w treningu."
        ),
        ModelType.GRADIENT_BOOSTING: (
            "**📈 Gradient Boosting**: Uczy się na błędach poprzedników. "
            "Często dokładniejszy, ale wolniejszy. "
            "⏱️ Może wymagać więcej czasu."
        ),
        ModelType.EXPONENTIAL_SMOOTHING: (
            "**📉 Exponential Smoothing (Holt-Winters)**: Modeluje trend i sezonowość bezpośrednio. "
            "Dobry dla stabilnych wzorców. "
            "📊 Najlepszy dla danych z wyraźną sezonowością."
        ),
        ModelType.BASELINE: (
            "**📏 Baseline (SMA-4)**: Prosta średnia krocząca z ostatnich 4 tygodni. "
            "Punkt odniesienia do porównań. "
            "📏 Szybki i prosty."
        ),
        ModelType.LSTM: (
            "**🧠 LSTM (Deep Learning)**: Sieć neuronowa z pamięcią długoterminową. "
            "Rozpoznaje złożone wzorce w danych. "
            "⏳ Dłuższy trening, potencjalnie najwyższa dokładność."
        ),
    }
    st.info(info_map.get(model_type, ""))


def _render_business_interpretation(result: ModelResult):
    """Render business-friendly interpretation of the forecast."""
    st.divider()
    st.subheader("💡 Interpretacja Biznesowa")

    if result.predictions.empty:
        st.write("Brak prognoz do interpretacji.")
        return

    # Calculate summary stats
    total_forecast = result.predictions["Predicted_Qty"].sum()
    avg_forecast = result.predictions["Predicted_Qty"].mean()
    weeks_count = len(result.predictions)

    # Error context
    mae = result.metrics.get("mae", 0)
    mae_context = f"(±{mae:.1f} jedn.)" if mae > 0 else ""

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown(
            f"""
        **Wnioski dla planowania:**
        * Przewidywane zapotrzebowanie na najbliższe **{weeks_count} tygodnie** wynosi łącznie **{total_forecast:,.0f}** jednostek.
        * Średnio należy przygotować ok. **{avg_forecast:.1f}** jednostek tygodniowo {mae_context}.
        """
        )

        if "forecast_change_pct" in result.metrics:
            change = result.metrics["forecast_change_pct"]
            icon = "📈" if change > 5 else "📉" if change < -5 else "➡️"
            desc = "Wzrost" if change > 5 else "Spadek" if change < -5 else "Stabilizacja"
            st.markdown(
                f"**Trend:** {icon} {desc} zapotrzebowania o **{abs(change):.1f}%** względem ostatnich tygodni."
            )

    with col2:
        info_card(
            "Rekomendacja",
            f"Zabezpiecz zapas na poziome min. **{total_forecast * 1.1:,.0f}** jednostek (110% prognozy) aby uniknąć braków.",
            card_type="success",
        )
