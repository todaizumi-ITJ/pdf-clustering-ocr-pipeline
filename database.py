"""SQLite データベースモジュール"""

import sqlite3
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

from config import Config


@dataclass
class Customer:
    """顧客レコード"""

    id: Optional[int]
    document_id: Optional[int]  # documentsテーブルとの関連
    contractor_name: str        # 契約者名
    contractor_kana: str        # ふりがな
    user_name: str              # 利用者名
    user_kana: str              # 利用者ふりがな
    postal_code: str            # 郵便番号
    address: str                # 住所
    phone: str                  # 電話番号
    email: str                  # メール
    memo: str                   # メモ
    lawyer_code: str            # 弁護士コード
    lawyer_name: str            # 弁護士事務所名
    provider_code: str          # プロバイダコード
    provider_name: str          # プロバイダ名
    confidence: float           # 抽出信頼度
    created_at: datetime

    @classmethod
    def from_row(cls, row: tuple) -> "Customer":
        return cls(
            id=row[0],
            document_id=row[1],
            contractor_name=row[2],
            contractor_kana=row[3],
            user_name=row[4],
            user_kana=row[5],
            postal_code=row[6],
            address=row[7],
            phone=row[8],
            email=row[9],
            memo=row[10],
            lawyer_code=row[11],
            lawyer_name=row[12],
            provider_code=row[13],
            provider_name=row[14],
            confidence=row[15],
            created_at=datetime.fromisoformat(row[16]) if row[16] else None,
        )


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


