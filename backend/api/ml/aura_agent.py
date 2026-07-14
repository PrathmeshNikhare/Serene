import os
import uuid
import logging
import json
import time
import vecs
import ollama
from huggingface_hub import InferenceClient
from backend.core.config import settings
from fastapi import BackgroundTasks

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Initialize vecs clients lazily to prevent server crashes on import
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

# Initialize Hugging Face InferenceClient for embeddings
hf_token = settings.HUGGINGFACEHUB_API_TOKEN
client = None
if hf_token:
    client = InferenceClient(token=hf_token, timeout=120.0)
else:
    logger.warning("HUGGINGFACEHUB_API_TOKEN is not set. Aura chat will run in fallback mode.")


# ==========================================
# EMBEDDING GENERATOR (Hugging Face)
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
            
        response = client.feature_extraction(text, model="BAAI/bge-base-en-v1.5")
        
        if hasattr(response, "tolist"):
            return response.tolist()
        return list(response)
    except Exception as e:
        logger.warning(f"Failed to generate embedding via Hugging Face API. Error: {e}")
        return []


# ==========================================
# MEMORY SYNTHESIS (DENSE & RICH FACT EXTRACTION)
# ==========================================
def synthesize_memory(chat_log: str) -> str:
    """Uses Phi-4 via Ollama to extract comprehensive, high-density facts to prevent lossy compression."""
    prompt = f"""
    Analyze the following user chat log and extract the core clinical facts.
    Return a dense, bulleted summary capturing:
    - Primary emotional state or mood patterns
    - Specific triggers, topics, or entities mentioned (e.g., family, work, specific events)
    - Key contextual insights or coping steps discussed
    
    Do not use conversational filler. Be highly precise and comprehensive.
    
    CHAT LOG:
    {chat_log}
    """
    try:
        if not client:
            return chat_log
            
        messages = [
            {"role": "system", "content": "You are a clinical memory synthesizer specializing in dense information extraction."},
            {"role": "user", "content": prompt}
        ]
        response = client.chat_completion(
            model="microsoft/phi-4",
            messages=messages,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Failed to synthesize memory via Hugging Face API: {e}")
        return chat_log

def process_and_save_memory(user_id: str, chat_log: str):
    """Synthesizes the chat log into a dense fact structure, then embeds and saves it."""
    synthesized_fact = synthesize_memory(chat_log)
    save_memory(user_id, synthesized_fact)


# ==========================================
# WRITE TO MEMORY
# ==========================================
def save_memory(user_id: str, text_chunk: str):
    """Embeds a chunk of text and saves it to Supabase pgvector."""
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
        memory_id = str(uuid.uuid4())
        collection.upsert([
            (memory_id, embedding_vector, {"user_id": user_id, "text": text_chunk})
        ])
        collection.create_index()
        logger.info(f"Memory saved successfully for user {user_id}.")
    except Exception as e:
        logger.error(f"Failed to write memory to database: {e}")


# ==========================================
# RETRIEVE PAST MEMORIES (ALGORITHMIC MULTI-QUERY RETRIEVAL)
# ==========================================
def generate_query_variations(live_message: str) -> list[str]:
    """Uses Phi-4 via Ollama to generate alternative phrasing variants for a wider semantic search net."""
    prompt = f"""
    Given the following user statement from a mental wellness session, generate exactly 2 alternative ways someone might express the same underlying emotional issue, anxiety, or trigger. 
    Format your output strictly as a JSON list of strings. Do not include any explanation or markdown code blocks.
    
    STATEMENT: "{live_message}"
    """
    variations = [live_message] # Always keep the original query
    try:
        if not client:
            raise Exception("Hugging Face client not initialized.")
            
        response = client.chat_completion(
            model="microsoft/phi-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        cleaned_response = response.choices[0].message.content.strip()
        
        # Strip code blocks if the model ignored instructions
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            if cleaned_response.startswith("json"):
                cleaned_response = cleaned_response.split("\n", 1)[1].strip()

        parsed = json.loads(cleaned_response)
        if isinstance(parsed, list):
            variations.extend([str(item) for item in parsed])
    except Exception as e:
        logger.warning(f"Failed to generate query variations via Hugging Face API, falling back to original query. Error: {e}")
        
    return variations

def retrieve_past_memories(user_id: str, live_message: str, top_k: int = 3) -> list[str]:
    """
    Executes an expanded multi-query vector search using Reciprocal Rank Fusion (RRF)
    to mathematically combine and surface the most relevant memories.
    """
    logger.info(f"Searching long-term memory for user {user_id} via multi-query expansion...")
    
    collection = get_memory_collection()
    if collection is None:
        logger.error("Memory collection is not initialized. Skipping past memory context.")
        return []

    # Step 1: Get query variants from local Ollama
    queries_to_search = generate_query_variations(live_message)
    
    # Dictionary to hold the fusion scores for each memory
    rrf_scores = {}

    # Step 2: Query for each variation and apply RRF math
    for query_text in queries_to_search:
        bge_formatted_query = f"Represent this sentence for searching relevant passages: {query_text}"
        query_vector = generate_embedding(bge_formatted_query)
        
        if not query_vector:
            continue

        try:
            # Pull top 5 for each variation to get a deeper pool of candidates
            results = collection.query(
                data=query_vector,
                limit=5,
                filters={"user_id": {"$eq": user_id}},
                include_metadata=True,
                include_value=False
            )
            
            for rank, record in enumerate(results):
                if record[1] and "text" in record[1]:
                    text_content = record[1]["text"]
                    
                    # RRF Formula: 1 / (rank + k) where k is traditionally 60
                    score = 1.0 / (rank + 1 + 60)
                    
                    if text_content not in rrf_scores:
                        rrf_scores[text_content] = 0.0
                    rrf_scores[text_content] += score
                        
        except Exception as e:
            logger.error(f"Failed query execution iteration: {e}")

    # Step 3: Sort memories by their combined RRF score (highest to lowest)
    ranked_memories = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)
    
    # Step 4: Return just the text of the absolute best top_k matches
    return [memory_text for memory_text, score in ranked_memories][:top_k]


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
    """Queries memories, constructs the system prompt, and infers using local Phi-4."""
    past_memories = retrieve_past_memories(user_id, message, top_k=3)
    background_tasks.add_task(process_and_save_memory, user_id, message)
    
    if past_memories:
        memories_context = "\n".join(f"- {m}" for m in past_memories)
    else:
        memories_context = "No relevant past conversations remembered."
        
    clinical_state_text = json.dumps(phase_2_insights, indent=2) if phase_2_insights else "No recent clinical insights available."
        
    # Format RLHF Rules if provided
    rlhf_text = ""
    if rlhf_rules:
        rlhf_text = f"\n[USER PREFERENCES & BOUNDARIES]\n- The user responds well to: {', '.join(rlhf_rules.get('preferred_interventions', []))}\n- CRITICAL: Do NOT suggest or push: {', '.join(rlhf_rules.get('avoid_interventions', []))}\n"
        
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

    try:
        if not client:
            raise Exception("Hugging Face client not initialized.")
            
        response = client.chat_completion(
            model="microsoft/phi-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling Hugging Face API LLM: {e}")
        return "I'm sorry, I'm having a little trouble thinking right now. Let's take a deep breath together. How else can I support you?"


# ==========================================
# EVALUATION & SEEDING SCRIPT
# ==========================================
def evaluate_rag_accuracy(dataset_path: str):
    """
    Evaluates the vector database retrieval using Hit Rate @ 3 and MRR.
    Runs across the full dataset safely using a dynamic API throttle.
    """
    try:
        with open(dataset_path, 'r') as f:
            dataset = json.load(f)
    except FileNotFoundError:
        logger.error(f"Could not find {dataset_path}")
        return
        
    total_queries = len(dataset)
    hits = 0
    mrr_sum = 0.0
    successful_evals = 0

    print(f"\n--- STARTING THROTTLED FULL RAG EVALUATION ({total_queries} queries) ---")
    print("Guardrails active: 2.5-second pacing delay per API interaction.")

    for i, test_case in enumerate(dataset):
        query = test_case["query"]
        expected_memory = test_case["expected_memory_chunk"]
        
        try:
            # 1. Execute the multi-query expanded retrieval layer
            retrieved_list = retrieve_past_memories(user_id="test_user", live_message=query, top_k=3)
            successful_evals += 1
            
            # 2. Check metrics
            rank = 0
            for index, retrieved_memory in enumerate(retrieved_list):
                if expected_memory in retrieved_memory:
                    rank = index + 1
                    break
            
            if rank > 0:
                hits += 1
                mrr_sum += (1.0 / rank)
                
        except Exception as api_error:
            # If rate-limits a specific window, catch it and keep the script alive
            logger.warning(f"\n[Skipped Query {i+1}] Temporary API hiccup: {api_error}")
            print("Cooling down pipeline for 5 seconds...")
            time.sleep(5.0)
            continue

        # 3. Mandated pacing throttle
        time.sleep(2.5)
            
        # Progress reporter
        if (i + 1) % 5 == 0:
            current_interim_hit_rate = (hits / successful_evals) * 100 if successful_evals > 0 else 0
            print(f"Progress: {i + 1}/{total_queries} processed... Interim Hit Rate: {current_interim_hit_rate:.2f}%")

    # Final Math Check based on valid processed iterations
    if successful_evals == 0:
        print("\n Evaluation failed: No queries were successfully processed by the API.")
        return

    hit_rate = (hits / successful_evals) * 100
    mrr = (mrr_sum / successful_evals)

    print("\n==========================================")
    print("FINAL FULL-DATASET RAG EVALUATION SCORES")
    print("==========================================")
    print(f"Total Dataset Queries: {total_queries}")
    print(f"Successfully Evaluated: {successful_evals}/{total_queries}")
    print(f"Hit Rate @ 3:           {hit_rate:.2f}% (Target: > 85%)")
    print(f"MRR:                    {mrr:.4f}  (Target: > 0.7500)")
    print("==========================================")

def seed_database(dataset_path: str, user_id: str):
    """Seeds the database using the updated Phi-4 dense extraction logic."""
    print("STARTING DATABASE SEEDING")
    try:
        with open(dataset_path, 'r') as f:
            dataset = json.load(f)
    except FileNotFoundError:
        logging.error(f"Could not find {dataset_path}")
        return

    total_memories = len(dataset)
    for i, test_case in enumerate(dataset):
        memory_to_save = test_case["expected_memory_chunk"]
        save_memory(user_id=user_id, text_chunk=memory_to_save)
        if (i + 1) % 10 == 0:
            print(f"Uploaded {i + 1}/{total_memories} memories...")
    print("SEEDING COMPLETE.")

if __name__ == "__main__":
    # IMPORTANT STEP BEFORE RUNNING EVALUATOR:
    # 1. Un-comment the line below to completely clean and refresh your vector DB state
    #seed_database("memory_retrieval_dataset.json", user_id="test_user")
    
    # 2. Run the evaluator
    evaluate_rag_accuracy("memory_retrieval_dataset.json")