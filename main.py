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
import sys
import re
from pathlib import Path

from chardet.universaldetector import UniversalDetector

try:
    import UnityPy
    UNITYPY_AVAILABLE = True
except ImportError:
    UNITYPY_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

args = None
debug_mode = False

def check_dependencies():
    required_tools = {
        'electron': ['asar'],
        'renpy': ['unrpa'],
        'rpgmakervxace': ['rvpacker'],
        'ue3': ['umodel'],
        'ue4': ['umodel'],
        'ue5': ['umodel'],
    }

    optional_tools = {
        'wolf': ['arc_unpacker', 'GARbro'],
        'ue4': ['UnrealPak'],
        'ue5': ['UnrealPak'],
        'godot': ['godotpcktool', 'gdsdecomp'],
    }

    if args.type in required_tools:
        for tool in required_tools[args.type]:
            if shutil.which(tool) is None:
                print(f"Error: '{tool}' binary not found. Please install it and add to your PATH.")
                if args.type.startswith('ue'):
                    print(f"Download UModel from: https://www.gildor.org/en/projects/umodel")
                else:
                    print(f"Installation instructions: https://github.com/search?q={tool}")
                sys.exit(1)

        if debug_mode:
            print(f"All required tools for {args.type} found.")

    if args.type in optional_tools:
        for tool in optional_tools[args.type]:
            if shutil.which(tool) is None:
                if debug_mode:
                    print(f"Note: Optional tool '{tool}' not found. Some features may be limited.")

def extract_unity_with_unitypy(file_path, output_folder):
    if not UNITYPY_AVAILABLE:
        return False

    try:
        env = UnityPy.load(file_path)
        extracted_count = 0

        for obj in env.objects:
            if obj.type.name == "Texture2D":
                try:
                    data = obj.read()

                    name = None
                    if hasattr(data, 'm_Name'):
                        name = data.m_Name
                    elif hasattr(data, 'name'):
                        name = data.name
                    else:
                        name = f"texture_{obj.path_id}"

                    name = re.sub(r'[<>:"/\\|?*]', '_', str(name))

                    if hasattr(data, 'image') and data.image:
                        img = data.image
                        dest = os.path.join(output_folder, "Textures", f"{name}.png")
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        img.save(dest)
                        extracted_count += 1
                except Exception as e:
                    if debug_mode:
                        print(f"    Error extracting texture: {e}")

            elif obj.type.name == "AudioClip":
                try:
                    data = obj.read()

                    name = None
                    if hasattr(data, 'm_Name'):
                        name = data.m_Name
                    elif hasattr(data, 'name'):
                        name = data.name
                    else:
                        name = f"audio_{obj.path_id}"

                    name = re.sub(r'[<>:"/\\|?*]', '_', str(name))

                    audio_data = None
                    if hasattr(data, 'samples') and data.samples:
                        if isinstance(data.samples, dict):

                            for sample_name, sample_data in data.samples.items():
                                if sample_data:
                                    ext = ".wav" if hasattr(data, 'm_CompressionFormat') and data.m_CompressionFormat == 0 else ".ogg"
                                    dest = os.path.join(output_folder, "Audio", f"{name}_{sample_name}{ext}")
                                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                                    with open(dest, "wb") as f:
                                        f.write(sample_data)
                                    extracted_count += 1
                        else:

                            audio_data = data.samples
                    elif hasattr(data, 'm_AudioData'):
                        audio_data = data.m_AudioData

                    if audio_data:
                        ext = ".wav" if hasattr(data, 'm_CompressionFormat') and data.m_CompressionFormat == 0 else ".ogg"
                        dest = os.path.join(output_folder, "Audio", f"{name}{ext}")
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        with open(dest, "wb") as f:
                            f.write(audio_data)
                        extracted_count += 1
                except Exception as e:
                    if debug_mode:
                        print(f"    Error extracting audio: {e}")

            elif obj.type.name == "TextAsset":
                try:
                    data = obj.read()

                    name = None
                    if hasattr(data, 'm_Name'):
                        name = data.m_Name
                    elif hasattr(data, 'name'):
                        name = data.name
                    else:
                        name = f"text_{obj.path_id}"

                    name = re.sub(r'[<>:"/\\|?*]', '_', str(name))

                    text_data = None
                    if hasattr(data, 'm_Script'):
                        text_data = data.m_Script
                    elif hasattr(data, 'text'):
                        text_data = data.text
                    elif hasattr(data, 'script'):
                        text_data = data.script
                    else:
                        text_data = str(data)

                    if text_data:
                        dest = os.path.join(output_folder, "Text", f"{name}.txt")
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        if isinstance(text_data, bytes):
                            with open(dest, "wb") as f:
                                f.write(text_data)
                        else:
                            with open(dest, "w", encoding='utf-8') as f:
                                f.write(str(text_data))
                        extracted_count += 1
                except Exception as e:
                    if debug_mode:
                        print(f"    Error extracting text: {e}")

            elif obj.type.name == "Shader":
                try:
                    data = obj.read()

                    name = None
                    if hasattr(data, 'm_Name'):
                        name = data.m_Name
                    elif hasattr(data, 'name'):
                        name = data.name
                    else:
                        name = f"shader_{obj.path_id}"

                    name = re.sub(r'[<>:"/\\|?*]', '_', str(name))

                    if hasattr(data, 'm_Script'):
                        script_data = data.m_Script
                    elif hasattr(data, 'script'):
                        script_data = data.script
                    else:
                        script_data = None

                    if script_data:
                        dest = os.path.join(output_folder, "Shaders", f"{name}.shader")
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        if isinstance(script_data, bytes):
                            with open(dest, "wb") as f:
                                f.write(script_data)
                        else:
                            with open(dest, "w", encoding='utf-8') as f:
                                f.write(str(script_data))
                        extracted_count += 1
                except Exception as e:
                    if debug_mode:
                        print(f"    Error extracting shader: {e}")

            elif obj.type.name == "Mesh":
                try:
                    data = obj.read()

                    name = None
                    if hasattr(data, 'm_Name'):
                        name = data.m_Name
                    elif hasattr(data, 'name'):
                        name = data.name
                    else:
                        name = f"mesh_{obj.path_id}"

                    name = re.sub(r'[<>:"/\\|?*]', '_', str(name))

                    if hasattr(data, 'export'):
                        dest = os.path.join(output_folder, "Models", f"{name}.obj")
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        with open(dest, "w", encoding='utf-8') as f:
                            f.write(data.export())
                        extracted_count += 1
                except Exception as e:
                    if debug_mode:
                        print(f"    Error extracting mesh: {e}")

            elif obj.type.name == "Sprite":
                try:
                    data = obj.read()

                    name = None
                    if hasattr(data, 'm_Name'):
                        name = data.m_Name
                    elif hasattr(data, 'name'):
                        name = data.name
                    else:
                        name = f"sprite_{obj.path_id}"

                    name = re.sub(r'[<>:"/\\|?*]', '_', str(name))

                    if hasattr(data, 'image') and data.image:
                        img = data.image
                        dest = os.path.join(output_folder, "Sprites", f"{name}.png")
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        img.save(dest)
                        extracted_count += 1
                except Exception as e:
                    if debug_mode:
                        print(f"    Error extracting sprite: {e}")

            elif obj.type.name == "MonoBehaviour":
                try:

                    data = obj.read()
                    name = f"monobehaviour_{obj.path_id}"

                    try:
                        tree = data.read_typetree()
                        if tree:
                            dest = os.path.join(output_folder, "Data", f"{name}.json")
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            with open(dest, "w", encoding='utf-8') as f:
                                json.dump(tree, f, indent=2)
                            extracted_count += 1
                    except:
                        pass
                except Exception as e:
                    if debug_mode:
                        print(f"    Error extracting MonoBehaviour: {e}")

        if debug_mode and extracted_count > 0:
            print(f"    Successfully extracted {extracted_count} assets")

        return extracted_count > 0

    except Exception as e:
        if debug_mode:
            print(f"  UnityPy error: {e}")
        return False

