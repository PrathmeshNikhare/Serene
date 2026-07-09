import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Add workspace root to path
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(workspace_root)

# Load env variables from root .env
env_path = os.path.join(workspace_root, ".env")
load_dotenv(dotenv_path=env_path)

from backend.core.config import settings
from backend.models.database import Base

def init_db():
    db_url = settings.DATABASE_URL or os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL is not set in the environment or .env file.")
        print("Please check your .env file at the project root.")
        sys.exit(1)
        
    # Mask password for logging
    masked_url = db_url
    if "@" in db_url:
        parts = db_url.split("@")
        cred_parts = parts[0].split(":")
        if len(cred_parts) > 2:
            masked_url = f"{cred_parts[0]}:{cred_parts[1]}:****@{parts[1]}"
            
    print(f"Connecting to database: {masked_url}...")
    
    try:
        # Create SQLAlchemy engine
        engine = create_engine(db_url)
        
        # Connect and enable pgvector extension first
        with engine.connect() as conn:
            print("Enabling pgvector extension if it does not exist...")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            print("pgvector extension check complete.")
        
        # Create all tables
        print("Creating all tables defined in backend/models/database.py...")
        Base.metadata.create_all(bind=engine)
        print("Database schema created successfully in Supabase!")
        
    except Exception as e:
        print(f"ERROR: Failed to initialize database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
