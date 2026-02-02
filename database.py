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


@dataclass
class Disclosure:
    """プロバイダ開示文書レコード"""

    id: Optional[int]
    document_id: Optional[int]      # documentsテーブルとの関連
    document_number: str            # 管理番号 (SL3502等)
    provider_name: str              # プロバイダ名
    disclosure_date: str            # 開示日
    court_case_number: str          # 裁判所事件番号
    requester_name: str             # 請求者（著作権者）
    requester_lawyer: str           # 請求者代理人
    created_at: datetime

    @classmethod
    def from_row(cls, row: tuple) -> "Disclosure":
        return cls(
            id=row[0],
            document_id=row[1],
            document_number=row[2],
            provider_name=row[3],
            disclosure_date=row[4],
            court_case_number=row[5],
            requester_name=row[6],
            requester_lawyer=row[7],
            created_at=datetime.fromisoformat(row[8]) if row[8] else None,
        )


@dataclass
class DisclosedSubscriber:
    """開示された契約者情報レコード"""

    id: Optional[int]
    disclosure_id: int              # disclosuresとの関連
    sequence_number: int            # 番号（リスト内の順番）
    catalog_number: int             # 目録番号
    subscriber_name: str            # 契約者氏名
    subscriber_address: str         # 契約者住所
    subscriber_postal_code: str     # 郵便番号
    subscriber_phone: str           # 電話番号
    subscriber_email: str           # メールアドレス
    ip_address: str                 # IPアドレス
    port_number: int                # ポート番号
    communication_datetime: str     # 通信日時
    created_at: datetime

    @classmethod
    def from_row(cls, row: tuple) -> "DisclosedSubscriber":
        return cls(
            id=row[0],
            disclosure_id=row[1],
            sequence_number=row[2],
            catalog_number=row[3],
            subscriber_name=row[4],
            subscriber_address=row[5],
            subscriber_postal_code=row[6],
            subscriber_phone=row[7],
            subscriber_email=row[8],
            ip_address=row[9],
            port_number=row[10],
            communication_datetime=row[11],
            created_at=datetime.fromisoformat(row[12]) if row[12] else None,
        )