def setup_asset_ripper():
    print("AssetRipper is required for Unity extraction.")
    choice = input('Download AssetRipper (~100MB)? (y/n): ')
    if choice.lower() != 'y':
        print("Cannot extract Unity assets without AssetRipper.")
        return False

    print("Downloading AssetRipper...")
    asset_ripper_url = "https://github.com/AssetRipper/AssetRipper/releases/download/0.3.4.0/AssetRipper_linux_x64.zip"
    asset_ripper_zip_path = "AssetRipper_linux_x64.zip"
    asset_ripper_folder = "AssetRipper"

    if not os.path.exists(asset_ripper_folder):
        try:
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
                "Licenses"
            ]

            for file_name in files_to_chmod:
                file_path = os.path.join(asset_ripper_folder, file_name)
                if os.path.exists(file_path):
                    os.chmod(file_path, 0o755)

            print("✓ AssetRipper installed successfully")
            return True

        except Exception as e:
            print(f"Error installing AssetRipper: {e}")
            return False
    return True

def discover_unity_files(directory):
    choice = input('Unity extraction can be resource-intensive. Continue? (y/n): ')
    if choice.lower() != 'y':
        print("Skipping Unity extraction.")
        return

    unity_extensions = ('.assets', '.bundle', '.unity3d', '.resource')
    unity_data_path = None

    for item in os.listdir(directory):
        if item.endswith('_Data') and os.path.isdir(os.path.join(directory, item)):
            unity_data_path = os.path.join(directory, item)
            break

    found_files = []
    search_paths = [unity_data_path] if unity_data_path else [directory]

    for search_path in search_paths:
        for root, _, files in os.walk(search_path):

            if 'Unity_' in root and '_extracted' in root:
                continue

            for file in files:
                if file.endswith(unity_extensions):

                    file_path = os.path.join(root, file)
                    try:
                        if os.path.getsize(file_path) > 1024:  
                            found_files.append(file_path)
                    except:
                        pass

    if not found_files:
        print("No Unity asset files found.")
        return

    print(f"Found {len(found_files)} Unity asset file(s)")

    has_assetripper = os.path.exists("./AssetRipper/AssetRipper")

    if not has_assetripper and not UNITYPY_AVAILABLE:
        print("\nNo Unity extraction tools available!")
        choice = input("Would you like to:\n1. Download AssetRipper\n2. Install UnityPy (pip install UnityPy)\n3. Skip\nChoice (1/2/3): ")

        if choice == '1':
            if not setup_asset_ripper():
                return
        elif choice == '2':
            print("\nTo install UnityPy, run:")
            print("pip install UnityPy")
            print("\nThen run this script again.")
            return
        else:
            print("\nAlternative Unity extraction tools:")
            print("AssetStudio GUI: https://github.com/Perfare/AssetStudio")
            print("UABE: https://github.com/SeriousCache/UABE")
            return
    elif not has_assetripper and UNITYPY_AVAILABLE:
        print("Using UnityPy for extraction...")
    elif has_assetripper and not UNITYPY_AVAILABLE:
        print("Using AssetRipper for extraction...")
    else:
        print("Using AssetRipper with UnityPy fallback...")

    print("\nStarting extraction...")

    total_extracted = 0

    for i, file_path in enumerate(found_files):
        print(f"\n[{i+1}/{len(found_files)}] Processing {os.path.basename(file_path)}...")
        extracted = extract_all_assets(file_path)
        if extracted:
            total_extracted += 1

    extracted_folders = []

    check_paths = []
    check_paths.extend(search_paths)

    if unity_data_path and unity_data_path != directory:
        check_paths.append(directory)

    for check_path in check_paths:
        try:

            for root, dirs, _ in os.walk(check_path):
                for dir_name in dirs:
                    if 'Unity_' in dir_name and '_extracted' in dir_name:
                        full_path = os.path.join(root, dir_name)
                        if full_path not in extracted_folders:
                            extracted_folders.append(full_path)
        except Exception as e:
            if debug_mode:
                print(f"Error checking for extracted folders in {check_path}: {e}")

    if debug_mode:
        print(f"\nFound {len(extracted_folders)} extracted folders:")
        for folder in extracted_folders:
            print(f"  - {folder}")

    if extracted_folders or total_extracted > 0:

        merge_destination = search_paths[0] if search_paths else directory
        print(f"\n✓ Successfully extracted from {total_extracted} asset file(s)")
        merge_folders(merge_destination, "Unity_combined")
    else:
        print("\n⚠ No files were successfully extracted.")
        print("\nThis could be because:")
        print("- The game uses a newer Unity version not supported by current tools")
        print("- The assets are encrypted or use custom compression")
        print("- The game uses IL2CPP which requires additional steps")

