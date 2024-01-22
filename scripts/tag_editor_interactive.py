import base64
from collections import OrderedDict
import io
from operator import itemgetter
import os
import argparse
import shutil
import sys
import uuid
import webbrowser

from tqdm import tqdm
from functions import *
from tag_editor import create_text_files, process_files
from flask import Flask, jsonify, render_template, request, send_from_directory
from threading import Thread
from werkzeug.serving import make_server
from PIL import Image

WEBSERVER_PORT = 5050


def start_image_input_server(image_folder, keywords_path, backup_path):
    template_folder = os.path.join(os.getcwd(), "templates")
    app = Flask(__name__, template_folder=template_folder, static_folder=image_folder)

    image_files = list_images_recursive(image_folder)

    if len(image_files) <= 0:
        print("Folder contains no images.")
        return

    current_image_index = -1

    # Counter to keep track of the current image index
    def select_starting_image():
        return int(
            input(
                "Select a starting image between 0 and {}: ".format(
                    len(image_files) - 1
                )
            )
        )

    while current_image_index == -1:
        _index = select_starting_image()

        # if index is out of range, let the user input again
        if _index < 0 or _index >= len(image_files):
            print(
                "Index {} is not valid, use values between 0 and {}".format(
                    _index, len(image_files) - 1
                )
            )
            continue

        current_image_index = _index

    # Print the selected image index and name
    print(
        "Selected image: {} - {}".format(
            current_image_index, image_files[current_image_index]
        )
    )

    def run_server():
        # Run the Flask app without debug mode in a separate thread
        print("Starting webserver on: 127.0.0.1:{}".format(WEBSERVER_PORT))
        http_server = make_server("127.0.0.1", WEBSERVER_PORT, app)
        http_server.serve_forever()

    # Start the server in a separate thread
    server_thread = Thread(target=run_server)
    server_thread.start()

    @app.route("/shutdown")
    def shutdown():
        print("Shutting down webserver...")
        # time.sleep(1)  # Adjust the delay as needed
        sys.exit()

    @app.route("/abort_submission", methods=["POST"])
    def abort_submission():
        print("Shutting down webserver...")
        # time.sleep(1)  # Adjust the delay as needed
        sys.exit()

    @app.route("/")
    def index():
        nonlocal current_image_index

        # update the keywords.json before sending it
        update_keywords_json(image_folder, keywords_path + "/keywords.json")

        # If all images have been processed, set the shutdown signal
        # if current_image_index >= len(image_files):
        #     _value = (
        #         "All images processed."
        #         + "<script>setTimeout(function(){ window.location.href = 'http://localhost:"
        #         + str(WEBSERVER_PORT)
        #         + "/shutdown'; }, 1000);</script>"
        #     )
        #     return _value

        # Get the current image file name
        current_image = image_files[current_image_index]

        # Render the template with the current image
        return render_template("index.html", image=current_image)

    # Route to serve the keywords.json file
    @app.route("/get_keywords", methods=["GET"])
    def get_keywords():
        # update the keywords.json before sending it
        update_keywords_json(image_folder, keywords_path + "/keywords.json")

        return send_from_directory(keywords_path, "keywords.json")

    @app.route("/get_text_content/<path:image_name>")
    def get_text_content(image_name):
        # Create the full path for the corresponding text file
        txt_file_path = (
            os.path.splitext(os.path.join(image_folder, image_name))[0] + ".txt"
        )

        # Return nothing if the txt file doesn't exist yet
        if not os.path.exists(txt_file_path):
            # print("Image '{}' does not exist".format(txt_file_path))
            return ""

        # remove trailing commas from file
        remove_trailing_commas(txt_file_path)

        # Read the content of the text file
        with open(txt_file_path, "r") as txt_file:
            text_content = txt_file.read()

        return text_content

    # Route for going to the previous image
    @app.route("/previous_image", methods=["GET"])
    def backward():
        nonlocal current_image_index

        # Ensure we don't go below zero
        current_image_index = max(0, current_image_index - 1)

        # Redirect to the previous image
        return index()

    # Route for going to the next image
    @app.route("/next_image", methods=["GET"])
    def forward():
        nonlocal current_image_index

        # Ensure we don't go beyond the last image
        current_image_index = min(len(image_files) - 1, current_image_index + 1)

        # Redirect to the next image
        return index()

    def increment_image_index():
        nonlocal current_image_index
        if current_image_index < (len(image_files) - 1):
            current_image_index += 1

    @app.route("/submit", methods=["POST"])
    def submit():
        nonlocal current_image_index
        # remove , and " " at the end of the input
        user_input = request.form["user_input"].rstrip(", ")

        if not user_input:
            increment_image_index()
            return index()

        current_image = image_files[current_image_index]
        txt_file_path = (
            os.path.splitext(os.path.join(image_folder, current_image))[0] + ".txt"
        )

        with open(
            txt_file_path, "a" if os.path.exists(txt_file_path) else "w"
        ) as txt_file:
            txt_file.write(
                ("," if not is_text_file_empty(txt_file_path) else "") + user_input
            )

        increment_image_index()

        return index()

    # clear tags of the current selected image
    @app.route("/clear_tags", methods=["GET"])
    def clear_tags():
        nonlocal current_image_index

        current_image = image_files[current_image_index]
        txt_file_path = (
            os.path.splitext(os.path.join(image_folder, current_image))[0] + ".txt"
        )

        with open(txt_file_path, "w"):
            print("Clearing tags for image:", current_image)

        return ""

    # This function copies an image file and its corresponding text file (if it exists)
    # while generating a new unique identifier for the image and the text file.
    def copy_original_image(current_image, current_image_path):
        base, ext = os.path.splitext(current_image_path)

        # Check if the current image path contains a hash
        if "_hash_" in base:
            # If a hash exists, split the base and the hash
            base, hash_ext = base.split("_hash_")

        # generate a new hash
        hash = generate_hash()

        new_image_path = os.path.join(
            os.path.dirname(current_image_path), f"{base}_hash_{hash}{ext}"
        )

        # generate new hash until a unique one is found
        while os.path.exists(new_image_path):
            print("duplicate hash found, generating a new one...")
            hash = generate_hash()
            new_image_path = os.path.join(
                os.path.dirname(current_image_path), f"{base}_hash_{hash}{ext}"
            )

        # copy image to new path
        shutil.copy2(current_image_path, new_image_path)

        # txt file of the current image
        txt_file = current_image.replace(os.path.splitext(current_image)[1], ".txt")
        txt_file = os.path.join(os.path.dirname(current_image_path), txt_file)

        if os.path.exists(txt_file):
            new_txt_file = os.path.join(
                os.path.dirname(current_image_path), f"{base}_hash_{hash}.txt"
            )
            shutil.copy2(txt_file, new_txt_file)
        else:
            print(f"No text file found for {current_image_path}")

        return new_image_path

    @app.route("/upload_cropped_image_copy", methods=["POST"])
    @app.route("/upload_cropped_image", methods=["POST"])
    def upload_cropped_image():
        data = request.get_json()
        cropped_data_url = data.get("croppedImage")

        nonlocal current_image_index
        nonlocal image_files

        current_image = image_files[current_image_index]
        current_image_path = os.path.join(image_folder, current_image)

        # Generate a unique identifier
        unique_id = generate_hash()  # Use the first 8 characters of the UUID

        # Create a backup filename with the unique identifier
        backup_filename = (
            os.path.splitext(current_image)[0] + os.path.splitext(current_image)[1]
        )
        backup_filepath = os.path.join(backup_path, backup_filename)

        # Check if a file with the same name already exists
        while os.path.exists(backup_filepath):
            backup_filename = f"{os.path.splitext(current_image)[0]}_{unique_id}{os.path.splitext(current_image)[1]}"
            backup_filepath = os.path.join(backup_path, backup_filename)

        # Create the full path for the backup file
        backup_filepath = os.path.join(backup_path, backup_filename)

        # Copy the current image to the backup file
        shutil.copy2(current_image_path, backup_filepath)

        new_image_path = current_image_path

        # if the path is copy, make a copy in the image folder as well and insert it into the image_files list
        if request.path == "/upload_cropped_image_copy":
            new_image_path = copy_original_image(current_image, current_image_path)

        # remove the current file before the cropped one is saved
        os.remove(current_image_path)

        # Handle the cropped data URL
        _, encoded_data = cropped_data_url.split(",", 1)
        image_data = base64.b64decode(encoded_data)

        # Save the cropped image
        cropped_image = Image.open(io.BytesIO(image_data)).convert("RGB")
        jpg_path = os.path.join(
            image_folder,
            current_image.replace(os.path.splitext(current_image)[1], ".jpg"),
        )
        cropped_image.save(jpg_path, "JPEG", quality=100)

        ########## IMPORTANT ##############
        # update image list to make sure all current images are found in case file ending changed
        # insert after current index to guarantee images are in the correct order
        # the order here is important because the image at the current index is what will be tagged
        # this has to do with the client side code that triggers a /submit
        ########## IMPORTANT ##############

        if not (os.path.basename(new_image_path) in image_files):
            image_files.insert(
                current_image_index + 1, os.path.basename(new_image_path)
            )

        return jsonify({"message": "Cropped image received and saved successfully"})

    # Open the default web browser
    webbrowser.open("http://127.0.0.1:{}".format(WEBSERVER_PORT))

    return server_thread


