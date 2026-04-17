# 追加クラウドサービス対応 設計メモ（Dropbox / Google Drive）

本ドキュメントは、b4m-necromancer に Nextcloud 以外のクラウドストレージ（Dropbox / Google Drive）を追加サポートする際の設計方針をまとめたものです。  
現時点では **実装は行わず、方針レベルの仕様書** として扱います。

---

## 1. 全体方針

- 既存の Nextcloud 実装と同様に、**「アップロード処理」はアダプタ層に閉じ込める**。
  - `scan.py` 側は「どのクラウドか」を意識しない。
  - 代わりに `upload_adapter.get_uploader_from_config()` から得たオブジェクトに対して、
    - `upload_directory(dir_path: str) -> bool`
    - `upload_file(file_path: str) -> bool`
    - `upload_pdf(pdf_path: str) -> bool`
    を呼ぶだけにする。
- 利用するクラウド（Nextcloud / Dropbox / Google Drive）は、
  - `~/app/config/upload.json` の `provider` フィールドで指定する。
- OAuth の認可フロー（ブラウザでのログインなど）は、**スキャナ本体コードから切り離し、専用のセットアップスクリプト（CLI ツール）で行う**。

---

## 2. 設定ファイル設計（upload.json 拡張）

### 2.1 現状

現状の `upload.json` は Nextcloud 前提:

```json
{
  "provider": "nextcloud",
  "nextcloud": {
    "endpoint": "https://your-nextcloud-server.com/remote.php/dav/files/username/",
    "username": "your_username",
    "password": "your_password",
    "upload_folder": "Scans/",
    "delete_after_upload": true
  }
}
```

### 2.2 将来の拡張イメージ

Dropbox / Google Drive を含める場合の例（あくまでイメージ・未確定）:

```json
{
  "provider": "gdrive",

  "nextcloud": {
    "endpoint": "https://your-nextcloud-server.com/remote.php/dav/files/username/",
    "username": "your_username",
    "password": "your_password",
    "upload_folder": "Scans/",
    "delete_after_upload": true
  },

  "dropbox": {
    "app_key": "DROPBOX_APP_KEY",
    "app_secret": "DROPBOX_APP_SECRET",
    "access_token": "short_lived_access_token_optional",
    "refresh_token": "long_lived_refresh_token",
    "upload_folder": "/Scans",
    "delete_after_upload": true
  },

  "gdrive": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "client_secret": "YOUR_CLIENT_SECRET",
    "access_token": "short_lived_access_token_optional",
    "refresh_token": "long_lived_refresh_token",
    "token_uri": "https://oauth2.googleapis.com/token",
    "folder_id": "google_drive_folder_id",
    "delete_after_upload": true
  }
}
```

- 実際のキー名・構造は、各クラウドの Python SDK / API 仕様を確認した上で最終決定する（**現時点ではイメージレベル**）。
- `provider` が `"nextcloud" / "dropbox" / "gdrive"` のいずれかになり、  
  `upload_adapter` 側がそれに応じて適切な Uploader を返す。

---

## 3. アップロードアダプタ層の拡張

### 3.1 現状

- `app/lib/upload_adapter.py` にて:
  - `NextcloudUploader` クラス
  - `get_uploader_from_config()` が実装済み。
- `scan.py` は、`get_uploader_from_config()` の戻り値に対して:
  - `upload_directory(...)`
  - `upload_file(...)`
  - `upload_pdf(...)`
 だけを呼び出している。

### 3.2 追加予定のクラス

1. `DropboxUploader`
   - 役割:
     - Dropbox API を使って `upload_directory / upload_file / upload_pdf` を実装。
     - 必要に応じて、`refresh_token` から `access_token` を更新する。
   - 実装候補:
     - 公式 SDK (`dropbox` パッケージ) を利用するか、HTTP ベースで自前実装するかは要検討（**未確定**）。

2. `GoogleDriveUploader`
   - 役割:
     - Google Drive API を使って `upload_directory / upload_file / upload_pdf` を実装。
     - `refresh_token` によるアクセストークン更新を内部で行う。
   - 実装候補:
     - `google-api-python-client` + `google-auth` などを利用する方向が有力（**未確定**）。

