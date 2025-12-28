"""
Progress Indicators - Reusable UI components for loading and progress.
Provides consistent progress feedback across the application.
"""

import streamlit as st
import time
from typing import Optional, Callable, List, Any
from contextlib import contextmanager


class ProgressIndicator:
    """
    Reusable progress indicator components for Streamlit.
    
    Usage:
        # Simple spinner
        with ProgressIndicator.spinner("Loading..."):
            result = do_something()
        
        # Multi-step progress
        result = ProgressIndicator.with_steps(
            func=lambda: heavy_computation(),
            steps=["Step 1", "Step 2", "Step 3"]
        )
    """
    
    @staticmethod
    @contextmanager
    def spinner(message: str = "Przetwarzanie..."):
        """Simple spinner context manager."""
        with st.spinner(message):
            yield
    
    @staticmethod
    def with_steps(
        func: Callable,
        steps: List[str],
        success_message: str = "✅ Zakończono"
    ) -> Any:
        """
        Execute function with multi-step progress bar.
        
        Args:
            func: Function to execute
            steps: List of step descriptions
            success_message: Message to show on completion
            
        Returns:
            Result of func
        """
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Show steps
            for i, step in enumerate(steps):
                progress = (i + 0.5) / len(steps)
                status_text.text(f"⏳ {step}")
                progress_bar.progress(progress)
                time.sleep(0.1)  # Visual feedback
            
            # Execute
            result = func()
            
            # Complete
            progress_bar.progress(1.0)
            status_text.text(success_message)
            time.sleep(0.3)
            
            # Cleanup
            progress_bar.empty()
            status_text.empty()
            
            return result
            
        except Exception as e:
            progress_bar.empty()
            status_text.error(f"❌ Błąd: {e}")
            raise
    
    @staticmethod
    def with_timing(func: Callable, message: str = "Przetwarzanie...") -> tuple:
        """
        Execute function and track timing.
        
        Returns:
            Tuple of (result, duration_ms)
        """
        progress_bar = st.progress(0, text=message)
        
        try:
            progress_bar.progress(30, text="Wykonywanie...")
            start = time.time()
            
            result = func()
            
            duration = (time.time() - start) * 1000
            progress_bar.progress(100, text=f"Zakończono w {duration:.0f}ms")
            time.sleep(0.3)
            progress_bar.empty()
            
            return result, duration
            
        except Exception as e:
            progress_bar.progress(100, text=f"Błąd: {e}")
            raise


class AIThinkingIndicator:
    """
    Animated indicator for AI operations.
    Shows "thinking" animation while AI processes.
    """
    
    @staticmethod
    @contextmanager
    def thinking(message: str = "AI analizuje dane..."):
        """
        Context manager for AI thinking indicator.
        
        Usage:
            with AIThinkingIndicator.thinking("Generowanie analizy..."):
                response = ai_client.generate(prompt)
        """
        status = st.status(message, expanded=True)
        
        try:
            with status:
                st.write("🔍 Analizowanie danych...")
                yield status
                st.write("✅ Zakończono")
        except Exception as e:
            with status:
                st.error(f"❌ {e}")
            raise
    
    @staticmethod
    def detailed_progress(steps: List[str]) -> 'DetailedProgress':
        """
        Create a detailed progress indicator with step-by-step updates.
        
        Returns:
            DetailedProgress context manager
        """
        return DetailedProgress(steps)


class DetailedProgress:
    """
    Detailed progress indicator with step tracking.
    
    Usage:
        with DetailedProgress(["Loading", "Processing", "Finishing"]) as dp:
            dp.update(0, "Loading data")
            data = load()
            dp.update(1, "Processing")
            result = process(data)
            dp.update(2, "Done")
    """
    
    def __init__(self, steps: List[str]):
        self.steps = steps
        self.status = None
    
    def __enter__(self):
        self.status = st.status("Przetwarzanie...", expanded=True)
        self.status.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.status:
            self.status.__exit__(exc_type, exc_val, exc_tb)
    
    def update(self, step_index: int, message: str = None):
        """Update progress to specific step."""
        if self.status is None:
            return
        
        if step_index < len(self.steps):
            step_name = self.steps[step_index]
            display = message or step_name
            st.write(f"{'✅' if step_index > 0 else '⏳'} {display}")


class ModelTrainingProgress:
    """
    Specialized progress indicator for ML model training.
    """
    
    @staticmethod
    @contextmanager
    def training(model_name: str):
        """
        Show training progress for ML model.
        
        Usage:
            with ModelTrainingProgress.training("Random Forest"):
                model.fit(X, y)
        """
        progress = st.progress(0, text=f"Trenowanie {model_name}...")
        start_time = time.time()
        
        try:
            progress.progress(10, text="Przygotowywanie cech...")
            yield progress
            
            duration = time.time() - start_time
            progress.progress(100, text=f"Model {model_name} wytrenowany w {duration:.1f}s")
            time.sleep(0.3)
            
        except Exception as e:
            progress.progress(100, text=f"Błąd treningu: {e}")
            raise
        finally:
            progress.empty()


# Convenience functions
def show_loading(message: str = "Ładowanie..."):
    """Quick loading spinner."""
    return ProgressIndicator.spinner(message)


def show_ai_thinking(message: str = "AI myśli..."):
    """Quick AI thinking indicator."""
    return AIThinkingIndicator.thinking(message)
