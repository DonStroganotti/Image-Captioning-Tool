import os
import argparse

def create_text_files(folder_path, initial_text):
    # Get a list of all files in the folder
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

    counter = 0

    # Iterate through each file
    for file_name in files:
        # Check if a text file with the same name already exists
        text_file_name = os.path.splitext(file_name)[0] + '.txt'
        text_file_path = os.path.join(folder_path, text_file_name)

        if not os.path.exists(text_file_path):
            counter+=1
            # Create a new text file
            with open(text_file_path, 'w') as text_file:
                text_file.write(initial_text)

    if counter > 0:
        print("Created {} files", counter)


def process_files(path, operation, keyword1, keyword2):
    # Get a list of all .txt files in the specified folder
    txt_files = [f for f in os.listdir(path) if f.endswith('.txt')]

    for file_name in txt_files:
        file_path = os.path.join(path, file_name)

        # Read the content of the file
        with open(file_path, 'r') as file:
            content = file.read()

        # Perform the specified operation
        if operation == 'append':
            content += ' ' + keyword1
        elif operation == 'replace':
            content = content.replace(keyword1, keyword2)
        elif operation == 'prepend':
            content = keyword1 + ' ' + content

        # Write the modified content back to the file
        with open(file_path, 'w') as file:
            file.write(content)

def main():
    parser = argparse.ArgumentParser(description="Process .txt files in a folder.")
    parser.add_argument("--path", required=True, help="Path to the folder containing .txt files.")
    parser.add_argument("--append", help="Append a word to each file.")
    parser.add_argument("--replace", nargs=2, help="Replace a word in each file. Provide two arguments: word_to_replace new_word")
    parser.add_argument("--prepend", help="Prepend a word to each file.")
    parser.add_argument("--init", help="Creates text files for all files that do not already have it, add initial keyword to it")
    
    args = parser.parse_args()

    if not any([args.append, args.replace, args.prepend, args.init]):
        print("Please provide one of --append, --replace, --init, or --prepend.")
        return

    if not os.path.isdir(args.path):
        print("Invalid path. Please provide a valid folder path.")
        return

    if args.append:
        process_files(args.path, 'append', args.append, None)
    elif args.replace:
        process_files(args.path, 'replace', args.replace[0], args.replace[1])
    elif args.prepend:
        process_files(args.path, 'prepend', args.prepend, None)
    elif args.init:
        create_text_files(args.path, args.init)

    print("Operation completed successfully.")

if __name__ == "__main__":
    main()
