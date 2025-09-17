import os
from dotenv import load_dotenv
import logging

load_dotenv() 
TOKEN = os.getenv("TOKEN")
dbname = os.getenv("DB_NAME")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    filename="app.log",
    filemode="a",
    )
logger = logging.getLogger(__name__)

