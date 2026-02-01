"""
PDF フィールド抽出 Webアプリ

起動方法:
    streamlit run app.py
"""

import streamlit as st
import tempfile
import os
from pathlib import Path
from datetime import datetime

from config import Config
from converter import PDFConverter
from ocr_service import GoogleVisionOCR
from field_extractor import FieldExtractor, ExtractedFields
from database import Database, Feedback
from exporter import CSVExporter
from code_master import CodeMaster

# ページ設定
st.set_page_config(
    page_title="PDF フィールド抽出",
    page_icon="📄",
    layout="wide",
)

# セッション状態の初期化
if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = []
if "db" not in st.session_state:
    Config.setup_directories()
    st.session_state.db = Database()
if "code_master" not in st.session_state:
    st.session_state.code_master = CodeMaster()


def init_services():
    """サービスを初期化"""
    try:
        converter = PDFConverter()
        ocr = GoogleVisionOCR()
        extractor = FieldExtractor()
        return converter, ocr, extractor, None
    except Exception as e:
        return None, None, None, str(e)


def process_pdf(pdf_file, converter, ocr, extractor) -> ExtractedFields:
    """PDFを処理してフィールドを抽出"""
    # 一時ファイルに保存
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_file.getvalue())
        tmp_path = Path(tmp.name)

    try:
        # PDF→画像変換
        image_paths = converter.convert(tmp_path)

        # OCR実行
        ocr_results = ocr.ocr_document(image_paths, tmp_path)
        ocr_text = ocr.get_combined_text(ocr_results)

        # フィールド抽出
        fields = extractor.extract(ocr_text, tmp_path)
        fields.pdf_path = pdf_file.name

        return fields

    finally:
        # 一時ファイル削除
        tmp_path.unlink(missing_ok=True)
        converter.cleanup(tmp_path)


def render_sidebar():
    """サイドバーを描画"""
    with st.sidebar:
        st.header("設定")

        # API キー状態
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        google_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        st.subheader("API状態")
        if anthropic_key:
            st.success("Claude API: 設定済み")
        else:
            st.error("Claude API: 未設定")
            st.text_input("ANTHROPIC_API_KEY", type="password", key="api_key_input")

        if google_creds and Path(google_creds).exists():
            st.success("Google Vision: 設定済み")
        else:
            st.warning("Google Vision: 未設定")

        st.divider()

        # 統計
        st.subheader("処理統計")
        stats = st.session_state.db.get_customer_stats()
        st.metric("総顧客数", stats["total"])

        if stats["by_lawyer"]:
            st.write("弁護士別:")
            for code, count in list(stats["by_lawyer"].items())[:5]:
                name = st.session_state.code_master.get_lawyer_name(code)
                st.write(f"  {code}: {name} ({count}件)")


