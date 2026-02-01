"""OCR + 特徴抽出モジュール"""

from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np
import pytesseract
from PIL import Image

from config import Config


@dataclass
class DocumentFeatures:
    """文書の特徴量"""

    pdf_path: Path
    text: str  # OCRテキスト
    layout_features: np.ndarray  # レイアウト特徴量
    text_blocks: List[dict]  # テキストブロック情報


class FeatureExtractor:
    """特徴抽出クラス"""

    def __init__(self):
        self.tesseract_lang = Config.TESSERACT_LANG

    def extract(self, image_path: Path, pdf_path: Path = None) -> DocumentFeatures:
        """
        画像から特徴を抽出

        Args:
            image_path: 画像ファイルのパス
            pdf_path: 元のPDFパス（記録用）

        Returns:
            DocumentFeatures オブジェクト
        """
        image_path = Path(image_path)

        # 画像読み込み
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"画像を読み込めません: {image_path}")

        # OCRテキスト抽出
        text = self._extract_text(image_path)

        # テキストブロック検出
        text_blocks = self._detect_text_blocks(image)

        # レイアウト特徴量抽出
        layout_features = self._extract_layout_features(image, text_blocks)

        return DocumentFeatures(
            pdf_path=pdf_path or image_path,
            text=text,
            layout_features=layout_features,
            text_blocks=text_blocks,
        )

    def _extract_text(self, image_path: Path) -> str:
        """Tesseractで簡易OCR"""
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang=self.tesseract_lang)
            return text.strip()
        except Exception as e:
            print(f"OCRエラー [{image_path}]: {e}")
            return ""

    def _detect_text_blocks(self, image: np.ndarray) -> List[dict]:
        """テキストブロックを検出"""
        # グレースケール変換
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 二値化
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 膨張処理でテキスト領域を結合
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 10))
        dilated = cv2.dilate(binary, kernel, iterations=3)

        # 輪郭検出
        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # 画像サイズで正規化
        h, w = image.shape[:2]
        blocks = []
        for contour in contours:
            x, y, bw, bh = cv2.boundingRect(contour)
            # 小さすぎる領域は無視
            if bw * bh < (w * h * 0.001):
                continue
            blocks.append(
                {
                    "x": x / w,  # 正規化座標
                    "y": y / h,
                    "width": bw / w,
                    "height": bh / h,
                    "area": (bw * bh) / (w * h),
                }
            )

        # Y座標でソート（上から下へ）
        blocks.sort(key=lambda b: b["y"])
        return blocks

    def _extract_layout_features(
        self, image: np.ndarray, text_blocks: List[dict]
    ) -> np.ndarray:
        """レイアウト特徴量を抽出"""
        h, w = image.shape[:2]

        features = []

        # 1. テキストブロック数
        features.append(len(text_blocks))

        # 2. テキスト領域の総面積比
        total_area = sum(b["area"] for b in text_blocks)
        features.append(total_area)

        # 3. 画像を3x3グリッドに分割し、各セルの密度を計算
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        grid_features = self._compute_grid_density(gray, 3, 3)
        features.extend(grid_features)

        # 4. テキストブロックの位置分布（上部/中央/下部）
        if text_blocks:
            y_positions = [b["y"] + b["height"] / 2 for b in text_blocks]
            features.append(np.mean(y_positions))
            features.append(np.std(y_positions) if len(y_positions) > 1 else 0)
        else:
            features.extend([0.5, 0])

        # 5. 水平線・垂直線の検出（表の存在を示唆）
        lines = self._detect_lines(gray)
        features.append(lines["horizontal"])
        features.append(lines["vertical"])

        return np.array(features, dtype=np.float32)

    def _compute_grid_density(
        self, gray: np.ndarray, rows: int, cols: int
    ) -> List[float]:
        """画像をグリッドに分割して各セルの密度を計算"""
        h, w = gray.shape
        cell_h, cell_w = h // rows, w // cols

        densities = []
        for i in range(rows):
            for j in range(cols):
                cell = gray[
                    i * cell_h : (i + 1) * cell_h, j * cell_w : (j + 1) * cell_w
                ]
                # 黒いピクセルの割合（テキスト密度）
                density = np.sum(cell < 128) / cell.size
                densities.append(density)

        return densities

    def _detect_lines(self, gray: np.ndarray) -> dict:
        """水平線・垂直線を検出"""
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Hough変換で直線検出
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10
        )

        horizontal = 0
        vertical = 0

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                if angle < 10:  # ほぼ水平
                    horizontal += 1
                elif angle > 80:  # ほぼ垂直
                    vertical += 1

        # 正規化（多くても100程度と想定）
        return {
            "horizontal": min(horizontal / 100, 1.0),
            "vertical": min(vertical / 100, 1.0),
        }

    def extract_batch(
        self, image_paths: List[Tuple[Path, Path]]
    ) -> List[DocumentFeatures]:
        """
        複数画像から特徴を一括抽出

        Args:
            image_paths: [(image_path, pdf_path), ...] のリスト

        Returns:
            DocumentFeatures のリスト
        """
        results = []
        for image_path, pdf_path in image_paths:
            try:
                features = self.extract(image_path, pdf_path)
                results.append(features)
            except Exception as e:
                print(f"特徴抽出エラー [{image_path}]: {e}")
        return results
