# Base image with Python 3.10
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy the application files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir \
    streamlit \
    pandas \
    psycopg2-binary \
    asyncpg \
    plotly

# Command to run the Streamlit app
CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.enableCORS=false"]
