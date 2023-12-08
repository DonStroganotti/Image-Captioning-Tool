import os
import argparse
import sys
import webbrowser
from functions import *
from tag_editor import create_text_files, process_files
from flask import Flask, render_template, request, send_from_directory
from threading import Thread
from werkzeug.serving import make_server

def start_image_input_server(image_folder, keywords_path):
    template_folder = os.path.join(os.getcwd(), 'templates')
    app = Flask(__name__, template_folder=template_folder, static_folder=image_folder)
    
    # Get a list of all image files in the folder
    #image_files = sorted([f for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))], key=extract_numbers)
    
    image_files = list_images_recursive(image_folder)
    print(*image_files, sep="\n")

    if len(image_files) <= 0:
        print("Folder contains no images.")
        return

    current_image_index = -1

    # Counter to keep track of the current image index
    def select_starting_image():
        return int(input("Select a starting image between 0 and {}: ".format(len(image_files)-1)))
    
    while(current_image_index == -1):
        _index = select_starting_image()

        # if index is out of range, let the user input again
        if(_index < 0 or _index >= len(image_files)): 
            print("Index {} is not valid, use values between 0 and {}".format(_index, len(image_files)-1))
            continue
        current_image_index = _index

    # Print the selected image index and name
    print("Selected image: {} - {}".format(current_image_index, image_files[current_image_index]))

    def run_server():
        # Run the Flask app without debug mode in a separate thread
        print("Starting webserver on: 127.0.0.1:5000")
        http_server = make_server('127.0.0.1', 5000, app)
        http_server.serve_forever()

    # Start the server in a separate thread
    server_thread = Thread(target=run_server)
    server_thread.start()

    @app.route('/shutdown')
    def shutdown():
        print("Shutting down webserver...")
        #time.sleep(1)  # Adjust the delay as needed
        sys.exit()

    @app.route('/abort_submission', methods=['POST'])
    def abort_submission():
        print("Shutting down webserver...")
        #time.sleep(1)  # Adjust the delay as needed
        sys.exit()

    @app.route('/')
    def index():
        nonlocal current_image_index

        # update the keywords.json before sending it 
        update_keywords_json(image_folder, keywords_path+"/keywords.json")

        # If all images have been processed, set the shutdown signal
        if current_image_index >= len(image_files):
            return 'All images processed. Thank you!<script>setTimeout(function(){ window.location.href = "http://localhost:5000/shutdown"; }, 1000);</script>'

        # Get the current image file name
        current_image = image_files[current_image_index]

        print("current image: ", current_image)

        # Render the template with the current image
        return render_template('index.html', image=current_image)

    # Route to serve the keywords.json file
    @app.route('/get_keywords', methods=['GET'])
    def get_keywords():
        # update the keywords.json before sending it 
        update_keywords_json(image_folder, keywords_path+"/keywords.json")

        return send_from_directory(keywords_path, 'keywords.json')

    @app.route('/get_text_content/<path:image_name>')
    def get_text_content(image_name):
        # Create the full path for the corresponding text file
        txt_file_path = os.path.splitext(os.path.join(image_folder, image_name))[0] + '.txt'

        # Return nothing if the txt file doesn't exist yet
        if not os.path.exists(txt_file_path):
            #print("Image '{}' does not exist".format(txt_file_path))
            return ""
        
        # remove trailing commas from file
        remove_trailing_commas(txt_file_path)

        # Read the content of the text file
        with open(txt_file_path, 'r') as txt_file:
            text_content = txt_file.read()

        return text_content
    # Route for going to the previous image
    @app.route('/previous_image', methods=['GET'])
    def backward():
        nonlocal current_image_index

        # Ensure we don't go below zero
        current_image_index = max(0, current_image_index - 1)

        # Redirect to the previous image
        return index()
    
    # Route for going to the next image
    @app.route('/next_image', methods=['GET'])
    def forward():
        nonlocal current_image_index

        # Ensure we don't go beyond the last image
        current_image_index = min(len(image_files) - 1, current_image_index + 1)

        # Redirect to the next image
        return index()

    @app.route('/', methods=['POST'])
    def process_text():
        nonlocal current_image_index

        # Get the user input from the form, and remove trailing commas
        user_input = request.form['user_input']

        # remove trailing comma and spaces
        while user_input.endswith(',') or user_input.endswith(' '):
            user_input = user_input[:-1]

        if len(user_input) <= 0:
            # Move on to the next image
            current_image_index += 1
            return index()

        # Get the current image file name
        current_image = image_files[current_image_index]

        # Create the full path for the corresponding text file
        txt_file_path = os.path.splitext(os.path.join(image_folder, current_image))[0] + '.txt'

        # Create the text file if it doesn't exist
        if not os.path.exists(txt_file_path):
            open(txt_file_path, 'w').close()

        is_empty = is_text_file_empty(txt_file_path)

        # Append the user input to the text file
        with open(txt_file_path, 'a') as txt_file:
            txt_file.write(("," if not is_empty else "") + user_input)

        # Move on to the next image
        current_image_index += 1

        # Redirect to the next image or completion message
        return index()

    # Open the default web browser
    webbrowser.open('http://127.0.0.1:5000')

    return server_thread

