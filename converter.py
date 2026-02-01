"""PDF→画像変換モジュール"""

from pathlib import Path
from typing import List
import shutil

from pdf2image import convert_from_path
from PIL import Image

from config import Config


class PDFConverter:
    """PDFを画像に変換するクラス"""

    def __init__(self, temp_dir: Path = None):
        self.temp_dir = temp_dir or Config.TEMP_DIR
        self.temp_dir.mkdir(exist_ok=True)

    def convert(self, pdf_path: Path) -> List[Path]:
        """
        PDFを画像に変換

        Args:
            pdf_path: PDFファイルのパス

        Returns:
            変換された画像ファイルのパスリスト
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDFが見つかりません: {pdf_path}")

        # PDFごとのサブディレクトリを作成
        doc_temp_dir = self.temp_dir / pdf_path.stem
        doc_temp_dir.mkdir(exist_ok=True)

        # PDF→画像変換
        images = convert_from_path(
            pdf_path,
            dpi=Config.DPI,
            fmt=Config.IMAGE_FORMAT.lower(),
        )

        # 画像を保存
        image_paths = []
        for i, image in enumerate(images):
            image_path = doc_temp_dir / f"page_{i + 1:03d}.{Config.IMAGE_FORMAT.lower()}"
            image.save(image_path, Config.IMAGE_FORMAT)
            image_paths.append(image_path)

        return image_paths

    def convert_batch(self, pdf_paths: List[Path]) -> dict:
        """
        複数のPDFを一括変換

        Args:
            pdf_paths: PDFファイルのパスリスト

        Returns:
            {pdf_path: [image_paths]} の辞書
        """
        results = {}
        for pdf_path in pdf_paths:
            try:
                results[pdf_path] = self.convert(pdf_path)
            except Exception as e:
                print(f"変換エラー [{pdf_path}]: {e}")
                results[pdf_path] = []
        return results

    def get_first_page_image(self, pdf_path: Path) -> Path:
        """
        PDFの1ページ目のみを画像化（クラスタリング用）

        Args:
            pdf_path: PDFファイルのパス

        Returns:
            1ページ目の画像パス
        """
        pdf_path = Path(pdf_path)
        doc_temp_dir = self.temp_dir / pdf_path.stem
        doc_temp_dir.mkdir(exist_ok=True)

        images = convert_from_path(
            pdf_path,
            dpi=Config.DPI,
            fmt=Config.IMAGE_FORMAT.lower(),
            first_page=1,
            last_page=1,
        )

        image_path = doc_temp_dir / f"page_001.{Config.IMAGE_FORMAT.lower()}"
        images[0].save(image_path, Config.IMAGE_FORMAT)

        return image_path

    def cleanup(self, pdf_path: Path = None):
        """
        一時ファイルを削除

        Args:
            pdf_path: 特定のPDFの一時ファイルのみ削除（Noneで全削除）
        """
        if pdf_path:
            doc_temp_dir = self.temp_dir / Path(pdf_path).stem
            if doc_temp_dir.exists():
                shutil.rmtree(doc_temp_dir)
        else:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.temp_dir.mkdir(exist_ok=True)
