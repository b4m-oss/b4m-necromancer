# b4m-necromancer - revive your old scanner with Raspberry Pi ZERO 2

[English](./README.md)

このシステムは、テンキーパッドからの入力によってドキュメントスキャンを自動実行するためのソリューションです。
テンキーの数字を押してEnterを押すだけで、異なるモードでのスキャンが可能です。

## モチベーション

メーカーサポートの切れたスキャナを、OSSの力を使って蘇らせる。

開発者は、FujitsuのiX500を使っていましたが、ある時、iOSアプリのサポートが打ち切られました。
どうしてもWiFi下でリモートにファイルをアップデートしたかったため、様々な方策を考えました。
結果、SANEというライブラリを見つけ、これをRaspberry Pi ZERO 2で動かすことを思いついたのです。

## 何ができますか？

- サポートの切れたスキャナを継続して使用することができます
- 自動でクラウドサービスにスキャンした内容をアップロードすることができます
- 細かな設定を自分でプリセットとして用意することができます
- テンキー入力から操作を実行できます

## 必要なハードウェア

- Raspberry Pi Zero 2W（または他のRaspberry Pi）
- ScanSnap iX500スキャナー（または他のSANE対応スキャナー）
- テンキーパッド（USBまたはBluetooth接続）

## 機能

- テンキーパッドからの入力を監視
- 数字キーごとに異なるスキャンモードを実行（diary、receipt、flyer）
- スキャンした文書をNextcloudに自動アップロード
- システム起動時に自動的にサービス開始
- ログ出力による動作記録


## インストール方法

### 自動インストール

以下では、リポジトリを `~/b4m-necromancer` にクローンする前提で説明します。

1. Raspberry Pi 上でリポジトリをクローンします
2. `app` ディレクトリに移動してインストールスクリプトを実行します

```bash
git clone https://github.com/b4m-oss/b4m-necromancer.git ~/b4m-necromancer
cd ~/b4m-necromancer/app
chmod +x install.sh
./install.sh
```

### 手動インストール

[手動インストール](./docs/ja/manual_installation.md)を参照して下さい。

## セットアップと設定

[セットアップと設定](./docs/ja/setup_config.md)を参照して下さい。

## 使い方

システムを起動すると、テンキーパッドの監視が自動的に開始されます。以下の操作でスキャンを実行できます：

1. テンキーの「1」→ Enter：`mode.json` の `keybindings["1"]` で指定されたモード（デフォルト: diary）でスキャン
2. テンキーの「2」→ Enter：`keybindings["2"]` のモード（デフォルト: receipt）でスキャン
3. テンキーの「3」→ Enter：`keybindings["3"]` のモード（デフォルト: flyer）でスキャン

数字キーを押してから5秒以内にEnterを押さない場合、入力はクリアされます。また、別の数字キーを押すと入力は上書きされます。

## トラブルシューティング

[トラブルシューティング](./docs/ja/troubleshoot.md)を参照して下さい。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細はLICENSEファイルを参照してください。 


-------------

Developed by Kohki SHIKATA / B4M LLC. from Osaka with ❤️