@dataclass
class Feedback:
    """フィードバックレコード"""

    id: Optional[int]
    category: str           # ui, feature, bug, performance, other
    priority: str           # low, medium, high
    content: str            # フィードバック内容
    status: str             # pending, in_progress, done, rejected
    user_name: str          # 投稿者名（任意）
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: tuple) -> "Feedback":
        return cls(
            id=row[0],
            category=row[1],
            priority=row[2],
            content=row[3],
            status=row[4],
            user_name=row[5],
            created_at=datetime.fromisoformat(row[6]) if row[6] else None,
            updated_at=datetime.fromisoformat(row[7]) if row[7] else None,
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

                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER,
                    contractor_name TEXT NOT NULL,
                    contractor_kana TEXT,
                    user_name TEXT,
                    user_kana TEXT,
                    postal_code TEXT,
                    address TEXT NOT NULL,
                    phone TEXT,
                    email TEXT,
                    memo TEXT,
                    lawyer_code TEXT DEFAULT 'XX',
                    lawyer_name TEXT,
                    provider_code TEXT DEFAULT 'XX',
                    provider_name TEXT,
                    confidence REAL DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                );

                CREATE INDEX IF NOT EXISTS idx_customers_lawyer
                ON customers(lawyer_code);

                CREATE INDEX IF NOT EXISTS idx_customers_provider
                ON customers(provider_code);

                CREATE INDEX IF NOT EXISTS idx_customers_contractor
                ON customers(contractor_name);

                CREATE TABLE IF NOT EXISTS feedbacks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    priority TEXT DEFAULT 'medium',
                    content TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    user_name TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_feedbacks_status
                ON feedbacks(status);

                CREATE INDEX IF NOT EXISTS idx_feedbacks_category
                ON feedbacks(category);

                CREATE INDEX IF NOT EXISTS idx_feedbacks_priority
                ON feedbacks(priority);
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
            conn.execute("DELETE FROM customers")
            conn.execute("DELETE FROM feedbacks")

    # ==================== 顧客情報 ====================

    def insert_customer(
        self,
        contractor_name: str,
        address: str,
        document_id: int = None,
        contractor_kana: str = "",
        user_name: str = "",
        user_kana: str = "",
        postal_code: str = "",
        phone: str = "",
        email: str = "",
        memo: str = "",
        lawyer_code: str = "XX",
        lawyer_name: str = "",
        provider_code: str = "XX",
        provider_name: str = "",
        confidence: float = 0,
    ) -> int:
        """
        顧客情報を挿入

        Returns:
            挿入されたレコードのID
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO customers
                (document_id, contractor_name, contractor_kana, user_name, user_kana,
                 postal_code, address, phone, email, memo,
                 lawyer_code, lawyer_name, provider_code, provider_name, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (document_id, contractor_name, contractor_kana, user_name, user_kana,
                 postal_code, address, phone, email, memo,
                 lawyer_code, lawyer_name, provider_code, provider_name, confidence),
            )
            return cursor.lastrowid

    def insert_customer_from_fields(self, fields, document_id: int = None) -> int:
        """
        ExtractedFieldsから顧客情報を挿入

        Args:
            fields: ExtractedFieldsオブジェクト
            document_id: 関連するdocumentのID

        Returns:
            挿入されたレコードのID
        """
        return self.insert_customer(
            document_id=document_id,
            contractor_name=fields.contractor_name,
            contractor_kana=fields.contractor_kana,
            user_name=fields.user_name,
            user_kana=fields.user_kana,
            postal_code=fields.postal_code,
            address=fields.address,
            phone=fields.phone,
            email=fields.email,
            memo=fields.memo,
            lawyer_code=fields.lawyer_code,
            lawyer_name=fields.lawyer_name,
            provider_code=fields.provider_code,
            provider_name=fields.provider_name,
            confidence=fields.confidence,
        )

    def get_customer(self, customer_id: int) -> Optional[Customer]:
        """IDで顧客を取得"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM customers WHERE id = ?", (customer_id,)
            ).fetchone()
            return Customer.from_row(row) if row else None

    def get_all_customers(self) -> List[Customer]:
        """全顧客を取得"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM customers ORDER BY created_at DESC"
            ).fetchall()
            return [Customer.from_row(row) for row in rows]

    def get_customers_by_lawyer(self, lawyer_code: str) -> List[Customer]:
        """弁護士コードで顧客を取得"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM customers WHERE lawyer_code = ? ORDER BY created_at DESC",
                (lawyer_code,),
            ).fetchall()
            return [Customer.from_row(row) for row in rows]

    def get_customers_by_provider(self, provider_code: str) -> List[Customer]:
        """プロバイダコードで顧客を取得"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM customers WHERE provider_code = ? ORDER BY created_at DESC",
                (provider_code,),
            ).fetchall()
            return [Customer.from_row(row) for row in rows]

    def search_customers(self, query: str, limit: int = 100) -> List[Customer]:
        """顧客を検索（名前・住所）"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM customers
                WHERE contractor_name LIKE ?
                   OR user_name LIKE ?
                   OR address LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", f"%{query}%", limit),
            ).fetchall()
            return [Customer.from_row(row) for row in rows]

    def get_customer_stats(self) -> dict:
        """顧客統計を取得"""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]

            by_lawyer = conn.execute(
                """
                SELECT lawyer_code, COUNT(*) as count
                FROM customers
                GROUP BY lawyer_code
                ORDER BY count DESC
                """
            ).fetchall()

            by_provider = conn.execute(
                """
                SELECT provider_code, COUNT(*) as count
                FROM customers
                GROUP BY provider_code
                ORDER BY count DESC
                """
            ).fetchall()

            return {
                "total": total,
                "by_lawyer": {row[0]: row[1] for row in by_lawyer},
                "by_provider": {row[0]: row[1] for row in by_provider},
            }

    def delete_customer(self, customer_id: int):
        """顧客を削除"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))

    # ==================== フィードバック ====================

    def insert_feedback(
        self,
        category: str,
        content: str,
        priority: str = "medium",
        user_name: str = "",
    ) -> int:
        """
        フィードバックを挿入

        Args:
            category: カテゴリ（ui, feature, bug, performance, other）
            content: フィードバック内容
            priority: 優先度（low, medium, high）
            user_name: 投稿者名（任意）

        Returns:
            挿入されたレコードのID
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO feedbacks (category, priority, content, user_name)
                VALUES (?, ?, ?, ?)
                """,
                (category, priority, content, user_name),
            )
            return cursor.lastrowid

    def get_feedback(self, feedback_id: int) -> Optional[Feedback]:
        """IDでフィードバックを取得"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM feedbacks WHERE id = ?", (feedback_id,)
            ).fetchone()
            return Feedback.from_row(row) if row else None

    def get_all_feedbacks(self, limit: int = 100) -> List[Feedback]:
        """全フィードバックを取得（新しい順）"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM feedbacks ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [Feedback.from_row(row) for row in rows]

    def get_feedbacks_by_status(self, status: str) -> List[Feedback]:
        """ステータスでフィードバックを取得"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM feedbacks WHERE status = ? ORDER BY priority DESC, created_at DESC",
                (status,),
            ).fetchall()
            return [Feedback.from_row(row) for row in rows]

    def get_pending_feedbacks(self) -> List[Feedback]:
        """未対応のフィードバックを取得"""
        return self.get_feedbacks_by_status("pending")

    def get_feedbacks_by_category(self, category: str) -> List[Feedback]:
        """カテゴリでフィードバックを取得"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM feedbacks WHERE category = ? ORDER BY created_at DESC",
                (category,),
            ).fetchall()
            return [Feedback.from_row(row) for row in rows]

    def update_feedback_status(self, feedback_id: int, status: str):
        """フィードバックのステータスを更新"""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE feedbacks
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, feedback_id),
            )

    def get_feedback_stats(self) -> dict:
        """フィードバック統計を取得"""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM feedbacks").fetchone()[0]

            by_status = conn.execute(
                """
                SELECT status, COUNT(*) as count
                FROM feedbacks
                GROUP BY status
                """
            ).fetchall()

            by_category = conn.execute(
                """
                SELECT category, COUNT(*) as count
                FROM feedbacks
                GROUP BY category
                ORDER BY count DESC
                """
            ).fetchall()

            by_priority = conn.execute(
                """
                SELECT priority, COUNT(*) as count
                FROM feedbacks
                GROUP BY priority
                """
            ).fetchall()

            return {
                "total": total,
                "by_status": {row[0]: row[1] for row in by_status},
                "by_category": {row[0]: row[1] for row in by_category},
                "by_priority": {row[0]: row[1] for row in by_priority},
            }

    def delete_feedback(self, feedback_id: int):
        """フィードバックを削除"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM feedbacks WHERE id = ?", (feedback_id,))