def backup_images(source_folder, backup_folder):
    print(f"Backing up images to {backup_folder}...")

    # Get the list of existing filenames in the backup folder
    existing_filenames = set(os.listdir(backup_folder))

    for filename in os.listdir(source_folder):
        if filename.lower().endswith(
            (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
        ):
            source_path = os.path.join(source_folder, filename)

            # Generate a unique identifier
            unique_id = generate_hash()  # Use the first 8 characters of the UUID

            # Append the unique identifier to the filename if there's a collision
            backup_filename = filename
            while backup_filename in existing_filenames:
                backup_filename = f"{os.path.splitext(filename)[0]}_{unique_id}{os.path.splitext(filename)[1]}"

            backup_path = os.path.join(backup_folder, backup_filename)

            shutil.copy2(source_path, backup_path)


def validate_path(path):
    if not os.path.isabs(path):
        path = os.path.join(os.getcwd(), path)
    return path


def validate_image_folder(path):
    is_top_level_folder = os.path.normpath(path) == os.path.normpath(os.getcwd())

    while (
        is_top_level_folder == True
        or not os.path.isdir(path)
        or not any(
            file.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))
            for file in list_images_recursive(path)
        )
    ):
        print(
            "Invalid path {}\nor folder doesn't contain images. Please provide a valid image folder path.".format(
                path
            )
        )
        path = validate_path(input("Enter a new path to an image folder: "))
        is_top_level_folder = os.path.normpath(path) == os.path.normpath(os.getcwd())

    return path


