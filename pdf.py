#!/usr/bin/env python3
"""
pdf.py: PNG → Tesseract Searchable PDF 변환 및 병합
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path
import logging

# Logger 설정 (한/영)
logger = logging.getLogger('pdf')
ch = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s: %(message)s')
ch.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(ch)

def run_tesseract(input_path, output_path, lang, tess_path):
    """
    Tesseract를 이용해 PNG를 PDF로 변환합니다.
    Converts PNG to searchable PDF using Tesseract.
    """
    cmd = [tess_path, str(input_path), str(output_path.with_suffix('')), '-l', lang, 'pdf']
    logger.info(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    return output_path

def merge_pdfs(pdf_files, merged_path):
    """
    여러 PDF를 하나로 병합합니다.
    Merge multiple PDFs into one.
    """
    try:
        from PyPDF2 import PdfMerger
    except ImportError:
        logger.error("PyPDF2가 필요합니다. pip install PyPDF2")
        sys.exit(1)
    merger = PdfMerger()
    for pdf in sorted(pdf_files, key=lambda x: str(x)):
        with open(pdf, 'rb') as f:
            merger.append(f)
    merger.write(str(merged_path))
    merger.close()
    logger.info(f"병합 PDF 저장: {merged_path}")

def main():
    parser = argparse.ArgumentParser(description='PNG → Tesseract Searchable PDF 변환 및 병합\nConvert PNG to searchable PDF and merge.',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--input-file', '-if', help='입력 파일 (Input file)')
    parser.add_argument('--input-dir', '-id', help='입력 디렉토리 (Input directory)')
    parser.add_argument('--output-file', '-of', help='출력 파일 (Output file)')
    parser.add_argument('--output-dir', '-od', help='출력 디렉토리 (Output directory)')
    parser.add_argument('--merge', '-m', action='store_true', help='결과 병합 (Merge outputs)')
    parser.add_argument('--lang', '-l', default='kor+eng+chi_tra', help='Tesseract 언어 (Language for OCR)')
    parser.add_argument('--tess', default='tesseract', help='Tesseract 실행 경로 (Tesseract path)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='로그 레벨 (Log level)')
    args = parser.parse_args()
    # Logger 레벨 설정
    log_level = getattr(logging, args.log_level.upper())
    logger.setLevel(log_level)
    ch.setLevel(log_level)

    if args.input_file:
        input_path = Path(args.input_file)
        output_path = Path(args.output_file) if args.output_file else input_path.with_suffix('.pdf')
        run_tesseract(input_path, output_path, args.lang, args.tess)
        logger.info(f"PDF 저장: {output_path}")
        return

    if args.input_dir:
        input_dir = Path(args.input_dir)
        output_dir = Path(args.output_dir) if args.output_dir else input_dir
        output_dir.mkdir(exist_ok=True)
        png_files = sorted(list(input_dir.glob('*.png')) + list(input_dir.glob('*.PNG')))
        for png in png_files:
            pdf_path = output_dir / (png.stem + '.pdf')
            if pdf_path.exists():
                logger.info(f"이미 존재: {pdf_path} → 건너뜀")
            else:
                run_tesseract(png, pdf_path, args.lang, args.tess)
                logger.info(f"PDF 저장: {pdf_path}")
        if args.merge:
            all_pdfs = sorted(list(output_dir.glob('*.pdf')) + list(output_dir.glob('*.PDF')), key=lambda x: str(x))
            if not all_pdfs:
                logger.warning(f"병합할 PDF 파일이 없습니다: {output_dir}")
            else:
                merged_path = output_dir / f"{input_dir.name}_merged.pdf"
                merge_pdfs(all_pdfs, merged_path)
        return
    logger.error("--input-file/-if 또는 --input-dir/-id 중 하나를 지정하세요.")
    sys.exit(1)

if __name__ == '__main__':
    main()