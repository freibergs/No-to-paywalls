import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('articles.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            article_id TEXT UNIQUE,
            title TEXT,
            lead TEXT,
            text_content TEXT,
            meta_image_url TEXT,
            full_url TEXT,
            timestamp DATETIME
        )
    ''')
    conn.commit()
    conn.close()

def get_article_from_cache(article_id):
    conn = sqlite3.connect('articles.db')
    c = conn.cursor()
    c.execute('SELECT * FROM articles WHERE article_id = ?', (article_id,))
    article = c.fetchone()
    conn.close()
    if article:
        return {
            "source": article[1],
            "article_id": article[2],
            "title": article[3],
            "lead": article[4],
            "text_content": article[5],
            "meta_image_url": article[6],
            "full_url": article[7]
        }
    return None

def save_article_to_cache(article_id, title, lead, text_content, meta_image_url, full_url, source):
    conn = sqlite3.connect('articles.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO articles 
        (source, article_id, title, lead, text_content, meta_image_url, full_url, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (source, article_id, title, lead, text_content, meta_image_url, full_url, datetime.now()))
    conn.commit()
    conn.close()