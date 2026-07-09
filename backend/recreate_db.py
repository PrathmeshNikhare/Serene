import os
import sys
from sqlalchemy import create_engine, text

# Add workspace root to path
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(workspace_root)

# Load env variables from root .env
from dotenv import load_dotenv
env_path = os.path.join(workspace_root, ".env")
load_dotenv(dotenv_path=env_path)

from backend.core.config import settings
from backend.models.database import Base

def recreate_db():
    db_url = settings.DATABASE_URL
    if not db_url:
        print("ERROR: DATABASE_URL is not set.")
        sys.exit(1)
        
    print("Connecting to database to drop and recreate tables...")
    engine = create_engine(db_url)
    
    try:
        with engine.connect() as conn:
            print("Dropping existing tables CASCADE...")
            conn.execute(text("DROP TABLE IF EXISTS user_nudge_feedback CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS aura_memories CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS ai_insights_cache CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS mood_logs CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
            conn.commit()
            print("Successfully dropped existing tables.")
            
        print("Creating all tables defined in backend/models/database.py...")
        Base.metadata.create_all(bind=engine)
        print("Database tables recreated successfully!")
        
    except Exception as e:
        print(f"ERROR: Failed to recreate database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    recreate_db()
