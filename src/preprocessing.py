import pandas as pd


def prepare_time_series(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts raw aggregated data into a proper time series format.

    Expected columns in df: 'Year', 'Week', 'TowarId', 'Quantity'

    1. Creates a 'Date' column from Year-Week.
    2. Handles missing weeks (fills with 0 for each product).
    """
    if df.empty:
        return df

    # Create Date from ISO Week
    # usage: from_isocalendar(year, week, day)
    # We'll use day=1 (Monday) to represent the week
    df["Date"] = df.apply(lambda row: pd.Timestamp.fromisocalendar(int(row["Year"]), int(row["Week"]), 1), axis=1)

    # Sort
    df = df.sort_values("Date")

    # We might want to pivot to have full time range for each product,
    # but for now let's just ensure types are correct.
    df["Quantity"] = pd.to_numeric(df["Quantity"]).fillna(0)

    return df


def fill_missing_weeks(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures every product has a record for every week in the range.
    """
    if df.empty:
        return df

    # Get full range of dates
    min_date = df["Date"].min()
    max_date = df["Date"].max()
    all_dates = pd.date_range(start=min_date, end=max_date, freq="W-MON")

    products = df["TowarId"].unique()

    # Create a MultiIndex of complete (Product, Date) pairs
    multi_index = pd.MultiIndex.from_product([products, all_dates], names=["TowarId", "Date"])

    # Reindex
    df_indexed = df.set_index(["TowarId", "Date"])
    df_full = df_indexed.reindex(multi_index, fill_value=0).reset_index()

    # Recover Year/Week if needed
    df_full["Year"] = df_full["Date"].dt.isocalendar().year
    df_full["Week"] = df_full["Date"].dt.isocalendar().week

    return df_full
