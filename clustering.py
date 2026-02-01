"""ベクトル化 & クラスタリングモジュール"""

from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass

import numpy as np
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler
from sentence_transformers import SentenceTransformer

from config import Config
from feature_extractor import DocumentFeatures


@dataclass
class ClusterResult:
    """クラスタリング結果"""

    pdf_path: Path
    cluster_id: int
    combined_vector: np.ndarray


class DocumentClusterer:
    """文書クラスタリングクラス"""

    def __init__(self):
        self.embedding_model = None  # 遅延ロード
        self.scaler = StandardScaler()

    def _load_embedding_model(self):
        """埋め込みモデルを遅延ロード"""
        if self.embedding_model is None:
            print("埋め込みモデルをロード中...")
            self.embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)

    def compute_text_embeddings(self, texts: List[str]) -> np.ndarray:
        """テキストを埋め込みベクトルに変換"""
        self._load_embedding_model()

        # 空テキストの処理
        processed_texts = [t if t.strip() else "空のドキュメント" for t in texts]
        embeddings = self.embedding_model.encode(
            processed_texts, show_progress_bar=True
        )

        return np.array(embeddings)

    def combine_features(
        self,
        text_embeddings: np.ndarray,
        layout_features: List[np.ndarray],
        text_weight: float = None,
        layout_weight: float = None,
    ) -> np.ndarray:
        """
        テキスト埋め込みとレイアウト特徴量を結合

        Args:
            text_embeddings: テキスト埋め込み (n_docs, embedding_dim)
            layout_features: レイアウト特徴量のリスト
            text_weight: テキスト特徴量の重み
            layout_weight: レイアウト特徴量の重み

        Returns:
            結合された特徴量ベクトル
        """
        text_weight = text_weight or Config.TEXT_WEIGHT
        layout_weight = layout_weight or Config.LAYOUT_WEIGHT

        # レイアウト特徴量を配列に変換
        layout_array = np.array(layout_features)

        # 正規化
        text_normalized = self.scaler.fit_transform(text_embeddings)
        layout_normalized = self.scaler.fit_transform(layout_array)

        # 重み付け結合
        combined = np.hstack(
            [text_normalized * text_weight, layout_normalized * layout_weight]
        )

        return combined

    def cluster(
        self,
        features: np.ndarray,
        method: str = None,
        n_clusters: int = None,
    ) -> np.ndarray:
        """
        クラスタリングを実行

        Args:
            features: 特徴量ベクトル
            method: "dbscan" or "kmeans"
            n_clusters: k-meansの場合のクラスタ数

        Returns:
            クラスタラベルの配列
        """
        method = method or Config.CLUSTERING_METHOD

        if method == "dbscan":
            clusterer = DBSCAN(
                eps=Config.DBSCAN_EPS,
                min_samples=Config.DBSCAN_MIN_SAMPLES,
                metric="cosine",
            )
        elif method == "kmeans":
            n_clusters = n_clusters or Config.KMEANS_N_CLUSTERS
            # データ数がクラスタ数より少ない場合は調整
            n_clusters = min(n_clusters, len(features))
            clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        else:
            raise ValueError(f"未対応のクラスタリング手法: {method}")

        labels = clusterer.fit_predict(features)
        return labels

    def process(
        self,
        doc_features: List[DocumentFeatures],
        method: str = None,
        n_clusters: int = None,
    ) -> List[ClusterResult]:
        """
        文書特徴量からクラスタリングまで一括処理

        Args:
            doc_features: DocumentFeatures のリスト
            method: クラスタリング手法
            n_clusters: k-meansの場合のクラスタ数

        Returns:
            ClusterResult のリスト
        """
        if not doc_features:
            return []

        # テキスト埋め込み計算
        texts = [df.text for df in doc_features]
        text_embeddings = self.compute_text_embeddings(texts)

        # レイアウト特徴量取得
        layout_features = [df.layout_features for df in doc_features]

        # 特徴量結合
        combined = self.combine_features(text_embeddings, layout_features)

        # クラスタリング
        labels = self.cluster(combined, method, n_clusters)

        # 結果をまとめる
        results = []
        for df, label, vector in zip(doc_features, labels, combined):
            results.append(
                ClusterResult(
                    pdf_path=df.pdf_path,
                    cluster_id=int(label),
                    combined_vector=vector,
                )
            )

        return results

    def get_cluster_summary(self, results: List[ClusterResult]) -> Dict[int, List[Path]]:
        """
        クラスタごとのPDFリストを取得

        Args:
            results: ClusterResult のリスト

        Returns:
            {cluster_id: [pdf_paths]} の辞書
        """
        summary = {}
        for r in results:
            if r.cluster_id not in summary:
                summary[r.cluster_id] = []
            summary[r.cluster_id].append(r.pdf_path)
        return summary

    def print_cluster_summary(self, results: List[ClusterResult]):
        """クラスタリング結果のサマリーを表示"""
        summary = self.get_cluster_summary(results)

        print("\n=== クラスタリング結果 ===")
        for cluster_id in sorted(summary.keys()):
            pdfs = summary[cluster_id]
            label = "ノイズ" if cluster_id == -1 else f"クラスタ {cluster_id}"
            print(f"\n[{label}] ({len(pdfs)}件)")
            for pdf in pdfs[:5]:  # 最大5件表示
                print(f"  - {pdf.name}")
            if len(pdfs) > 5:
                print(f"  ... 他 {len(pdfs) - 5}件")
