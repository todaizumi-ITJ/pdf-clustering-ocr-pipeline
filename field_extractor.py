"""
フィールド抽出モジュール

Claude APIを使用してOCRテキストから構造化データを抽出する
"""

import json
import logging
import os
from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path

from anthropic import Anthropic

from code_master import CodeMaster

logger = logging.getLogger(__name__)


@dataclass
class ExtractedFields:
    """抽出されたフィールド"""
    # 契約者/利用者情報
    contractor_name: str = ""          # 契約者名 *
    contractor_kana: str = ""          # ふりがな
    user_name: str = ""                # 利用者名
    user_kana: str = ""                # 利用者ふりがな
    postal_code: str = ""              # 郵便番号
    address: str = ""                  # 住所 *
    phone: str = ""                    # 電話番号
    email: str = ""                    # メール
    memo: str = ""                     # メモ

    # コード情報
    lawyer_code: str = "XX"            # 弁護士コード
    lawyer_name: str = ""              # 弁護士事務所名（参照用）
    provider_code: str = "XX"          # プロバイダコード
    provider_name: str = ""            # プロバイダ名（参照用）

    # メタ情報
    pdf_path: str = ""                 # 元のPDFパス
    confidence: float = 0.0            # 抽出信頼度

    def to_dict(self) -> dict:
        return asdict(self)


class FieldExtractor:
    """Claude APIを使用したフィールド抽出クラス"""

    EXTRACTION_PROMPT = """以下のOCRテキストから、受任通知に記載された情報を抽出してください。

## 抽出するフィールド
1. contractor_name: 契約者名（必須）
2. contractor_kana: 契約者ふりがな
3. user_name: 利用者名（契約者と異なる場合）
4. user_kana: 利用者ふりがな
5. postal_code: 郵便番号（例: 123-4567）
6. address: 住所（必須）
7. phone: 電話番号
8. email: メールアドレス
9. memo: その他特記事項

10. lawyer_name: 弁護士事務所名・法律事務所名
11. provider_name: プロバイダ名・通信事業者名

## 注意事項
- 見つからない項目は空文字""にしてください
- 郵便番号はハイフン付き形式（123-4567）に統一してください
- 電話番号はハイフン付き形式に統一してください
- 推測せず、テキストに明記されている情報のみ抽出してください

## 出力形式
JSON形式で出力してください。```json などのマークダウン記法は使わず、純粋なJSONのみを出力してください。

## OCRテキスト
{ocr_text}
"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-haiku-20240307"):
        """
        Args:
            api_key: Anthropic API キー（省略時は環境変数から取得）
            model: 使用するClaudeモデル
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY が設定されていません")

        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        self.code_master = CodeMaster()

    def extract(self, ocr_text: str, pdf_path: Optional[Path] = None) -> ExtractedFields:
        """
        OCRテキストからフィールドを抽出

        Args:
            ocr_text: OCRで抽出されたテキスト
            pdf_path: 元のPDFファイルパス

        Returns:
            ExtractedFields: 抽出されたフィールド
        """
        if not ocr_text or not ocr_text.strip():
            logger.warning("OCRテキストが空です")
            return ExtractedFields(pdf_path=str(pdf_path) if pdf_path else "")

        try:
            # Claude APIで抽出
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": self.EXTRACTION_PROMPT.format(ocr_text=ocr_text)
                    }
                ]
            )

            # レスポンスをパース
            result_text = response.content[0].text.strip()
            result = json.loads(result_text)

            # ExtractedFieldsに変換
            fields = ExtractedFields(
                contractor_name=result.get("contractor_name", ""),
                contractor_kana=result.get("contractor_kana", ""),
                user_name=result.get("user_name", ""),
                user_kana=result.get("user_kana", ""),
                postal_code=result.get("postal_code", ""),
                address=result.get("address", ""),
                phone=result.get("phone", ""),
                email=result.get("email", ""),
                memo=result.get("memo", ""),
                pdf_path=str(pdf_path) if pdf_path else "",
                confidence=1.0
            )

            # 弁護士コードを検索
            lawyer_name = result.get("lawyer_name", "")
            fields.lawyer_name = lawyer_name
            fields.lawyer_code = self.code_master.find_lawyer_code(lawyer_name)

            # プロバイダコードを検索
            provider_name = result.get("provider_name", "")
            fields.provider_name = provider_name
            fields.provider_code = self.code_master.find_provider_code(provider_name)

            logger.info(f"フィールド抽出完了: {pdf_path}")
            return fields

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {e}")
            return ExtractedFields(pdf_path=str(pdf_path) if pdf_path else "", confidence=0.0)
        except Exception as e:
            logger.error(f"フィールド抽出エラー: {e}")
            return ExtractedFields(pdf_path=str(pdf_path) if pdf_path else "", confidence=0.0)

    def extract_batch(self, documents: list[tuple[str, Path]]) -> list[ExtractedFields]:
        """
        複数文書を一括処理

        Args:
            documents: (OCRテキスト, PDFパス) のリスト

        Returns:
            ExtractedFieldsのリスト
        """
        results = []
        for ocr_text, pdf_path in documents:
            result = self.extract(ocr_text, pdf_path)
            results.append(result)
        return results
