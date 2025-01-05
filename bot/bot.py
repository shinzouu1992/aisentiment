import logging
from telegram.ext import Application, MessageHandler, filters
import httpx
import json
import asyncpg
import os
import asyncio

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Environment Variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")
NEUROCHAIN_API_KEY = os.getenv("NEUROCHAIN_API_KEY", "your_neurochain_api_key")
TELEGRAM_API_KEY = os.getenv("TELEGRAM_API_KEY", "your_telegram_api_key")

# Check for missing critical environment variables
if not DATABASE_URL or not NEUROCHAIN_API_KEY or not TELEGRAM_API_KEY:
    logger.error("One or more environment variables are missing. Please check the .env file.")
    exit(1)

# Global cache to track processed message IDs
processed_messages = set()


async def ensure_schema(conn):
    """Ensure the database schema is correct."""
    try:
        # Create the table if it doesn't exist
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS sentiment_analysis (
                message_id TEXT PRIMARY KEY,
                user_name TEXT,
                message TEXT,
                sentiment TEXT,
                justification TEXT,
                emotion TEXT,
                urgency TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Ensure the `created_at` column exists
        await conn.execute('''
            ALTER TABLE sentiment_analysis
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        ''')

        logger.info("Database schema ensured.")
    except Exception as e:
        logger.error(f"Error ensuring database schema: {e}")
        raise



async def store_in_db(message_id, user_name, message_text, sentiment, justification, emotion, urgency):
    """Store message, sentiment, justification, emotion, and urgency in the database."""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Ensure the schema is correct before inserting data
        await ensure_schema(conn)

        # Insert the data into the table
        result = await conn.execute('''
            INSERT INTO sentiment_analysis(
                message_id, user_name, message, sentiment, justification, emotion, urgency
            )
            VALUES($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (message_id) DO NOTHING
        ''', message_id, user_name, message_text, sentiment, justification, emotion, urgency)

        if result == "INSERT 0 0":
            logger.warning(f"[MessageID: {message_id}] Duplicate message. Skipping database insert.")
        else:
            logger.info(f"[MessageID: {message_id}] Message successfully stored in the database.")

        await conn.close()
    except Exception as e:
        logger.error(f"[MessageID: {message_id}] Database error: {e}")


async def handle_message(update, context):
    """Handle incoming messages from the Telegram bot."""
    message_id = str(update.message.message_id)
    user_name = update.message.from_user.first_name
    message_text = update.message.text

    # Skip if the message has already been processed
    if message_id in processed_messages:
        logger.warning(f"[MessageID: {message_id}] Message already processed. Skipping.")
        return

    # Mark the message as being processed
    processed_messages.add(message_id)

    logger.info(f"Message from {user_name}: {message_text} (MessageID: {message_id})")

    url = 'https://ncmb.neurochain.io/tasks/message'
    data = {
        "model": "Mistral-7B-Instruct-v0.2-GPTQ",
        "prompt": f'[INST] You are sentiment analytic. respond in format '
                  f'SENTIMENT: sentiment, JUSTIFICATION: basis on which the sentiment was derived, '
                  f'EMOTIONS: emotions, URGENCY: level of urgency [/INST] Analyze this message: {message_text}',
        "max_tokens": 1024,
        "temperature": 0.6,
        "top_p": 0.95,
        "frequency_penalty": 0,
        "presence_penalty": 1.1,
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {NEUROCHAIN_API_KEY}',
    }

    # Retry logic for API call
    for attempt in range(3):  # Retry up to 3 times
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=headers, timeout=30)

            if response.status_code in [200, 201]:
                parsed_response = response.json()
                if 'choices' in parsed_response and isinstance(parsed_response['choices'], list) and len(parsed_response['choices']) > 0:
                    text = parsed_response['choices'][0].get('text', '')

                    # Validate text content
                    if not text:
                        logger.error(f"[MessageID: {message_id}] API response 'text' field is empty or missing.")
                        return

                    # Improved Parsing Logic
                    try:
                        sentiment = None
                        justification = None
                        emotion = None
                        urgency = None

                        lines = text.splitlines()
                        for line in lines:
                            if line.startswith("SENTIMENT:"):
                                sentiment = line.split("SENTIMENT:")[1].strip()
                            elif line.startswith("JUSTIFICATION:"):
                                justification = line.split("JUSTIFICATION:")[1].strip()
                            elif line.startswith("EMOTIONS:"):
                                emotion = line.split("EMOTIONS:")[1].strip()
                            elif line.startswith("URGENCY:"):
                                urgency = line.split("URGENCY:")[1].strip()

                        if not (sentiment and justification and emotion and urgency):
                            raise ValueError("Some fields are missing in the parsed response.")

                        logger.info(f"[MessageID: {message_id}] SENTIMENT: {sentiment}")
                        logger.info(f"[MessageID: {message_id}] JUSTIFICATION: {justification}")
                        logger.info(f"[MessageID: {message_id}] EMOTIONS: {emotion}")
                        logger.info(f"[MessageID: {message_id}] URGENCY: {urgency}")

                        # Store in the database
                        await store_in_db(message_id, user_name, message_text, sentiment, justification, emotion, urgency)

                    except Exception as e:
                        logger.error(f"[MessageID: {message_id}] Error parsing text: {e}")
                        logger.error(f"[MessageID: {message_id}] Received text: {text}")
                        return
                else:
                    logger.error(f"[MessageID: {message_id}] Unexpected API response format or missing 'choices'.")
            else:
                logger.error(f"[MessageID: {message_id}] API call failed with status {response.status_code}: {response.text}")
            break  # Exit loop if successful or unrecoverable error occurs
        except httpx.RequestError as e:
            logger.error(f"[MessageID: {message_id}] API request failed on attempt {attempt + 1}: {e}")
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            logger.error(f"[MessageID: {message_id}] Unexpected error: {e}")
            break


def main():
    """Run the bot."""
    try:
        message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
        application = Application.builder().token(TELEGRAM_API_KEY).concurrent_updates(True).build()
        application.add_handler(message_handler)
        application.run_polling()
    except Exception as e:
        logger.error(f"Bot encountered an error: {e}")


if __name__ == '__main__':
    main()
