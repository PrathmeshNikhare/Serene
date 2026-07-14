import os
import uuid
import logging
import json
import time
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
        _collection = _vx.get_or_create_collection(name="serene_memories_v2", dimension=768)
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
    Takes raw text and uses Hugging Face Inference API with `BAAI/bge-base-en-v1.5` 
    to convert it into a 768-dimensional floating point array.
    """
    try:
        if not client:
            logger.error("Hugging Face client not initialized. Cannot generate embeddings.")
            return []
            
        # Call HF feature extraction (returns a numpy array)
        response = client.feature_extraction(text, model="BAAI/bge-base-en-v1.5")
        
        # Convert numpy array to list if needed
        if hasattr(response, "tolist"):
            return response.tolist()
        return list(response)
    except Exception as e:
        logger.warning(f"Failed to generate embedding via Hugging Face API. Error: {e}")
        return []

# ==========================================
# MEMORY SYNTHESIS & TRANSFORMATION
# ==========================================
def transform_query_for_search(live_message: str) -> str:
    """Uses LLM to translate a raw user message into a clinical concept for better matching."""
    prompt = f"""
    You are a clinical psychologist. Translate the user's raw message into a concise, 
    third-person clinical observation or psychological state, similar to a case note.
    Do not include advice, pleasantries, or filler.
    
    USER MESSAGE: "{live_message}"
    """
    try:
        if not client:
            return live_message
            
        messages = [
            {"role": "system", "content": "You are a precise clinical analyzer."},
            {"role": "user", "content": prompt}
        ]
        response = client.chat_completion(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            messages=messages,
            max_tokens=50,
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Query transformation failed: {e}")
        return live_message

def synthesize_memory(chat_log: str) -> str:
    """Uses a lightweight HF LLM to summarize the session into a concise clinical fact."""
    prompt = f"""
    Analyze the following user chat log and extract the core clinical fact or state.
    Format your response as a single, concise sentence.
    Do not include any conversational filler.
    
    CHAT LOG:
    {chat_log}
    """
    try:
        if not client:
            return chat_log
            
        messages = [
            {"role": "system", "content": "You are a clinical memory synthesizer."},
            {"role": "user", "content": prompt}
        ]
        response = client.chat_completion(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            messages=messages,
            max_tokens=50,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Failed to synthesize memory via Hugging Face API: {e}")
        return chat_log # Fallback to raw text

def process_and_save_memory(user_id: str, chat_log: str):
    """Synthesizes the chat log into a fact, then embeds and saves it."""
    synthesized_fact = synthesize_memory(chat_log)
    save_memory(user_id, synthesized_fact)

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
    Translates user message, embeds it, and mathematically searches the database
    for the top `k` most conceptually similar past messages.
    """
    logger.info(f"Searching long-term memory for user {user_id}...")
    
    # 1. Transform raw query to clinical query
    search_query = transform_query_for_search(live_message)
    logger.info(f"Transformed Query for Search: '{search_query}'")
    
    # 2. THE FIX: Apply BGE prefix to the TRANSFORMED query, not the raw message
    bge_formatted_query = f"Represent this sentence for searching relevant passages: {search_query}"
    
    # 3. Embed and search
    query_vector = generate_embedding(bge_formatted_query)
    
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
    phase_2_insights: dict = None,
    rlhf_rules: dict = None
) -> str:
    """
    Queries historical memories, builds context-aware system prompt, 
    requests an LLM response, and schedules a background memory-save.
    """
    import json
    
    # 1. Retrieve past memories context (RAG)
    past_memories = retrieve_past_memories(user_id, message, top_k=3)
    
    # 2. Queue the current message to be synthesized and saved as memory asynchronously
    background_tasks.add_task(process_and_save_memory, user_id, message)
    
    # 3. Format memories context
    if past_memories:
        memories_context = "\n".join(f"- {m}" for m in past_memories)
    else:
        memories_context = "No relevant past conversations remembered."
        
    clinical_state_text = json.dumps(phase_2_insights, indent=2) if phase_2_insights else "No recent clinical insights available."
    
    # Format RLHF Rules if provided
    rlhf_text = ""
    if rlhf_rules:
        rlhf_text = f"""
[USER PREFERENCES & BOUNDARIES]
- The user responds well to: {', '.join(rlhf_rules.get('preferred_interventions', []))}
- CRITICAL: Do NOT suggest or push: {', '.join(rlhf_rules.get('avoid_interventions', []))}
"""
        
    system_prompt = f"""You are Aura, an empathetic, caring, and professional mental wellness companion on the Serene platform.
Your primary objective is to listen, support, and help the user reflect on their stress and emotions.
You are NOT a medical doctor or a clinical psychologist. Never diagnose the user, prescribe medication, or offer clinical treatment plans. Instead, focus on mindfulness, breathing exercises, cognitive reframing, and actionable self-care micro-steps.

User Demographics and Persona:
- Age: {user_age}
- Gender: {user_gender}
- Persona: {user_persona}

[CURRENT CLINICAL STATE]
{clinical_state_text}
{rlhf_text}
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

def evaluate_rag_accuracy(dataset_path: str):
    """
    Evaluates the vector database retrieval using Hit Rate @ 3 and MRR.
    """
    # 1. Load the Golden Dataset
    try:
        with open(dataset_path, 'r') as f:
            dataset = json.load(f)
    except FileNotFoundError:
        logging.error(f"Could not find {dataset_path}")
        return
        
    total_queries = len(dataset)
    hits = 0
    mrr_sum = 0.0

    print(f"--- 🧪 STARTING RAG EVALUATION ({total_queries} queries) ---")

    # 2. Iterate through the Golden Dataset
    for i, test_case in enumerate(dataset):
        query = test_case["query"]
        expected_memory = test_case["expected_memory_chunk"]
        
        # ADDED DELAY: Prevent hitting HF free tier API rate limits (HTTP 429)
        time.sleep(2.0)
        
        # 3. Call your Vector DB
        retrieved_list = retrieve_past_memories(user_id="test_user", live_message=query, top_k=3)

        # 4. Calculate Metrics on the List of 3
        rank = 0
        for index, retrieved_memory in enumerate(retrieved_list):
            if expected_memory in retrieved_memory:
                rank = index + 1 # 1-based indexing (1st, 2nd, 3rd)
                break
        
        if rank > 0:
            hits += 1
            mrr_sum += (1.0 / rank) # 1/1 = 1.0, 1/2 = 0.5, 1/3 = 0.33
            
        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1}/{total_queries} queries...")

    # 5. Final Math
    hit_rate = (hits / total_queries) * 100
    mrr = (mrr_sum / total_queries)

    print("\n==========================================")
    print("FINAL RAG EVALUATION SCORES")
    print("==========================================")
    print(f"Total Test Cases: {total_queries}")
    print(f"Hit Rate @ 3:     {hit_rate:.2f}% (Target: > 85%)")
    print(f"MRR:              {mrr:.4f}  (Target: > 0.7500)")
    print("==========================================")
    
    if mrr < 0.75:
        print("Tip: MRR is low. Consider increasing chunk overlap or using a stronger embedding model.")

def seed_database(dataset_path: str, user_id: str):
    """
    Reads the Golden Dataset and uploads ONLY the expected memories 
    into the Vector Database so we have a corpus to search against.
    """
    print("STARTING DATABASE SEEDING")
    print(f"Target User: {user_id}")
    
    # 1. Load the dataset
    try:
        with open(dataset_path, 'r') as f:
            dataset = json.load(f)
    except FileNotFoundError:
        logging.error(f"Could not find {dataset_path}")
        return

    # 2. Iterate and upload the memories
    total_memories = len(dataset)
    for i, test_case in enumerate(dataset):
        memory_to_save = test_case["expected_memory_chunk"]
        
        # ADDED DELAY: Prevent hitting HF rate limits during seeding
        time.sleep(1.0)
        
        # Call the function from Component 3 to embed and save to Supabase
        save_memory(user_id=user_id, text_chunk=memory_to_save)
        
        if (i + 1) % 10 == 0:
            print(f"Uploaded {i + 1}/{total_memories} memories...")

    print("SEEDING COMPLETE. The database is now ready for the RAG Evaluator!")
    
    # Optional: Add some "noise" (random irrelevant memories) to make the test harder
    noise_memories = [
        "User likes to eat pizza on Fridays.",
        "User watched a documentary about penguins last night.",
        "User needs to buy milk and eggs from the grocery store."
    ]
    print("\nAdding some random noise to test the AI's precision...")
    for noise in noise_memories:
        time.sleep(1.0)
        save_memory(user_id=user_id, text_chunk=noise)
        
    print("Noise added. You can now run rag_evaluator.py!")

if __name__ == "__main__":
    # We use "test_user" because that is the user ID the rag_evaluator is set to query
    
    # Step 1: Uncomment this once if your database is empty to seed it
    # seed_database("memory_retrieval_dataset.json", user_id="test_user")
    
    # Step 2: Run the evaluator
    evaluate_rag_accuracy("memory_retrieval_dataset.json")