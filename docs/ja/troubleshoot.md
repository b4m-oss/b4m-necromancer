# b4m-necromancer トラブルシューティング

## サービスの状態確認

```bash
sudo systemctl status scanner_service.service
```

## ログの確認

```bash
tail -f /var/log/scanner/scanner.log
```

## 手動実行

```bash
# 対話モード（インストール済みの ~/app を直接実行）
python3 ~/app/keypad_scanner.py

# デーモンモード
python3 ~/app/keypad_daemon.py
```

## デバイスパスの指定

特定のテンキーパッドを使用する場合：

```bash
python3 ~/app/keypad_daemon.py --device /dev/input/event0
```

----------

以上