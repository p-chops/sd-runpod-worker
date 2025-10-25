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
        "**Your task**\n\n"
        "You will be given a CSV file with columns: name, frame, prompt. "
        "Your task is to produce a new CSV with the prompts in the prompt column replaced with new ones. "
        "\n\n"
        "**Prompting guide**\n\n"
        "\n\n"
        "For each scene, generate a concise, specific, and visually evocative art prompt for an img2img model being applied to a single scene. "
        "Reference concrete artistic styles, name real artists, avoiding the obvious ones, "
        "include historical periods or genres, and make the image visually striking or with fantasy/surreal elements. "
        "Keep the prompt brief (less than one sentence) but vivid and distinct."
        "\n\n"
        "**Input CSV**\n\n"
        f"{csv_data}"
        "\n\n"
        "**Output format**\n\n"
        "Return a CSV with the same columns (name, frame, prompt) and the same rows, but with the prompt column filled in with the newly generated prompts. "
        "Answer only with the CSV header and rows, with no commentary or markdown."
        "\n\n"
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
    updated_csv = generate_prompt(csv_data) + '\n'

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