def extract_all_assets(file_path):
    dir_name = os.path.dirname(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]

    output_folder = os.path.join(dir_name, f"Unity_{base_name}_extracted")
    counter = 1
    while os.path.exists(output_folder):
        counter += 1
        output_folder = os.path.join(dir_name, f"Unity_{base_name}_extracted_{counter}")

    os.makedirs(output_folder)
    extraction_successful = False

    if os.path.exists("./AssetRipper/AssetRipper"):

        asset_ripper_command = [
            "./AssetRipper/AssetRipper", 
            file_path, 
            "-o", output_folder,
            "-q"  
        ]

        if debug_mode:
            print(f"Running: {' '.join(asset_ripper_command)}")
            asset_ripper_command.append("-v")  

        try:

            result = subprocess.run(
                asset_ripper_command, 
                text=True,
                stdin=subprocess.DEVNULL,  
                stdout=subprocess.PIPE if not debug_mode else None,
                stderr=subprocess.STDOUT if not debug_mode else None
            )

            extracted_files = sum(len(files) for _, _, files in os.walk(output_folder))
            if extracted_files > 0:
                print(f"  ✓ Extracted {extracted_files} files")
                extraction_successful = True
                return True
            else:
                if debug_mode and result.stdout:
                    print(f"  AssetRipper output: {result.stdout}")

        except Exception as e:
            if debug_mode:
                print(f"AssetRipper error: {e}")

    if UNITYPY_AVAILABLE and not extraction_successful:
        print(f"  Trying UnityPy method...")
        if extract_unity_with_unitypy(file_path, output_folder):
            extracted_files = sum(len(files) for _, _, files in os.walk(output_folder))
            print(f"  ✓ Extracted {extracted_files} files with UnityPy")
            return True

    if not extraction_successful:
        print(f"  ⚠ No files extracted from {os.path.basename(file_path)}")

        try:
            os.rmdir(output_folder)
        except:
            pass

    return extraction_successful

def merge_folders(root_directory, combined_folder_name):
    combined_folder_path = os.path.join(root_directory, combined_folder_name)
    if not os.path.exists(combined_folder_path):
        os.makedirs(combined_folder_path)

    extracted_count = 0
    merged_folders = []

    for walk_root, walk_dirs, _ in os.walk(root_directory):

        if walk_root == combined_folder_path:
            continue

        for dir_name in walk_dirs:
            if 'Unity_' in dir_name and '_extracted' in dir_name:
                source_folder = os.path.join(walk_root, dir_name)
                merged_folders.append(source_folder)

                for file_root, _, files in os.walk(source_folder):
                    for file in files:
                        source_file_path = os.path.join(file_root, file)

                        ext = os.path.splitext(file)[1].lower()
                        type_folder = {
                            '.png': 'Textures',
                            '.jpg': 'Textures',
                            '.jpeg': 'Textures',
                            '.tga': 'Textures',
                            '.dds': 'Textures',
                            '.wav': 'Audio',
                            '.mp3': 'Audio',
                            '.ogg': 'Audio',
                            '.prefab': 'Prefabs',
                            '.mat': 'Materials',
                            '.shader': 'Shaders',
                            '.cs': 'Scripts',
                            '.txt': 'Text',
                            '.json': 'Data',
                            '.xml': 'Data',
                            '.asset': 'Assets',
                            '.mesh': 'Models',
                            '.fbx': 'Models',
                            '.obj': 'Models'
                        }.get(ext, 'Other')

                        if 'Sprites' in file_root:
                            type_folder = 'Sprites'
                        elif 'Textures' in file_root and ext in ['.png', '.jpg', '.jpeg', '.tga', '.dds']:
                            type_folder = 'Textures'

                        dest_folder = os.path.join(combined_folder_path, type_folder)
                        os.makedirs(dest_folder, exist_ok=True)

                        rel_path = os.path.relpath(file_root, source_folder)
                        if rel_path != '.':
                            dest_folder = os.path.join(dest_folder, rel_path)
                            os.makedirs(dest_folder, exist_ok=True)

                        dest_file_path = os.path.join(dest_folder, file)
                        counter = 1
                        while os.path.exists(dest_file_path):
                            name, ext = os.path.splitext(file)
                            dest_file_path = os.path.join(dest_folder, f"{name}_{counter}{ext}")
                            counter += 1

                        try:
                            shutil.copy2(source_file_path, dest_file_path)
                            extracted_count += 1
                        except Exception as e:
                            if debug_mode:
                                print(f"Could not copy {file}: {e}")

    for folder in merged_folders:
        try:
            shutil.rmtree(folder)
        except Exception as e:
            if debug_mode:
                print(f"Warning: Could not remove {folder}: {e}")

    if extracted_count > 0:
        print(f"\n✓ Merged {extracted_count} files from {len(merged_folders)} folders to:")
        print(f"   {combined_folder_path}")

        print("\nExtracted content summary:")
        for type_folder in ['Textures', 'Audio', 'Text', 'Data', 'Models', 'Sprites', 'Other']:
            folder_path = os.path.join(combined_folder_path, type_folder)
            if os.path.exists(folder_path):
                count = sum(len(files) for _, _, files in os.walk(folder_path))
                if count > 0:
                    print(f"  - {type_folder}: {count} files")
    else:
        print(f"\n⚠ No files found to merge.")

        try:
            os.rmdir(combined_folder_path)
        except:
            pass

