"""SQLite データベースモジュール"""

import sqlite3
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

from config import Config


@dataclass
class Document:
    """文書レコード"""

    id: Optional[int]
    filename: str
    filepath: str
    cluster_id: int
    ocr_text: str
    page_count: int
    confidence: float
    created_at: datetime

    @classmethod
    def from_row(cls, row: tuple) -> "Document":
        return cls(
            id=row[0],
            filename=row[1],
            filepath=row[2],
            cluster_id=row[3],
            ocr_text=row[4],
            page_count=row[5],
            confidence=row[6],
            created_at=datetime.fromisoformat(row[7]) if row[7] else None,
        )


class Database:
    """SQLiteデータベース操作クラス"""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Config.DB_PATH
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_db()

    def _init_db(self):
        """データベースを初期化"""
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    filepath TEXT NOT NULL UNIQUE,
                    cluster_id INTEGER NOT NULL,
                    ocr_text TEXT,
                    page_count INTEGER DEFAULT 1,
                    confidence REAL DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS clusters (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    document_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_documents_cluster
                ON documents(cluster_id);

                CREATE INDEX IF NOT EXISTS idx_documents_filename
                ON documents(filename);
            """
            )

    def _get_connection(self) -> sqlite3.Connection:
        """データベース接続を取得"""
        return sqlite3.connect(self.db_path)

    def insert_document(
        self,
        filename: str,
        filepath: str,
        cluster_id: int,
        ocr_text: str = "",
        page_count: int = 1,
        confidence: float = 0,
    ) -> int:
        """
        文書を挿入

        Returns:
            挿入されたレコードのID
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO documents
                (filename, filepath, cluster_id, ocr_text, page_count, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (filename, filepath, cluster_id, ocr_text, page_count, confidence),
            )
            return cursor.lastrowid

    def insert_documents_batch(self, documents: List[dict]) -> int:
        """
        複数文書を一括挿入

        Args:
            documents: [{"filename", "filepath", "cluster_id", "ocr_text", ...}]

        Returns:
            挿入された件数
        """
        with self._get_connection() as conn:
            cursor = conn.executemany(
                """
                INSERT OR REPLACE INTO documents
                (filename, filepath, cluster_id, ocr_text, page_count, confidence)
                VALUES (:filename, :filepath, :cluster_id, :ocr_text, :page_count, :confidence)
                """,
                documents,
            )
            return cursor.rowcount

    def get_document(self, doc_id: int) -> Optional[Document]:
        """IDで文書を取得"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ?", (doc_id,)
            ).fetchone()
            return Document.from_row(row) if row else None

    def get_document_by_filepath(self, filepath: str) -> Optional[Document]:
        """ファイルパスで文書を取得"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE filepath = ?", (filepath,)
            ).fetchone()
            return Document.from_row(row) if row else None

    def get_documents_by_cluster(self, cluster_id: int) -> List[Document]:
        """クラスタIDで文書を取得"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM documents WHERE cluster_id = ? ORDER BY filename",
                (cluster_id,),
            ).fetchall()
            return [Document.from_row(row) for row in rows]

    def get_all_documents(self) -> List[Document]:
        """全文書を取得"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM documents ORDER BY cluster_id, filename"
            ).fetchall()
            return [Document.from_row(row) for row in rows]

    def update_cluster(self, cluster_id: int, name: str = None, description: str = None):
        """クラスタ情報を更新"""
        with self._get_connection() as conn:
            # ドキュメント数をカウント
            count = conn.execute(
                "SELECT COUNT(*) FROM documents WHERE cluster_id = ?", (cluster_id,)
            ).fetchone()[0]

            conn.execute(
                """
                INSERT OR REPLACE INTO clusters (id, name, description, document_count)
                VALUES (?, ?, ?, ?)
                """,
                (cluster_id, name or f"クラスタ {cluster_id}", description, count),
            )

    def update_all_cluster_counts(self):
        """全クラスタのドキュメント数を更新"""
        with self._get_connection() as conn:
            # クラスタIDを取得
            cluster_ids = conn.execute(
                "SELECT DISTINCT cluster_id FROM documents"
            ).fetchall()

            for (cluster_id,) in cluster_ids:
                self.update_cluster(cluster_id)

    def get_cluster_stats(self) -> List[dict]:
        """クラスタ統計を取得"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    cluster_id,
                    COUNT(*) as doc_count,
                    AVG(confidence) as avg_confidence,
                    SUM(page_count) as total_pages
                FROM documents
                GROUP BY cluster_id
                ORDER BY cluster_id
                """
            ).fetchall()

            return [
                {
                    "cluster_id": row[0],
                    "document_count": row[1],
                    "avg_confidence": row[2],
                    "total_pages": row[3],
                }
                for row in rows
            ]

    def search_text(self, query: str, limit: int = 100) -> List[Document]:
        """テキスト検索"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM documents
                WHERE ocr_text LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (f"%{query}%", limit),
            ).fetchall()
            return [Document.from_row(row) for row in rows]

    def delete_document(self, doc_id: int):
        """文書を削除"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

    def clear_all(self):
        """全データを削除"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM documents")
            conn.execute("DELETE FROM clusters")
