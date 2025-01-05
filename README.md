To create a `docker-compose.yml` file that sets up a PostgreSQL container and runs your Telegram bot, you need to define services for both PostgreSQL and the bot in the Docker Compose file.

Here's how you can create a `docker-compose.yml` file that will start a PostgreSQL container and your Telegram bot container:

### Directory Structure:
Before starting, you should have the following directory structure:

```
/your-project/
│
├── bot/
│   ├── bot.py  # Your Telegram bot script
│   ├── requirements.txt  # Python dependencies (e.g., asyncpg, httpx, python-telegram-bot)
│   ├── Dockerfile  # Dockerfile used to build bot container
│
├── docker-compose.yml  # Docker Compose configuration file
```

### Step 1: `docker-compose.yml`

```yaml
version: '3.8'

services:
  # PostgreSQL container
  postgres:
    image: postgres:14
    environment:
      POSTGRES_USER: your_user
      POSTGRES_PASSWORD: your_password
      POSTGRES_DB: your_database
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # Telegram bot container
  telegram-bot:
    build: ./bot  # Path to the bot folder where the Dockerfile is located
    environment:
      DATABASE_URL: postgres://your_user:your_password@postgres/your_database  # Database connection string for the bot
      NEUROCHAIN_API_KEY: your-neurochainai-api-key #add your NeurochainAI API key that will be used for network communication
      TELEGRAM_API_KEY: your_telegram_api_key # generate and add your Telegram Bot Token from @Botfather
    depends_on:
      - postgres  # Ensure PostgreSQL starts before the bot
    volumes:
      - ./bot:/app  # Mount the bot folder to the container
    restart: always

volumes:
  postgres_data:
    driver: local

```

### Step 2: `Dockerfile` for the bot

Inside your `bot/` folder, create a `Dockerfile` to define how your bot will be built and run.

```Dockerfile
# Base image with Python 3.10
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Copy the current directory content to the container
COPY . /app

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the bot script
CMD ["python", "bot.py"]
```

### Step 3: `requirements.txt`

You need to have a `requirements.txt` file in the `bot/` folder to define your Python dependencies.

```txt
python-telegram-bot==20.0
httpx==0.24.0
asyncpg==0.27.0
```

### Step 4: Build and Run with Docker Compose

To start your PostgreSQL and Telegram bot using Docker Compose:

1. Open a terminal and navigate to your project directory (where `docker-compose.yml` is located).
2. Run the following command to build and start the containers:

```bash
docker-compose up --build
```

This command will:
- Pull the PostgreSQL image.
- Build your bot container using the `Dockerfile` in the `bot/` folder.
- Start both the PostgreSQL and bot services.

### Running the Bot
Once you run `docker-compose up --build`, the bot and PostgreSQL will start, and your bot should now interact with the PostgreSQL database as per your bot logic. The logs will be displayed in the terminal.

You can stop the containers with:

```bash
docker-compose down
```

This setup ensures that your bot is running in a container and interacting with PostgreSQL. For any additional PostreSQL query logic or results dashboard feel free to edit or amend this code.