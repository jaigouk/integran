import os
import json
import time
import sys
import re
import hashlib
from datetime import datetime
from tqdm import tqdm

# --- CORRECTED IMPORTS for Vertex AI ---
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, Part

from comfy_api_simplified import ComfyApiWrapper, ComfyWorkflowWrapper
from PIL import Image
import io

# --- Main Configuration ---
# V V V - TUNE YOUR SETTINGS HERE - V V V

# -- Style Configuration: The heart of your "single designer" look --
STYLE_GUIDE = {
    "ARTIST_SIGNATURE": "Studio Mnemonic style",
    "TRIGGER_WORD": "book page", # LoRA trigger word
    "STYLE_KEYWORDS": "charming characters, clean lines, vibrant but harmonious colors, detailed textures, whimsical atmosphere, professional illustration, high quality artwork",
    "NEGATIVE_PROMPT": (
        "photorealistic, ugly, tiling, poorly drawn hands, poorly drawn feet, poorly drawn face, "
        "out of frame, extra limbs, disfigured, deformed, body out of frame, bad anatomy, "
        "watermark, signature, cut off, low contrast, underexposed, overexposed, bad art, "
        "beginner, amateur, distorted face, cluttered, scary, dark, boring, text errors, mutated"
    )
}

# -- ComfyUI & Model Configuration --
COMFYUI_CONFIG = {
    "SERVER_ADDRESS": "127.0.0.1:8188", # Your server address
    # --- IMPORTANT: Match these node titles to your workflow_api.json file ---
    "NODE_CHECKPOINT_LOADER": "CheckpointLoader",
    "NODE_LORA_LOADER": "LoraLoader",
    "NODE_POSITIVE_PROMPT": "PositivePrompt",
    "NODE_NEGATIVE_PROMPT": "NegativePrompt",
    "NODE_KSAMPLER": "KSampler",
    "NODE_EMPTY_LATENT": "EmptyLatentImage",
    "NODE_IMAGE_OUTPUT": "ImageOutput"
}
CHECKPOINT_MODEL_NAME = "sd_xl_base_1.0.safetensors"
LORA_MODEL_NAME = "children_book2.safetensors"
LORA_STRENGTH = 0.75 # Tuned for a stronger artistic style

# -- Gemini API Configuration --
GEMINI_MODEL_ID = "gemini-1.5-pro-001" # Use a specific model version for Vertex
GEMINI_CACHE_FILE = "gemini_childrens_book_cache.json"
RATE_LIMIT_DELAY = 2.0  # Seconds between Gemini API calls
MAX_RETRIES = 3

# -- File & Path Configuration --
DATASET_PATH = "data/final_dataset.json"
WORKFLOW_API_PATH = "workflow_api_childrens_book.json"
OUTPUT_DIRECTORY = "output_images_childrens_book"
BATCH_SAVE_INTERVAL = 5

# -- Image Optimization Configuration --
TARGET_FILE_SIZE_KB = 150
JPEG_QUALITY_START = 90 # Start higher for better quality
JPEG_QUALITY_MIN = 75

# ^ ^ ^ - END OF CONFIGURATION - ^ ^ ^


# --- CORRECTED Gemini Client Initialization for Vertex AI ---
try:
    project_id = os.environ.get("GCP_PROJECT_ID")
    location = os.environ.get("GCP_REGION", "europe-west3") # Default location

    if not project_id:
        raise ValueError("GCP_PROJECT_ID environment variable is not set.")

    vertexai.init(project=project_id, location=location)
    
    GEMINI_MODEL = GenerativeModel(GEMINI_MODEL_ID)
    
    print(f"✅ Vertex AI initialized for project '{project_id}' in '{location}'.")

except Exception as e:
    print(f"❌ Critical Error: Could not initialize Vertex AI.")
    print(f"   Ensure 'gcloud auth application-default login' is run and the 'google-cloud-aiplatform' library is installed.")
    print(f"   Error details: {e}")
    sys.exit(1)


def get_deterministic_seed(seed_string: str) -> int:
    """
    Generates a deterministic, consistent integer seed from a string (like a question_id).
    This ensures that running the script again for the same question yields the *exact* same image.
    """
    hash_bytes = hashlib.sha256(seed_string.encode('utf-8')).digest()
    seed = int.from_bytes(hash_bytes[:8], 'little', signed=False)
    return seed


