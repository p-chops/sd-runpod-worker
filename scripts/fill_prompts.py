import csv
import json
import os
import argparse
from tqdm import tqdm
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables (e.g., OpenAI API key)
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY in .env or environment.")

# Initialize single client instance
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_prompt(csv_data):
    """
    Generate specific, scholarly, and visually evocative prompts for all rows in the CSV using OpenAI's Responses API.

    Args:
        csv_data (str): The CSV data as a string, with placeholders for the 'prompt' column.

    Returns:
        str: The updated CSV data with the 'prompt' column filled in.
    """
    instruction = (
        "Here's a CSV of a prompt schedule, with the prompt column empty--fill it with brief prompts. "
        "For each scene, generate a concise, specific, and visually evocative art prompt for an img2img model being applied to a single scene. "
        "Reference concrete artistic styles (e.g., Baroque, Ukiyo-e, Art Deco), name real artists (e.g., Monet, Vermeer, Kandinsky), "
        "include historical periods or genres (Victorian, Mughal, cyberpunk, film noir), and make the image striking or surreal. "
        "Keep the prompt brief (less than one sentence) but vivid and distinct."
        "Return only the CSV data as plaintext, with no markdown or explanations.\n\n"
        f"{csv_data}"
    )

    try:
        resp = client.responses.create(
            model="gpt-4o",
            input=instruction,
        )
    except Exception as e:
        raise RuntimeError(f"OpenAI request failed: {e}")

    # Extract the returned CSV from the response
    text = str(resp.output[0].content[0].text)

    if not text:
        raise RuntimeError("OpenAI returned an empty response for the prompt generation.")

    return text.strip()

def fill_prompts(input_csv, output_csv):
    """
    Read the input CSV, generate prompts for all rows in a single query, and save the updated CSV.

    Args:
        input_csv (str): Path to the input CSV file.
        output_csv (str): Path to the output CSV file.
    """
    # Read the input CSV as a string
    with open(input_csv, 'r', encoding='utf-8') as infile:
        csv_data = infile.read()

    # Generate the updated CSV with prompts
    updated_csv = generate_prompt(csv_data)

    # Write the updated CSV to the output file
    with open(output_csv, 'w', encoding='utf-8', newline='') as outfile:
        outfile.write(updated_csv)

    print(f"Updated CSV saved to {output_csv}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fill in prompts for a CSV using OpenAI's GPT-5 mini Responses API.")
    parser.add_argument('input_csv', help="Path to the input CSV file.")
    parser.add_argument('output_csv', help="Path to the output CSV file.")
    args = parser.parse_args()

    try:
        # fill_prompts('scenes.csv', 'foo.csv')
        fill_prompts(args.input_csv, args.output_csv)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
