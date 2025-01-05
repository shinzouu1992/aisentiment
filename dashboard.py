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
            SELECT created_at, sentiment, emotion, user_name
            FROM sentiment_analysis
            ORDER BY created_at DESC
        """
        data = await conn.fetch(query)
        await conn.close()
        return pd.DataFrame(data, columns=["created_at", "sentiment", "emotion", "user_name"])
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()


# Streamlit UI
st.title("Community Sentiment Dashboard")
st.sidebar.header("Dashboard Options")

# Sidebar filters
show_trends = st.sidebar.checkbox("Show Sentiment Trends", value=True)
show_emotions = st.sidebar.checkbox("Show Emotion Distribution", value=True)
show_users = st.sidebar.checkbox("Show User Contributions", value=True)

# Fetch data
st.text("Fetching data from the database...")
try:
    data = asyncio.run(fetch_data())
except Exception as e:
    data = pd.DataFrame()
    st.error(f"Data fetching failed: {e}")

if not data.empty:
    data["created_at"] = pd.to_datetime(data["created_at"])

    if show_trends:
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
        )
        st.plotly_chart(fig)

    if show_emotions:
        st.subheader("Emotion Distribution")
        emotion_counts = data["emotion"].value_counts().reset_index()
        emotion_counts.columns = ["emotion", "count"]
        fig = px.pie(
            emotion_counts,
            names="emotion",
            values="count",
            title="Emotion Distribution",
        )
        st.plotly_chart(fig)

    if show_users:
        st.subheader("Top Users by Contributions")
        user_counts = data["user_name"].value_counts().reset_index()
        user_counts.columns = ["user_name", "count"]
        fig = px.bar(
            user_counts.head(10),
            x="user_name",
            y="count",
            title="Top Users by Message Count",
            labels={"user_name": "User", "count": "Messages"},
        )
        st.plotly_chart(fig)

    st.dataframe(data)
else:
    st.warning("No data available to display.")
