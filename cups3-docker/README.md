# CUPS 3.0 Docker Build

Docker環境でOpenPrinting CUPS 3.0をソースからビルドし、ホスト環境に依存せずにCUPS 3.0の全コンポーネントを利用できるようにするスクリプトです。

## CUPS 3.0 アーキテクチャ

CUPS 3.0はCUPS 2.x以前とは根本的に異なる設計です。プリンタードライバーを廃止し、3つの独立したコンポーネントに分離されています。

| コンポーネント | リポジトリ | 状態 | 説明 |
|---|---|---|---|
| **libcups** | [OpenPrinting/libcups](https://github.com/OpenPrinting/libcups) | v3.0.0 安定版 | HTTP/HTTPS/IPP通信用Cライブラリ。2.x以前とのバイナリ互換性なし |
| **cups-local** | [OpenPrinting/cups-local](https://github.com/OpenPrinting/cups-local) | alpha (master) | ユーザーごとのローカルスプーラ。一時キュー、基本フィルタリング。一般ユーザー権限で動作 |
| **cups-sharing** | [OpenPrinting/cups-sharing](https://github.com/OpenPrinting/cups-sharing) | alpha (master) | ネットワーク共有サーバー。永続キュー、ジョブ管理、Web UI。root権限で動作 |

cups-localとcups-sharingは[PAPPL](https://github.com/michaelrsweet/pappl)フレームワーク上に構築されています。

> **注意**: GitHubリポジトリ `OpenPrinting/cups` はCUPS **2.x系**のコードです。3.x系は上記3つの別リポジトリです。

## ビルド依存関係チェーン

```
libcups v3.0.0  (安定版)
    └─> PAPPL v2.x  (masterブランチ、v2.0未リリース)
            ├─> cups-local   (alpha)
            └─> cups-sharing (alpha)
```

## 使い方

### ビルド

```bash
./build-cups3.sh build
```

マルチステージDockerビルドにより、全コンポーネントをソースからコンパイルします。ランタイムイメージにはビルドツールを含まないため、イメージサイズが最小化されます。

### 実行

```bash
# cups-local (ローカル印刷サーバー) を起動
./build-cups3.sh run

# cups-sharing (ネットワーク共有サーバー) を起動 (ポート631)
./build-cups3.sh run-sharing

# CUPS 3.0ツール環境を開く
./build-cups3.sh tools

# コンテナ内でシェルを開く
./build-cups3.sh shell

# バージョン情報表示
./build-cups3.sh version

# イメージ削除
./build-cups3.sh clean
```

### 含まれるツール

- `ipptool` - IPPプロトコルテスト
- `ippfind` - DNS-SD/mDNSによるIPPプリンター検出
- `ippeveprinter` - 仮想IPP Everywhereプリンター
- `ipptransform` - ファイル形式変換

## 動作要件

- Docker (x86_64 Linux)
- インターネット接続 (ソースコードのクローンに必要)

## 既知の制限事項

- cups-localとcups-sharingはアルファ品質です
- PAPPL v2.0は正式リリースされていないためmasterブランチからビルドしています
- コンテナ内からホストのUSBプリンターにアクセスするには `--device` フラグが必要です
- mDNS/DNS-SDによるプリンター検出には `--network=host` が必要です

## 参考リンク

- [OpenPrinting CUPS v3 概要](https://openprinting.github.io/cups/cups3.html)
- [CUPS 3.0 Wiki](https://github.com/OpenPrinting/cups/wiki/CUPS-3.0)
- [libcups v3.0.0 リリースノート](https://openprinting.github.io/libcups-3.0.0/)