@dataclass
class AcceptanceNotice:
    """受任通知レコード"""

    id: Optional[int]
    document_id: Optional[int]      # documentsテーブルとの関連
    notice_date: str                # 通知日
    court_case_number: str          # 裁判所事件番号

    # 契約者情報（プロバイダ開示の名義人）
    subscriber_name: str            # 契約名義人
    subscriber_address: str
    subscriber_postal_code: str

    # 利用者情報（実際の依頼者）
    user_name: str                  # 当職依頼者/利用者
    user_address: str
    user_postal_code: str
    user_phone: str
    user_email: str
    is_same_as_subscriber: bool     # 契約者と利用者が同一人物か

    # 相手方情報
    plaintiff_name: str             # 貴職依頼者（著作権者）
    plaintiff_lawyer_firm: str      # 相手方弁護士事務所
    plaintiff_lawyer_name: str      # 相手方弁護士名

    # 依頼者側弁護士情報
    lawyer_firm: str                # 弁護士事務所名
    lawyer_name: str                # 担当弁護士名
    lawyer_address: str
    lawyer_phone: str
    lawyer_fax: str
    lawyer_email: str

    # 侵害情報
    infringement_ip: str
    infringement_datetime: str
    work_title: str                 # 著作物名
    work_hash: str                  # ハッシュ値

    created_at: datetime

    @classmethod
    def from_row(cls, row: tuple) -> "AcceptanceNotice":
        return cls(
            id=row[0],
            document_id=row[1],
            notice_date=row[2],
            court_case_number=row[3],
            subscriber_name=row[4],
            subscriber_address=row[5],
            subscriber_postal_code=row[6],
            user_name=row[7],
            user_address=row[8],
            user_postal_code=row[9],
            user_phone=row[10],
            user_email=row[11],
            is_same_as_subscriber=bool(row[12]),
            plaintiff_name=row[13],
            plaintiff_lawyer_firm=row[14],
            plaintiff_lawyer_name=row[15],
            lawyer_firm=row[16],
            lawyer_name=row[17],
            lawyer_address=row[18],
            lawyer_phone=row[19],
            lawyer_fax=row[20],
            lawyer_email=row[21],
            infringement_ip=row[22],
            infringement_datetime=row[23],
            work_title=row[24],
            work_hash=row[25],
            created_at=datetime.fromisoformat(row[26]) if row[26] else None,
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

                -- ==================== プロバイダ開示 ====================

                CREATE TABLE IF NOT EXISTS disclosures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER,
                    document_number TEXT,
                    provider_name TEXT,
                    disclosure_date TEXT,
                    court_case_number TEXT,
                    requester_name TEXT,
                    requester_lawyer TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                );

                CREATE INDEX IF NOT EXISTS idx_disclosures_provider
                ON disclosures(provider_name);

                CREATE INDEX IF NOT EXISTS idx_disclosures_court_case
                ON disclosures(court_case_number);

                CREATE TABLE IF NOT EXISTS disclosed_subscribers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    disclosure_id INTEGER NOT NULL,
                    sequence_number INTEGER,
                    catalog_number INTEGER,
                    subscriber_name TEXT,
                    subscriber_address TEXT,
                    subscriber_postal_code TEXT,
                    subscriber_phone TEXT,
                    subscriber_email TEXT,
                    ip_address TEXT,
                    port_number INTEGER,
                    communication_datetime TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (disclosure_id) REFERENCES disclosures(id)
                );

                CREATE INDEX IF NOT EXISTS idx_disclosed_subscribers_disclosure
                ON disclosed_subscribers(disclosure_id);

                CREATE INDEX IF NOT EXISTS idx_disclosed_subscribers_name
                ON disclosed_subscribers(subscriber_name);

                CREATE INDEX IF NOT EXISTS idx_disclosed_subscribers_ip
                ON disclosed_subscribers(ip_address);

                -- ==================== 受任通知 ====================

                CREATE TABLE IF NOT EXISTS acceptance_notices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER,
                    notice_date TEXT,
                    court_case_number TEXT,

                    -- 契約者情報
                    subscriber_name TEXT,
                    subscriber_address TEXT,
                    subscriber_postal_code TEXT,

                    -- 利用者情報
                    user_name TEXT,
                    user_address TEXT,
                    user_postal_code TEXT,
                    user_phone TEXT,
                    user_email TEXT,
                    is_same_as_subscriber INTEGER DEFAULT 1,

                    -- 相手方情報
                    plaintiff_name TEXT,
                    plaintiff_lawyer_firm TEXT,
                    plaintiff_lawyer_name TEXT,

                    -- 依頼者側弁護士情報
                    lawyer_firm TEXT,
                    lawyer_name TEXT,
                    lawyer_address TEXT,
                    lawyer_phone TEXT,
                    lawyer_fax TEXT,
                    lawyer_email TEXT,

                    -- 侵害情報
                    infringement_ip TEXT,
                    infringement_datetime TEXT,
                    work_title TEXT,
                    work_hash TEXT,

                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                );

                CREATE INDEX IF NOT EXISTS idx_acceptance_notices_court_case
                ON acceptance_notices(court_case_number);

                CREATE INDEX IF NOT EXISTS idx_acceptance_notices_subscriber
                ON acceptance_notices(subscriber_name);

                CREATE INDEX IF NOT EXISTS idx_acceptance_notices_user
                ON acceptance_notices(user_name);

                CREATE INDEX IF NOT EXISTS idx_acceptance_notices_plaintiff
                ON acceptance_notices(plaintiff_name);
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
            conn.execute("DELETE FROM disclosures")
            conn.execute("DELETE FROM disclosed_subscribers")
            conn.execute("DELETE FROM acceptance_notices")

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

    # ==================== プロバイダ開示 ====================

    def insert_disclosure(
        self,
        document_number: str = "",
        provider_name: str = "",
        disclosure_date: str = "",
        court_case_number: str = "",
        requester_name: str = "",
        requester_lawyer: str = "",
        document_id: int = None,
    ) -> int:
        """
        プロバイダ開示文書を挿入

        Returns:
            挿入されたレコードのID
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO disclosures
                (document_id, document_number, provider_name, disclosure_date,
                 court_case_number, requester_name, requester_lawyer)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (document_id, document_number, provider_name, disclosure_date,
                 court_case_number, requester_name, requester_lawyer),
            )
            return cursor.lastrowid

    def insert_disclosed_subscriber(
        self,
        disclosure_id: int,
        subscriber_name: str = "",
        subscriber_address: str = "",
        subscriber_postal_code: str = "",
        subscriber_phone: str = "",
        subscriber_email: str = "",
        ip_address: str = "",
        port_number: int = 0,
        communication_datetime: str = "",
        sequence_number: int = 0,
        catalog_number: int = 0,
    ) -> int:
        """
        開示された契約者情報を挿入

        Returns:
            挿入されたレコードのID
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO disclosed_subscribers
                (disclosure_id, sequence_number, catalog_number,
                 subscriber_name, subscriber_address, subscriber_postal_code,
                 subscriber_phone, subscriber_email,
                 ip_address, port_number, communication_datetime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (disclosure_id, sequence_number, catalog_number,
                 subscriber_name, subscriber_address, subscriber_postal_code,
                 subscriber_phone, subscriber_email,
                 ip_address, port_number, communication_datetime),
            )
            return cursor.lastrowid

    def get_disclosure(self, disclosure_id: int) -> Optional[Disclosure]:
        """IDでプロバイダ開示を取得"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM disclosures WHERE id = ?", (disclosure_id,)
            ).fetchone()
            return Disclosure.from_row(row) if row else None

    def get_all_disclosures(self) -> List[Disclosure]:
        """全プロバイダ開示を取得"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM disclosures ORDER BY created_at DESC"
            ).fetchall()
            return [Disclosure.from_row(row) for row in rows]

    def get_disclosed_subscribers(self, disclosure_id: int) -> List[DisclosedSubscriber]:
        """開示IDで契約者リストを取得"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM disclosed_subscribers WHERE disclosure_id = ? ORDER BY sequence_number",
                (disclosure_id,),
            ).fetchall()
            return [DisclosedSubscriber.from_row(row) for row in rows]

    def search_disclosed_subscribers(self, query: str, limit: int = 100) -> List[DisclosedSubscriber]:
        """契約者を検索（名前・住所・IP）"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM disclosed_subscribers
                WHERE subscriber_name LIKE ?
                   OR subscriber_address LIKE ?
                   OR ip_address LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", f"%{query}%", limit),
            ).fetchall()
            return [DisclosedSubscriber.from_row(row) for row in rows]

    # ==================== 受任通知 ====================

    def insert_acceptance_notice(
        self,
        notice_date: str = "",
        court_case_number: str = "",
        subscriber_name: str = "",
        subscriber_address: str = "",
        subscriber_postal_code: str = "",
        user_name: str = "",
        user_address: str = "",
        user_postal_code: str = "",
        user_phone: str = "",
        user_email: str = "",
        is_same_as_subscriber: bool = True,
        plaintiff_name: str = "",
        plaintiff_lawyer_firm: str = "",
        plaintiff_lawyer_name: str = "",
        lawyer_firm: str = "",
        lawyer_name: str = "",
        lawyer_address: str = "",
        lawyer_phone: str = "",
        lawyer_fax: str = "",
        lawyer_email: str = "",
        infringement_ip: str = "",
        infringement_datetime: str = "",
        work_title: str = "",
        work_hash: str = "",
        document_id: int = None,
    ) -> int:
        """
        受任通知を挿入

        Returns:
            挿入されたレコードのID
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO acceptance_notices
                (document_id, notice_date, court_case_number,
                 subscriber_name, subscriber_address, subscriber_postal_code,
                 user_name, user_address, user_postal_code, user_phone, user_email,
                 is_same_as_subscriber,
                 plaintiff_name, plaintiff_lawyer_firm, plaintiff_lawyer_name,
                 lawyer_firm, lawyer_name, lawyer_address, lawyer_phone, lawyer_fax, lawyer_email,
                 infringement_ip, infringement_datetime, work_title, work_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (document_id, notice_date, court_case_number,
                 subscriber_name, subscriber_address, subscriber_postal_code,
                 user_name, user_address, user_postal_code, user_phone, user_email,
                 1 if is_same_as_subscriber else 0,
                 plaintiff_name, plaintiff_lawyer_firm, plaintiff_lawyer_name,
                 lawyer_firm, lawyer_name, lawyer_address, lawyer_phone, lawyer_fax, lawyer_email,
                 infringement_ip, infringement_datetime, work_title, work_hash),
            )
            return cursor.lastrowid

    def get_acceptance_notice(self, notice_id: int) -> Optional[AcceptanceNotice]:
        """IDで受任通知を取得"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM acceptance_notices WHERE id = ?", (notice_id,)
            ).fetchone()
            return AcceptanceNotice.from_row(row) if row else None

    def get_all_acceptance_notices(self) -> List[AcceptanceNotice]:
        """全受任通知を取得"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM acceptance_notices ORDER BY created_at DESC"
            ).fetchall()
            return [AcceptanceNotice.from_row(row) for row in rows]

    def get_acceptance_notices_by_plaintiff(self, plaintiff_name: str) -> List[AcceptanceNotice]:
        """著作権者名で受任通知を取得"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM acceptance_notices WHERE plaintiff_name LIKE ? ORDER BY created_at DESC",
                (f"%{plaintiff_name}%",),
            ).fetchall()
            return [AcceptanceNotice.from_row(row) for row in rows]

    def search_acceptance_notices(self, query: str, limit: int = 100) -> List[AcceptanceNotice]:
        """受任通知を検索（名前・事件番号）"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM acceptance_notices
                WHERE subscriber_name LIKE ?
                   OR user_name LIKE ?
                   OR court_case_number LIKE ?
                   OR plaintiff_name LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", limit),
            ).fetchall()
            return [AcceptanceNotice.from_row(row) for row in rows]

    def get_acceptance_notice_stats(self) -> dict:
        """受任通知の統計を取得"""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM acceptance_notices").fetchone()[0]

            # 契約者と利用者が異なるケース
            different_user = conn.execute(
                "SELECT COUNT(*) FROM acceptance_notices WHERE is_same_as_subscriber = 0"
            ).fetchone()[0]

            by_plaintiff = conn.execute(
                """
                SELECT plaintiff_name, COUNT(*) as count
                FROM acceptance_notices
                WHERE plaintiff_name IS NOT NULL AND plaintiff_name != ''
                GROUP BY plaintiff_name
                ORDER BY count DESC
                LIMIT 10
                """
            ).fetchall()

            by_lawyer_firm = conn.execute(
                """
                SELECT lawyer_firm, COUNT(*) as count
                FROM acceptance_notices
                WHERE lawyer_firm IS NOT NULL AND lawyer_firm != ''
                GROUP BY lawyer_firm
                ORDER BY count DESC
                LIMIT 10
                """
            ).fetchall()

            return {
                "total": total,
                "different_user_count": different_user,
                "by_plaintiff": {row[0]: row[1] for row in by_plaintiff},
                "by_lawyer_firm": {row[0]: row[1] for row in by_lawyer_firm},
            }