def load_gemini_cache() -> dict:
    """Load Gemini API response cache from file."""
    if os.path.exists(GEMINI_CACHE_FILE):
        try:
            with open(GEMINI_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  - Warning: Could not load cache file: {e}. Starting with an empty cache.")
    return {}


def save_gemini_cache(cache: dict) -> None:
    """Save Gemini API response cache to file."""
    try:
        with open(GEMINI_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"  - Error saving cache: {e}")


def is_question_processed(question_id: str, cache: dict) -> bool:
    """Check if a question has already been successfully processed."""
    entry = cache.get(question_id)
    return entry and entry.get('status') == 'success' and entry.get('data', {}).get('image_generated', False)


def add_to_cache(cache: dict, question_id: str, data: dict, status: str = 'success') -> None:
    """Add a response to the cache with a timestamp."""
    cache[question_id] = {'status': status, 'data': data, 'timestamp': datetime.now().isoformat()}

def generate_childrens_book_prompt(question_data: dict, cache: dict, question_id: str) -> dict | None:
    if cache.get(question_id, {}).get('status') == 'success':
        cached_prompt_data = cache[question_id].get('data', {}).get('prompt_data')
        if cached_prompt_data:
            print(f"  - Using cached Gemini response for question {question_id}")
            return cached_prompt_data

    question = question_data.get("question", "")
    correct_answer = question_data.get("correct", "")
    existing_mnemonic = question_data.get("mnemonic", {}).get("en", "")
    explanation_en = question_data.get("explanations", {}).get("en", "")
    is_image_question = question_data.get("is_image_question", False)

    if not existing_mnemonic:
        existing_mnemonic = f"A visual way to remember the answer: {correct_answer}"

    if is_image_question:
        correct_answer_letter = question_data.get("correct_answer_letter", "")
        image_descriptions = question_data.get("image_descriptions", [])
        correct_image_description = ""
        if correct_answer_letter and image_descriptions:
            try:
                correct_index = ord(correct_answer_letter.upper()) - ord('A')
                if 0 <= correct_index < len(image_descriptions):
                    correct_image_description = image_descriptions[correct_index]
            except (ValueError, TypeError): pass

        question_type_info = f"""
- **Task Type**: This is an IMAGE IDENTIFICATION question. The illustration must teach the user how to IDENTIFY the correct image based on the mnemonic.
- **Correct Image Description**: "{correct_image_description}"
"""
    else:
        question_type_info = f"""
- **Task Type**: This is a TEXT-BASED question. The illustration must help the user REMEMBER the correct text answer via the mnemonic.
- **Correct Answer**: "{correct_answer}"
"""
    meta_prompt = f"""
You are an expert prompt engineer for the "children_book2.safetensors" LoRA model on SDXL.
Your task is to create a JSON object with prompts to generate a high-quality, mnemonic illustration.
**DESIGNER STYLE GUIDE (FOR CONSISTENCY):**
Your PRIMARY GOAL is to ensure all images look like they were made by ONE talented designer.
- **Artist Signature**: The desired style is "{STYLE_GUIDE['ARTIST_SIGNATURE']}". It is whimsical, artistic, and professional.
- **Core Style Keywords**: "{STYLE_GUIDE['STYLE_KEYWORDS']}".
- **Composition**: Focus on a clear, central mnemonic symbol. The background should be supportive but not distracting.
**INPUT DATA:**
- **Mnemonic to Visualize**: "{existing_mnemonic}"
- **Original Question**: "{question}"
- **Explanation**: "{explanation_en[:250]}..."
{question_type_info}
**LoRA & PROMPT BEST PRACTICES:**
1.  **Trigger Word**: The positive prompt MUST start with "{STYLE_GUIDE['TRIGGER_WORD']}".
2.  **Mnemonic Emphasis**: Key mnemonic symbols should be weighted like `(symbol:1.3)` for focus. Avoid over-weighting.
3.  **German Text Integration**: To render German text (like in the mnemonic), describe it as a physical object.
    - Example: "...with the German word 'Wahl' written on a wooden sign in clear, bold letters."
    - Use phrases like "clear text label", "high-contrast text", "bold sans-serif font", "billboard-style lettering".
4.  **Composition**: Create a simple, uncluttered scene a child can easily understand. The mnemonic must be the hero of the image.
**OUTPUT FORMAT (Strictly JSON):**
Generate ONLY a valid JSON object based on the following template. Do not add any text before or after the JSON block.
{{
  "positive_prompt": "book page, [A detailed description of the scene that visualizes the mnemonic, incorporating the '{STYLE_GUIDE['ARTIST_SIGNATURE']}' and using keywords like '{STYLE_GUIDE['STYLE_KEYWORDS']}']. The scene should clearly feature elements from the mnemonic '{existing_mnemonic}'.",
  "negative_prompt": "{STYLE_GUIDE['NEGATIVE_PROMPT']}",
  "story_connection": "[Explain in one sentence how the generated artistic scene creates an unforgettable connection to the mnemonic.]"
}}
"""
    retries = 0
    while retries < MAX_RETRIES:
        try:
            time.sleep(RATE_LIMIT_DELAY)
            
            # --- CORRECTED API Call for Vertex AI SDK ---
            config = GenerationConfig(
                temperature=0.8,
                max_output_tokens=768,
                response_mime_type="application/json",
            )
            response = GEMINI_MODEL.generate_content(
                [meta_prompt],
                generation_config=config,
            )
            response_text = response.text.strip()
            parsed_response = json.loads(response_text)

            if all(field in parsed_response for field in ['positive_prompt', 'negative_prompt']):
                add_to_cache(cache, question_id, {'prompt_data': parsed_response})
                print(f"  - Cached new Gemini response for question {question_id}")
                return parsed_response
            else:
                raise ValueError("Response missing required fields.")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"  - ⚠️ Gemini response parsing failed (Attempt {retries + 1}/{MAX_RETRIES}): {e}")
            retries += 1
            time.sleep(RATE_LIMIT_DELAY * 2)
        except Exception as e:
            print(f"  - ❌ Error calling Vertex AI API (Attempt {retries + 1}/{MAX_RETRIES}): {e}")
            retries += 1
            time.sleep(RATE_LIMIT_DELAY * 2)

    print(f"  - ❌ Failed to get a valid response from Gemini for {question_id} after {MAX_RETRIES} attempts.")
    add_to_cache(cache, question_id, {'error': 'Failed to generate prompt'}, status='error')
    return None