def render_upload_tab():
    """アップロードタブを描画"""
    st.header("PDFアップロード")

    # ファイルアップロード
    uploaded_files = st.file_uploader(
        "PDFファイルを選択（複数可）",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        st.info(f"{len(uploaded_files)} 件のPDFが選択されています")

        if st.button("抽出開始", type="primary"):
            converter, ocr, extractor, error = init_services()

            if error:
                st.error(f"初期化エラー: {error}")
                return

            progress = st.progress(0)
            results = []

            for i, pdf_file in enumerate(uploaded_files):
                with st.spinner(f"処理中: {pdf_file.name}"):
                    try:
                        fields = process_pdf(pdf_file, converter, ocr, extractor)
                        results.append(fields)
                        st.success(f"完了: {pdf_file.name}")
                    except Exception as e:
                        st.error(f"エラー: {pdf_file.name} - {e}")

                progress.progress((i + 1) / len(uploaded_files))

            st.session_state.extracted_data = results
            st.success(f"{len(results)} 件の抽出が完了しました")

    # 抽出結果の表示
    if st.session_state.extracted_data:
        st.divider()
        st.subheader("抽出結果")

        for i, fields in enumerate(st.session_state.extracted_data):
            with st.expander(f"📄 {fields.pdf_path}", expanded=(i == 0)):
                col1, col2 = st.columns(2)

                with col1:
                    st.text_input("契約者名", value=fields.contractor_name, key=f"name_{i}")
                    st.text_input("ふりがな", value=fields.contractor_kana, key=f"kana_{i}")
                    st.text_input("利用者名", value=fields.user_name, key=f"user_{i}")
                    st.text_input("利用者ふりがな", value=fields.user_kana, key=f"user_kana_{i}")
                    st.text_input("郵便番号", value=fields.postal_code, key=f"zip_{i}")

                with col2:
                    st.text_input("住所", value=fields.address, key=f"addr_{i}")
                    st.text_input("電話番号", value=fields.phone, key=f"phone_{i}")
                    st.text_input("メール", value=fields.email, key=f"email_{i}")
                    st.text_input("弁護士", value=f"{fields.lawyer_code}: {fields.lawyer_name}", key=f"lawyer_{i}", disabled=True)
                    st.text_input("プロバイダ", value=f"{fields.provider_code}: {fields.provider_name}", key=f"provider_{i}", disabled=True)

                st.text_area("メモ", value=fields.memo, key=f"memo_{i}")

        # 保存ボタン
        col1, col2 = st.columns(2)
        with col1:
            if st.button("データベースに保存", type="primary"):
                for fields in st.session_state.extracted_data:
                    st.session_state.db.insert_customer_from_fields(fields)
                st.success("保存しました")
                st.session_state.extracted_data = []
                st.rerun()

        with col2:
            if st.button("クリア"):
                st.session_state.extracted_data = []
                st.rerun()


def render_history_tab():
    """履歴タブを描画"""
    st.header("処理履歴")

    # 検索
    search_query = st.text_input("検索（名前・住所）")

    if search_query:
        customers = st.session_state.db.search_customers(search_query)
    else:
        customers = st.session_state.db.get_all_customers()

    st.info(f"{len(customers)} 件")

    if customers:
        # テーブル表示用データ
        data = []
        for c in customers:
            data.append({
                "ID": c.id,
                "契約者名": c.contractor_name,
                "住所": c.address[:30] + "..." if len(c.address) > 30 else c.address,
                "電話番号": c.phone,
                "弁護士": c.lawyer_code,
                "プロバイダ": c.provider_code,
                "登録日": c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else "",
            })

        st.dataframe(data, use_container_width=True)

        # CSV出力
        if st.button("CSVダウンロード"):
            exporter = CSVExporter()
            csv_path = exporter.export_customers(st.session_state.db)
            with open(csv_path, "rb") as f:
                st.download_button(
                    "ダウンロード",
                    f,
                    file_name="customers.csv",
                    mime="text/csv",
                )


def render_master_tab():
    """マスタ管理タブを描画"""
    st.header("コードマスタ管理")

    tab1, tab2 = st.tabs(["弁護士", "プロバイダ"])

    with tab1:
        st.subheader("弁護士マスタ")

        lawyers = st.session_state.code_master.list_lawyers()
        for code, name in lawyers.items():
            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                st.text(code)
            with col2:
                st.text(name)

        st.divider()
        st.subheader("追加")
        col1, col2, col3 = st.columns([1, 2, 2])
        with col1:
            new_code = st.text_input("コード", max_chars=2, key="new_lawyer_code")
        with col2:
            new_name = st.text_input("事務所名", key="new_lawyer_name")
        with col3:
            new_aliases = st.text_input("別名（カンマ区切り）", key="new_lawyer_aliases")

        if st.button("弁護士追加"):
            if new_code and new_name:
                aliases = [a.strip() for a in new_aliases.split(",")] if new_aliases else []
                st.session_state.code_master.add_lawyer(new_code.upper(), new_name, aliases)
                st.success(f"追加しました: {new_code}")
                st.rerun()

    with tab2:
        st.subheader("プロバイダマスタ")

        providers = st.session_state.code_master.list_providers()
        for code, name in providers.items():
            col1, col2 = st.columns([1, 3])
            with col1:
                st.text(code)
            with col2:
                st.text(name)

        st.divider()
        st.subheader("追加")
        col1, col2, col3 = st.columns([1, 2, 2])
        with col1:
            new_code = st.text_input("コード", max_chars=2, key="new_provider_code")
        with col2:
            new_name = st.text_input("プロバイダ名", key="new_provider_name")
        with col3:
            new_aliases = st.text_input("別名（カンマ区切り）", key="new_provider_aliases")

        if st.button("プロバイダ追加"):
            if new_code and new_name:
                aliases = [a.strip() for a in new_aliases.split(",")] if new_aliases else []
                st.session_state.code_master.add_provider(new_code.upper(), new_name, aliases)
                st.success(f"追加しました: {new_code}")
                st.rerun()


def render_feedback_tab():
    """フィードバックタブを描画"""
    st.header("💬 改善提案・フィードバック")

    # 送信フォームと一覧を2カラムで表示
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("新しい提案を送信")

        with st.form("feedback_form"):
            category = st.selectbox(
                "カテゴリ",
                options=["ui", "feature", "bug", "performance", "other"],
                format_func=lambda x: {
                    "ui": "UI/操作性",
                    "feature": "機能追加",
                    "bug": "不具合報告",
                    "performance": "処理速度",
                    "other": "その他",
                }[x],
            )

            priority = st.selectbox(
                "優先度",
                options=["low", "medium", "high"],
                index=1,
                format_func=lambda x: {
                    "low": "低（あったらいいな）",
                    "medium": "中（改善希望）",
                    "high": "高（業務に支障）",
                }[x],
            )

            content = st.text_area(
                "内容（具体的に記載してください）",
                placeholder="例：住所入力時に郵便番号から自動補完できると便利です",
                height=150,
            )

            user_name = st.text_input("お名前（任意）")

            submitted = st.form_submit_button("送信する", type="primary")

            if submitted:
                if content.strip():
                    st.session_state.db.insert_feedback(
                        category=category,
                        content=content,
                        priority=priority,
                        user_name=user_name,
                    )
                    st.success("フィードバックを送信しました。ありがとうございます！")
                    st.rerun()
                else:
                    st.error("内容を入力してください")

    with col2:
        st.subheader("過去の提案")

        # 統計表示
        stats = st.session_state.db.get_feedback_stats()
        if stats["total"] > 0:
            cols = st.columns(4)
            with cols[0]:
                st.metric("総数", stats["total"])
            with cols[1]:
                pending = stats["by_status"].get("pending", 0)
                st.metric("未対応", pending)
            with cols[2]:
                in_progress = stats["by_status"].get("in_progress", 0)
                st.metric("対応中", in_progress)
            with cols[3]:
                done = stats["by_status"].get("done", 0)
                st.metric("完了", done)

        # フィルタ
        filter_status = st.selectbox(
            "ステータスで絞り込み",
            options=["all", "pending", "in_progress", "done", "rejected"],
            format_func=lambda x: {
                "all": "すべて",
                "pending": "未対応",
                "in_progress": "対応中",
                "done": "完了",
                "rejected": "却下",
            }[x],
        )

        # フィードバック一覧
        if filter_status == "all":
            feedbacks = st.session_state.db.get_all_feedbacks(limit=50)
        else:
            feedbacks = st.session_state.db.get_feedbacks_by_status(filter_status)

        if feedbacks:
            for fb in feedbacks:
                status_colors = {
                    "pending": "🟡",
                    "in_progress": "🔵",
                    "done": "🟢",
                    "rejected": "🔴",
                }
                category_labels = {
                    "ui": "UI/操作性",
                    "feature": "機能追加",
                    "bug": "不具合",
                    "performance": "速度",
                    "other": "その他",
                }
                priority_labels = {
                    "low": "低",
                    "medium": "中",
                    "high": "高",
                }

                with st.expander(
                    f"{status_colors.get(fb.status, '⚪')} [{category_labels.get(fb.category, fb.category)}] {fb.content[:40]}..."
                    if len(fb.content) > 40
                    else f"{status_colors.get(fb.status, '⚪')} [{category_labels.get(fb.category, fb.category)}] {fb.content}"
                ):
                    st.write(f"**内容:** {fb.content}")
                    st.write(f"**優先度:** {priority_labels.get(fb.priority, fb.priority)}")
                    st.write(f"**投稿者:** {fb.user_name or '匿名'}")
                    st.write(f"**登録日:** {fb.created_at.strftime('%Y/%m/%d %H:%M') if fb.created_at else '-'}")

                    # ステータス変更（管理用）
                    new_status = st.selectbox(
                        "ステータス変更",
                        options=["pending", "in_progress", "done", "rejected"],
                        index=["pending", "in_progress", "done", "rejected"].index(fb.status),
                        format_func=lambda x: {
                            "pending": "未対応",
                            "in_progress": "対応中",
                            "done": "完了",
                            "rejected": "却下",
                        }[x],
                        key=f"status_{fb.id}",
                    )

                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("更新", key=f"update_{fb.id}"):
                            st.session_state.db.update_feedback_status(fb.id, new_status)
                            st.success("更新しました")
                            st.rerun()
                    with col_b:
                        if st.button("削除", key=f"delete_{fb.id}"):
                            st.session_state.db.delete_feedback(fb.id)
                            st.success("削除しました")
                            st.rerun()
        else:
            st.info("フィードバックはまだありません")


def main():
    st.title("📄 PDF フィールド抽出システム")

    render_sidebar()

    # メインタブ
    tab1, tab2, tab3, tab4 = st.tabs(["アップロード", "履歴", "マスタ管理", "💬 フィードバック"])

    with tab1:
        render_upload_tab()

    with tab2:
        render_history_tab()

    with tab3:
        render_master_tab()

    with tab4:
        render_feedback_tab()


if __name__ == "__main__":
    main()