def discover_rpa(directory):
    rpa_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".rpa"):
                rpa_files.append(os.path.join(root, file))

    if not rpa_files:
        print("No RPA files found.")
        return

    print(f"Found {len(rpa_files)} RPA file(s)")

    for rpa_file in rpa_files:
        print(f"Extracting {os.path.basename(rpa_file)}...")
        extract_rpa_with_unrpa(rpa_file)

def extract_rpa_with_unrpa(rpa_file_path):
    base_name = os.path.splitext(os.path.basename(rpa_file_path))[0]
    output_dir = os.path.join(os.path.dirname(rpa_file_path), f'RPA_{base_name}_extracted')

    try:
        subprocess.run(["unrpa", "--mkdir", "-p", output_dir, rpa_file_path], 
                      check=True, capture_output=True)
        print(f"✓ Extracted to {output_dir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to extract {os.path.basename(rpa_file_path)}")
        if debug_mode:
            print(f"Error: {e.stderr.decode()}")
        return False

def discover_asar(directory):
    asar_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".asar"):
                asar_files.append(os.path.join(root, file))

    if not asar_files:
        print("No ASAR files found.")
        return

    print(f"Found {len(asar_files)} ASAR file(s)")

    for asar_file in asar_files:
        print(f"Extracting {os.path.basename(asar_file)}...")
        extract_asar(os.path.dirname(asar_file), os.path.basename(asar_file))

def extract_asar(root, file):
    file_path = os.path.join(root, file)
    base_name = os.path.splitext(file)[0]
    output_path = os.path.join(root, f'ASAR_{base_name}_extracted')

    try:
        subprocess.run(['asar', 'extract', file_path, output_path], 
                      check=True, capture_output=True)
        print(f"✓ Extracted to {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to extract {file}")
        if debug_mode:
            print(f"Error: {e.stderr.decode()}")
        return False

class Decrypter:
    default_header_len = 16
    default_signature = "5250474d56000000"
    default_version = "000301"
    default_remain = "0000000000"

    @staticmethod
    def get_normal_png_header(length=16):
        png_header = bytes.fromhex('89 50 4E 47 0D 0A 1A 0A 00 00 00 0D 49 48 44 52')
        return png_header[:length]

    def __init__(self, encryption_key):
        self.encrypt_code = encryption_key
        self.encryption_code_array = self.split_encryption_code()
        self.ignore_fake_header = False
        self.header_len = None
        self.signature = None
        self.version = None
        self.remain = None
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
            raise Exception("Fake-Header doesn't match the Template-Fake-Header")

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
        for i in range(min(header_len, len(array_buffer))):
            if i < len(self.encryption_code_array):
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

        processed_count = 0
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_ext = os.path.splitext(file)[1]

                if file_ext in (file_types.keys() if operation == "decrypt" else file_types.values()):
                    orig_file_path = os.path.join(root, file)
                    new_file_ext = file_types.get(file_ext, file_ext)
                    new_file_name = os.path.splitext(file)[0] + new_file_ext
                    new_file_path = os.path.join(root, new_file_name)

                    try:
                        with open(orig_file_path, 'rb') as f:
                            content = f.read()

                        new_content = self.encrypt(content) if operation == "encrypt" else self.decrypt(content)

                        with open(new_file_path, 'wb') as f:
                            f.write(new_content)

                        if operation == "decrypt" and orig_file_path != new_file_path:
                            os.remove(orig_file_path)

                        processed_count += 1

                    except Exception as e:
                        print(f"Error processing {file}: {e}")

        print(f"✓ Processed {processed_count} file(s)")

