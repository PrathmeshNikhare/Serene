import os
import uuid
import logging
import vecs
import ollama

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# ==========================================
# 1. DATABASE CONNECTION
# ==========================================
# In production, this is your Supabase PostgreSQL connection string.
# Example: "postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT].supabase.co:5432/postgres"
DB_CONNECTION = os.getenv(
    "SUPABASE_DB_URL", 
    "postgresql://postgres:postgres@localhost:54322/postgres" # Default local fallback
)

# Connect to the database via Supabase's `vecs` client
# This automatically enables the pgvector extension if it's not already enabled!
vx = vecs.create_client(DB_CONNECTION)

# Create a collection (table) for our memories. 
# mxbai-embed-large outputs exactly 1024 dimensions.
memory_collection = vx.get_or_create_collection(name="serene_memories", dimension=1024)

# ==========================================
# 2. EMBEDDING FUNCTION (Math Translation)
# ==========================================
def generate_embedding(text: str) -> list[float]:
    """
    Takes raw text and uses local Ollama with `mxbai-embed-large` 
    to convert it into a 1024-dimensional floating point array.
    """
    try:
        response = ollama.embeddings(model="mxbai-embed-large", prompt=text)
        return response["embedding"]
    except Exception as e:
        logging.error(f"Failed to generate embedding. Is Ollama running? Error: {e}")
        return []

# ==========================================
# 3. WRITE TO MEMORY (Phase 2)
# ==========================================
def save_memory(user_id: str, text_chunk: str):
    """
    Embeds a chunk of text and saves it to Supabase pgvector.
    We store the raw text and user_id in the metadata so we can retrieve it later.
    """
    logging.info("Embedding memory...")
    embedding_vector = generate_embedding(text_chunk)
    
    if not embedding_vector:
        return

    # Generate a unique ID for this specific memory chunk
    memory_id = str(uuid.uuid4())
    
    # vecs requires a list of tuples: (id, vector, metadata)
    memory_collection.upsert([
        (memory_id, embedding_vector, {"user_id": user_id, "text": text_chunk})
    ])
    
    # Create an HNSW index for lightning-fast querying in the future
    memory_collection.create_index()
    logging.info(f"Memory saved successfully for user {user_id}.")

# ==========================================
# 4. RETRIEVE PAST MEMORIES (Phase 3)
# ==========================================
def retrieve_past_memories(user_id: str, live_message: str, top_k: int = 3) -> list[str]:
    """
    Takes what the user just typed, embeds it, and mathematically searches
    the database for the top `k` most conceptually similar past messages.
    """
    logging.info("Searching long-term memory...")
    query_vector = generate_embedding(live_message)
    
    if not query_vector:
        return []

    # Query the collection
    results = memory_collection.query(
        data=query_vector,                     # The vector we are searching for
        limit=top_k,                           # How many memories to return
        filters={"user_id": {"$eq": user_id}}, # CRITICAL: Only search THIS user's memories
        include_metadata=True,                 # We need the metadata to get the actual text
        include_value=False                    # We don't need the raw math array returned
    )
    
    # Results come back as a list of tuples: (id, metadata)
    # We just want to extract the text from the metadata dictionary
    past_memories = [record[1]["text"] for record in results]
    
    return past_memories

# ==========================================
# LIVE TEST EXECUTION
# ==========================================
if __name__ == "__main__":
    test_user = "user_prathmesh_99"
    
    print("\n--- 🧠 SERENE MEMORY SYSTEM TEST ---\n")
    
    # 1. Let's save a past memory
    print("Writing a past memory to the database...")
    past_session = "I had a complete breakdown last month during finals week. I couldn't sleep for days and my chest felt tight constantly. I tried doing a 5-minute breathing exercise and it barely helped, but it was something."
    # Uncomment to actually save (requires DB connection):
    # save_memory(test_user, past_session) 
    
    print("\nSimulating a new day. User opens the app.")
    live_input = "I'm feeling really overwhelmed again today, it feels like everything is piling up."
    print(f"🗣️ USER SAYS: '{live_input}'")
    
    # 2. Let's retrieve relevant memories based on the new input
    print("\nSearching database for contextual memories...")
    # Uncomment to actually query (requires DB connection):
    # retrieved = retrieve_past_memories(test_user, live_input)
    # print(f"🔍 RETRIEVED: {retrieved}")