def validate_path(path):
    if not os.path.isabs(path):
        path = os.path.join(os.getcwd(), path)
    return path

def validate_image_folder(path):
    is_top_level_folder = (os.path.normpath(path) == os.path.normpath(os.getcwd()))

    while is_top_level_folder == True or not os.path.isdir(path) or not any(file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')) for file in list_images_recursive(path)):
        print("Invalid path {}\nor folder doesn't contain images. Please provide a valid image folder path.".format(path))
        path = validate_path(input("Enter a new path to an image folder: "))
        is_top_level_folder = (os.path.normpath(path) == os.path.normpath(os.getcwd()))

    return path

def main_interactive(initial_path, keywords_path):
    image_folder_path = validate_path(initial_path)
    
    image_folder_path = validate_image_folder(image_folder_path)

    # if keywords path is empty or none create a subfolder in the images folder for the keywords
    if keywords_path == None or keywords_path == "":
        os.makedirs(image_folder_path+"\keywords", exist_ok=True)
        keywords_path = image_folder_path+"\keywords"

    keywords_path = validate_path(keywords_path)

    while True:
        print("\nAvailable Operations:")
        print("1. Append a word to each file")
        print("2. Replace a word in each file")
        print("3. Prepend a word to each file")
        print("4. Create text files with initial text")
        print("5. Process images and append text to corresponding files")
        print("6. Outputs the content of all txt files into a new file as a list")
        print("7. Lists all files that contain a specific keyword")
        print("8. Exit")

        choice = input("Enter the operation number (1-8): ")

        if choice == '1':
            append_word = input("Enter the word to append: ")
            process_files(image_folder_path, 'append', append_word, None)
        elif choice == '2':
            replace_word = input("Enter the word to replace: ")
            new_word = input("Enter the new word: ")
            process_files(image_folder_path, 'replace', replace_word, new_word)
        elif choice == '3':
            prepend_word = input("Enter the word to prepend: ")
            process_files(image_folder_path, 'prepend', prepend_word, None)
        elif choice == '4':
            initial_text = input("Enter the initial text: ")
            create_text_files(image_folder_path, initial_text)
        elif choice == '5':
            thread = start_image_input_server(image_folder_path, keywords_path)
            thread.join()
            #start_image_input_server(folder_path)
        elif choice == '6':
            file_name = input("Please input the name for the output file: ")
            read_and_sort_text_files(image_folder_path, os.path.dirname(__file__) + "/" + file_name)
        elif choice == '7':
            keyword = input("Input the keyword you are searching for: ")
            print(list_files_with_keyword(image_folder_path, keyword))
        elif choice == '8':
            print("Exiting the interactive terminal.")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 8.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive script to process text files and images.")
    parser.add_argument("--path", required=True, help="Initial path to the folder.")
    parser.add_argument("--keywords", default=None, required=False, help="Path to keywords file folder")
    args = parser.parse_args()

    main_interactive(args.path, args.keywords)
