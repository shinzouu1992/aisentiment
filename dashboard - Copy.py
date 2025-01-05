import streamlit as st
import pandas as pd
import asyncpg
import plotly.express as px
import asyncio
import os

# Database connection string
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres/dbname")

# Async function to fetch data
async def fetch_data():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        query = """
            SELECT created_at, sentiment, emotion, user_name, message
            FROM sentiment_analysis
            ORDER BY created_at DESC
        """
        data = await conn.fetch(query)
        await conn.close()
        df = pd.DataFrame(data, columns=["created_at", "sentiment", "emotion", "user_name", "message"])
        df["created_at"] = pd.to_datetime(df["created_at"])
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# Clean sentiment strings
def clean_sentiments(df):
    df["sentiment"] = df["sentiment"].str.split(",").str[0].str.strip()  # Extract primary sentiment
    return df

# Streamlit UI
st.set_page_config(page_title="Community Sentiment Dashboard", layout="wide")
st.title("🚀 Community Sentiment Dashboard")
st.sidebar.header("Dashboard Options")

# Sidebar filters
date_range = st.sidebar.date_input("Filter by Date Range", [])
sentiment_filter = st.sidebar.multiselect("Filter by Sentiment", options=["Positive", "Neutral", "Negative"])
emotion_filter = st.sidebar.multiselect("Filter by Emotion", options=["Happy", "Sad", "Angry", "Frustrated"])

# Fetch and process data
st.text("Fetching data from the database...")
data = asyncio.run(fetch_data())

if not data.empty:
    data = clean_sentiments(data)  # Clean sentiment strings

    # Apply filters
    if date_range and len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range)
        data = data[(data["created_at"] >= start_date) & (data["created_at"] <= end_date)]

    if sentiment_filter:
        data = data[data["sentiment"].isin(sentiment_filter)]
    if emotion_filter:
        data = data[data["emotion"].isin(emotion_filter)]

    if data.empty:
        st.warning("No data available for the selected filters.")
    else:
        # Summary Section
        st.subheader("📌 Key Insights")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Messages", len(data))
        with col2:
            st.metric("Unique Users", data["user_name"].nunique())
        with col3:
            st.metric("Top Sentiment", data["sentiment"].mode().iloc[0])
        with col4:
            st.metric("Top Emotion", data["emotion"].mode().iloc[0])

        # Tabs for visualization
        tab1, tab2, tab3 = st.tabs(["📈 Trends", "🎭 Emotions", "👥 Users"])

        # Sentiment Trends
        with tab1:
            st.subheader("Sentiment Trends Over Time")
            sentiment_trends = (
                data.groupby([data["created_at"].dt.date, "sentiment"])
                .size()
                .reset_index(name="count")
            )
            fig = px.line(
                sentiment_trends,
                x="created_at",
                y="count",
                color="sentiment",
                title="Sentiment Trends",
                labels={"created_at": "Date", "count": "Count"},
                color_discrete_map={"Positive": "green", "Negative": "red", "Neutral": "blue"},
            )
            fig.update_layout(xaxis=dict(tickformat="%b %d", tickangle=45))
            st.plotly_chart(fig, use_container_width=True)

        # Emotion Distribution
        with tab2:
            st.subheader("Emotion Distribution")
            emotion_counts = data["emotion"].value_counts().reset_index()
            emotion_counts.columns = ["emotion", "count"]
            fig = px.pie(
                emotion_counts,
                names="emotion",
                values="count",
                title="Emotion Distribution",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            st.plotly_chart(fig)

        # Top User Contributions
        with tab3:
            st.subheader("Top Users by Contributions")
            user_counts = data["user_name"].value_counts().reset_index()
            user_counts.columns = ["user_name", "count"]
            fig = px.bar(
                user_counts.head(10),
                x="user_name",
                y="count",
                title="Top Users by Message Count",
                labels={"user_name": "User", "count": "Messages"},
                color="count",
                color_continuous_scale="Plasma",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Data Table
        st.subheader("📋 Detailed Data Table")
        st.dataframe(data, use_container_width=True)
else:
    st.warning("No data available to display.")
