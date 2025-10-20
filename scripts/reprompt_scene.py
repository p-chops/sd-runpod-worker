import csv
import os
import argparse
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables (e.g., OpenAI API key)
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY in .env or environment.")

# Initialize single client instance
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_single_prompt(scene_name, frame_number):
    """
    Generate a specific, scholarly, and visually evocative prompt for a single scene using OpenAI's Responses API.

    Args:
        scene_name (str): The name of the scene.
        frame_number (int): The frame number associated with the scene.

    Returns:
        str: The generated prompt.
    """
    instruction = (
        f"Generate a concise, specific, and visually evocative art prompt for an img2img model being applied to a single scene. "
        "Reference concrete artistic styles, name real artists, avoiding the obvious ones, "
        "include historical periods or genres, and make the image visually striking or with fantasy/surreal elements. "
        "Keep the prompt brief (less than one sentence) but vivid and distinct."
    )

    try:
        resp = client.responses.create(
            model="gpt-4o",
            input=instruction,
            max_output_tokens=120,
        )
    except Exception as e:
        raise RuntimeError(f"OpenAI request failed: {e}")

    text = getattr(resp, "output_text", None)
    if not text:
        raise RuntimeError("OpenAI returned an empty response for the prompt generation.")

    return text.strip()

def update_scene_prompt(scenes_csv, scene_name):
    """
    Update the prompt for a specific scene in the scenes CSV file.

    Args:
        scenes_csv (str): Path to the scenes CSV file.
        scene_name (str): The name of the scene to update.
    """
    print(f"Updating prompt for scene '{scene_name}' in {scenes_csv}...")

    # Read the scenes CSV
    with open(scenes_csv, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        rows = list(reader)

    # Find the scene and update its prompt
    scene_found = False
    for row in rows:
        if row['name'] == scene_name:
            scene_found = True
            start_frame = int(row['frame'])
            print(f"Found scene '{scene_name}' at frame {start_frame}. Generating new prompt...")
            new_prompt = generate_single_prompt(scene_name, start_frame)
            row['prompt'] = new_prompt
            print(f"New prompt generated: {new_prompt}")
            break

    if not scene_found:
        print(f"Error: Scene '{scene_name}' not found in {scenes_csv}.")
        return

    # Write the updated CSV back
    print(f"Writing updated scenes CSV: {scenes_csv}")
    with open(scenes_csv, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=['name', 'frame', 'prompt'])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated scene '{scene_name}' in {scenes_csv}. Process complete.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Update the prompt for a specific scene in the scenes CSV file.")
    parser.add_argument('scenes_csv', help="Path to the scenes CSV file.")
    parser.add_argument('scene_name', help="Name of the scene to update.")
    args = parser.parse_args()

    try:
        update_scene_prompt(args.scenes_csv, args.scene_name)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
