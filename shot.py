import os
import argparse
import logging
import time
import sys
import subprocess
import platform
import psutil
import cv2
import numpy as np

# Attempt to import pyautogui for screen/window capture. If unavailable, set to None for graceful error handling later.
try:
    import pyautogui
    pyautogui.FAILSAFE = False  # Disable failsafe to prevent unwanted interruptions during automation.
except ImportError:
    pyautogui = None

from PIL import Image

# Logger 설정 (한/영)
# 로그 레벨 및 포맷을 통일적으로 관리합니다. (Consistent logger setup for all modules)
logger = logging.getLogger('window_capture')
ch = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s: %(message)s')
ch.setFormatter(formatter)
if not logger.hasHandlers():
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
            logger.error("Install with: pip install pyautogui pillow psutil")
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
    def crop_left_third(image_path, output_path, margin_top=0, margin_bottom=0, margin_left=0, margin_right=0):
        """
        Open image, then crop outer non-white using Pillow+numpy and save final output.
        Only the left third is kept, and margins are applied after non-white crop for clean results.
        """
        try:
            img = Image.open(image_path)
            temp_path = output_path + ".cvtmp.png"
            img.save(temp_path)
            # Crop outer non-white using Pillow+numpy for robust whitespace removal.
            WindowCapture.crop_nonwhite_bbox_with_margin(temp_path, output_path, margin_top, margin_bottom, margin_left, margin_right)
            os.remove(temp_path)
            logger.info(f"Cropped image saved: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Cropping failed: {e}")
            return False

    @staticmethod
    def crop_nonwhite_bbox_with_margin(input_path, output_path, margin_top=0, margin_bottom=0, margin_left=0, margin_right=0):
        """
        Use Pillow+numpy to crop out all outer areas that are not pure white (255,255,255), then apply margins.
        This ensures the final image is tightly cropped to content, which is important for OCR and PDF generation.
        """
        img = Image.open(input_path).convert("RGB")
        arr = np.array(img)
        mask = np.all(arr == 255, axis=2)  # True: pure white
        coords = np.argwhere(~mask)
        if coords.size == 0:
            logger.warning("Non-white area not found. Saving original.")
            img.save(output_path)
            print(f"[INFO] Final cropped image size: {img.size}")
            return True
        y0, x0 = coords.min(axis=0)
        y1, x1 = coords.max(axis=0) + 1
        # Apply margins, ensuring we don't crop past image bounds.
        y0 = max(0, y0 + margin_top)
        y1 = max(y0, y1 - margin_bottom)
        x0 = max(0, x0 + margin_left)
        x1 = max(x0, x1 - margin_right)
        cropped = img.crop((x0, y0, x1, y1))
        print(f"[INFO] Final cropped image size (after margin): {cropped.size}")
        cropped.save(output_path)
        return True

    @staticmethod
    def capture_window(x, y, width, height, output_path, margin_top=0, margin_bottom=0, margin_left=0, margin_right=0):
        """
        Capture the left third of a window using pyautogui, then crop and save.
        This approach is chosen to focus on a specific region (e.g., for book scanning or document capture).
        """
        try:
            if not pyautogui:
                logger.error("pyautogui is required for capturing")
                return False
            # Only capture the left 1/3 of the window for consistent output and to match user requirements.
            region_width = width // 3
            logger.info(f"Capturing region ({x}, {y}) {region_width}x{height} (left 1/3 of window)...")
            temp_path = output_path + ".tmp.png"
            screenshot = pyautogui.screenshot(region=(x, y, region_width, height))
            screenshot.save(temp_path)
            WindowCapture.crop_left_third(temp_path, output_path, margin_top, margin_bottom, margin_left, margin_right)
            os.remove(temp_path)
            return True
        except Exception as e:
            logger.error(f"Capture failed: {str(e)}")
            return False

    @staticmethod
    def capture_fullscreen(output_path, margin_top=0, margin_bottom=0, margin_left=0, margin_right=0):
        """
        Capture the entire screen, then crop and save only the left third.
        This is a fallback for when no window is specified, ensuring the tool is always usable.
        """
        try:
            if not pyautogui:
                logger.error("pyautogui is required for capturing")
                return False
            logger.info("Capturing full screen...")
            temp_path = output_path + ".tmp.png"
            screenshot = pyautogui.screenshot()
            screenshot.save(temp_path)
            WindowCapture.crop_left_third(temp_path, output_path, margin_top, margin_bottom, margin_left, margin_right)
            os.remove(temp_path)
            return True
        except Exception as e:
            logger.error(f"Capture failed: {str(e)}")
            return False

