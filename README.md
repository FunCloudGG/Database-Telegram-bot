# Telegram Database Bot

A small educational project: a Telegram bot for interacting with a database.

## Main File
`database_telebot.py`

## Features
- Add and search records in the database via Telegram
- Demonstrates basic bot functionality
- (Planned) Multi-language support and improved project structure

## Installation
1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the bot:

```bash
python database_telebot.py
```

## Tests

Basic database tests using pytest:

```bash
pytest -v
```

## Technologies

* Python 3.11+
* psycopg2
* pyTelegramBotAPI (telebot)
* pytest
* python-dotenv

## Notes

* Environment variables (like database credentials) should be stored in a `.env` file and **not** committed.
* Tested locally with a PostgreSQL database.

