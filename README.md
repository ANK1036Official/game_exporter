
## Introduction
`game_exporter` is a game decryption tool designed for extracting assets such as images, code, sound, and more from various common game types.

Currently, this is `Linux only`, but there are future plans to add Windows support.


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
python3 main.py --help

# Do the thing
python3 main.py -d ./some_game/ -o decrypt --type type_here
```

## Supported Game Types

- [x] RPGMaker MV
- [x] Electron based games
- [x] RenPy
- [x] Unity
- [ ] Unreal Engine 3
- [ ] Unreal Engine 4
- [ ] Unreal Engine 5
- [ ] Wolf RPG

## Roadmap

- Add support for Unreal Engine (versions 3, 4, 5)
- Add support for Wolf RPG
- (???)
- Add Windows support.

## Acknowledgments

The RPGMaker code in this project is based off of Petschko's RPG Maker Decryption tool.