def activate_app(app_name):
    """
    Activate the given app using AppleScript (bring to foreground).
    This is necessary for automation, as only the frontmost window can be reliably captured.
    """
    try:
        script = f'tell application "{app_name}" to activate'
        subprocess.run(['osascript', '-e', script], capture_output=True, timeout=5)
        logger.info(f"Activated app: {app_name}")
        time.sleep(0.5)  # Wait for the app to come to the foreground.
    except Exception as e:
        logger.warning(f"Failed to activate app {app_name}: {e}")

def set_window_size_and_position(app_name, width=None, height=None, x=None, y=None):
    """
    Set the front window of the app to the given size and position using AppleScript.
    This allows for consistent capture regions, which is important for batch operations.
    """
    if width is None and height is None and x is None and y is None:
        return
    size_part = f"set size of front window of theApp to {{{width if width else 'item 1 of size of front window of theApp'}, {height if height else 'item 2 of size of front window of theApp'}}}"
    pos_part = f"set position of front window of theApp to {{{x}, {y}}}" if x is not None and y is not None else ""
    script = f'''
    tell application "System Events"
        set theApp to first process whose name is "{app_name}"
        {size_part}
        {pos_part}
    end tell
    '''
    try:
        subprocess.run(['osascript', '-e', script], check=True)
        logger.info(f"Set window size to {width}x{height} and position to {x},{y} for app '{app_name}'")
    except Exception as e:
        logger.warning(f"Failed to set window size/position: {e}")

def batch_capture(
    app_name, window_label, output_dir, book, start, no, next_action, delay, width, height, top, bottom, left, right, log_level='DEBUG'
):
    """
    Batch capture pages from a window and save as images.
    Returns list of captured image paths.
    """
    logger.setLevel(getattr(logging, log_level.upper()))
    ch.setLevel(getattr(logging, log_level.upper()))
    if not WindowCapture._check_dependencies():
        raise RuntimeError("Missing dependencies or not macOS")
    info = WindowCapture.get_window_info(app_name, window_label)
    if not info:
        raise RuntimeError("No matching window found")
    proc_name, win_name, x, y, w, h = info
    if width:
        w = width
    if height:
        h = height
    if width or height:
        set_window_size_and_position(proc_name, width, height)
        info = WindowCapture.get_window_info(app_name, window_label)
        if not info:
            raise RuntimeError("No matching window after resize")
        proc_name, win_name, x, y, w, h = info
    import pyautogui
    screen_size = pyautogui.size()
    logger.info(f"Window position: ({x}, {y}), size: {w}x{h}, screen size: {screen_size}")
    activate_app(proc_name)
    os.makedirs(output_dir, exist_ok=True)
    total_pages = start + no - 1
    pad_width = len(str(total_pages))
    img_paths = []
    for i in range(start, start + no):
        logger.info(f"[Batch] Capturing page {i}")
        activate_app(proc_name)
        if delay > 0:
            logger.debug(f"Waiting {delay} seconds before capture...")
            time.sleep(delay)
        out_path = os.path.join(output_dir, f"{book}_{str(i).zfill(pad_width)}.png")
        WindowCapture.capture_window(x, y, w, h, out_path, top, bottom, left, right)
        img_paths.append(out_path)
        time.sleep(0.1)
        if ',' in next_action:
            try:
                nx, ny = map(int, next_action.split(','))
                pyautogui.click(nx, ny)
            except Exception:
                logger.error("--next must be 'x,y' for click or a key name for press.")
                raise
        else:
            pyautogui.press(next_action)
        time.sleep(0.1)
    logger.info(f"Batch capture complete. Images saved to {output_dir}")
    return img_paths

