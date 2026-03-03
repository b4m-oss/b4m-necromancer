# b4m-necromancer - revive your old scanner with Raspberry Pi ZERO 2

[日本語版](./README_ja.md)

This system is a small solution to automate document scanning from a numeric keypad.  
By pressing a number key on the keypad and then Enter, you can trigger different scan modes.

## Motivation

Bring EOL (end-of-life) scanners back to life with OSS.

The author used a Fujitsu ScanSnap iX500. At some point, the official iOS app support was dropped.  
Because uploading scanned documents over Wi-Fi was still an essential workflow, various alternatives were explored.  
As a result, SANE was discovered, and the idea came up to drive the scanner from a Raspberry Pi Zero 2 over the network.

## What does it do?

- Keep using a scanner that has lost official software support.
- Automatically upload scanned documents to a cloud service.
- Prepare fine-grained presets for different scan modes.
- Operate everything from a numeric keypad.

## Required hardware

- Raspberry Pi Zero 2W (or another Raspberry Pi)
- ScanSnap iX500 (or another SANE-compatible scanner)
- Numeric keypad (USB or Bluetooth)

## Features

- Monitor input from a numeric keypad.
- Execute different scan modes per number key (diary, receipt, flyer).
- Automatically upload scanned documents to Nextcloud (via WebDAV).
- Start the keypad daemon automatically at system boot (systemd service).
- Log scan activity to a log file.


## Installation

### Automatic installation

In the following steps, we assume that the repository is cloned to `~/b4m-necromancer`.

1. Clone the repository on your Raspberry Pi.
2. Change into the `app` directory and run the install script.

```bash
git clone https://github.com/b4m-oss/b4m-necromancer.git ~/b4m-necromancer
cd ~/b4m-necromancer/app
chmod +x install.sh
./install.sh
```

### Manual installation

See [Manual installation](./docs/en/manual_installation.md)  
日本語版: [手動インストール](./docs/ja/manual_installation.md)

## Setup and configuration

See [Setup and configuration](./docs/en/setup_config.md)  
日本語版: [セットアップと設定](./docs/ja/setup_config.md)

## How to use

Once the system is running, the keypad daemon starts automatically and waits for input.  
Use the keypad as follows:

1. Press `1` on the keypad → Enter: scan with the mode mapped from `mode.json` `keybindings["1"]` (default: `diary`).
2. Press `2` on the keypad → Enter: scan with `keybindings["2"]` (default: `receipt`).
3. Press `3` on the keypad → Enter: scan with `keybindings["3"]` (default: `flyer`).

If you do not press Enter within 5 seconds after pressing a digit, the input buffer is cleared.  
Pressing another digit overwrites the previous one.

## Troubleshooting

See [Troubleshooting](./docs/en/troubleshoot.md)  
日本語版: [トラブルシューティング](./docs/ja/troubleshoot.md)

## License

This project is released under the MIT License. See the `LICENSE` file for details.


-------------

Developed by Kohki SHIKATA / B4M LLC. from Osaka with ❤️

