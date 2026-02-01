"""設定管理モジュール"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    """アプリケーション設定"""

    # パス設定
    BASE_DIR = Path(__file__).parent
    INPUT_DIR = BASE_DIR / "input"
    OUTPUT_DIR = BASE_DIR / "output"
    TEMP_DIR = BASE_DIR / "temp"
    DB_PATH = OUTPUT_DIR / "documents.db"

    # PDF→画像変換設定
    DPI = 300
    IMAGE_FORMAT = "PNG"

    # Tesseract設定（簡易OCR用）
    TESSERACT_LANG = "jpn"  # 日本語

    # Google Cloud Vision設定
    # 環境変数 GOOGLE_APPLICATION_CREDENTIALS にサービスアカウントキーのパスを設定
    GCV_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    # クラスタリング設定
    CLUSTERING_METHOD = "dbscan"  # "dbscan" or "kmeans"
    DBSCAN_EPS = 0.5  # DBSCANの距離閾値
    DBSCAN_MIN_SAMPLES = 2  # DBSCANの最小サンプル数
    KMEANS_N_CLUSTERS = 10  # k-meansのクラスタ数（オプション指定時）

    # sentence-transformers モデル
    EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

    # 特徴量の重み（テキスト vs レイアウト）
    TEXT_WEIGHT = 0.7
    LAYOUT_WEIGHT = 0.3

    # CSV出力設定
    CSV_ENCODING = "utf-8-sig"  # BOM付きUTF-8（Excel対応）

    @classmethod
    def setup_directories(cls):
        """必要なディレクトリを作成"""
        cls.INPUT_DIR.mkdir(exist_ok=True)
        cls.OUTPUT_DIR.mkdir(exist_ok=True)
        cls.TEMP_DIR.mkdir(exist_ok=True)

    @classmethod
    def validate(cls):
        """設定の検証"""
        errors = []

        if cls.GCV_CREDENTIALS and not Path(cls.GCV_CREDENTIALS).exists():
            errors.append(
                f"Google Cloud認証ファイルが見つかりません: {cls.GCV_CREDENTIALS}"
            )

        return errors
