# package/github_bridge/gui_fetch.py
"""
GitHub 레포지토리 정보를 AI용으로 가져오는 GUI 프로그램
"""
import sys
import os
from pathlib import Path
from typing import List, Optional

# 프로젝트 루트를 sys.path에 추가
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QProgressBar, QCheckBox, QSpinBox, QGroupBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

import httpx

BASE_URL = "http://localhost:8787"


class FetchWorker(QThread):
    """백그라운드에서 GitHub 데이터를 가져오는 워커"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, owner: str, repo: str, files: List[str], 
                 include_issues: bool, max_issues: int):
        super().__init__()
        self.owner = owner
        self.repo = repo
        self.files = files
        self.include_issues = include_issues
        self.max_issues = max_issues

    def run(self):
        try:
            output = []
            
            # 레포지토리 정보
            self.progress.emit("Fetching repository information...")
            repo_info = self._fetch_repo_info()
            output.append(f"# GitHub Repository: {self.owner}/{self.repo}\n\n")
            output.append(f"## Repository Information\n")
            output.append(f"- Name: {repo_info.get('full_name')}\n")
            output.append(f"- Description: {repo_info.get('description', 'N/A')}\n")
            output.append(f"- Default Branch: {repo_info.get('default_branch')}\n")
            output.append(f"- Stars: {repo_info.get('stargazers_count')}\n")
            output.append(f"- Issues: {repo_info.get('open_issues_count')}\n")
            output.append(f"\n")
            
            # 파일 내용
            if self.files:
                output.append(f"## File Contents\n\n")
                default_branch = repo_info.get("default_branch", "main")
                
                for i, file_path in enumerate(self.files):
                    self.progress.emit(f"Fetching file {i+1}/{len(self.files)}: {file_path}...")
                    try:
                        file_data = self._fetch_file(file_path, default_branch)
                        if file_data.get("type") == "file":
                            content = file_data.get("decoded", "")
                            output.append(f"### {file_path}\n\n")
                            output.append("```\n")
                            output.append(content)
                            output.append("\n```\n\n")
                    except Exception as e:
                        output.append(f"### {file_path}\n\n")
                        output.append(f"Error: {e}\n\n")
            
            # 이슈 목록
            if self.include_issues:
                self.progress.emit(f"Fetching issues (max {self.max_issues})...")
                try:
                    issue_list = self._fetch_issues()
                    output.append(f"## Issues\n\n")
                    output.append(f"Total Issues: {len(issue_list)}\n\n")
                    
                    for issue in issue_list[:self.max_issues]:
                        number = issue.get("number")
                        title = issue.get("title", "N/A")
                        state = issue.get("state", "N/A")
                        created = issue.get("created_at", "N/A")
                        labels = [l.get("name") for l in issue.get("labels", [])]
                        
                        output.append(f"### Issue #{number}: {title}\n")
                        output.append(f"- State: {state}\n")
                        output.append(f"- Created: {created}\n")
                        if labels:
                            output.append(f"- Labels: {', '.join(labels)}\n")
                        output.append(f"- URL: {issue.get('html_url')}\n")
                        
                        body = issue.get("body", "")
                        if body:
                            body_preview = body[:200] + "..." if len(body) > 200 else body
                            output.append(f"- Body Preview: {body_preview}\n")
                        output.append(f"\n")
                except Exception as e:
                    output.append(f"Error fetching issues: {e}\n\n")
            
            self.finished.emit("".join(output))
            
        except Exception as e:
            self.error.emit(str(e))

    def _fetch_repo_info(self):
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"{BASE_URL}/get_repo", 
                          params={"owner": self.owner, "repo": self.repo})
            r.raise_for_status()
            return r.json()

    def _fetch_file(self, path: str, ref: str):
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"{BASE_URL}/fetch_file",
                          params={"owner": self.owner, "repo": self.repo, 
                                 "path": path, "ref": ref})
            r.raise_for_status()
            return r.json()

    def _fetch_issues(self):
        q = f"repo:{self.owner}/{self.repo} is:issue state:all"
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"{BASE_URL}/search_issues",
                          params={"q": q, "per_page": self.max_issues})
            r.raise_for_status()
            return r.json().get("items", [])


class GitHubFetchGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitHub Repository Fetcher for AI")
        self.setGeometry(100, 100, 900, 700)
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 레포지토리 정보 입력
        repo_group = QGroupBox("Repository Information")
        repo_layout = QVBoxLayout()
        
        # Owner
        owner_layout = QHBoxLayout()
        owner_layout.addWidget(QLabel("Owner:"))
        self.owner_input = QLineEdit("HENRY9300807")
        owner_layout.addWidget(self.owner_input)
        repo_layout.addLayout(owner_layout)
        
        # Repo
        repo_input_layout = QHBoxLayout()
        repo_input_layout.addWidget(QLabel("Repository:"))
        self.repo_input = QLineEdit("vision-sorter")
        repo_input_layout.addWidget(self.repo_input)
        repo_layout.addLayout(repo_input_layout)
        
        repo_group.setLayout(repo_layout)
        layout.addWidget(repo_group)
        
        # 파일 선택
        files_group = QGroupBox("Files to Fetch")
        files_layout = QVBoxLayout()
        
        # 파일 입력
        file_input_layout = QHBoxLayout()
        file_input_layout.addWidget(QLabel("File Path:"))
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("예: main.py 또는 package/capture_96_limit.py")
        self.file_input.setToolTip(
            "GitHub 레포지토리 루트 기준 파일 경로\n"
            "예시:\n"
            "- main.py (루트 파일)\n"
            "- package/capture_96_limit.py (하위 폴더 파일)\n"
            "- ui/color_definition.py\n"
            "⚠️ 로컬 경로가 아닌 GitHub 경로를 입력하세요!"
        )
        file_input_layout.addWidget(self.file_input)
        self.add_file_btn = QPushButton("Add")
        self.add_file_btn.clicked.connect(self.add_file)
        file_input_layout.addWidget(self.add_file_btn)
        files_layout.addLayout(file_input_layout)
        
        # 도움말 라벨
        help_label = QLabel("💡 팁: GitHub 레포지토리 루트 기준으로 경로 입력 (예: main.py, package/file.py)")
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: gray; font-size: 9pt;")
        files_layout.addWidget(help_label)
        
        # 파일 목록
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(150)
        files_layout.addWidget(self.file_list)
        
        # 파일 삭제 버튼
        remove_file_btn = QPushButton("Remove Selected")
        remove_file_btn.clicked.connect(self.remove_file)
        files_layout.addWidget(remove_file_btn)
        
        # 자동 파일 탐색 버튼
        auto_files_btn = QPushButton("🔍 Auto Find Files")
        auto_files_btn.clicked.connect(self.auto_find_files)
        auto_files_btn.setToolTip("레포지토리에서 주요 파일을 자동으로 탐색합니다 (main.py, README.md 등)")
        files_layout.addWidget(auto_files_btn)
        
        # 모든 파일 가져오기 버튼
        all_files_btn = QPushButton("📁 Get All Files")
        all_files_btn.clicked.connect(self.get_all_files)
        all_files_btn.setToolTip("브랜치의 모든 파일을 가져옵니다 (재귀적 탐색)")
        all_files_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        files_layout.addWidget(all_files_btn)
        
        files_group.setLayout(files_layout)
        layout.addWidget(files_group)
        
        # 이슈 옵션
        issues_group = QGroupBox("Issues")
        issues_layout = QHBoxLayout()
        self.include_issues_check = QCheckBox("Include Issues")
        self.include_issues_check.setChecked(True)
        issues_layout.addWidget(self.include_issues_check)
        issues_layout.addWidget(QLabel("Max Issues:"))
        self.max_issues_spin = QSpinBox()
        self.max_issues_spin.setMinimum(1)
        self.max_issues_spin.setMaximum(1000)
        self.max_issues_spin.setValue(50)
        issues_layout.addWidget(self.max_issues_spin)
        issues_layout.addStretch()
        issues_group.setLayout(issues_layout)
        layout.addWidget(issues_group)
        
        # 버튼들
        button_layout = QHBoxLayout()
        self.fetch_btn = QPushButton("Fetch Repository Info")
        self.fetch_btn.clicked.connect(self.start_fetch)
        button_layout.addWidget(self.fetch_btn)
        
        self.save_btn = QPushButton("Save to File")
        self.save_btn.clicked.connect(self.save_to_file)
        self.save_btn.setEnabled(False)
        button_layout.addWidget(self.save_btn)
        
        self.copy_btn = QPushButton("Copy to Clipboard")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.copy_btn.setEnabled(False)
        button_layout.addWidget(self.copy_btn)
        
        layout.addLayout(button_layout)
        
        # 진행 상태
        self.progress_label = QLabel("Ready")
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 결과 출력
        result_label = QLabel("Result:")
        layout.addWidget(result_label)
        
        self.result_text = QTextEdit()
        self.result_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.result_text)
        
        # 워커
        self.worker = None

    def add_file(self):
        file_path = self.file_input.text().strip()
        if file_path:
            self.file_list.addItem(file_path)
            self.file_input.clear()

    def remove_file(self):
        current_item = self.file_list.currentItem()
        if current_item:
            self.file_list.takeItem(self.file_list.row(current_item))

    def auto_find_files(self):
        """자동으로 주요 파일 탐색"""
        owner = self.owner_input.text().strip()
        repo = self.repo_input.text().strip()
        
        if not owner or not repo:
            QMessageBox.warning(self, "Error", "Owner and Repository를 먼저 입력하세요!")
            return
        
        self.progress_label.setText("주요 파일 탐색 중...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        try:
            # fetch_for_ai의 get_default_files 함수 사용
            from package.github_bridge.fetch_for_ai import get_default_files
            files = get_default_files(owner, repo)
            
            # 파일 목록 업데이트
            self.file_list.clear()
            for file_path in files:
                self.file_list.addItem(file_path)
            
            self.progress_bar.setVisible(False)
            self.progress_label.setText(f"✅ {len(files)}개 주요 파일 발견: {', '.join(files)}")
            QMessageBox.information(self, "Success", f"자동으로 {len(files)}개 주요 파일을 찾았습니다!")
        except Exception as e:
            self.progress_bar.setVisible(False)
            self.progress_label.setText(f"오류: {str(e)}")
            QMessageBox.warning(self, "Error", f"파일 탐색 실패:\n{str(e)}")
    
    def get_all_files(self):
        """브랜치의 모든 파일 가져오기"""
        owner = self.owner_input.text().strip()
        repo = self.repo_input.text().strip()
        
        if not owner or not repo:
            QMessageBox.warning(self, "Error", "Owner and Repository를 먼저 입력하세요!")
            return
        
        # 확인 다이얼로그
        reply = QMessageBox.question(
            self, "Get All Files",
            f"{owner}/{repo} 브랜치의 모든 파일을 가져옵니다.\n"
            f"파일이 많으면 시간이 걸릴 수 있습니다.\n\n"
            f"계속하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.progress_label.setText("모든 파일 탐색 중... (시간이 걸릴 수 있습니다)")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.file_list.clear()
        
        try:
            # fetch_for_ai의 get_all_files 함수 사용
            from package.github_bridge.fetch_for_ai import get_all_files
            files = get_all_files(owner, repo)
            
            # 파일 목록 업데이트
            for file_path in files:
                self.file_list.addItem(file_path)
            
            self.progress_bar.setVisible(False)
            self.progress_label.setText(f"✅ {len(files)}개 파일 발견!")
            QMessageBox.information(
                self, "Success", 
                f"✅ {len(files)}개 파일을 모두 찾았습니다!\n\n"
                f"이제 'Fetch Repository Info' 버튼을 클릭하세요."
            )
        except Exception as e:
            self.progress_bar.setVisible(False)
            self.progress_label.setText(f"오류: {str(e)}")
            QMessageBox.critical(self, "Error", f"파일 탐색 실패:\n{str(e)}")
    
    def start_fetch(self):
        owner = self.owner_input.text().strip()
        repo = self.repo_input.text().strip()
        
        if not owner or not repo:
            QMessageBox.warning(self, "Error", "Owner and Repository are required!")
            return
        
        files = []
        for i in range(self.file_list.count()):
            files.append(self.file_list.item(i).text())
        
        # 파일이 없으면 자동 탐색 제안
        if not files:
            reply = QMessageBox.question(
                self, "No Files Selected",
                "파일이 선택되지 않았습니다.\n자동으로 주요 파일을 탐색하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.auto_find_files()
                # 자동 탐색 후 다시 파일 목록 가져오기
                files = []
                for i in range(self.file_list.count()):
                    files.append(self.file_list.item(i).text())
            else:
                QMessageBox.warning(self, "Error", "최소 1개 이상의 파일을 선택하세요!")
                return
        
        # UI 비활성화
        self.fetch_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 무한 진행바
        self.result_text.clear()
        
        # 워커 시작
        self.worker = FetchWorker(
            owner=owner,
            repo=repo,
            files=files,
            include_issues=self.include_issues_check.isChecked(),
            max_issues=self.max_issues_spin.value()
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def update_progress(self, message: str):
        self.progress_label.setText(message)

    def on_finished(self, result: str):
        self.result_text.setPlainText(result)
        self.progress_bar.setVisible(False)
        self.fetch_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)
        self.progress_label.setText("Completed!")
        QMessageBox.information(self, "Success", "Repository information fetched successfully!")

    def on_error(self, error: str):
        self.progress_bar.setVisible(False)
        self.fetch_btn.setEnabled(True)
        self.progress_label.setText(f"Error: {error}")
        QMessageBox.critical(self, "Error", f"Failed to fetch repository information:\n{error}")

    def save_to_file(self):
        if not self.result_text.toPlainText():
            QMessageBox.warning(self, "Warning", "No data to save!")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Repository Info", "repo_info.txt", "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(self.result_text.toPlainText())
                QMessageBox.information(self, "Success", f"Saved to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")

    def copy_to_clipboard(self):
        text = self.result_text.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "Success", "Copied to clipboard!")
        else:
            QMessageBox.warning(self, "Warning", "No data to copy!")


def main():
    app = QApplication(sys.argv)
    
    # CI 가드
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    
    window = GitHubFetchGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