def discover_rpgmakermz(directory):
    system_json_path = find_system_json(directory)
    if system_json_path:
        system_data = read_system_json(system_json_path)
        encryption_key = system_data.get('encryptionKey', None)

        if encryption_key:
            print(f"Found RPGMaker MZ project with encryption")
            decrypter = Decrypter(encryption_key)

            mz_types = {
                '.png_': '.png',
                '.ogg_': '.ogg',
                '.m4a_': '.m4a'
            }

            processed = 0
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if any(file.endswith(ext) for ext in mz_types.keys()):
                        file_path = os.path.join(root, file)
                        new_ext = mz_types.get(os.path.splitext(file)[1], '')
                        new_path = os.path.splitext(file_path)[0] + new_ext

                        try:
                            with open(file_path, 'rb') as f:
                                content = f.read()
                            decrypted = decrypter.decrypt(content)
                            with open(new_path, 'wb') as f:
                                f.write(decrypted)
                            os.remove(file_path)
                            processed += 1
                        except Exception as e:
                            print(f"Error processing {file}: {e}")

            print(f"✓ Decrypted {processed} MZ file(s)")
        else:
            print("No encryption found in MZ project")
    else:
        print("Not a valid RPGMaker MZ project (System.json not found)")

def discover_gamemaker(directory):
    data_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file == "data.win" or file.endswith(".win"):
                data_files.append(os.path.join(root, file))

    if not data_files:
        print("No GameMaker data files found.")
        return

    print(f"Found {len(data_files)} GameMaker data file(s)")
    print("GameMaker extraction requires UndertaleModTool.")
    print("Please download from: https://github.com/krzys-h/UndertaleModTool")

def discover_godot(directory):
    pck_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".pck"):
                file_path = os.path.join(root, file)
                if is_godot_pck(file_path):
                    pck_files.append(file_path)
            elif file.endswith(".exe"):

                file_path = os.path.join(root, file)
                if is_godot_pck(file_path):
                    pck_files.append(file_path)

    if not pck_files:
        print("No Godot PCK files found.")
        return

    print(f"Found {len(pck_files)} Godot PCK file(s)")

    print("Extracting Godot assets...")
    for pck_file in pck_files:
        print(f"\nExtracting {os.path.basename(pck_file)}...")
        extract_godot_pck_builtin(pck_file)

def is_godot_pck(file_path):
    try:
        with open(file_path, 'rb') as f:

            magic = f.read(4)
            if magic == b'GDPC':
                return True

            f.seek(-4, 2)
            magic = f.read(4)
            if magic == b'GDPC':
                return True

            f.seek(0)
            data = f.read(1024)
            if b'GDPC' in data:
                return True

        return False
    except:
        return False

def extract_godot_pck_builtin(pck_path):
    output_dir = os.path.splitext(pck_path)[0] + "_extracted"
    os.makedirs(output_dir, exist_ok=True)

    try:
        with open(pck_path, 'rb') as f:

            f.seek(0)
            data = f.read(4)
            pck_start = 0

            if data != b'GDPC':

                f.seek(-12, 2)  
                footer = f.read(12)
                if footer[8:12] == b'GDPC':
                    pck_start = struct.unpack('<Q', footer[0:8])[0]
                    f.seek(pck_start)
                    data = f.read(4)
                else:
                    print(f"✗ Not a valid Godot PCK file")
                    return False

            version = struct.unpack('<I', f.read(4))[0]
            major = struct.unpack('<I', f.read(4))[0]
            minor = struct.unpack('<I', f.read(4))[0]
            patch = struct.unpack('<I', f.read(4))[0]

            print(f"  Godot version: {major}.{minor}.{patch}")

            f.seek(16 * 4, 1)

            file_count = struct.unpack('<I', f.read(4))[0]
            print(f"  Files in PCK: {file_count}")

            files_info = []

            for i in range(file_count):

                path_len = struct.unpack('<I', f.read(4))[0]

                path = f.read(path_len).decode('utf-8')

                file_offset = struct.unpack('<Q', f.read(8))[0]
                file_size = struct.unpack('<Q', f.read(8))[0]

                f.read(16)

                files_info.append({
                    'path': path,
                    'offset': file_offset + pck_start,
                    'size': file_size
                })

            extracted_count = 0
            for file_info in files_info:
                try:
                    f.seek(file_info['offset'])
                    file_data = f.read(file_info['size'])

                    output_path = os.path.join(output_dir, file_info['path'].replace('res://', ''))
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)

                    if output_path.endswith('.stex'):

                        png_path = output_path.replace('.stex', '.png')
                        if convert_stex_to_png(file_data, png_path):
                            extracted_count += 1
                            continue

                    with open(output_path, 'wb') as out_f:
                        out_f.write(file_data)
                    extracted_count += 1

                except Exception as e:
                    if debug_mode:
                        print(f"    Error extracting {file_info['path']}: {e}")

            print(f"  ✓ Extracted {extracted_count} files to {output_dir}")

            process_godot_imports(output_dir)

            return True

    except Exception as e:
        print(f"✗ Failed to extract {os.path.basename(pck_path)}: {e}")
        return False

def convert_stex_to_png(stex_data, output_path):
    try:

        offset = 0

        png_sig = b'\x89PNG\r\n\x1a\n'
        png_start = stex_data.find(png_sig)

        if png_start != -1:

            with open(output_path, 'wb') as f:
                f.write(stex_data[png_start:])
            return True

        webp_sig = b'RIFF'
        webp_start = stex_data.find(webp_sig)

        if webp_start != -1 and stex_data[webp_start+8:webp_start+12] == b'WEBP':

            webp_path = output_path.replace('.png', '.webp')
            with open(webp_path, 'wb') as f:
                f.write(stex_data[webp_start:])

            if PIL_AVAILABLE:
                try:
                    img = Image.open(webp_path)
                    img.save(output_path, 'PNG')
                    os.remove(webp_path)
                    return True
                except:

                    return True
            else:

                if debug_mode:
                    print(f"    WebP found but Pillow not available for conversion")
                return True

        raw_path = output_path.replace('.png', '.stex')
        with open(raw_path, 'wb') as f:
            f.write(stex_data)

        return False

    except Exception as e:
        if debug_mode:
            print(f"    Error converting STEX: {e}")
        return False

