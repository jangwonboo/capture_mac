#!/usr/bin/env python3
import os
import argparse
import logging
import sys
import platform
import subprocess
from pathlib import Path

# Attempt to import pyautogui for screen/window capture. If unavailable, set to None for graceful error handling later.
try:
    import pyautogui
    pyautogui.FAILSAFE = False  # Disable failsafe to prevent unwanted interruptions during automation.
except ImportError:
    pyautogui = None

from PIL import Image

# Configure logger for this module. This allows for flexible log level control and consistent formatting.
logger = logging.getLogger('window_capture')
ch = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s: %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class WindowCapture:
    """
    macOS only: Provides window and fullscreen capture using pyautogui and AppleScript.
    This class centralizes all capture-related logic for maintainability and platform-specific handling.
    """
    @staticmethod
    def _check_dependencies():
        # Check for required dependencies and platform. This ensures the tool fails fast with clear errors if misconfigured.
        missing = []
        if pyautogui is None:
            missing.append("pyautogui")
        try:
            import PIL
        except ImportError:
            missing.append("Pillow")
        if platform.system() != "Darwin":
            missing.append("macOS only")
        if missing:
            logger.error(f"Missing or unsupported: {', '.join(missing)}")
            logger.error("Install with: pip install pyautogui pillow")
            return False
        return True

    @staticmethod
    def list_windows():
        """
        Print all available windows (app name, title, position, size).
        Uses AppleScript to enumerate windows, as Python cannot natively access this info on macOS.
        """
        script = '''
        tell application "System Events"
            set windowList to {}
            repeat with proc in (every process whose background only is false)
                try
                    set procName to name of proc
                    repeat with win in (every window of proc)
                        try
                            set winName to name of win
                            set winPos to position of win
                            set winSize to size of win
                            set x to item 1 of winPos
                            set y to item 2 of winPos
                            set w to item 1 of winSize
                            set h to item 2 of winSize
                            if w > 10 and h > 10 then
                                if winName is "" then set winName to "<" & procName & ">"
                                set end of windowList to procName & "|" & winName & "|" & x & "|" & y & "|" & w & "|" & h
                            end if
                        end try
                    end repeat
                end try
            end repeat
            return windowList
        end tell
        '''
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            logger.error(f"AppleScript failed: {result.stderr}")
            return
        windows_data = result.stdout.strip()
        if not windows_data or windows_data == "{}":
            logger.error("No windows found")
            return
        content = windows_data[1:-1] if windows_data.startswith('{') and windows_data.endswith('}') else windows_data
        items = [i.strip().strip('"') for i in content.split(',') if i.strip()]
        print("\nAvailable Windows:")
        for i, item in enumerate(items, 1):
            parts = item.split('|')
            if len(parts) == 6:
                proc_name, win_name, x, y, w, h = parts
                print(f"{i:2d}. [{proc_name}] {win_name}  ({x},{y}) {w}x{h}")

    @staticmethod
    def get_window_info(app_name=None, window_title=None):
        """
        Return window info only if app_name or title is an exact match (case-insensitive).
        Uses AppleScript for window enumeration, as this is not possible natively in Python on macOS.
        """
        if not WindowCapture._check_dependencies():
            return None
        script = '''
        tell application "System Events"
            set windowList to {}
            repeat with proc in (every process whose background only is false)
                try
                    set procName to name of proc
                    repeat with win in (every window of proc)
                        try
                            set winName to name of win
                            set winPos to position of win
                            set winSize to size of win
                            set x to item 1 of winPos
                            set y to item 2 of winPos
                            set w to item 1 of winSize
                            set h to item 2 of winSize
                            if w > 10 and h > 10 then
                                if winName is "" then set winName to "<" & procName & ">"
                                set end of windowList to procName & "|" & winName & "|" & x & "|" & y & "|" & w & "|" & h
                            end if
                        end try
                    end repeat
                end try
            end repeat
            return windowList
        end tell
        '''
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            logger.error(f"AppleScript failed: {result.stderr}")
            return None
        windows_data = result.stdout.strip()
        if not windows_data or windows_data == "{}":
            logger.error("No windows found")
            return None
        windows = []
        content = windows_data[1:-1] if windows_data.startswith('{') and windows_data.endswith('}') else windows_data
        items = [i.strip().strip('"') for i in content.split(',') if i.strip()]
        for item in items:
            parts = item.split('|')
            if len(parts) == 6:
                try:
                    proc_name, win_name, x, y, w, h = parts
                    x, y, w, h = int(float(x)), int(float(y)), int(float(w)), int(float(h))
                    windows.append((proc_name, win_name, x, y, w, h))
                except Exception:
                    continue
        # Only exact match (case-insensitive) to avoid ambiguity and ensure user intent.
        for proc_name, win_name, x, y, w, h in windows:
            if app_name and proc_name.lower() == app_name.lower():
                return (proc_name, win_name, x, y, w, h)
            if window_title and win_name.lower() == window_title.lower():
                return (proc_name, win_name, x, y, w, h)
        logger.error("No exact matching window found")
        return None

    @staticmethod
    def capture_window(x, y, width, height, output_path):
        """
        Capture the left third of a window using pyautogui, then crop and save.
        This approach is chosen to focus on a specific region (e.g., for book scanning or document capture).
        """
        try:
            if not pyautogui:
                logger.error("pyautogui is required for capturing")
                return False
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            screenshot.save(output_path)
            logger.info(f"Captured window saved: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Capture failed: {str(e)}")
            return False

    @staticmethod
    def capture_fullscreen(output_path):
        """
        Capture the entire screen, then crop and save only the left third.
        This is a fallback for when no window is specified, ensuring the tool is always usable.
        """
        try:
            if not pyautogui:
                logger.error("pyautogui is required for capturing")
                return False
            screenshot = pyautogui.screenshot()
            screenshot.save(output_path)
            logger.info(f"Captured full screen saved: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Capture failed: {str(e)}")
            return False

