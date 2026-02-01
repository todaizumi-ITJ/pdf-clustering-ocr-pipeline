"""Google Cloud Vision OCR モジュール"""

from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import time

from google.cloud import vision

from config import Config


@dataclass
class OCRResult:
    """OCR結果"""

    pdf_path: Path
    page_number: int
    text: str
    confidence: float
    blocks: List[dict]  # テキストブロック詳細


class GoogleVisionOCR:
    """Google Cloud Vision API を使ったOCR"""

    def __init__(self):
        self.client = None  # 遅延初期化

    def _init_client(self):
        """クライアントを遅延初期化"""
        if self.client is None:
            self.client = vision.ImageAnnotatorClient()

    def ocr_image(
        self, image_path: Path, pdf_path: Path = None, page_number: int = 1
    ) -> OCRResult:
        """
        画像にOCRを実行

        Args:
            image_path: 画像ファイルのパス
            pdf_path: 元のPDFパス（記録用）
            page_number: ページ番号

        Returns:
            OCRResult オブジェクト
        """
        self._init_client()
        image_path = Path(image_path)

        # 画像を読み込み
        with open(image_path, "rb") as f:
            content = f.read()

        image = vision.Image(content=content)

        # DOCUMENT_TEXT_DETECTION を使用（高精度）
        response = self.client.document_text_detection(
            image=image,
            image_context={"language_hints": ["ja"]},
        )

        if response.error.message:
            raise Exception(f"Vision API エラー: {response.error.message}")

        # 結果を解析
        full_text = ""
        blocks = []
        confidence_sum = 0
        confidence_count = 0

        if response.full_text_annotation:
            full_text = response.full_text_annotation.text

            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    block_text = ""
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            word_text = "".join(
                                [symbol.text for symbol in word.symbols]
                            )
                            block_text += word_text
                            confidence_sum += word.confidence
                            confidence_count += 1
                        block_text += "\n"

                    # バウンディングボックスを正規化座標で保存
                    vertices = block.bounding_box.vertices
                    blocks.append(
                        {
                            "text": block_text.strip(),
                            "vertices": [
                                {"x": v.x, "y": v.y} for v in vertices
                            ],
                            "confidence": block.confidence,
                        }
                    )

        avg_confidence = confidence_sum / confidence_count if confidence_count > 0 else 0

        return OCRResult(
            pdf_path=pdf_path or image_path,
            page_number=page_number,
            text=full_text,
            confidence=avg_confidence,
            blocks=blocks,
        )

    def ocr_document(
        self, image_paths: List[Path], pdf_path: Path, delay: float = 0.5
    ) -> List[OCRResult]:
        """
        複数ページの文書にOCRを実行

        Args:
            image_paths: 画像ファイルのパスリスト（ページ順）
            pdf_path: 元のPDFパス
            delay: API呼び出し間の待機時間（秒）

        Returns:
            OCRResult のリスト
        """
        results = []
        for i, image_path in enumerate(image_paths):
            try:
                result = self.ocr_image(image_path, pdf_path, page_number=i + 1)
                results.append(result)

                # レート制限対策
                if delay > 0 and i < len(image_paths) - 1:
                    time.sleep(delay)

            except Exception as e:
                print(f"OCRエラー [{image_path}]: {e}")

        return results

    def ocr_batch(
        self,
        documents: Dict[Path, List[Path]],
        delay: float = 0.5,
        progress_callback=None,
    ) -> Dict[Path, List[OCRResult]]:
        """
        複数文書に一括OCRを実行

        Args:
            documents: {pdf_path: [image_paths]} の辞書
            delay: API呼び出し間の待機時間
            progress_callback: 進捗コールバック関数

        Returns:
            {pdf_path: [OCRResult]} の辞書
        """
        results = {}
        total = len(documents)

        for i, (pdf_path, image_paths) in enumerate(documents.items()):
            if progress_callback:
                progress_callback(i + 1, total, pdf_path)

            results[pdf_path] = self.ocr_document(image_paths, pdf_path, delay)

        return results

    def get_combined_text(self, ocr_results: List[OCRResult]) -> str:
        """
        複数ページのOCR結果を結合

        Args:
            ocr_results: OCRResult のリスト

        Returns:
            結合されたテキスト
        """
        texts = []
        for result in sorted(ocr_results, key=lambda r: r.page_number):
            if result.text:
                texts.append(f"--- ページ {result.page_number} ---\n{result.text}")
        return "\n\n".join(texts)