def process_godot_imports(directory):
    import_files = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.import'):
                import_files.append(os.path.join(root, file))

    if not import_files:
        return

    print(f"\n  Processing {len(import_files)} import files...")

    recovered = 0
    for import_file in import_files:
        try:

            with open(import_file, 'r', encoding='utf-8') as f:
                content = f.read()

            for line in content.split('\n'):
                if line.startswith('source_file='):
                    source = line.split('=', 1)[1].strip('"')
                    source = source.replace('res://', '')

                    source_path = os.path.join(directory, source)
                    if os.path.exists(source_path):

                        dest_path = import_file[:-7]  
                        if not os.path.exists(dest_path):
                            shutil.copy2(source_path, dest_path)
                            recovered += 1
                    break

        except Exception as e:
            if debug_mode:
                print(f"    Error processing import: {e}")

    if recovered > 0:
        print(f"  ✓ Recovered {recovered} original files from imports")

def convert_godot_textures(directory):
    converted = 0

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.stex') or file.endswith('.tex'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'rb') as f:
                        data = f.read()

                    output_path = file_path.replace('.stex', '.png').replace('.tex', '.png')
                    if convert_stex_to_png(data, output_path):
                        converted += 1

                        os.remove(file_path)
                except Exception as e:
                    if debug_mode:
                        print(f"Error converting {file}: {e}")

    if converted > 0:
        print(f"  ✓ Converted {converted} textures to viewable format")

def discover_rpgmakervxace(directory):
    rgss_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith((".rgss3a", ".rgss2a", ".rgssad")):
                rgss_files.append(os.path.join(root, file))

    if not rgss_files:
        print("No RPGMaker VX Ace archives found.")
        return

    print(f"Found {len(rgss_files)} RGSS archive(s)")

    for rgss_file in rgss_files:
        print(f"Extracting {os.path.basename(rgss_file)}...")
        extract_rgss(rgss_file)

def extract_rgss(rgss_path):
    output_dir = os.path.splitext(rgss_path)[0] + "_extracted"

    try:
        subprocess.run(['rvpacker', '-x', rgss_path, '-o', output_dir], 
                      check=True, capture_output=True)
        print(f"✓ Extracted to {output_dir}")
        return True
    except subprocess.CalledProcessError:
        print(f"✗ Failed to extract {os.path.basename(rgss_path)}")
        print("Make sure rvpacker is installed: gem install rvpacker")
        return False

def discover_construct(directory):
    construct_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file in ["data.js", "data.json", "project.c3proj", "project.capx"]:
                construct_files.append(os.path.join(root, file))

    if construct_files:
        print(f"Found Construct project files:")
        for f in construct_files:
            print(f"  - {f}")
        print("\nConstruct projects are typically already in readable format.")
        print("Assets are usually in the 'images' and 'media' folders.")
    else:
        print("No Construct project files found.")

def discover_ue3(directory):
    ue3_files = []
    ue3_extensions = ('.upk', '.u', '.umap', '.ut3', '.xxx')

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(ue3_extensions):
                ue3_files.append(os.path.join(root, file))

    if not ue3_files:
        print("No Unreal Engine 3 packages found.")
        return

    print(f"Found {len(ue3_files)} UE3 package(s)")

    if shutil.which('umodel') is None:
        print("\nUModel is required for UE3 extraction.")
        print("Please download from: https://www.gildor.org/en/projects/umodel")
        return

    for upk_file in ue3_files:
        print(f"Extracting {os.path.basename(upk_file)}...")
        extract_ue_package(upk_file, 'ue3')

def discover_ue4(directory):
    pak_files = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.pak'):
                file_path = os.path.join(root, file)
                if is_ue4_pak(file_path):
                    pak_files.append(file_path)

    if not pak_files:
        print("No Unreal Engine 4 PAK files found.")
        return

    print(f"Found {len(pak_files)} UE4 PAK file(s)")

    if shutil.which('umodel') is None:
        print("\nUModel is required for UE4 extraction.")
        print("Please download from: https://www.gildor.org/en/projects/umodel")
        return

    for pak_file in pak_files:
        print(f"Extracting {os.path.basename(pak_file)}...")
        extract_ue_package(pak_file, 'ue4')

def discover_ue5(directory):
    ue5_files = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.pak', '.ucas', '.utoc')):
                file_path = os.path.join(root, file)

                if file.lower().endswith('.ucas'):
                    utoc_file = file_path.replace('.ucas', '.utoc')
                    if os.path.exists(utoc_file):
                        ue5_files.append(file_path)
                elif file.lower().endswith('.pak') and is_ue5_pak(file_path):
                    ue5_files.append(file_path)

    if not ue5_files:
        print("No Unreal Engine 5 packages found.")
        return

    print(f"Found {len(ue5_files)} UE5 package(s)")

    if shutil.which('umodel') is None:
        print("\nUModel is required for UE5 extraction.")
        print("Please download from: https://www.gildor.org/en/projects/umodel")
        print("Make sure to use a recent version that supports UE5.")
        return

    for ue5_file in ue5_files:
        print(f"Extracting {os.path.basename(ue5_file)}...")
        extract_ue_package(ue5_file, 'ue5')

