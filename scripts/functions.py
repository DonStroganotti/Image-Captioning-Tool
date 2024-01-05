from collections import Counter
import operator
import json
import os
import re
import uuid

from PIL import Image
from tqdm import tqdm


def remove_trailing_commas(file_path):
    try:
        changes = False
        # Read the content of the text file
        with open(file_path, "r") as file:
            content = file.read()

        # remove trailing comma and spaces
        while content.endswith(",") or content.endswith(" "):
            changes = True
            content = content[:-1]

        # Write the modified content back to the file
        with open(file_path, "w") as file:
            file.write(content)
        if changes == True:
            print(f"Trailing commas or spaces removed from {file_path}")
    except Exception as e:
        print(f"Error removing trailing commas or spaces: {e}")


def is_text_file_empty(txt_file_path):
    return os.path.getsize(txt_file_path) == 0


def extract_keywords_from_files(folder_path):
    # Collect all keywords from txt files in the specified folder and its subfolders
    keywords_set = set()
    keywords_counter = Counter()

    image_files = list_images_recursive(folder_path)

    for image_file in image_files:
        txt_file_path = os.path.splitext(image_file)[0] + ".txt"
        txt_file_path = os.path.join(folder_path, txt_file_path)

        if os.path.exists(txt_file_path):
            with open(txt_file_path, "r", encoding="utf-8") as file:
                content = file.read()
                # Assuming keywords are separated by commas
                keywords = [keyword.strip() for keyword in content.split(",")]
                keywords_set.update(keywords)
                # for word in keywords:
                keywords_counter.update(keywords)

    return list(keywords_set), keywords_counter


def update_keywords_json(folder_path, json_file_path):
    keywords_counter = Counter()

    # Get existing keywords from the JSON file
    existing_keywords = []
    if os.path.exists(json_file_path):
        with open(json_file_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
            existing_keywords = data.get("keywords", [])
            keywords_counter.update(existing_keywords)

    # Extract new keywords from txt files
    new_keywords, counter = extract_keywords_from_files(folder_path)

    keywords_counter.update(counter)

    # Combine existing and new keywords, and remove duplicates
    all_keywords = set(existing_keywords + new_keywords)

    # remove empty
    filtered_list = [item for item in all_keywords if item != ""]

    # sort list by occurence:
    filtered_list = [
        key
        for key, val in sorted(
            keywords_counter.items(), key=operator.itemgetter(1), reverse=True
        )
    ]

    # Update the keywords.json file
    with open(json_file_path, "w", encoding="utf-8") as json_file:
        json.dump({"keywords": filtered_list}, json_file, indent=2)


def save_all_captions_to_txt_file(input_folder, output_file_path):
    try:
        # Get a list of all text files in the input folder
        text_files = [f for f in os.listdir(input_folder) if f.lower().endswith(".txt")]

        # Sort the text files using a natural sort order
        sorted_text_files = sorted(text_files, key=extract_numbers)

        # Read the content of each text file and append it to a list
        content_list = []
        json_content_list = []
        for file_name in sorted_text_files:
            file_path = os.path.join(input_folder, file_name)
            with open(file_path, "r") as file:
                file_content = file.read()
                # remove newlines from the end
                while file_content.endswith("\n"):
                    file_content = file_content[:-1]
                content_list.append(file_content)
                json_content_list.append(
                    {"file_name": file_name, "caption": file_content}
                )

        # Write the content list to the output file as a .txt
        with open(output_file_path, "w") as output_file:
            output_file.write("\n".join(content_list))

        json_output_file_path = os.path.splitext(output_file_path)[0] + ".json"

        # # Write the json_content_list to a .json file
        with open(json_output_file_path, "w") as json_output_file:
            json.dump(json_content_list, json_output_file)

        print(
            f"Content of text files sorted and written to: \n{output_file_path}\n{json_output_file_path} "
        )
    except Exception as e:
        print(f"Error reading and sorting text files: {e}")


# This function reads the content of the input txt file and writes it to a .txt file
# with the same name as the image files in the output folder
# TODO: make it also able to read the .json file that 'save_all_captions_to_txt_file' outputs
def caption_file_to_individual_captions(input_txt_file, image_folder):
    try:
        image_files = list_images_recursive(image_folder)
        with open(input_txt_file, "r") as file:
            content_list = file.readlines()
        for image_file in image_files:
            output_file = os.path.join(
                image_folder, os.path.splitext(image_file)[0] + ".txt"
            )
            with open(output_file, "w") as output_file:
                output_file.write(content_list[image_files.index(image_file)])
        print(f"Content of input txt file written to text files in {image_folder}")
    except Exception as e:
        print(f"Error writing content to text files: {e}")


def list_files_with_keyword(folder_path, keyword):
    # Ensure the folder path exists
    if not os.path.exists(folder_path):
        print(f"Folder '{folder_path}' does not exist.")
        return []

    matching_files = []

    txt_files = list_files_recursive(folder_path, [".txt"])

    # Iterate through all files in the folder
    for file_name in txt_files:
        # Read the content of the text file
        with open(os.path.join(folder_path, file_name), "r", encoding="utf-8") as file:
            file_content = file.read()
        # Check if the keyword is present in the file content
        if keyword.lower() in file_content.lower():
            matching_files.append(file_name)

    return matching_files


# Function to extract numerical parts from a string for natural sorting
def extract_numbers(s):
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split("([0-9]+)", s)
    ]


