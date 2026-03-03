# b4m-necromancer Troubleshooting

## Check service status

```bash
sudo systemctl status scanner_service.service
```

## Check logs

```bash
tail -f /var/log/scanner/scanner.log
```

## Run scripts manually

```bash
# Interactive mode (run the installed ~/app directly)
python3 ~/app/keypad_scanner.py

# Daemon-like mode
python3 ~/app/keypad_daemon.py
```

## Specify device path

If you want to use a specific keypad device:

```bash
python3 ~/app/keypad_daemon.py --device /dev/input/event0
```

----------

Done.