def discover_wolf(directory):
    wolf_files = []
    data_folders = []

    for root, dirs, files in os.walk(directory):

        for file in files:
            if file.lower() in ['data.wolf', 'game.dat', 'game.exe']:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'rb') as f:
                        header = f.read(1024)
                        if b'wolf' in header.lower() or b'data.wolf' in header.lower():
                            wolf_files.append(file_path)
                except:
                    pass

        if 'Data' in dirs:
            data_path = os.path.join(root, 'Data')
            if os.path.exists(os.path.join(data_path, 'BasicData')):
                data_folders.append(data_path)

    if not wolf_files and not data_folders:
        print("No Wolf RPG game files found.")
        return

    print(f"Found Wolf RPG game")

    if data_folders:
        print("\nFound unencrypted Data folders:")
        for folder in data_folders:
            print(f"  - {folder}")
        print("\nThese appear to be already extracted.")

    if wolf_files:
        print(f"\nFound {len(wolf_files)} encrypted Wolf RPG file(s)")

        if shutil.which('arc_unpacker'):
            print("Using arc_unpacker...")
            for wolf_file in wolf_files:
                extract_wolf_arc_unpacker(wolf_file)
        else:
            print("\nWolf RPG extraction requires specialized tools:")
            print("1. arc_unpacker: https://github.com/vn-tools/arc_unpacker")
            print("2. GARbro: https://github.com/morkt/GARbro")
            print("3. DXExtract: Search for 'Wolf RPG DXExtract'")

def is_ue4_pak(file_path):
    try:
        with open(file_path, 'rb') as f:

            f.seek(-44, 2)  
            magic = f.read(4)
            if magic == b'\x00\x00\x00\x00':  
                return True
            f.seek(-204, 2)  
            data = f.read(204)

            return b'FPakInfo' in data or data[-4:] == b'\x5A\x6F\x12\xF1'
    except:
        return False

def is_ue5_pak(file_path):
    try:
        with open(file_path, 'rb') as f:

            f.seek(0)
            header = f.read(1024)

            return b'UnrealPak' in header or b'IoStore' in header
    except:
        return False

