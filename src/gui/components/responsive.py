"""
Responsive Layout Components.
CSS and layout utilities for mobile-friendly design.
"""

import streamlit as st


def apply_responsive_styles():
    """
    Apply responsive CSS styles for mobile-friendly layout.
    Call once at the start of the app.
    """
    st.markdown("""
    <style>
    /* Mobile responsive columns */
    @media (max-width: 768px) {
        .stColumns > div {
            flex-direction: column !important;
        }
        .stColumns > div > div {
            width: 100% !important;
            max-width: 100% !important;
        }
        
        /* Larger touch targets */
        .stButton > button {
            min-height: 48px;
            font-size: 16px;
        }
        
        .stSelectbox > div {
            min-height: 48px;
        }
        
        /* Better spacing on mobile */
        .stApp {
            padding: 0.5rem;
        }
        
        /* Sidebar adjustments */
        section[data-testid="stSidebar"] {
            width: 280px !important;
        }
    }
    
    /* Tablet responsive */
    @media (min-width: 769px) and (max-width: 1024px) {
        .stColumns > div > div {
            min-width: 200px;
        }
    }
    
    /* Card-like containers */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 1.5rem;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .info-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        border-left: 4px solid #007bff;
    }
    
    .success-card {
        background: #d4edda;
        border-radius: 8px;
        padding: 1rem;
        border-left: 4px solid #28a745;
    }
    
    .warning-card {
        background: #fff3cd;
        border-radius: 8px;
        padding: 1rem;
        border-left: 4px solid #ffc107;
    }
    
    /* Improved chart container */
    .chart-container {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    /* Status indicators */
    .status-green {
        color: #28a745;
        font-weight: 600;
    }
    
    .status-yellow {
        color: #ffc107;
        font-weight: 600;
    }
    
    .status-red {
        color: #dc3545;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)


def responsive_columns(ratios: list, gap: str = "medium"):
    """
    Create responsive columns that stack on mobile.
    
    Args:
        ratios: List of column width ratios, e.g., [2, 1, 1]
        gap: Gap size between columns: "small", "medium", "large"
        
    Returns:
        List of column objects
    """
    gap_sizes = {
        "small": "small",
        "medium": "medium", 
        "large": "large"
    }
    
    return st.columns(ratios, gap=gap_sizes.get(gap, "medium"))


def metric_card(title: str, value: str, delta: str = None, help_text: str = None):
    """
    Render a styled metric card.
    
    Args:
        title: Card title
        value: Main value to display
        delta: Change indicator (optional)
        help_text: Help tooltip (optional)
    """
    st.metric(
        label=title,
        value=value,
        delta=delta,
        help=help_text
    )


def info_card(title: str, content: str, card_type: str = "info"):
    """
    Render a styled info card.
    
    Args:
        title: Card title
        content: Card content
        card_type: "info", "success", "warning"
    """
    css_class = f"{card_type}-card"
    
    st.markdown(f"""
    <div class="{css_class}">
        <strong>{title}</strong><br/>
        {content}
    </div>
    """, unsafe_allow_html=True)


def two_column_layout():
    """
    Standard two-column layout (2:1 ratio).
    Responsive - stacks on mobile.
    """
    return st.columns([2, 1])


def three_column_layout():
    """
    Standard three-column layout (equal widths).
    Responsive - stacks on mobile.
    """
    return st.columns(3)


def sidebar_section(title: str):
    """
    Create a styled sidebar section.
    
    Usage:
        with sidebar_section("Settings"):
            st.selectbox(...)
    """
    st.sidebar.markdown(f"### {title}")
    st.sidebar.markdown("---")
