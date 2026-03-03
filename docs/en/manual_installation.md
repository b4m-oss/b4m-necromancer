# b4m-necromancer Manual Installation

1. Install required packages

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-evdev sane-utils
pip3 install evdev pillow
```

2. Create log directory

```bash
sudo mkdir -p /var/log/scanner
sudo chown $USER:$USER /var/log/scanner
```

3. Deploy application files

```bash
git clone https://github.com/b4m-oss/b4m-necromancer.git ~/b4m-necromancer
mkdir -p ~/app
cp -r ~/b4m-necromancer/app/* ~/app/
mkdir -p ~/app/tmp
```

4. Set up systemd service

```bash
sudo cp ~/b4m-necromancer/app/scanner_service.service /etc/systemd/system/

# Adjust user / group / working directory for your environment
sudo sed -i "s/User=kohki/User=$USER/g" /etc/systemd/system/scanner_service.service
sudo sed -i "s/Group=kohki/Group=$USER/g" /etc/systemd/system/scanner_service.service
sudo sed -i "s|WorkingDirectory=/home/kohki/app|WorkingDirectory=/home/$USER/app|g" /etc/systemd/system/scanner_service.service
sudo sed -i "s|ExecStart=/home/kohki/myscan/bin/python3 /home/kohki/app/keypad_daemon.py|ExecStart=/usr/bin/python3 /home/$USER/app/keypad_daemon.py|g" /etc/systemd/system/scanner_service.service
sudo sed -i '/^Environment="PYTHONPATH=/d' /etc/systemd/system/scanner_service.service
```

5. Make scripts executable

```bash
chmod +x ~/b4m-necromancer/app/keypad_daemon.py
chmod +x ~/b4m-necromancer/app/lib/scan.py
```

6. Enable and start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable scanner_service.service
sudo systemctl start scanner_service.service
```

-------

Done.

