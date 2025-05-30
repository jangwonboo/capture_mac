import sys
import os
# from PyQt5 import QtWidgets, uic # PyQt5 관련 임포트 주석 처리 또는 삭제
# from PyQt5.QtWidgets import QFileDialog, QMessageBox
# from PyQt5.QtCore import QThread, pyqtSignal
import subprocess
import json
from pathlib import Path

# PyQt6 임포트
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal

# pyuic6로 변환된 UI 파일에서 클래스 임포트
# pyuic6 실행 시 -o 옵션으로 지정한 파일 이름과 Ui_MainWindow 클래스 이름이 맞는지 확인하세요.
from legacy.ui_main_gui import Ui_MainWindow

SETTINGS_PATH = str(Path.home() / '.capture_gui_settings.json')

class Worker(QThread):
    # PyQt6 시그널 선언 방식 (PyQt5와 동일)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        try:
            # 단계별 실행
            if self.params['capture']:
                self.log_signal.emit('[1/3] 캡처 시작...')
                cmd = [
                    'python3', 'shot.py',
                    '--app', self.params['app_name'],
                    '--label', self.params['window_label'],
                    '--output-dir', self.params['output_dir'],
                    '--book', self.params['book'],
                    '--start', str(self.params['start']),
                    '--no', str(self.params['no']),
                    '--next', self.params['next_action'],
                    '--delay', str(self.params['delay']),
                    '--width', str(self.params['width']),
                    '--height', str(self.params['height']),\
                    '--top', str(self.params['top']),
                    '--bottom', str(self.params['bottom']),\
                    '--left', str(self.params['left']),\
                    '--right', str(self.params['right'])
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                self.log_signal.emit(result.stdout)
                if result.returncode != 0:
                    self.error_signal.emit(result.stderr)
                    return
            if self.params['pdf']:
                self.log_signal.emit('[2/3] PDF 변환 시작...')
                cmd = [
                    'python3', 'pdf.py',
                    '--input-dir', self.params['output_dir'],
                    '--lang', self.params['lang'],
                    '--tess', self.params['tess_path']
                ]
                if self.params['pdf_merge']:
                    cmd.append('--merge')
                result = subprocess.run(cmd, capture_output=True, text=True)
                self.log_signal.emit(result.stdout)
                if result.returncode != 0:
                    self.error_signal.emit(result.stderr)
                    return
            if self.params['ocr']:
                self.log_signal.emit('[3/3] OCR 시작...')
                cmd = [
                    'python3', 'llm_ocr.py',
                    '--input-dir', self.params['output_dir']
                ]
                if self.params['ocr_merge']:\
                    cmd.append('--merge')
                result = subprocess.run(cmd, capture_output=True, text=True)
                self.log_signal.emit(result.stdout)
                if result.returncode != 0:
                    self.error_signal.emit(result.stderr)
                    return
            self.finished_signal.emit()
        except Exception as e:
            self.error_signal.emit(str(e))


class ShotGui(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # uic.loadUi('main_gui.ui', self) # PyQt5 UI 로딩 방식 주석 처리 또는 삭제

        # PyQt6에서 pyuic6로 변환된 클래스를 사용하여 UI 로드
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # 이제 self.ui.위젯이름 형태로 위젯에 접근합니다.
        self.ui.browseOutputDirButton.clicked.connect(self.browse_output_dir)
        self.ui.runButton.clicked.connect(self.start_workflow)

        # 메뉴 액션 연결 (self.ui.action이름 형태 사용)
        self.ui.actionSaveSettings.triggered.connect(self.save_settings)
        self.ui.actionLoadSettings.triggered.connect(self.load_settings)

        # 로그 영역 (self.ui.logTextEdit 형태 사용)
        self.ui.logTextEdit.setReadOnly(True)

        self.worker = None

        # defaults 리스트에서도 위젯 접근 방식을 self.ui.위젯 형태로 변경
        self.defaults = [
            (self.ui.appNameLineEdit, '', 'setText', 'text'),
            (self.ui.windowLabelLineEdit, '', 'setText', 'text'),
            (self.ui.outputDirLineEdit, '', 'setText', 'text'),
            (self.ui.bookLineEdit, '', 'setText', 'text'),
            (self.ui.startSpinBox, 1, 'setValue', 'value'),
            (self.ui.noSpinBox, 1, 'setValue', 'value'),
            (self.ui.nextLineEdit, '', 'setText', 'text'),
            (self.ui.delaySpinBox, 1.0, 'setValue', 'value'),
            (self.ui.widthSpinBox, 0, 'setValue', 'value'),
            (self.ui.heightSpinBox, 0, 'setValue', 'value'),
            (self.ui.topSpinBox, 0, 'setValue', 'value'),
            (self.ui.bottomSpinBox, 0, 'setValue', 'value'),
            (self.ui.leftSpinBox, 0, 'setValue', 'value'),
            (self.ui.rightSpinBox, 0, 'setValue', 'value'),
            (self.ui.tessPathLineEdit, '', 'setText', 'text'),
            (self.ui.langLineEdit, '', 'setText', 'text'),
            (self.ui.ocrCheckBox, False, 'setChecked', 'checked'),
            (self.ui.pdfCheckBox, True, 'setChecked', 'checked'),
            (self.ui.textCheckBox, False, 'setChecked', 'checked'),
            (self.ui.mergeCheckBox, False, 'setChecked', 'checked'),
        ]

        self.load_settings()

        # 위젯 접근 방식 변경 (self.ui.위젯 형태 사용)
        self.ui.widthSpinBox.setEnabled(True)
        self.ui.heightSpinBox.setEnabled(True)
        self.ui.topSpinBox.setEnabled(True)
        self.ui.bottomSpinBox.setEnabled(True)
        self.ui.leftSpinBox.setEnabled(True)
        self.ui.rightSpinBox.setEnabled(True)

    def load_settings(self):
        try:
            with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # self.defaults 리스트의 widget 항목은 이미 self.ui.위젯 형태로 변경되었으므로 추가 수정 불필요
            for widget, default, set_method, value_type in self.defaults:
                key = widget.objectName()
                if key in data:
                    value = data[key]
                    if value_type == 'checked':
                        getattr(widget, set_method)(bool(value))
                    else:
                        getattr(widget, set_method)(value)
                else:
                    getattr(widget, set_method)(default)
        except Exception:
            # 파일 없거나 파싱 실패 시 defaults 적용
            # self.defaults 리스트의 widget 항목은 이미 self.ui.위젯 형태로 변경되었으므로 추가 수정 불필요
            for widget, default, set_method, _ in self.defaults:
                getattr(widget, set_method)(default)

    def save_settings(self):
        data = {}
        # self.defaults 리스트의 widget 항목은 이미 self.ui.위젯 형태로 변경되었으므로 추가 수정 불필요
        for widget, _, _, value_type in self.defaults:
            key = widget.objectName()
            if value_type == 'text':
                data[key] = widget.text()
            elif value_type == 'value':
                data[key] = widget.value()
            elif value_type == 'checked':
                data[key] = widget.isChecked()
        try:
            with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to save settings: {e}")

    # closeEvent 메소드는 변경 필요 없음
    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    def browse_output_dir(self):
        # QFileDialog는 PyQt6.QtWidgets에서 임포트하므로 변경 없음
        dir_path = QFileDialog.getExistingDirectory(self, 'Select Output Directory')
        if dir_path:
            self.ui.outputDirLineEdit.setText(dir_path) # self.ui 추가

    def get_params(self):
        # 위젯 접근 방식을 self.ui.위젯 형태로 변경
        output_dir = os.path.join(self.ui.outputDirLineEdit.text().strip(), self.ui.bookLineEdit.text().strip())
        params = {
            'app_name': self.ui.appNameLineEdit.text().strip(),
            'window_label': self.ui.windowLabelLineEdit.text().strip(),
            'output_dir': output_dir,
            'book': self.ui.bookLineEdit.text().strip(),
            'start': self.ui.startSpinBox.value(),
            'no': self.ui.noSpinBox.value(),
            'next_action': self.ui.nextLineEdit.text().strip(),
            'delay': self.ui.delaySpinBox.value(),
            'width': self.ui.widthSpinBox.value(),
            'height': self.ui.heightSpinBox.value(),
            'top': self.ui.topSpinBox.value(),
            'bottom': self.ui.bottomSpinBox.value(),
            'left': self.ui.leftSpinBox.value(),
            'right': self.ui.rightSpinBox.value(),
            'tess_path': self.ui.tessPathLineEdit.text().strip(),
            'lang': self.ui.langLineEdit.text().strip(),
            'capture': True, # 이 부분은 UI의 체크박스와 직접 연결되지 않은 로직
            'pdf': self.ui.pdfCheckBox.isChecked(), # self.ui 추가
            'pdf_merge': self.ui.mergeCheckBox.isChecked(), # self.ui 추가
            'ocr': self.ui.ocrCheckBox.isChecked(), # self.ui 추가
            'ocr_merge': self.ui.mergeCheckBox.isChecked(), # self.ui 추가
        }
        return params

    def start_workflow(self):
        if self.worker and self.worker.isRunning():
            self.ui.logTextEdit.append('이미 실행 중입니다.') # self.ui 추가
            return
        params = self.get_params() # get_params 내부에서 이미 self.ui 반영됨
        self.worker = Worker(params)
        self.worker.log_signal.connect(self.ui.logTextEdit.append) # self.ui 추가
        # QMessageBox는 PyQt6.QtWidgets에서 임포트하므로 변경 없음
        self.worker.error_signal.connect(lambda msg: QMessageBox.critical(self, 'Error', msg))
        self.worker.finished_signal.connect(lambda: self.ui.logTextEdit.append('완료.')) # self.ui 추가
        self.worker.start()

# main 실행 부분은 변경 필요 없음
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = ShotGui()
    window.show()
    sys.exit(app.exec_())