def generate_pdfs(img_files, tess_path, lang):
    """
    Generate searchable PDFs for each image using Tesseract.
    Returns list of generated PDF paths.
    """
    pdf_files = []
    for img_path in img_files:
        pdf_path = os.path.splitext(img_path)[0] + ".pdf"
        cmd = [tess_path, img_path, os.path.splitext(img_path)[0], "-l", lang, "pdf"]
        logger.debug(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        logger.info(f"PDF saved: {pdf_path}")
        pdf_files.append(pdf_path)
    return pdf_files

def run_ocr_on_dir(ocr_dir, merge=False):
    """
    Run Mistral OCR (ocr.py) on all images in the directory.
    """
    import asyncio
    import ocr
    asyncio.run(ocr.process_directory(ocr_dir, None, merge=merge))
    logger.info(f"Mistral OCR finished. Check {ocr_dir}")

def merge_outputs(output_dir, file_prefix, pdf_files, do_pdf_merge, do_text_merge):
    """
    Merge PDFs and/or OCR text files in the output directory.
    """
    if do_pdf_merge and len(pdf_files) > 1:
        merged_pdf = os.path.join(output_dir, f"{file_prefix}_merged.pdf")
        logger.info(f"Merging PDFs into {merged_pdf}")
        try:
            from PyPDF2 import PdfMerger
            merger = PdfMerger()
            for pdf in pdf_files:
                merger.append(pdf)
            merger.write(merged_pdf)
            merger.close()
            logger.info(f"Merged PDF saved: {merged_pdf}")
        except ImportError:
            logger.error("PyPDF2 is required for PDF merging. Install with: pip install PyPDF2")
    if do_text_merge:
        merged_txt = os.path.join(output_dir, f"{os.path.basename(output_dir)}_merged.txt")
        if os.path.exists(merged_txt):
            logger.info(f"Merged OCR text: {merged_txt}")
        else:
            logger.warning(f"Merged OCR text not found: {merged_txt}")

def main():
    # Argument parsing and CLI setup. (한/영)
    # 옵션을 pdf.py, llm_ocr.py와 일관성 있게 맞춥니다.
    parser = argparse.ArgumentParser(
        description='macOS Window Capture Tool (pyautogui only)\n윈도우/전체화면 캡처, OCR, PDF, 병합 자동화 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Capture Methods:
  1. Window Capture: Capture a window by exact app name or label (AppleScript)
  2. Full Screen: If no window specified, capture entire screen
  3. Batch Page Capture: Use --start, --no, --dir/-D, --next to capture multiple pages in a loop (auto focus, capture, crop, save, and next page by click or keypress)

After capture, only the left 1/3 of the image is saved, and then the outer pure-white area is automatically cropped. You can adjust the captured window size and apply crop margins.

Use --show to print all available windows and exit.

Dependencies:
  pip install pyautogui pillow psutil numpy
  (macOS only)

Example:
  python shot.py --app "Chrome" --start 1 --no 5 -D ./output --next 300,400
  python shot.py --app "Chrome" --start 1 --no 5 -D ./output --next right
"""
    )
    parser.add_argument('--input-file', '-if', help='입력 파일 (Input file)')
    parser.add_argument('--input-dir', '-id', help='입력 디렉토리 (Input directory)')
    parser.add_argument('--output-file', '-of', help='출력 파일 (Output file)')
    parser.add_argument('--output-dir', '-od', help='출력 디렉토리 (Output directory)', default='output')
    parser.add_argument('--merge', '-m', action='store_true', help='결과 병합 (Merge outputs)')
    parser.add_argument('--lang', '-l', default='eng+kor+chi_tra', help='Tesseract 언어 (Language for OCR)')
    parser.add_argument('--tess', default='tesseract', help='Tesseract 실행 경로 (Tesseract path)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='로그 레벨 (Log level)')
    # shot.py 고유 옵션 (윈도우/캡처/마진/배치)
    parser.add_argument('--app', '-a', default='Windows App', help='앱 이름 (App name to capture, exact match, case-insensitive)')
    parser.add_argument('--label', '-L', default='Mini PC', help='윈도우 타이틀 (Window title/label to capture, exact match, case-insensitive)')
    parser.add_argument('--show', '-s', action='store_true', help='윈도우 목록 출력 후 종료 (List all available windows and exit)')
    parser.add_argument('--start', '-S', default=1, type=int, help='시작 페이지 번호 (Start page number for batch capture)')
    parser.add_argument('--no', '-n', default=5, type=int, help='캡처할 페이지 수 (Number of pages to capture in batch)')
    parser.add_argument('--next', '-N', default='right', type=str, help="다음 페이지 동작: 'x,y' 클릭 또는 키 이름 (Next page action: 'x,y' for click or key name for press)")
    parser.add_argument('--delay', '-d', type=float, default=0, help='캡처 전 대기 시간 (Wait time before capture, seconds)')
    parser.add_argument('--width', '-w', type=int, default=3840, help='윈도우 너비 (Override captured window width, pixels)')
    parser.add_argument('--height', '-H', type=int, default=2160, help='윈도우 높이 (Override captured window height, pixels)')
    parser.add_argument('--top', '-t', type=int, default=60, help='상단 마진 (Crop margin from top, pixels)')
    parser.add_argument('--bottom', '-b', type=int, default=55, help='하단 마진 (Crop margin from bottom, pixels)')
    parser.add_argument('--left', '-l', type=int, default=0, help='좌측 마진 (Crop margin from left, pixels)')
    parser.add_argument('--right', '-r', type=int, default=0, help='우측 마진 (Crop margin from right, pixels)')
    args = parser.parse_args()
    # Logger 레벨 설정 (Set logger level)
    log_level = getattr(logging, args.log_level.upper())
    logger.setLevel(log_level)
    ch.setLevel(log_level)
    if not WindowCapture._check_dependencies():
        sys.exit(1)
    if args.show:
        WindowCapture.list_windows()
        sys.exit(0)
    if args.delay > 0:
        logger.debug(f"Waiting {args.delay} seconds...")
        time.sleep(args.delay)
    # Batch page capture mode: allows for automated multi-page capture, e.g., for digitizing books.
    output_dir = args.dir
    file_prefix = 'page'
    if args.book:
        output_dir = args.book
        file_prefix = args.book
    if args.start is not None and args.no is not None and output_dir and args.next:
        if not (args.app or args.label):
            logger.error("Batch mode requires --app or --label to specify the window.")
            sys.exit(1)
        info = WindowCapture.get_window_info(args.app, args.label)
        if not info:
            sys.exit(1)
        proc_name, win_name, x, y, w, h = info
        # Always use --width/--height if given, else use AppleScript values for flexibility.
        if args.width:
            w = args.width
        if args.height:
            h = args.height
        # Set window size if --width/--height are given for consistent capture area.
        if args.width or args.height:
            set_window_size_and_position(proc_name, args.width, args.height)
            # Re-fetch window info after resizing to get updated coordinates.
            info = WindowCapture.get_window_info(args.app, args.label)
            if not info:
                sys.exit(1)
            proc_name, win_name, x, y, w, h = info
        # Log window and screen info for debugging and reproducibility.
        import pyautogui
        screen_size = pyautogui.size()
        logger.info(f"Window position: ({x}, {y}), size: {w}x{h}, screen size: {screen_size}")
        activate_app(proc_name)
        os.makedirs(output_dir, exist_ok=True)
        # Determine zero padding width based on total page count
        total_pages = args.start + args.no - 1
        pad_width = len(str(total_pages))
        for i in range(args.start, args.start + args.no):
            logger.info(f"[Batch] Capturing page {i}")
            activate_app(proc_name)
            if args.delay > 0:
                logger.debug(f"Waiting {args.delay} seconds before capture...")
                time.sleep(args.delay)
            out_path = os.path.join(output_dir, f"{file_prefix}_{str(i).zfill(pad_width)}.png")
            # Always capture left 1/3: region=(x, y, w//3, h)
            WindowCapture.capture_window(x, y, w, h, out_path, args.top, args.bottom, args.left, args.right)
            time.sleep(0.1)
            # Next page action: either click or keypress, for hands-free batch capture.
            if ',' in args.next:
                try:
                    nx, ny = map(int, args.next.split(','))
                    pyautogui.click(nx, ny)
                except Exception:
                    logger.error("--next must be 'x,y' for click or a key name for press.")
                    sys.exit(1)
            else:
                pyautogui.press(args.next)
            time.sleep(0.1)
        logger.info(f"Batch capture complete. Images saved to {output_dir}")
        sys.exit(0)
    # Normal single capture mode: for ad-hoc or one-off captures.
    if args.app or args.label:
        info = WindowCapture.get_window_info(args.app, args.label)
        if not info:
            sys.exit(1)
        proc_name, win_name, x, y, w, h = info
        if args.width:
            w = args.width
        if args.height:
            h = args.height
        activate_app(proc_name)
        WindowCapture.capture_window(x, y, w, h, args.output, args.top, args.bottom, args.left, args.right)
    else:
        WindowCapture.capture_fullscreen(args.output, args.top, args.bottom, args.left, args.right)

if __name__ == '__main__':
    main()