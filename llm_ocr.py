#!/usr/bin/env python3
"""
llm_ocr.py: PNG → Mistral OCR 텍스트 추출 및 병합
"""
import os
import sys
import argparse
from pathlib import Path
import requests
import base64
from dotenv import load_dotenv
import time
from filelock import FileLock
import logging

# Logger 설정 (한/영)
logger = logging.getLogger('llm_ocr')
ch = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s: %(message)s')
ch.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(ch)

load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_OCR_MODEL = "mistral-ocr-latest"

def encode_file(file_path):
    """
    파일을 base64로 인코딩합니다.
    Encode file as base64 string.
    """
    with open(file_path, "rb") as file:
        return base64.b64encode(file.read()).decode('utf-8')

def perform_mistral_ocr(file_path):
    """
    Mistral API를 호출하여 OCR을 수행합니다.
    Perform OCR using Mistral API.
    """
    if not MISTRAL_API_KEY:
        logger.error("MISTRAL_API_KEY not set")
        return None
    ext = file_path.suffix.lower()
    base64_file = encode_file(file_path)
    mime_type = f"image/{ext[1:]}" if ext != '.jpg' else "image/jpeg"
    data_url = f"data:{mime_type};base64,{base64_file}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }
    data = {
        "model": MISTRAL_OCR_MODEL,
        "document": {
            "type": "image_url",
            "image_url": data_url
        }
    }
    response = requests.post(
        "https://api.mistral.ai/v1/ocr",
        headers=headers,
        json=data
    )
    if response.status_code == 200:
        ocr_result = response.json()
        all_text = ""
        for page in ocr_result.get("pages", []):
            all_text += page.get("markdown", "") + "\n\n"
        return all_text.strip()
    elif response.status_code == 429:
        logger.warning(f"Rate limit error: {file_path}")
        return "RATE_LIMIT"
    else:
        logger.error(f"Mistral OCR API error: {response.status_code} - {response.text}")
        return None

def main():
    parser = argparse.ArgumentParser(description='PNG → Mistral OCR 텍스트 추출 및 병합\nExtract text from PNG using Mistral OCR and merge.',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--input-file', '-if', help='입력 파일 (Input file)')
    parser.add_argument('--input-dir', '-id', help='입력 디렉토리 (Input directory)')
    parser.add_argument('--output-file', '-of', help='출력 파일 (Output file)')
    parser.add_argument('--output-dir', '-od', help='출력 디렉토리 (Output directory)')
    parser.add_argument('--merge', '-m', action='store_true', help='결과 병합 (Merge outputs)')
    parser.add_argument('--lang', '-l', default='kor+eng', help='(미사용, 호환성용 / Not used, for compatibility)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='로그 레벨 (Log level)')
    args = parser.parse_args()
    # Logger 레벨 설정
    log_level = getattr(logging, args.log_level.upper())
    logger.setLevel(log_level)
    ch.setLevel(log_level)

    if args.input_file:
        input_path = Path(args.input_file)
        output_path = Path(args.output_file) if args.output_file else input_path.with_suffix('.txt')
        text = perform_mistral_ocr(input_path)
        if text:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            logger.info(f"텍스트 저장: {output_path}")
        return

    if args.input_dir:
        input_dir = Path(args.input_dir)
        output_dir = Path(args.output_dir) if args.output_dir else input_dir
        output_dir.mkdir(exist_ok=True)
        png_files = sorted(input_dir.glob('*.png'))
        txt_files = []
        lock = FileLock("/tmp/mistral_api.lock")
        retry_list = []
        for png in png_files:
            txt_path = output_dir / (png.stem + '.txt')
            if txt_path.exists():
                logger.info(f"이미 존재: {txt_path} → 건너뜀")
                continue
            with lock:
                text = perform_mistral_ocr(png)
            if text == "RATE_LIMIT":
                retry_list.append(png)
            elif text:
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                txt_files.append(txt_path)
                logger.info(f"텍스트 저장: {txt_path}")
            time.sleep(0.2)
        if retry_list:
            logger.warning(f"Rate limit으로 실패한 파일 {len(retry_list)}개, 3초 후 재시도...")
            time.sleep(3)
            for png in retry_list:
                txt_path = output_dir / (png.stem + '.txt')
                with lock:
                    text = perform_mistral_ocr(png)
                if text and text != "RATE_LIMIT":
                    with open(txt_path, 'w', encoding='utf-8') as f:
                        f.write(text)
                    txt_files.append(txt_path)
                    logger.info(f"재시도 성공: {txt_path}")
                else:
                    logger.error(f"재시도 실패: {png}")
        if args.merge:
            all_txts = sorted(output_dir.glob('*.txt'), key=lambda x: str(x))
            if all_txts:
                merged_path = output_dir / f"{input_dir.name}_merged.txt"
                with open(merged_path, 'w', encoding='utf-8') as f:
                    for txt in all_txts:
                        with open(txt, 'r', encoding='utf-8') as tf:
                            f.write(tf.read().strip() + '\n\n')
                logger.info(f"병합 텍스트 저장: {merged_path}")
        return
    logger.error("--input-file/-if 또는 --input-dir/-id 중 하나를 지정하세요.")
    sys.exit(1)

if __name__ == '__main__':
    main()