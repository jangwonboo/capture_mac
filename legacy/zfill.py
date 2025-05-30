import os
import re
import argparse

# 파일명에서 book, page, ext 추출용 정규식
FILENAME_RE = re.compile(r'^(?P<book>.+)_(?P<page>\d+)\.(?P<ext>[^.]+)$')

def zero_pad_filenames(directory, padding):
    for fname in os.listdir(directory):
        match = FILENAME_RE.match(fname)
        if match:
            book = match.group('book')
            page = match.group('page')
            ext = match.group('ext')
            new_page = page.zfill(padding)
            new_fname = f"{book}_{new_page}.{ext}"
            if fname != new_fname:
                src = os.path.join(directory, fname)
                dst = os.path.join(directory, new_fname)
                print(f"Renaming: {fname} -> {new_fname}")
                os.rename(src, dst)

def main():
    parser = argparse.ArgumentParser(description="Zero-pad page numbers in filenames like {book}_{page}.ext")
    parser.add_argument('--directory', '-d', required=True, help='Target directory')
    parser.add_argument('--padding', '-p', type=int, required=True, help='Zero padding width (e.g., 3 for 001)')
    args = parser.parse_args()
    zero_pad_filenames(args.directory, args.padding)

if __name__ == "__main__":
    main()