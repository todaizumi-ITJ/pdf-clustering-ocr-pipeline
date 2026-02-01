"""CSV エクスポートモジュール"""

from pathlib import Path
from typing import List, Optional

import pandas as pd

from config import Config
from database import Database, Document


class CSVExporter:
    """CSV出力クラス"""

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Config.OUTPUT_DIR
        self.output_dir.mkdir(exist_ok=True)
        self.encoding = Config.CSV_ENCODING

    def export_all(
        self,
        db: Database,
        filename: str = "all_documents.csv",
        include_text: bool = True,
    ) -> Path:
        """
        全文書をCSVにエクスポート

        Args:
            db: Databaseインスタンス
            filename: 出力ファイル名
            include_text: OCRテキストを含めるか

        Returns:
            出力ファイルのパス
        """
        documents = db.get_all_documents()
        return self._export_documents(documents, filename, include_text)

    def export_by_cluster(
        self,
        db: Database,
        cluster_id: int,
        filename: str = None,
        include_text: bool = True,
    ) -> Path:
        """
        特定クラスタの文書をCSVにエクスポート

        Args:
            db: Databaseインスタンス
            cluster_id: クラスタID
            filename: 出力ファイル名（Noneで自動生成）
            include_text: OCRテキストを含めるか

        Returns:
            出力ファイルのパス
        """
        documents = db.get_documents_by_cluster(cluster_id)
        if filename is None:
            filename = f"cluster_{cluster_id}.csv"
        return self._export_documents(documents, filename, include_text)

    def export_all_clusters_separately(
        self,
        db: Database,
        include_text: bool = True,
    ) -> List[Path]:
        """
        各クラスタを個別のCSVにエクスポート

        Returns:
            出力ファイルのパスリスト
        """
        stats = db.get_cluster_stats()
        output_paths = []

        for stat in stats:
            cluster_id = stat["cluster_id"]
            path = self.export_by_cluster(db, cluster_id, include_text=include_text)
            output_paths.append(path)

        return output_paths

    def export_summary(self, db: Database, filename: str = "summary.csv") -> Path:
        """
        クラスタ統計サマリーをCSVにエクスポート

        Returns:
            出力ファイルのパス
        """
        stats = db.get_cluster_stats()

        df = pd.DataFrame(stats)
        df.columns = ["クラスタID", "文書数", "平均信頼度", "総ページ数"]

        output_path = self.output_dir / filename
        df.to_csv(output_path, index=False, encoding=self.encoding)

        return output_path

    def _export_documents(
        self,
        documents: List[Document],
        filename: str,
        include_text: bool = True,
    ) -> Path:
        """文書リストをCSVにエクスポート"""
        if not documents:
            # 空のCSVを作成
            output_path = self.output_dir / filename
            pd.DataFrame().to_csv(output_path, index=False, encoding=self.encoding)
            return output_path

        data = []
        for doc in documents:
            row = {
                "ID": doc.id,
                "ファイル名": doc.filename,
                "ファイルパス": doc.filepath,
                "クラスタID": doc.cluster_id,
                "ページ数": doc.page_count,
                "信頼度": round(doc.confidence, 3) if doc.confidence else 0,
                "登録日時": doc.created_at.isoformat() if doc.created_at else "",
            }
            if include_text:
                # テキストは長いので先頭500文字のみ
                text_preview = doc.ocr_text[:500] if doc.ocr_text else ""
                if len(doc.ocr_text or "") > 500:
                    text_preview += "..."
                row["OCRテキスト（プレビュー）"] = text_preview
                row["OCRテキスト（全文）"] = doc.ocr_text or ""

            data.append(row)

        df = pd.DataFrame(data)
        output_path = self.output_dir / filename
        df.to_csv(output_path, index=False, encoding=self.encoding)

        return output_path

    def export_search_results(
        self,
        db: Database,
        query: str,
        filename: str = None,
    ) -> Path:
        """
        検索結果をCSVにエクスポート

        Args:
            db: Databaseインスタンス
            query: 検索クエリ
            filename: 出力ファイル名

        Returns:
            出力ファイルのパス
        """
        documents = db.search_text(query)
        if filename is None:
            # クエリからファイル名を生成（特殊文字を除去）
            safe_query = "".join(c for c in query if c.isalnum() or c in "._- ")[:30]
            filename = f"search_{safe_query}.csv"

        return self._export_documents(documents, filename, include_text=True)
