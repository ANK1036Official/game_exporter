import argparse
import os
import json
import glob
import subprocess
import shutil
import struct
import zipfile
import urllib.request
import getpass

from chardet.universaldetector import UniversalDetector
# Dependency check

def check_dependencies():
    if shutil.which('asar') is None:
        print("Error: 'asar' binary not found. Please install it and add to your PATH.")
        exit(1)
    elif shutil.which('unrpa') is None:
        print("Error: 'unrpa' binary not found. Please install it and add to your PATH.")
        exit(1)
    else:
        if debug_mode:
            print("'asar' and 'unrpa' binaries found.")

# Unity
def setup_asset_ripper():
    choice = input('Using this type will require AssetRipper, which will be automatically downloaded.\nIs this okay? (y/n) : ')
    if choice.lower() == 'n':
        print("Exiting the script.")
        sys.exit(0)
    elif user_input.lower() == 'y':
        print("Installing AssetRipper...")
        asset_ripper_url = "https://github.com/AssetRipper/AssetRipper/releases/download/0.3.4.0/AssetRipper_linux_x64.zip" # You may need to update the version in the future.
        asset_ripper_zip_path = "AssetRipper_linux_x64.zip"
        asset_ripper_folder = "AssetRipper"

        if not os.path.exists(asset_ripper_folder):
            sudo_password = getpass.getpass("Enter your sudo password to properly download AssetRipper: ")
            os.makedirs(asset_ripper_folder)

            urllib.request.urlretrieve(asset_ripper_url, asset_ripper_zip_path)

            with zipfile.ZipFile(asset_ripper_zip_path, 'r') as zip_ref:
                zip_ref.extractall(asset_ripper_folder)

            os.remove(asset_ripper_zip_path)

            for root, _, files in os.walk(asset_ripper_folder):
                for file in files:
                    if file.endswith('.zip'):
                        inner_zip_path = os.path.join(root, file)
                        with zipfile.ZipFile(inner_zip_path, 'r') as inner_zip_ref:
                            inner_zip_ref.extractall(asset_ripper_folder)
                        os.remove(inner_zip_path)
                        break
            files_to_chmod = [
                "AssetRipper",
                "libcapstone.so",
                "libHarfBuzzSharp.so",
                "libSkiaSharp.so",
                "libTexture2DDecoderNative.so",
                "libvlc.dylib",
                "Licenses"
            ]

            for file_name in files_to_chmod:
                file_path = os.path.join(asset_ripper_folder, file_name)

                if os.path.exists(file_path):
                    chmod_command = f"echo {sudo_password} | sudo -S chmod +x {file_path}"
                    subprocess.run(chmod_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                else:
                    print(f"File {file_name} does not exist, skipping chmod.")
    else:
        print("Invalid input. Exiting the script.")
        sys.exit(1)


def discover_unity_files(directory):
    choice = input('This type can use a lot of time and RAM. Continue? (y/n)')
    if choice.lower() == 'n':
        print("Exiting the script.")
        sys.exit(0)
    elif user_input.lower() == 'y':
        setup_asset_ripper()
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(('.assets', '.asset', '.bundle', '.unity3d', '.apk')):
                    print(f"Processing {file}")
                    extract_all_assets(os.path.join(root, file))
        merge_folders(directory, "Unity_combined")
    else:
        print("Invalid input. Exiting the script.")
        sys.exit(1)


def extract_all_assets(file_path):
    dir_name = os.path.dirname(file_path)

    counter = 1
    output_folder = os.path.join(dir_name, f"Unity_extracted_{counter}")
    while os.path.exists(output_folder):
        counter += 1
        output_folder = os.path.join(dir_name, f"Unity_extracted_{counter}")

    os.makedirs(output_folder)

    asset_ripper_command = ["./AssetRipper/AssetRipper", file_path, "-o", output_folder, '-q']
    subprocess.run(asset_ripper_command)


def merge_folders(root_directory, combined_folder_name):
    combined_folder_path = os.path.join(root_directory, combined_folder_name)
    if not os.path.exists(combined_folder_path):
        os.makedirs(combined_folder_path)

    for root, _, files in os.walk(root_directory):
        if 'Unity_extracted' in root:
            for file in files:
                source_file_path = os.path.join(root, file)
                dest_file_path = os.path.join(combined_folder_path, file)

                counter = 1
                while os.path.exists(dest_file_path):
                    name, ext = os.path.splitext(file)
                    dest_file_path = os.path.join(combined_folder_path, f"{name}_{counter}{ext}")
                    counter += 1

                shutil.copy2(source_file_path, dest_file_path)
            
            try:
                shutil.rmtree(root)
            except Exception as e:
                print(f"An error occurred while trying to remove the folder {root}: {e}")

    print(f"Done! Files located at {root_directory}/Unity_combined")

# RenPy
def discover_rpa(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".rpa"):
                rpa_file_path = os.path.join(root, file)
                extract_rpa_with_unrpa(rpa_file_path)

def extract_rpa_with_unrpa(rpa_file_path):
    output_dir = os.path.join(os.path.dirname(rpa_file_path), 'out')

    try:
        subprocess.run(["unrpa", "--mkdir", "-p", output_dir, rpa_file_path], check=True)
        print(f"Successfully extracted {rpa_file_path} to {output_dir}")
        return True
    except subprocess.CalledProcessError:
        print(f"Failed to extract {rpa_file_path}")
        return False

# Electron based game

def discover_asar(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".asar"):
                extract_asar(root, file)
                return True

def extract_asar(root, file):
    file_path = os.path.join(root, file)
    output_path = os.path.join(root, 'out/')
    command = f'asar extract {file_path} {output_path}'

    if debug_mode:
        print(f"Executing command: {command}")

    subprocess.run(command, shell=True, check=True)
    return True

# RPGMaker MV
class Decrypter:
    default_header_len = 16
    default_signature = "5250474d56000000"
    default_version = "000301"
    default_remain = "0000000000"
    png_header_bytes = '89 50 4E 47 0D 0A 1A 0A 00 00 00 0D 49 48 44 52'
    def __init__(self, encryption_key):
        # Encryption-Fields
        self.encrypt_code = encryption_key
        self.encryption_code_array = self.split_encryption_code()

        # Option Fields
        self.ignore_fake_header = False

        # Fake-Header Info-Fields
        self.header_len = None
        self.signature = None
        self.version = None
        self.remain = None

        # Fake PNG-Header length
        self.png_header_len = None

    def split_encryption_code(self):
        if not self.encrypt_code:
            return []

        return [self.encrypt_code[i:i+2] for i in range(0, len(self.encrypt_code), 2)]

    def verify_fake_header(self, file_header):
        fake_header = self.build_fake_header()

        for i in range(self.get_header_len()):
            if file_header[i] != fake_header[i]:
                return False

        return True

    def build_fake_header(self):
        header_len = self.get_header_len()
        header_structure = self.get_signature() + self.get_version() + self.get_remain()

        fake_header = bytearray(header_len)

        for i in range(header_len):
            fake_header[i] = int(header_structure[i * 2:i * 2 + 2], 16)

        return fake_header

    def modify_file(self, rpg_file, mod_type, callback):
        with open(rpg_file.file, 'rb') as f:
            content = f.read()

        try:
            if mod_type == 'restore':
                rpg_file.content = self.restore_png_header(content)
            elif mod_type == 'encrypt':
                rpg_file.content = self.encrypt(content)
            else:  # default is 'decrypt'
                rpg_file.content = self.decrypt(content)

            rpg_file.create_blob_url(mod_type != 'encrypt')

            callback(rpg_file, None)
        except Exception as e:
            callback(rpg_file, e)

    def restore_png_header(self, array_buffer):
        if not array_buffer:
            raise Exception("File is empty or can't be read.")

        header_len = self.png_header_len if self.png_header_len is not None else self.get_header_len()
        png_start_header = Decrypter.get_normal_png_header(header_len)

        header_len = len(png_start_header)

        array_buffer = array_buffer[header_len * 2:]

        tmp_int8_arr = bytearray(len(array_buffer) + header_len)
        tmp_int8_arr[:header_len] = png_start_header
        tmp_int8_arr[header_len:] = array_buffer

        return tmp_int8_arr


    def encrypt(self, array_buffer):
        if not array_buffer:
            raise Exception("File is empty or can't be read.")

        array_buffer = self.x_or_bytes(array_buffer)
        fake_header = self.build_fake_header()

        tmp_int8_array = bytearray(len(array_buffer) + self.get_header_len())
        tmp_int8_array[:self.get_header_len()] = fake_header
        tmp_int8_array[self.get_header_len():] = array_buffer

        header = tmp_int8_array[:self.get_header_len()]
        if not self.verify_fake_header(header):
            raise Exception("Fake-Header doesn't match the Template-Fake-Header... Please report this Bug")

        return tmp_int8_array

    def decrypt(self, array_buffer):
        if not array_buffer:
            raise Exception("File is empty or can't be read.")

        if not self.ignore_fake_header:
            header = array_buffer[:self.get_header_len()]
            if not self.verify_fake_header(header):
                raise Exception("Fake-Header doesn't match the Template-Fake-Header.")

        array_buffer = bytearray(array_buffer[self.get_header_len():])
        array_buffer = self.x_or_bytes(array_buffer)

        return array_buffer

    def x_or_bytes(self, array_buffer):
        header_len = self.get_header_len()

        for i in range(header_len):
            array_buffer[i] = array_buffer[i] ^ int(self.encryption_code_array[i], 16)

        return array_buffer


    def get_header_len(self):
        if self.header_len is None or not isinstance(self.header_len, int):
            self.header_len = self.default_header_len

        return int(self.header_len)

    def get_signature(self):
        if self.signature is None:
            self.signature = self.default_signature

        return self.signature

    def get_version(self):
        if self.version is None:
            self.version = self.default_version

        return self.version

    def get_remain(self):
        if self.remain is None:
            self.remain = self.default_remain

        return self.remain

    def restore_header(self, rpg_file, callback):
        self.modify_file(rpg_file, 'restore', callback)

    def decrypt_file(self, rpg_file, callback):
        self.modify_file(rpg_file, 'decrypt', callback)

    def process_directory(self, directory, operation):
        if debug_mode:
            print(f"Processing directory: {directory} for operation: {operation}")

        file_types = {
            '.rpgmvp': '.png',
            '.png_': '.png',
            '.rpgmvm': '.m4a',
            '.m4a_': '.m4a',
            '.rpgmvo': '.ogg',
            '.ogg_': '.ogg'
        }

        for root, dirs, files in os.walk(directory):
            for file in files:
                file_ext = os.path.splitext(file)[1]

                if file_ext in file_types.keys() if operation == "decrypt" else file_types.values():
                    orig_file_path = os.path.join(root, file)
                    new_file_ext = file_types.get(file_ext, file_ext)
                    new_file_name = os.path.splitext(file)[0] + new_file_ext
                    new_file_path = os.path.join(root, new_file_name)
                    if debug_mode:
                        print(f"Processing file: {orig_file_path}")
                        print(f"New file path will be: {new_file_path}")

                    with open(orig_file_path, 'rb') as f:
                        content = f.read()

                    new_content = self.encrypt(content) if operation == "encrypt" else self.decrypt(content)

                    with open(new_file_path, 'wb') as f:
                        f.write(new_content)
                    if debug_mode:
                        print(f"Operation {operation} completed for file: {orig_file_path}")

def find_system_json(directory):
    if debug_mode:
        print(f"Searching for System.json recursively in directory: {directory}")
        print(f"Debug: Directory string type is {type(directory)} and value is {repr(directory)}")
    for root, dirs, files in os.walk(directory):
        if debug_mode:
            print(f"Checking in directory: {root}")
        if "System.json" in files:
            full_path = os.path.join(root, "System.json")
            if debug_mode:
                print(f"Found System.json at: {full_path}")
            return full_path
    if debug_mode:
        print("System.json not found.")
    return None


def read_system_json(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def parse_args():
    parser = argparse.ArgumentParser(description='Encrypt or decrypt RPG Maker files.')
    parser.add_argument('-d', '--directory', type=str, required=True, help='Directory containing the game files.')
    parser.add_argument('-o', '--operation', type=str, choices=['encrypt', 'decrypt'], required=True, help='Operation to perform: encrypt or decrypt.')
    parser.add_argument('--debug', help='Enable debug output.', action='store_true')
    parser.add_argument('--type', help='Specify the type of RPG Maker or other.', required=True, choices=['rpgmakermv', 'electron', 'renpy', 'unity'])
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    directory = args.directory
    operation = args.operation
    debug_mode = args.debug
    decrypter_type = args.type

    check_dependencies()

    if debug_mode:
        print(f"Arguments parsed. Directory: {directory}, Operation: {operation}, Type: {decrypter_type}")

    if decrypter_type == 'rpgmakermv':
        system_json_path = find_system_json(directory)
        if system_json_path:
            if debug_mode:
                print(f"Found System.json at: {system_json_path}")
            system_data = read_system_json(system_json_path)
            encryption_key = system_data.get('encryptionKey', None)

            if encryption_key:
                if debug_mode:
                    print(f"Encryption key found: {encryption_key}")
                decrypter = Decrypter(encryption_key)
                decrypter.process_directory(directory, operation)
            else:
                if debug_mode:
                    print("No encryption key found in System.json. Exiting.")
        else:
            if debug_mode:
                print("System.json not found. Exiting.")
    elif decrypter_type == 'electron':
        discover_asar(directory)
    elif decrypter_type == 'renpy':
        discover_rpa(directory)
    elif decrypter_type == 'unity':
        discover_unity_files(directory)