def optimize_image_size(image_path: str, target_size_kb: int = TARGET_FILE_SIZE_KB) -> bool:
    try:
        with Image.open(image_path) as img:
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P': img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            quality = JPEG_QUALITY_START
            while quality >= JPEG_QUALITY_MIN:
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=quality, optimize=True, progressive=True)
                size_kb = len(buffer.getvalue()) / 1024
                if size_kb <= target_size_kb:
                    new_path = os.path.splitext(image_path)[0] + '.jpg'
                    with open(new_path, 'wb') as f:
                        f.write(buffer.getvalue())
                    if new_path != image_path:
                        os.remove(image_path)
                    print(f"    - Optimized to {size_kb:.1f}KB at {quality}% quality -> {os.path.basename(new_path)}")
                    return True
                quality -= 5
            return False
    except Exception as e:
        print(f"    - Error optimizing image: {e}")
        return False

def generate_image_with_comfyui(prompt_data: dict, question_id: str, question_data: dict, api: ComfyApiWrapper, wf: ComfyWorkflowWrapper):
    print(f"  - Setting up ComfyUI workflow for question {question_id}...")
    try:
        cfg = COMFYUI_CONFIG
        wf.set_node_param(cfg["NODE_CHECKPOINT_LOADER"], "ckpt_name", CHECKPOINT_MODEL_NAME)
        wf.set_node_param(cfg["NODE_LORA_LOADER"], "lora_name", LORA_MODEL_NAME)
        # ... (rest of the function is unchanged)
        wf.set_node_param(cfg["NODE_LORA_LOADER"], "strength_model", LORA_STRENGTH)
        wf.set_node_param(cfg["NODE_LORA_LOADER"], "strength_clip", LORA_STRENGTH)
        wf.set_node_param(cfg["NODE_POSITIVE_PROMPT"], "text", prompt_data["positive_prompt"])
        wf.set_node_param(cfg["NODE_NEGATIVE_PROMPT"], "text", prompt_data["negative_prompt"])
        actual_id = question_data.get('id', question_id)
        wf.set_node_param(cfg["NODE_IMAGE_OUTPUT"], "filename_prefix", f"story_q{actual_id}_mnemonic")
        wf.set_node_param(cfg["NODE_EMPTY_LATENT"], "width", 768)
        wf.set_node_param(cfg["NODE_EMPTY_LATENT"], "height", 768)
        wf.set_node_param(cfg["NODE_EMPTY_LATENT"], "batch_size", 1)
        seed_value = get_deterministic_seed(question_id)
        wf.set_node_param(cfg["NODE_KSAMPLER"], "seed", seed_value)
        print(f"  - Using deterministic seed {seed_value} for consistency.")
        print(f"  - Story Connection: {prompt_data.get('story_connection', 'N/A')}")
        print(f"  - Positive Prompt: {prompt_data['positive_prompt'][:150]}...")
        print(f"  - Queueing illustration for question {question_id}...")
        results = api.queue_and_wait_images(wf, cfg["NODE_IMAGE_OUTPUT"])
        if not results:
            print(f"  - ❌ No images returned from ComfyUI for question {question_id}")
            return False
        for filename, image_data in results.items():
            output_path = os.path.join(OUTPUT_DIRECTORY, filename)
            with open(output_path, "wb") as f:
                f.write(image_data)
            print(f"  - Image saved: {output_path} ({len(image_data)/1024:.1f}KB)")
            optimize_image_size(output_path, TARGET_FILE_SIZE_KB)
        return True
    except Exception as e:
        print(f"  - ❌ Error in ComfyUI generation for question {question_id}: {e}")
        import traceback
        print(f"  - Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main function to generate consistent, high-quality mnemonic images."""
    num_questions_arg = sys.argv[1] if len(sys.argv) > 1 else None
    print(f"🎨 Starting HIGH-QUALITY mnemonic generation with '{STYLE_GUIDE['ARTIST_SIGNATURE']}' style...")
    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
    gemini_cache = load_gemini_cache()
    try:
        api = ComfyApiWrapper(f"http://{COMFYUI_CONFIG['SERVER_ADDRESS']}")
        wf = ComfyWorkflowWrapper(WORKFLOW_API_PATH)
        print("✅ ComfyUI API and workflow initialized successfully.")
    except Exception as e:
        print(f"❌ Critical Error: Could not connect to ComfyUI or load workflow.")
        print(f"   Please check your server address and that '{WORKFLOW_API_PATH}' is correct.")
        print(f"   Error details: {e}")
        return
    try:
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            dataset = json.load(f)
        questions = dataset.get("questions", {})
        if not questions:
            print("❌ Error: No questions found in the dataset.")
            return
        print(f"✅ Dataset loaded with {len(questions)} questions from {DATASET_PATH}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Critical Error: Could not load or parse dataset at '{DATASET_PATH}'.")
        print(f"   Error details: {e}")
        return
    questions_to_process = list(questions.items())
    if num_questions_arg:
        try:
            num_to_process = int(num_questions_arg)
            questions_to_process = questions_to_process[:num_to_process]
            print(f"🎯 Processing the first {len(questions_to_process)} questions as requested.")
        except ValueError:
            print(f"⚠️ Warning: Invalid number '{num_questions_arg}'. Processing all questions.")
    unprocessed_items = [
        (qid, qdata) for qid, qdata in questions_to_process
        if not is_question_processed(qid, gemini_cache)
    ]
    if not unprocessed_items:
        print("\n🎉 All requested questions have already been processed! Check the output directory.")
        return
    print(f"📊 Found {len(unprocessed_items)} new/unprocessed questions to generate.")
    successful_generations = 0
    failed_generations = 0
    try:
        with tqdm(unprocessed_items, desc=f"Generating in '{STYLE_GUIDE['ARTIST_SIGNATURE']}' style") as pbar:
            for question_id, question_data in pbar:
                pbar.set_postfix_str(f"ID: {question_id}", refresh=True)
                print(f"\n\n📖 Processing Question ID: {question_id}")
                print(f"   Mnemonic: {question_data.get('mnemonic', {}).get('en', 'N/A')}")
                prompt_data = generate_childrens_book_prompt(question_data, gemini_cache, question_id)
                if not prompt_data:
                    print(f"❌ Skipping {question_id} due to prompt generation error.")
                    failed_generations += 1
                    continue
                if generate_image_with_comfyui(prompt_data, question_id, question_data, api, wf):
                    successful_generations += 1
                    add_to_cache(gemini_cache, question_id, {'prompt_data': prompt_data, 'image_generated': True})
                else:
                    failed_generations += 1
                if successful_generations > 0 and successful_generations % BATCH_SAVE_INTERVAL == 0:
                    save_gemini_cache(gemini_cache)
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user.")
    finally:
        print("\n💾 Performing final cache save...")
        save_gemini_cache(gemini_cache)
        print("\n" + "="*50)
        print("✨ GENERATION SUMMARY ✨")
        print("="*50)
        print(f"✅ Successful generations: {successful_generations}")
        print(f"❌ Failed generations: {failed_generations}")
        print(f"🎨 Style: '{STYLE_GUIDE['ARTIST_SIGNATURE']}'")
        print(f"📂 Images saved in: '{OUTPUT_DIRECTORY}'")
        print("\n🎉 Process complete!")

if __name__ == "__main__":
    main()