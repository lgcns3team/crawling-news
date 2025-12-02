import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """
    .env 예시:
    DB_HOST=localhost
    DB_PORT=3306
    DB_USER=root
    DB_PASSWORD=xxxx
    DB_NAME=newsdb
    """
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        db=os.getenv("DB_NAME", "newsdb"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