def extract_ue_package(package_path, engine_version):
    base_name = os.path.splitext(os.path.basename(package_path))[0]
    output_dir = os.path.join(os.path.dirname(package_path), f'UE_{base_name}_extracted')

    cmd = ['umodel', '-export', '-out=' + output_dir]

    if engine_version == 'ue3':
        cmd.extend(['-3rdparty', '-sounds', '-tex=tga'])
    elif engine_version == 'ue4':
        cmd.extend(['-game=ue4', '-tex=png', '-sound'])
    elif engine_version == 'ue5':
        cmd.extend(['-game=ue5', '-tex=png', '-sound'])

    cmd.append(package_path)

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✓ Extracted to {output_dir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to extract {os.path.basename(package_path)}")
        if debug_mode:
            print(f"Error: {e.stderr.decode()}")
        return False

def extract_ue4_pak_unrealpak(pak_path):
    base_name = os.path.splitext(os.path.basename(pak_path))[0]
    output_dir = os.path.join(os.path.dirname(pak_path), f'UE4_{base_name}_extracted')

    response_file = f"{pak_path}.response.txt"
    with open(response_file, 'w') as f:
        f.write(f'"{pak_path}" -Extract "{output_dir}"')

    try:
        subprocess.run(['UnrealPak', response_file], check=True, capture_output=True)
        os.remove(response_file)
        print(f"✓ Extracted to {output_dir}")
        return True
    except subprocess.CalledProcessError:
        os.remove(response_file)
        print(f"✗ Failed with UnrealPak, trying UModel...")
        return extract_ue_package(pak_path, 'ue4')

def extract_wolf_arc_unpacker(wolf_file):
    base_name = os.path.splitext(os.path.basename(wolf_file))[0]
    output_dir = os.path.join(os.path.dirname(wolf_file), f'Wolf_{base_name}_extracted')

    try:
        subprocess.run(['arc_unpacker', '--fmt=wolf/wolf', wolf_file, '-o', output_dir], 
                      check=True, capture_output=True)
        print(f"✓ Extracted to {output_dir}")
        return True
    except subprocess.CalledProcessError:
        print(f"✗ Failed to extract {os.path.basename(wolf_file)}")
        return False

def find_system_json(directory):
    if debug_mode:
        print(f"Searching for System.json in: {directory}")

    for root, dirs, files in os.walk(directory):
        if "System.json" in files:
            full_path = os.path.join(root, "System.json")
            if debug_mode:
                print(f"Found System.json at: {full_path}")
            return full_path

    if debug_mode:
        print("System.json not found.")
    return None

def read_system_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error reading System.json: {e}")
        return None

def detect_game_engine(directory):
    indicators = {
        'rpgmakermv': ['System.json', 'Game.rpgproject'],
        'rpgmakermz': ['System.json', 'Game.rmmzproject'],
        'rpgmakervxace': ['.rgss3a', 'Game.rgss3a'],
        'renpy': ['.rpa', 'renpy'],
        'unity': ['UnityPlayer.dll', 'unity.default.company'],
        'electron': ['.asar', 'electron.exe'],
        'godot': ['.pck', 'godot'],
        'gamemaker': ['data.win', 'options.ini'],
        'construct': ['data.js', 'project.c3proj'],
        'ue3': ['.upk', '.u', '.umap'],
        'ue4': ['.pak', 'Engine/Binaries'],
        'ue5': ['.ucas', '.utoc', '.pak'],
        'wolf': ['Data.wolf', 'Game.dat', 'Data/BasicData']
    }

    detected = []
    for engine, files in indicators.items():
        for root, dirs, filenames in os.walk(directory):

            extensions = [ind for ind in files if ind.startswith('.')]
            if extensions and any(any(f.endswith(ext) for f in filenames) for ext in extensions):

                if engine == 'ue4' and any(f.endswith('.pak') for f in filenames):
                    pak_files = [os.path.join(root, f) for f in filenames if f.endswith('.pak')]
                    if any(is_ue4_pak(p) for p in pak_files):
                        detected.append(engine)
                        break
                elif engine == 'ue5' and (any(f.endswith('.ucas') for f in filenames) or 
                                        any(f.endswith('.pak') for f in filenames)):
                    if any(f.endswith('.ucas') for f in filenames):
                        detected.append(engine)
                        break
                    pak_files = [os.path.join(root, f) for f in filenames if f.endswith('.pak')]
                    if any(is_ue5_pak(p) for p in pak_files):
                        detected.append(engine)
                        break
                else:
                    detected.append(engine)
                    break

            non_extensions = [ind for ind in files if not ind.startswith('.')]
            if any(ind in filenames or ind in dirs for ind in non_extensions):
                detected.append(engine)
                break

    return list(set(detected))  

def parse_args():
    parser = argparse.ArgumentParser(
        description='Extract and decrypt game assets from various engines.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported game engines:
  rpgmakermv     - RPGMaker MV projects
  rpgmakermz     - RPGMaker MZ projects  
  rpgmakervxace  - RPGMaker VX/VX Ace (requires rvpacker)
  electron       - Electron/node-webkit apps
  renpy          - Ren'Py visual novels
  unity          - Unity games
  ue3            - Unreal Engine 3 games
  ue4            - Unreal Engine 4 games  
  ue5            - Unreal Engine 5 games
  wolf           - Wolf RPG Editor games
  gamemaker      - GameMaker Studio games
  godot          - Godot engine games
  construct      - Construct 2/3 games
  auto           - Auto-detect engine type

Examples:
  %(prog)s -d /path/to/game --type auto
  %(prog)s -d /path/to/game --type rpgmakermv -o decrypt
  %(prog)s -d /path/to/game --type ue4 --debug
  %(prog)s -d /path/to/game --type wolf
        """
    )

    parser.add_argument('-d', '--directory', type=str, required=True, 
                       help='Directory containing the game files')
    parser.add_argument('-o', '--operation', type=str, choices=['encrypt', 'decrypt'], 
                       default='decrypt', help='Operation to perform (default: decrypt)')
    parser.add_argument('--debug', help='Enable debug output', action='store_true')
    parser.add_argument('--type', help='Game engine type', required=True,
                       choices=['rpgmakermv', 'rpgmakermz', 'rpgmakervxace', 
                               'electron', 'renpy', 'unity', 'ue3', 'ue4', 'ue5',
                               'wolf', 'gamemaker', 'godot', 'construct', 'auto'])

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    directory = args.directory
    operation = args.operation
    debug_mode = args.debug
    engine_type = args.type

    print(f"Game Asset Extractor v3.0")
    print(f"========================")
    print(f"Directory: {directory}")
    print(f"Engine: {engine_type}")
    print(f"Operation: {operation}")
    if debug_mode:
        print(f"Debug: ENABLED")
    if UNITYPY_AVAILABLE:
        print(f"UnityPy: Available")
    if PIL_AVAILABLE:
        print(f"Pillow: Available (better image conversion)")
    print()

    if engine_type == 'auto':
        detected = detect_game_engine(directory)
        if not detected:
            print("Could not auto-detect game engine.")
            print("Please specify engine type manually.")
            sys.exit(1)
        elif len(detected) == 1:
            engine_type = detected[0]
            print(f"Auto-detected engine: {engine_type}\n")
        else:
            print(f"Multiple engines detected: {', '.join(detected)}")
            engine_type = detected[0]
            print(f"Using: {engine_type}\n")

    check_dependencies()

    try:
        if engine_type == 'rpgmakermv':
            system_json_path = find_system_json(directory)
            if system_json_path:
                system_data = read_system_json(system_json_path)
                if system_data:
                    encryption_key = system_data.get('encryptionKey', None)
                    if encryption_key:
                        print(f"Encryption key found: {encryption_key[:8]}...")
                        decrypter = Decrypter(encryption_key)
                        decrypter.process_directory(directory, operation)
                    else:
                        print("No encryption key found. Files may not be encrypted.")
            else:
                print("System.json not found. Not a valid RPGMaker MV project.")

        elif engine_type == 'rpgmakermz':
            discover_rpgmakermz(directory)

        elif engine_type == 'rpgmakervxace':
            discover_rpgmakervxace(directory)

        elif engine_type == 'electron':
            discover_asar(directory)

        elif engine_type == 'renpy':
            discover_rpa(directory)

        elif engine_type == 'unity':
            discover_unity_files(directory)

        elif engine_type == 'ue3':
            discover_ue3(directory)

        elif engine_type == 'ue4':
            discover_ue4(directory)

        elif engine_type == 'ue5':
            discover_ue5(directory)

        elif engine_type == 'wolf':
            discover_wolf(directory)

        elif engine_type == 'gamemaker':
            discover_gamemaker(directory)

        elif engine_type == 'godot':
            discover_godot(directory)

        elif engine_type == 'construct':
            discover_construct(directory)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        if debug_mode:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    print("\nDone!")
