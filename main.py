#!/usr/bin/env python3
"""
PDF クラスタリング & OCR パイプライン

使い方:
    python main.py --input ./pdfs --output ./results
    python main.py --input ./pdfs --output ./results --clusters 10
    python main.py --input ./pdfs --output ./results --export-csv
"""

import argparse
from pathlib import Path
from typing import List

from tqdm import tqdm

from config import Config
from converter import PDFConverter
from feature_extractor import FeatureExtractor, DocumentFeatures
from clustering import DocumentClusterer
from ocr_service import GoogleVisionOCR
from database import Database
from exporter import CSVExporter


def find_pdfs(input_dir: Path) -> List[Path]:
    """入力ディレクトリからPDFを検索"""
    input_dir = Path(input_dir)
    if not input_dir.exists():
        raise FileNotFoundError(f"入力ディレクトリが見つかりません: {input_dir}")

    pdfs = list(input_dir.glob("**/*.pdf"))
    print(f"PDFファイルを {len(pdfs)} 件発見")
    return pdfs


def run_pipeline(
    input_dir: Path,
    output_dir: Path = None,
    n_clusters: int = None,
    export_csv: bool = False,
    skip_ocr: bool = False,
):
    """
    パイプラインを実行

    Args:
        input_dir: 入力PDFディレクトリ
        output_dir: 出力ディレクトリ
        n_clusters: k-meansのクラスタ数（Noneでauto: DBSCAN）
        export_csv: CSV出力するか
        skip_ocr: 本番OCRをスキップするか（クラスタリングのみ）
    """
    # 設定
    if output_dir:
        Config.OUTPUT_DIR = Path(output_dir)
        Config.DB_PATH = Config.OUTPUT_DIR / "documents.db"
    Config.setup_directories()

    # エラーチェック
    errors = Config.validate()
    if errors and not skip_ocr:
        print("設定エラー:")
        for e in errors:
            print(f"  - {e}")
        print("\n本番OCRをスキップする場合は --skip-ocr オプションを使用してください")
        return

    # PDFを検索
    pdf_paths = find_pdfs(input_dir)
    if not pdf_paths:
        print("処理するPDFがありません")
        return

    # 初期化
    converter = PDFConverter()
    extractor = FeatureExtractor()
    clusterer = DocumentClusterer()
    db = Database()

    # ステップ1: PDF→画像変換 & 特徴抽出
    print("\n=== ステップ1: PDF変換 & 特徴抽出 ===")
    doc_features: List[DocumentFeatures] = []

    for pdf_path in tqdm(pdf_paths, desc="特徴抽出"):
        try:
            # 1ページ目のみ画像化（クラスタリング用）
            image_path = converter.get_first_page_image(pdf_path)

            # 特徴抽出
            features = extractor.extract(image_path, pdf_path)
            doc_features.append(features)

        except Exception as e:
            print(f"\nエラー [{pdf_path.name}]: {e}")

    if not doc_features:
        print("特徴抽出に成功したPDFがありません")
        return

    # ステップ2: クラスタリング
    print("\n=== ステップ2: クラスタリング ===")
    method = "kmeans" if n_clusters else "dbscan"
    cluster_results = clusterer.process(doc_features, method=method, n_clusters=n_clusters)

    # サマリー表示
    clusterer.print_cluster_summary(cluster_results)

    # ステップ3: 本番OCR
    if not skip_ocr:
        print("\n=== ステップ3: 本番OCR (Google Cloud Vision) ===")
        ocr_service = GoogleVisionOCR()

        # クラスタごとに処理
        cluster_summary = clusterer.get_cluster_summary(cluster_results)

        for cluster_id, pdf_list in cluster_summary.items():
            label = "ノイズ" if cluster_id == -1 else f"クラスタ {cluster_id}"
            print(f"\n[{label}] {len(pdf_list)}件を処理中...")

            for pdf_path in tqdm(pdf_list, desc=label):
                try:
                    # 全ページを画像化
                    image_paths = converter.convert(pdf_path)

                    # 本番OCR
                    ocr_results = ocr_service.ocr_document(image_paths, pdf_path)
                    combined_text = ocr_service.get_combined_text(ocr_results)

                    # 平均信頼度
                    avg_confidence = (
                        sum(r.confidence for r in ocr_results) / len(ocr_results)
                        if ocr_results
                        else 0
                    )

                    # DB保存
                    db.insert_document(
                        filename=pdf_path.name,
                        filepath=str(pdf_path.absolute()),
                        cluster_id=cluster_id,
                        ocr_text=combined_text,
                        page_count=len(image_paths),
                        confidence=avg_confidence,
                    )

                    # 一時ファイル削除
                    converter.cleanup(pdf_path)

                except Exception as e:
                    print(f"\nOCRエラー [{pdf_path.name}]: {e}")
    else:
        # OCRスキップ時はTesseractの結果を保存
        print("\n=== 本番OCRをスキップ（Tesseract結果を使用） ===")

        for features, result in zip(doc_features, cluster_results):
            db.insert_document(
                filename=features.pdf_path.name,
                filepath=str(features.pdf_path.absolute()),
                cluster_id=result.cluster_id,
                ocr_text=features.text,  # Tesseractの結果
                page_count=1,
                confidence=0,
            )

    # クラスタ統計を更新
    db.update_all_cluster_counts()

    # ステップ4: 出力
    print("\n=== ステップ4: 結果出力 ===")
    print(f"データベース: {Config.DB_PATH}")

    if export_csv:
        exporter = CSVExporter()

        # 全件CSV
        all_csv = exporter.export_all(db)
        print(f"全件CSV: {all_csv}")

        # サマリーCSV
        summary_csv = exporter.export_summary(db)
        print(f"サマリーCSV: {summary_csv}")

        # クラスタ別CSV
        cluster_csvs = exporter.export_all_clusters_separately(db)
        print(f"クラスタ別CSV: {len(cluster_csvs)}件出力")

    # 一時ファイル削除
    converter.cleanup()

    print("\n=== 完了 ===")
    stats = db.get_cluster_stats()
    total_docs = sum(s["document_count"] for s in stats)
    print(f"処理文書数: {total_docs}")
    print(f"クラスタ数: {len(stats)}")


def main():
    parser = argparse.ArgumentParser(
        description="PDF クラスタリング & OCR パイプライン"
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        required=True,
        help="入力PDFディレクトリ",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="出力ディレクトリ（デフォルト: ./output）",
    )
    parser.add_argument(
        "--clusters", "-c",
        type=int,
        default=None,
        help="クラスタ数（指定時k-means、未指定でDBSCAN自動）",
    )
    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="CSV出力を有効化",
    )
    parser.add_argument(
        "--skip-ocr",
        action="store_true",
        help="本番OCRをスキップ（クラスタリングのみ）",
    )

    args = parser.parse_args()

    run_pipeline(
        input_dir=args.input,
        output_dir=args.output,
        n_clusters=args.clusters,
        export_csv=args.export_csv,
        skip_ocr=args.skip_ocr,
    )


if __name__ == "__main__":
    main()
