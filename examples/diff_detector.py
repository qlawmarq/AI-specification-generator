import subprocess
from typing import Dict, List, Set
import hashlib
import json


class SemanticDiffDetector:
    def __init__(self):
        self.parser = Parser()
        # 複数言語対応
        self.languages = {
            "python": Language(tspython.language(), "python"),
            "javascript": Language(tsjavascript.language(), "javascript"),
        }

    def detect_semantic_changes(self, repo_path: Path) -> Dict:
        """セマンティックな変更を検出"""

        # 1. Gitで変更ファイルを取得
        changed_files = self._get_changed_files()

        # 2. 各ファイルの変更内容を詳細分析
        change_analysis = {}

        for file_path in changed_files:
            if self._is_supported_file(file_path):
                analysis = self._analyze_file_changes(file_path)
                change_analysis[file_path] = analysis

        return change_analysis

    def _get_changed_files(self) -> List[str]:
        """Git差分でファイル変更を検出"""
        cmd = ["git", "diff", "--name-only", "HEAD~1"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip().split("\n") if result.stdout else []

    def _analyze_file_changes(self, file_path: str) -> Dict:
        """ファイルの変更をAST レベルで分析"""

        # 変更前後のコードを取得
        old_content = self._get_file_at_commit(file_path, "HEAD~1")
        new_content = self._get_current_file_content(file_path)

        # AST解析
        lang = self._detect_language_from_path(file_path)
        self.parser.set_language(self.languages[lang])

        old_tree = self.parser.parse(bytes(old_content, "utf8"))
        new_tree = self.parser.parse(bytes(new_content, "utf8"))

        # セマンティック差分を抽出
        changes = self._extract_semantic_differences(old_tree, new_tree)

        return {
            "file_path": file_path,
            "language": lang,
            "changes": changes,
            "impact_score": self._calculate_impact_score(changes),
            "affected_functions": self._get_affected_functions(changes),
            "dependency_analysis": self._analyze_dependencies(file_path, changes),
        }

    def _extract_semantic_differences(self, old_tree, new_tree):
        """AST間のセマンティック差分を抽出"""

        # クエリでfunction/class定義を抽出
        function_query = """
        (function_definition
          name: (identifier) @function.name
          body: (block) @function.body) @function.def
        """

        class_query = """
        (class_definition
          name: (identifier) @class.name
          body: (block) @class.body) @class.def
        """

        old_functions = self._extract_code_elements(old_tree, function_query)
        new_functions = self._extract_code_elements(new_tree, function_query)

        old_classes = self._extract_code_elements(old_tree, class_query)
        new_classes = self._extract_code_elements(new_tree, class_query)

        return {
            "added_functions": set(new_functions) - set(old_functions),
            "removed_functions": set(old_functions) - set(new_functions),
            "modified_functions": self._find_modified_elements(
                old_functions, new_functions
            ),
            "added_classes": set(new_classes) - set(old_classes),
            "removed_classes": set(old_classes) - set(new_classes),
            "modified_classes": self._find_modified_elements(old_classes, new_classes),
        }
