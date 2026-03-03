#!/bin/bash
# Installation script for the document scanner system.
#
# This script deploys files from the repository's app directory
# into the runtime directory ($HOME/app) and sets up a systemd service.

set -e

APP_SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DST_DIR="$HOME/app"

echo "Installing required packages..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-evdev sane-utils

echo "Creating Python virtual environment..."
mkdir -p "$APP_DST_DIR"
python3 -m venv "${APP_DST_DIR}/venv"

echo "Installing Python packages into virtual environment..."
"${APP_DST_DIR}/venv/bin/pip" install --upgrade pip
"${APP_DST_DIR}/venv/bin/pip" install -r "${APP_SRC_DIR}/requirements.txt"

echo "Deploying application files to ${APP_DST_DIR}..."
mkdir -p "$APP_DST_DIR"
cp -r "${APP_SRC_DIR}/"* "$APP_DST_DIR/"

echo "Creating log directory..."
sudo mkdir -p /var/log/scanner
sudo chown $USER:$USER /var/log/scanner

echo "Creating temporary directory for scans..."
mkdir -p "$APP_DST_DIR/tmp"

echo "Installing systemd service..."
# Copy service file (treated as a template)
sudo cp "$APP_DST_DIR/scanner_service.service" /etc/systemd/system/

# Replace template placeholders with current user and app path
sudo sed -i "s/User=__USER__/User=$USER/g" /etc/systemd/system/scanner_service.service
sudo sed -i "s/Group=__USER__/Group=$USER/g" /etc/systemd/system/scanner_service.service
sudo sed -i "s|WorkingDirectory=__APP_WORKDIR__|WorkingDirectory=${APP_DST_DIR}|g" /etc/systemd/system/scanner_service.service
sudo sed -i "s|ExecStart=/usr/bin/python3 __APP_WORKDIR__/keypad_daemon.py|ExecStart=${APP_DST_DIR}/venv/bin/python ${APP_DST_DIR}/keypad_daemon.py|g" /etc/systemd/system/scanner_service.service

echo "Adding convenient CLI alias (necro) to shell config..."
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$rc" ]; then
        if ! grep -q "b4m-necromancer: CLI aliases" "$rc"; then
            cat >> "$rc" <<'EOF'
# b4m-necromancer: CLI aliases
alias necro="$HOME/app/venv/bin/python -m app.lib.scan"
EOF
            echo "Alias added to $rc"
        else
            echo "Alias already present in $rc"
        fi
    fi
done

echo "Making scripts executable..."
chmod +x "${APP_DST_DIR}/keypad_daemon.py"
chmod +x "${APP_DST_DIR}/lib/scan.py"

echo "Enabling systemd service..."
sudo systemctl daemon-reload
sudo systemctl enable scanner_service.service

echo "Installation finished!"
echo "To start the service: sudo systemctl start scanner_service.service"
echo "To check status:      sudo systemctl status scanner_service.service"
echo ""
echo "Start the service now? [y/N]"
read start_service

if [[ "$start_service" == "y" || "$start_service" == "Y" ]]; then
    echo "Starting service..."
    sudo systemctl start scanner_service.service
    echo "Service status:"
    sudo systemctl status scanner_service.service
else
    echo "Service was not started. You can start it manually later."
fi

echo "Setup complete!"