def main_interactive(initial_path, keywords_path, backup_path):
    image_folder_path = validate_path(initial_path)
    image_folder_path = validate_image_folder(image_folder_path)
    backup_folder_path = validate_path(backup_path)

    # Check if the folder exists
    if not os.path.exists(backup_folder_path):
        # If it doesn't exist, create the folder
        os.makedirs(backup_folder_path)

    if not os.path.isdir(backup_folder_path):
        print("backup folder '{}' is invalid!".format(backup_folder_path))
        return

    print("Image folder path: ", image_folder_path)
    print("Backup folder path: ", backup_folder_path)

    # if keywords path is empty or none create a subfolder in the images folder for the keywords
    if keywords_path == None or keywords_path == "":
        os.makedirs(image_folder_path + "\keywords", exist_ok=True)
        keywords_path = image_folder_path + "\keywords"

    keywords_path = validate_path(keywords_path)

    while True:
        print("\nAvailable Operations:")
        print("1. Append a word to each file")
        print("2. Replace a word in each file")
        print("3. Prepend a word to each file")
        print("4. Create text files with initial text")
        print("5. Process images and append text to corresponding files")
        print("6. Outputs the content of all txt files into a new file as a list")
        print(
            "7. Reads the line of a txt file and matches them to corresponding image files"
        )
        print("8. Lists all files that contain a specific keyword")
        print("9. Backup and Resize Images")
        print("10. filename to .txt files")
        print("11. count tokens in .txt files")
        print("12. get full prompts that includes keywords")
        print("13. Exit")

        choice = input("Enter the operation number (1-9): ")

        if choice == "1":
            append_word = input("Enter the word to append: ")
            process_files(image_folder_path, "append", append_word, None)
        elif choice == "2":
            replace_word = input("Enter the word to replace: ")
            new_word = input("Enter the new word: ")
            process_files(image_folder_path, "replace", replace_word, new_word)
        elif choice == "3":
            prepend_word = input("Enter the word to prepend: ")
            process_files(image_folder_path, "prepend", prepend_word, None)
        elif choice == "4":
            initial_text = input("Enter the initial text: ")
            create_text_files(image_folder_path, initial_text)
        elif choice == "5":
            thread = start_image_input_server(
                image_folder_path, keywords_path, backup_folder_path
            )
            thread.join()
            # start_image_input_server(folder_path)
        elif choice == "6":
            file_name = input("Please input the name for the output file: ")
            save_all_captions_to_txt_file(
                # move one folder up from the image folder by getting the folder of the folder
                image_folder_path,
                os.path.dirname(image_folder_path) + "/" + file_name,
            )
        elif choice == "7":
            captions_file_path = input("Please input the path for the caption file: ")
            caption_file_to_individual_captions(captions_file_path, image_folder_path)
        elif choice == "8":
            keyword = input("Input the keyword you are searching for: ")
            file_list = list_files_with_keyword(image_folder_path, keyword)
            print(f"There are {len(file_list)} entries in the list.")
            print("\n".join(file_list))
        elif choice == "9":
            # Option to backup and resize images
            resize_target = input(
                "Enter the target pixel count (width height), e.g., 1024 1024: "
            )
            try:
                target_width, target_height = map(int, resize_target.split())
            except ValueError:
                print(
                    "Invalid input for target pixel count. Please enter two integers separated by a space."
                )
                continue
            backup = input("Do you want to backup the original images? yes/no:")
            if backup != "no":
                # Backup images
                backup_images(image_folder_path, backup_folder_path)
            # Resize images
            resize_images(
                image_folder_path,
                image_folder_path,
                target_pixel_count=(target_width, target_height),
            )
        elif choice == "10":
            split_token = " "
            tmp = input("Split token, by default a whitespace:")
            if tmp != split_token and len(tmp) > 0:
                split_token = tmp
            print(f"Split token: '{split_token}'")
            create_text_file_from_filename(image_folder_path, split_token)

        elif choice == "11":
            save_path = os.path.join(image_folder_path, "keywords.json")

            if os.path.exists(save_path):
                print(f"{save_path} already exists, reading...")
                with open(save_path, "r") as f:
                    _keywords = json.load(f)
                    keywords = {}
                    for key, value in _keywords.items():
                        keywords[key.strip()] = value
                    print("sorting keywords...")
                    keywords = OrderedDict(
                        sorted(keywords.items(), key=itemgetter(1), reverse=True)
                    )

            else:
                print("Counting keywords in files...")
                keywords = count_keywords_in_txt_files(image_folder_path)
                print("sorting keywords...")
                keywords = OrderedDict(
                    sorted(keywords.items(), key=itemgetter(1), reverse=True)
                )

            with open(save_path, "w") as f:
                cleaned = {}
                # ignore keywords that only have 1 entry
                for k, v in keywords.items():
                    if v > 1:
                        cleaned[k] = v
                json.dump(cleaned, f, indent=4)
                print(f"saving to: {save_path}")
        elif choice == "12":
            print(
                "To load keywords and settings from a json file input the file name instead of keywords."
            )
            print("Otherwise input a list of comma separated keywords:")

            keywords = input()

            # json format
            """
                [
                    {
                        filename: name,
                        keywords: [list of keywords],
                    },
                    {
                        filename: name,
                        keywords: [list of keywords],
                    }
                ]
            """

            def save_prompts(output_filename, prompts):
                overwrite = True
                if os.path.exists(output_filename) == True:
                    print(f"Filename {output_filename} already exists")
                    _overwrite = input("Do you want to overwrite the file? yes/no: ")
                    if _overwrite.lower() != "yes":
                        overwrite = False

                if overwrite == True:
                    with open(output_filename, "w") as f:
                        for prompt in prompts:
                            f.write(prompt + "\n")

            if ".json" in keywords:
                with open(keywords, "r") as f:
                    json_data = json.load(f)

                    for entry in json_data:
                        filename = entry["filename"]
                        keywords = entry["keywords"]
                        prompts = get_full_prompts_that_include_all_keywords(
                            image_folder_path, keywords
                        )
                        print(f"{len(prompts)} prompts found for keywords: {keywords}")
                        save_prompts(filename, prompts)

            else:
                keywords = [keyword.strip() for keyword in keywords.split(",")]

                prompts = get_full_prompts_that_include_all_keywords(
                    image_folder_path, keywords
                )

                print(f"{len(prompts)} prompts found for keywords: {keywords}")

                output_filename = input("Save list of prompts to filname: ")

                save_prompts(output_filename, prompts)
        elif choice == "13":
            print("Exiting the interactive terminal.")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 10.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Interactive script to process text files and images."
    )
    parser.add_argument("--path", required=True, help="Initial path to the folder.")
    parser.add_argument(
        "--keywords", default=None, required=False, help="Path to keywords file folder"
    )
    parser.add_argument(
        "--backup", default="backup", required=False, help="Path to backup folder"
    )
    args = parser.parse_args()

    main_interactive(args.path, args.keywords, args.backup)