3. `get_uploader_from_config()` の拡張

```python
def get_uploader_from_config():
    raw = _load_upload_config_raw()
    provider = raw.get("provider", "nextcloud")

    if provider == "nextcloud":
        return NextcloudUploader()
    if provider == "dropbox":
        return DropboxUploader(raw.get("dropbox", {}))
    if provider == "gdrive":
        return GoogleDriveUploader(raw.get("gdrive", {}))

    print(f"Warning: unsupported provider specified: {provider}. Falling back to Nextcloud.")
    return NextcloudUploader()
```

- 具体的な引数（設定 dict の形）やエラー処理は、実装時に詰める。

---

## 4. OAuth / 認可フローの扱い

### 4.1 基本方針

- **スキャナ本体（daemon / scan.py）は OAuth の認可フローを一切持たない**。
- OAuth 認可は、**別のセットアップスクリプトで行う**。
  - 例:
    - `tools/setup_dropbox_oauth.py`
    - `tools/setup_gdrive_oauth.py`
  - これらは「対話的 CLI ツール」として実装する想定。

### 4.2 セットアップスクリプトの役割（イメージ）

1. 必要なクレデンシャル（`app_key`, `client_id` など）を対話的に受け取るか、  
   もしくは別ファイルから読む。
2. Dropbox / Google の OAuth エンドポイントに対し、認可 URL を生成。
3. ユーザーに「この URL をブラウザで開いて認可してください」「認可コードをここに貼ってください」と案内。
4. 取得した認可コードを使ってトークンエンドポイントにリクエストし、
   - `access_token`
   - `refresh_token`
   を取得。
5. それらのトークンを `upload.json` の該当セクション（`dropbox` / `gdrive`）に保存する。

> 備考:  
> Raspberry Pi 上にブラウザが無い場合、**デバイスフロー**（特に Google Drive）を利用する設計も検討対象。  
> この場合、端末側では「ブラウザで URL を開いてコードを入力してください」と表示するだけでよい。

---

## 5. ランタイムでのトークン管理

- ランタイム（`DropboxUploader` / `GoogleDriveUploader`）は、以下を責務とする:
  - `upload_*` 呼び出し時に、有効なアクセストークンがあるか確認。
  - 有効期限切れであれば、`refresh_token` を用いてトークンを更新。
  - 更新に失敗した場合:
    - ログに詳細を出力。
    - アップロードは失敗として呼び出し元に `False` を返す。
    - ローカルファイルは削除しない（安全側）。
- トークン更新結果の永続化（`upload.json` に新アクセストークンを書き戻すかどうか）は、実装時に要検討（**未確定**）。

---

## 6. セキュリティ・運用ポリシー

- `upload.json` は既に `.gitignore` 済みとし、**Git 管理しない**。
- 必要であれば、クレデンシャル専用の `upload.secrets.json` などを用意し、
  - `upload.json` にはプロバイダー種別やフォルダ ID など非機微情報のみ記録
  - 機微情報（`client_secret`, `refresh_token` など）は別ファイルに分離
  する案も検討可（**未確定**）。
- アップロード失敗時は:
  - エラー内容をログ出力。
  - ローカル側のスキャンデータは削除しない。

---

## 7. 実装ステップ案（まだ着手しない）

1. `upload.json` のスキーマ定義を README / docs に追加（「Dropbox / GDrive セクションは将来追加予定」として）。
2. `upload_adapter.py` に `DropboxUploader` / `GoogleDriveUploader` クラスの骨格を追加（中身は TODO のままでもよい）。
3. OAuth 設定用 CLI スクリプトのインターフェースを決める。
4. 各クラウドの公式 SDK の採用可否を検討し、依存パッケージ方針を固める。
5. 実機テスト（RPZ2W + iX500）で、Nextcloud と同様の UX で動作するか確認。

現時点では、ここまでを「仕様メモ」として残すにとどめ、  
実装・依存追加・ドキュメント更新は、将来的なニーズに応じて別タスクとして行う。

