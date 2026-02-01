"""
コードマスタ管理モジュール

弁護士事務所名・プロバイダ名から2文字コードへの変換を行う
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CodeMaster:
    """コードマスタ管理クラス"""

    def __init__(self, master_file: Optional[Path] = None):
        """
        Args:
            master_file: マスタファイルのパス（デフォルト: code_master.json）
        """
        if master_file is None:
            master_file = Path(__file__).parent / "code_master.json"

        self.master_file = master_file
        self.lawyers: dict = {}
        self.providers: dict = {}
        self._load_master()

    def _load_master(self) -> None:
        """マスタファイルを読み込む"""
        try:
            with open(self.master_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.lawyers = data.get('lawyers', {})
            self.providers = data.get('providers', {})
            logger.info(f"コードマスタを読み込みました: 弁護士{len(self.lawyers)}件, プロバイダ{len(self.providers)}件")
        except FileNotFoundError:
            logger.warning(f"マスタファイルが見つかりません: {self.master_file}")
        except json.JSONDecodeError as e:
            logger.error(f"マスタファイルの解析に失敗: {e}")

    def find_lawyer_code(self, text: str) -> str:
        """
        テキストから弁護士コードを検索

        Args:
            text: 検索対象のテキスト（事務所名など）

        Returns:
            2文字の弁護士コード（見つからない場合は"XX"）
        """
        if not text:
            return "XX"

        text_lower = text.lower()

        for code, info in self.lawyers.items():
            if code == "XX":
                continue
            # 正式名称でマッチ
            if info['name'] in text:
                return code
            # エイリアスでマッチ
            for alias in info.get('aliases', []):
                if alias.lower() in text_lower:
                    return code

        return "XX"

    def find_provider_code(self, text: str) -> str:
        """
        テキストからプロバイダコードを検索

        Args:
            text: 検索対象のテキスト（プロバイダ名など）

        Returns:
            2文字のプロバイダコード（見つからない場合は"XX"）
        """
        if not text:
            return "XX"

        text_lower = text.lower()

        for code, info in self.providers.items():
            if code == "XX":
                continue
            # 正式名称でマッチ
            if info['name'].lower() in text_lower:
                return code
            # エイリアスでマッチ
            for alias in info.get('aliases', []):
                if alias.lower() in text_lower:
                    return code

        return "XX"

    def get_lawyer_name(self, code: str) -> str:
        """コードから弁護士事務所名を取得"""
        return self.lawyers.get(code, {}).get('name', '不明')

    def get_provider_name(self, code: str) -> str:
        """コードからプロバイダ名を取得"""
        return self.providers.get(code, {}).get('name', '不明')

    def add_lawyer(self, code: str, name: str, aliases: list[str] = None) -> None:
        """弁護士コードを追加"""
        self.lawyers[code] = {
            'name': name,
            'aliases': aliases or []
        }
        self._save_master()

    def add_provider(self, code: str, name: str, aliases: list[str] = None) -> None:
        """プロバイダコードを追加"""
        self.providers[code] = {
            'name': name,
            'aliases': aliases or []
        }
        self._save_master()

    def _save_master(self) -> None:
        """マスタファイルを保存"""
        data = {
            'lawyers': self.lawyers,
            'providers': self.providers
        }
        with open(self.master_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("コードマスタを保存しました")

    def list_lawyers(self) -> dict:
        """全弁護士コードを取得"""
        return {code: info['name'] for code, info in self.lawyers.items()}

    def list_providers(self) -> dict:
        """全プロバイダコードを取得"""
        return {code: info['name'] for code, info in self.providers.items()}
