# ViewModels package for MVVM architecture
"""
ViewModels encapsulate business logic and state management
separate from the UI layer.
"""

from .analysis_viewmodel import AnalysisState, AnalysisSummary, AnalysisViewModel
from .base_viewmodel import BaseViewModel, LoadingState, ViewModelState
from .prediction_viewmodel import ModelResult, ModelType, PredictionState, PredictionViewModel

__all__ = [
    # Base
    "BaseViewModel",
    "ViewModelState",
    "LoadingState",
    # Prediction
    "PredictionViewModel",
    "PredictionState",
    "ModelType",
    "ModelResult",
    # Analysis
    "AnalysisViewModel",
    "AnalysisState",
    "AnalysisSummary",
]
