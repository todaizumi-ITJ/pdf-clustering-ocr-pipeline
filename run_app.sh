#!/bin/bash
# PDF フィールド抽出アプリ起動スクリプト

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

# .envファイルがあれば読み込み
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 必要な環境変数のチェック
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "警告: ANTHROPIC_API_KEY が設定されていません"
    echo ".env ファイルに以下を追加してください:"
    echo "ANTHROPIC_API_KEY=your-api-key"
fi

if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "警告: GOOGLE_APPLICATION_CREDENTIALS が設定されていません"
fi

# Streamlit起動
echo "アプリを起動しています..."
echo "ブラウザで http://localhost:8501 を開いてください"
streamlit run app.py --server.port 8501