def list_files_recursive(base_folder, file_endings=[]):
    file_paths = []
    for root, dirs, files in os.walk(base_folder):
        for file in files:
            if file.lower().endswith(tuple(file_endings)):
                relative_path = os.path.relpath(
                    os.path.join(root, file), base_folder
                ).replace(os.path.sep, "/")
                file_paths.append(relative_path)
    return file_paths


def list_images_recursive(base_folder):
    image_files = list_files_recursive(
        base_folder, [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]
    )
    return sorted(image_files, key=extract_numbers)


def generate_hash():
    "return str(uuid.uuid4())[:8]"
    return str(uuid.uuid4())[:8]


def resize_images(
    input_folder, output_folder, target_pixel_count=(1024, 1024), quality=95
):
    # Get the list of image filenames
    # image_filenames = [
    #     filename
    #     for filename in os.listdir(input_folder)
    #     if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))
    # ]

    image_filenames = list_images_recursive(input_folder)

    # Use tqdm to create a progress bar
    for filename in tqdm(image_filenames, desc="Resizing Images", unit="image"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename)

        _target_px_count = target_pixel_count[0] * target_pixel_count[1]
        # Open the image
        with Image.open(input_path) as img:
            _width, _height = img.size
            _pxCount = _width * _height

            # Resize while maintaining aspect ratio
            while _pxCount > _target_px_count:
                _width *= 0.99
                _height *= 0.99
                _pxCount = _width * _height

            # Resize while maintaining aspect ratio
            while _pxCount < _target_px_count:
                _width *= 1.01
                _height *= 1.01
                _pxCount = _width * _height

            _width = int(_width)
            _height = int(_height)

            # Save the resized image as JPEG with the specified quality
            img = img.resize(size=(_width, _height))
            img.convert("RGB").save(output_path, "JPEG", quality=quality)


def get_image_txt_file_pairs(input_folder):
    image_filenames = list_images_recursive(input_folder)

    images_with_txt_file = []
    images_without_txt_file = []

    total_images = 0
    missing_txt_files = 0

    new_txt_file_paths = []
    txt_file_paths = []

    for image in image_filenames:
        total_images += 1
        txt_file_name = image.rpartition(".")[0] + ".txt"
        txt_file_path = os.path.join(input_folder, txt_file_name)
        if os.path.exists(txt_file_path):
            images_with_txt_file.append(image)
            txt_file_paths.append(txt_file_path)
        else:
            images_without_txt_file.append(image)
            new_txt_file_paths.append(txt_file_path)
            missing_txt_files += 1

    return (
        images_with_txt_file,
        images_without_txt_file,
        total_images,
        missing_txt_files,
        new_txt_file_paths,
        txt_file_paths,
    )


def count_keywords_in_txt_files(input_folder):
    (
        images_with_txt_file,
        images_without_txt_file,
        total_images,
        missing_txt_files,
        new_txt_file_paths,
        txt_file_paths,
    ) = get_image_txt_file_pairs(input_folder)

    keyword_counter = Counter()

    for file in txt_file_paths:
        with open(file, "r") as f:
            file_content = f.read()
            _tokens = [item.strip() for item in file_content.split(",") if item != ""]
            tokens = []
            for t in _tokens:
                # ignore token if it is too short or doesn't contain letters
                if len(t) > 1 and re.match("[a-zA-Z]", t):
                    tokens.append(t)

            keyword_counter.update(tokens)

    return keyword_counter


def create_text_file_from_filename(input_folder, split_token=" "):
    (
        images_with_txt_file,
        images_without_txt_file,
        total_images,
        missing_txt_files,
        new_txt_file_paths,
        txt_file_paths,
    ) = get_image_txt_file_pairs(input_folder)

    print(f"{missing_txt_files} out of {total_images} images are missing .txt files.")

    print(
        f"Creating {missing_txt_files} .txt files from filenames using '{split_token}' to separate keywords..."
    )

    for txt_file_name in new_txt_file_paths:
        basename = os.path.basename(txt_file_name).rpartition(".")[0]
        tokens = [item.strip() for item in basename.split(split_token) if item != ""]
        if len(tokens) == 0:
            print(f"File: {txt_file_name} is missing tokens")
        with open(txt_file_name, "w") as f:
            f.write(",".join(tokens))


def get_full_prompts_that_include_all_keywords(directory, keywords=[]):
    txt_files = list_files_recursive(directory, [".txt"])
    output = []

    for file in txt_files:
        contains_all = True
        for keyword in keywords:
            basename = os.path.basename(file.rpartition(".")[0])
            if keyword not in basename:
                contains_all = False
        if contains_all:
            output.append(basename)

    return output
