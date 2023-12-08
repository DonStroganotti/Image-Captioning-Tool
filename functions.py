import json
import os
import re

def remove_trailing_commas(file_path):
    try:
        # Read the content of the text file
        with open(file_path, 'r') as file:
            content = file.read()

        # remove trailing comma and spaces
        while content.endswith(',') or content.endswith(' '):
            content = content[:-1]

        # Write the modified content back to the file
        with open(file_path, 'w') as file:
            file.write(content)

        print(f"Trailing commas or spaces removed from {file_path}")
    except Exception as e:
        print(f"Error removing trailing commas or spaces: {e}")

        
def is_text_file_empty(txt_file_path):
    return os.path.getsize(txt_file_path) == 0

# Function to extract numerical parts from a string for natural sorting
def extract_numbers(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def extract_keywords_from_files(folder_path):
    # Collect all keywords from txt files in the specified folder
    keywords_set = set()

    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(folder_path, filename)
            
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                # Assuming keywords are separated by commas
                keywords = [keyword.strip() for keyword in content.split(",")]
                keywords_set.update(keywords)

    return list(keywords_set)

def update_keywords_json(folder_path, json_file_path):
    # Get existing keywords from the JSON file
    existing_keywords = []
    if os.path.exists(json_file_path):
        with open(json_file_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
            existing_keywords = data.get("keywords", [])

    # Extract new keywords from txt files
    new_keywords = extract_keywords_from_files(folder_path)

    # Combine existing and new keywords, and remove duplicates
    all_keywords = list(set(existing_keywords + new_keywords))

    # remove empty
    filtered_list = [item for item in all_keywords if item != ""]

    # Update the keywords.json file
    with open(json_file_path, "w", encoding="utf-8") as json_file:
        json.dump({"keywords": filtered_list}, json_file, indent=2)

def read_and_sort_text_files(input_folder, output_file):
    try:
        # Get a list of all text files in the input folder
        text_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.txt')]

        # Sort the text files using a natural sort order
        sorted_text_files = sorted(text_files, key=extract_numbers)

        # Read the content of each text file and append it to a list
        content_list = []
        for file_name in sorted_text_files:
            file_path = os.path.join(input_folder, file_name)
            with open(file_path, 'r') as file:
                content_list.append(file.read())

        # Write the content list to the output file
        with open(output_file, 'w') as output_file:
            output_file.write('\n'.join(content_list))

        print(f"Content of text files sorted and written to {output_file}")
    except Exception as e:
        print(f"Error reading and sorting text files: {e}")
