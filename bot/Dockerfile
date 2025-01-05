# Use Python 3.10 slim image as the base
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Copy the current directory content to the container
COPY . /app

# Upgrade pip to the latest version
RUN pip install --upgrade pip

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run the bot script
CMD ["python", "bot.py"]
