# ViewModels package for MVVM architecture
"""
ViewModels encapsulate business logic and state management
separate from the UI layer.
"""

from .base_viewmodel import (
    BaseViewModel,
    ViewModelState,
    LoadingState
)

from .prediction_viewmodel import (
    PredictionViewModel,
    PredictionState,
    ModelType,
    ModelResult
)

from .analysis_viewmodel import (
    AnalysisViewModel,
    AnalysisState,
    AnalysisSummary
)

__all__ = [
    # Base
    'BaseViewModel',
    'ViewModelState',
    'LoadingState',
    # Prediction
    'PredictionViewModel',
    'PredictionState',
    'ModelType',
    'ModelResult',
    # Analysis
    'AnalysisViewModel',
    'AnalysisState',
    'AnalysisSummary',
]