def resize_window(app_name, win_name, width, height):
    script = f'''
    tell application "System Events"
        set proc to first process whose name is "{app_name}"
        set win to first window of proc whose name is "{win_name}"
        set size of win to {{{width}, {height}}}
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Resize failed: {result.stderr}")

def activate_app(app_name):
    """
    Activate the given app using AppleScript (bring to foreground).
    """
    try:
        script = f'tell application "{app_name}" to activate'
        subprocess.run(['osascript', '-e', script], capture_output=True, timeout=5)
        logger.info(f"Activated app: {app_name}")
    except Exception as e:
        logger.warning(f"Failed to activate app {app_name}: {e}")

def send_key_applescript(app_name, key):
    script = f'''
    tell application "{app_name}" to activate
    tell application "System Events"
        keystroke "{key}"
    end tell
    '''
    subprocess.run(['osascript', '-e', script])

def main():
    parser = argparse.ArgumentParser(description='macOS Window Capture Tool (PNG, batch, margin, resize)')
    parser.add_argument('--output-dir', '-od', default='output', help='출력 디렉토리 (default: output)')
    parser.add_argument('--app', '-a', default='Windows App', help='캡처할 앱 이름 (정확히 일치, 대소문자 무시)')
    parser.add_argument('--label', '-L', default='Mini PC', help='캡처할 윈도우 타이틀 (정확히 일치, 대소문자 무시)')
    parser.add_argument('--width', '-W', default=2880, type=int, help='캡처할 윈도우 너비 (pixels)')
    parser.add_argument('--height', '-H', default=1800, type=int, help='캡처할 윈도우 높이 (pixels)')
    parser.add_argument('--book', '-b', default='book', help='파일명 접두어')
    parser.add_argument('--start', '-s', default=1, type=int, help='시작 페이지 번호 (default: 1)')
    parser.add_argument('--no', '-n', default=5, type=int, help='캡처할 페이지 수 (default: 1)')
    parser.add_argument('--next', default='right', help='다음 페이지로 이동하기 위한 키 입력 (예: right)')
    parser.add_argument('--delay', '-d', default=0.1, type=float,  help='각 캡처 사이의 지연 시간 (초) (default: 0.5)')
    parser.add_argument('--top', '-T', default = 45, type=int, help='캡처 영역 상단 마진 (pixels)')
    parser.add_argument('--bottom', '-B', default =45, type=int, help='캡처 영역 하단 마진 (pixels)')
    parser.add_argument('--left', '-l', default = 0, type=int, help='캡처 영역 왼쪽 마진 (pixels)')
    parser.add_argument('--right', '-R', default = 0, type=int, help='캡처 영역 오른쪽 마진 (pixels)')

    args = parser.parse_args()
    logger.setLevel(logging.INFO)
    ch.setLevel(logging.INFO)
    if not WindowCapture._check_dependencies():
        sys.exit(1)
    output_dir = Path(args.output_dir) / args.book
    output_dir.mkdir(parents=True, exist_ok=True)

    info = WindowCapture.get_window_info(args.app, args.label)
    if not info:
        sys.exit(1)
    proc_name, win_name, x, y, w, h = info

    # width/height 파라미터가 있으면 리사이즈
    if args.width and args.height:
        resize_window(proc_name, win_name, args.width, args.height)
        w, h = args.width, args.height
    elif args.width:
        resize_window(proc_name, win_name, args.width, h)
        w = args.width
    elif args.height:
        resize_window(proc_name, win_name, w, args.height)
        h = args.height

    for i in range(args.no):
        current_page_num = args.start + i
        output_path_page = output_dir / f'{current_page_num:04d}.png'

        # 마진 적용
        capture_x = x + args.left
        capture_y = y + args.top
        capture_width = w - args.left - args.right
        capture_height = h - args.top - args.bottom

        if capture_width <= 0 or capture_height <= 0:
            logger.error(f"Invalid capture area for page {current_page_num}. Check margin values.")
            sys.exit(1)

        activate_app(proc_name)
        logger.info(f"Capturing page {current_page_num}...")
        WindowCapture.capture_window(capture_x, capture_y, capture_width, capture_height, str(output_path_page))

        # 다음 페이지 넘김
        if i < args.no - 1 and args.next:
            try:
                send_key_applescript(proc_name, args.next)
            except Exception as e:
                logger.warning(f"Next page action failed: {e}")
            if args.delay > 0:
                import time
                time.sleep(args.delay)

if __name__ == '__main__':
    main()