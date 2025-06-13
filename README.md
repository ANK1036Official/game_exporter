## Introduction
`game_exporter` is a game decryption tool designed for extracting assets such as images, code, sound, and more from various common game types.
Currently, this is `Linux only`, but there are future plans to add Windows support.

Note: If the 2025 version does not work properly, please downgrade to the 0.0.3 release, which only supports:
- RPGMaker MV
- Electron based games
- RenPy
- Unity

## Installation
Instructions for how to install the tool.
```bash
# First install asar
npm install -g asar
# Then download the repo.
git clone https://github.com/yourusername/game_exporter.git
cd game_exporter
# Lastly, install the requirements.txt dependencies
pip install -r requirements.txt
```

## Usage
```bash
# Check the help
python3 game_exporter.py --help
# Do the thing
python3 game_exporter.py -d ./some_game/ -o decrypt --type type_here
```

## Supported Game Types
- [x] RPGMaker MV
- [x] RPGMaker MZ
- [x] RPGMaker VX/VX Ace
- [x] Electron based games
- [x] RenPy
- [x] Unity
- [x] Unreal Engine 3
- [x] Unreal Engine 4
- [ ] Unreal Engine 5
- [x] Wolf RPG
- [x] Godot
- [x] Construct 2/3
- [x] GameMaker Studio

## Roadmap
- Add GUI interface
- Add Windows support
- Add macOS support

## Acknowledgments
The RPGMaker code in this project is based off of Petschko's RPG Maker Decryption tool.

### Tools that cannot be installed via pip:

1. **asar** (for Electron games): `npm install -g asar`

2. **rvpacker** (for RPGMaker VX/VX Ace) - Install with Ruby: `gem install rvpacker`

3. **umodel** (for Unreal Engine 3/4) - Manual download from: https://www.gildor.org/en/projects/umodel

4. **arc_unpacker** (for Wolf RPG) - Build from source:
   ```bash
   git clone https://github.com/vn-tools/arc_unpacker
   cd arc_unpacker
   mkdir build && cd build
   cmake ..
   make
   sudo make install
   ```

Note: The script will auto-download some tools like AssetRipper (for Unity) and godotpcktool (for Godot) when needed.
