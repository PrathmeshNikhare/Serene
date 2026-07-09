import os
import uuid
import logging
import vecs
from huggingface_hub import InferenceClient
from backend.core.config import settings
from fastapi import BackgroundTasks

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Initialize vecs clients lazily to prevent server crashes on import when config is being loaded
_vx = None
_collection = None

def get_memory_collection():
    global _vx, _collection
    if _collection is not None:
        return _collection
    
    db_url = settings.DATABASE_URL
    if not db_url:
        logger.error("DATABASE_URL is not set in backend settings configuration.")
        return None
    
    try:
        logger.info("Initializing vecs client for Supabase PostgreSQL...")
        _vx = vecs.create_client(db_url)
        _collection = _vx.get_or_create_collection(name="serene_memories", dimension=1024)
        return _collection
    except Exception as e:
        logger.error(f"Failed to connect to pgvector database via vecs client: {e}")
        return None

# Initialize Hugging Face InferenceClient
hf_token = settings.HUGGINGFACEHUB_API_TOKEN
client = None
if hf_token:
    client = InferenceClient(
        model="meta-llama/Meta-Llama-3-8B-Instruct",
        token=hf_token,
        timeout=120.0
    )
else:
    logger.warning("HUGGINGFACEHUB_API_TOKEN is not set. Aura chat will run in fallback mode.")

# ==========================================
# EMBEDDING GENERATOR
# ==========================================
def generate_embedding(text: str) -> list[float]:
    """
    Takes raw text and uses Hugging Face Inference API with `mxbai-embed-large-v1` 
    to convert it into a 1024-dimensional floating point array.
    """
    try:
        if not client:
            logger.warning("Hugging Face Client not initialized. Cannot generate embedding.")
            return []
            
        response = client.feature_extraction(text, model="mixedbread-ai/mxbai-embed-large-v1")
        
        # Convert numpy array to list if needed
        if hasattr(response, "tolist"):
            return response.tolist()
        return list(response)
    except Exception as e:
        logger.warning(f"Failed to generate embedding via Hugging Face API. Error: {e}")
        return []

# ==========================================
# WRITE TO MEMORY
# ==========================================
def save_memory(user_id: str, text_chunk: str):
    """
    Embeds a chunk of text and saves it to Supabase pgvector.
    Stores raw text and user_id in the metadata so we can retrieve it later.
    """
    logger.info(f"Embedding and saving memory for user {user_id}...")
    embedding_vector = generate_embedding(text_chunk)
    
    if not embedding_vector:
        logger.warning("Skipping memory save: could not generate embedding.")
        return

    collection = get_memory_collection()
    if collection is None:
        logger.error("Skipping memory save: memory collection not available.")
        return

    try:
        # Generate a unique ID for this specific memory chunk
        memory_id = str(uuid.uuid4())
        
        # vecs requires a list of tuples: (id, vector, metadata)
        collection.upsert([
            (memory_id, embedding_vector, {"user_id": user_id, "text": text_chunk})
        ])
        
        # Create an HNSW index for fast querying in the future
        collection.create_index()
        logger.info(f"Memory saved successfully for user {user_id}.")
    except Exception as e:
        logger.error(f"Failed to write memory to database: {e}")

# ==========================================
# RETRIEVE PAST MEMORIES
# ==========================================
def retrieve_past_memories(user_id: str, live_message: str, top_k: int = 3) -> list[str]:
    """
    Embeds user message and mathematically searches the database
    for the top `k` most conceptually similar past messages.
    """
    logger.info(f"Searching long-term memory for user {user_id}...")
    query_vector = generate_embedding(live_message)
    
    if not query_vector:
        logger.warning("Could not generate query embedding. Skipping past memory context.")
        return []

    collection = get_memory_collection()
    if collection is None:
        logger.error("Memory collection is not initialized. Skipping past memory context.")
        return []

    try:
        # Query the collection
        results = collection.query(
            data=query_vector,                     # The vector we are searching for
            limit=top_k,                           # How many memories to return
            filters={"user_id": {"$eq": user_id}}, # CRITICAL: Only search THIS user's memories
            include_metadata=True,                 # We need the metadata to get the actual text
            include_value=False                    # We don't need the raw math array returned
        )
        
        past_memories = [record[1]["text"] for record in results if record[1] and "text" in record[1]]
        logger.info(f"Retrieved {len(past_memories)} contextual memories.")
        return past_memories
    except Exception as e:
        logger.error(f"Failed to retrieve memories from pgvector: {e}")
        return []

# ==========================================
# CHATBOT INFERENCE & ORCHESTRATION
# ==========================================
def get_aura_response(
    user_id: str,
    user_persona: str,
    user_age: int,
    user_gender: str,
    message: str,
    background_tasks: BackgroundTasks,
    phase_2_insights: dict = None
) -> str:
    """
    Queries historical memories, builds context-aware system prompt, 
    requests an LLM response, and schedules a background memory-save.
    """
    import json
    
    # 1. Retrieve past memories context (RAG)
    past_memories = retrieve_past_memories(user_id, message, top_k=3)
    
    # 2. Queue the current message to be saved as memory asynchronously
    background_tasks.add_task(save_memory, user_id, message)
    
    # 3. Format memories context
    if past_memories:
        memories_context = "\n".join(f"- {m}" for m in past_memories)
    else:
        memories_context = "No relevant past conversations remembered."
        
    clinical_state_text = json.dumps(phase_2_insights, indent=2) if phase_2_insights else "No recent clinical insights available."
        
    system_prompt = f"""You are Aura, an empathetic, caring, and professional mental wellness companion on the Serene platform.
Your primary objective is to listen, support, and help the user reflect on their stress and emotions.
You are NOT a medical doctor or a clinical psychologist. Never diagnose the user, prescribe medication, or offer clinical treatment plans. Instead, focus on mindfulness, breathing exercises, cognitive reframing, and actionable self-care micro-steps.

User Demographics and Persona:
- Age: {user_age}
- Gender: {user_gender}
- Persona: {user_persona}

[CURRENT CLINICAL STATE]
{clinical_state_text}

[USER'S PAST MEMORIES]
{memories_context}

[INSTRUCTIONS]
Respond to the user with deep empathy. Use the clinical state to inform your context, 
and reference past memories if relevant. Acknowledge their past context naturally in your response if it is relevant. Respond in a warm, comforting, and personalized tone appropriate for their persona. Keep your responses concise (2-4 paragraphs) to keep the chat conversational. Do not sound like a robot listing data.
"""

    # 4. Generate response via Hugging Face Client
    try:
        if client:
            response = client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=500,
                temperature=0.7
            )
            return response.choices[0].message.content
        else:
            logger.warning("Hugging Face Client not initialized. Returning generic response.")
            return "I hear you, and I want to support you. It seems my AI connection is currently offline, but please remember to take deep breaths and speak kindly to yourself today."
    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
        return "I'm sorry, I'm having a little trouble thinking right now. Let's take a deep breath together. How else can I support you?"
