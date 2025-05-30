capture/
├── shot.py
├── pdf.py
├── llm_ocr.py
├── requirements.txt
├── README.md
├── .env
├── output/
│ └── ... (이미지, PDF, 텍스트 결과물)
└── legacy/
---

## ❓ FAQ

- **Q. 윈도우/리눅스에서도 동작하나요?**  
  A. 캡처(shot.py)는 macOS 전용(AppleScript, pyautogui 기반)입니다. PDF/OCR 변환은 OS 제한이 없습니다.

- **Q. Tesseract가 설치되어 있어야 하나요?**  
  A. 네, PDF 변환에는 Tesseract CLI가 필요합니다.  
  (brew install tesseract 등으로 설치)

- **Q. Mistral OCR은 유료인가요?**  
  A. Mistral API 키가 필요하며, 요금 정책은 공식 문서를 참고하세요.

---

## 🏷️ 라이선스 (License)

MIT License

---

## 💡 구조 설명 (Why this structure?)

- **옵션 일관성**: 모든 스크립트가 동일한 CLI 옵션을 사용하여 자동화/연동이 쉽습니다.
- **로깅**: logger를 사용해 디버깅과 에러 추적이 용이합니다.
- **한/영 주석**: 유지보수성과 협업을 위해 주요 함수/옵션에 한글+영문 주석을 추가했습니다.
- **macOS 특화**: 윈도우 캡처는 AppleScript와 pyautogui를 활용하여 macOS에서만 동작합니다.

# Capture 프로젝트

---

## 📦 설치 방법 (Installation)

1. Python 3.8 이상 필요
2. 의존성 설치:
   ```bash
   pip install -r requirements.txt
   ```
3. Tesseract 설치 (PDF/OCR 변환용):
   - macOS: `brew install tesseract`
   - Ubuntu: `sudo apt install tesseract-ocr`
4. (선택) Mistral API 키 발급 및 .env 파일에 추가

---

## 🖥️ 지원 환경 (Supported Platforms)

- **macOS**: 전체 기능 지원 (스크린샷, PDF 변환, OCR)
- **Windows/Linux**: PDF 변환, OCR만 지원 (스크린샷 기능 미지원)

---

## 🗂️ 파일/디렉토리 역할 (Project Structure)

- `shot.py` : macOS에서 화면 캡처 및 이미지 저장
- `pdf.py` : PDF 파일을 이미지/텍스트로 변환
- `llm_ocr.py` : 이미지/PDF에서 OCR 및 LLM 기반 텍스트 추출
- `output/` : 결과물(이미지, PDF, 텍스트 등) 저장 폴더
- `legacy/` : 이전 버전 코드/백업
- `.env` : 환경 변수 (API 키 등)

---

## 🚀 사용법 (Usage)

### 1. 화면 캡처 (macOS 전용)
```bash
python shot.py --output output/브랜드/shot.png
```

### 2. PDF → 이미지/텍스트 변환
```bash
python pdf.py --input input.pdf --output output/브랜드/
```

### 3. OCR 및 LLM 텍스트 추출
```bash
python llm_ocr.py --input output/브랜드/shot.png --output output/브랜드/ocr.txt
```

---

## 💡 예제 (Examples)

1. PDF 파일을 이미지로 변환 후 OCR 수행:
   ```bash
   python pdf.py --input sample.pdf --output output/sample/
   python llm_ocr.py --input output/sample/page1.png --output output/sample/page1.txt
   ```
2. macOS에서 화면 캡처 후 텍스트 추출:
   ```bash
   python shot.py --output output/shot.png
   python llm_ocr.py --input output/shot.png --output output/shot.txt
   ```
