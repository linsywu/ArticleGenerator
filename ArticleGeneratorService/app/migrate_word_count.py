"""Add word_count columns to accounts table"""
from app.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(accounts)"))
        columns = [row[1] for row in result.fetchall()]
        if "word_count_options" not in columns:
            conn.execute(text("ALTER TABLE accounts ADD COLUMN word_count_options TEXT"))
            print("Added word_count_options column")
        if "word_count" not in columns:
            conn.execute(text("ALTER TABLE accounts ADD COLUMN word_count INTEGER"))
            print("Added word_count column")
        conn.commit()

if __name__ == "__main__":
    migrate()
    print("Migration complete")
