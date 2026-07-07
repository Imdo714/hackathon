# 스마트글래스 개인정보 보호용 이미지 왜곡 API

본 프로젝트는 스마트글래스 환경에서 사용자의 개인정보(계좌번호, 비밀번호, 주민등록번호 등)를 안전하게 보호하기 위해, 이미지를 데이터베이스에 저장하기 전에 원본 내용을 사람이 육안으로 식별할 수 없도록 강하게 왜곡(Warping)하는 REST API입니다.

단순 블러 처리를 배제하고, **Elastic Distortion**과 **Grid Warping**을 결합하여 성능을 최적화(OpenCV `remap` 1회 적용)하였으며, 텍스트 형태가 심하게 무너지도록 설계되었습니다.

## 기술 스택
- Python 3.11+
- FastAPI & Uvicorn
- OpenCV (cv2)
- NumPy, SciPy
- Pillow(PIL)

## 디렉토리 구조
```
project/
├── app.py             # FastAPI 서버 및 라우팅 구현
├── image_warp.py      # Elastic Distortion 및 Grid Warping 핵심 알고리즘 구현
├── requirements.txt   # 의존성 패키지 목록
└── README.md          # 프로젝트 설명서
```

## 설치 방법

1. 필수 패키지를 설치합니다.
```bash
pip install -r requirements.txt
```

## 서버 실행

아래 명령어를 통해 서버를 실행합니다.
```bash
uvicorn app:app --reload
```
서버가 정상적으로 실행되면 `http://localhost:8000` 에서 대기합니다.

## API 문서 (Swagger)
웹 브라우저를 열고 아래 주소로 접속하면, 입력 파라미터를 테스트해 볼 수 있는 Swagger UI를 확인할 수 있습니다.
- **Swagger URL**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 실행 예제 및 테스트 코드

### 1. `curl`을 이용한 테스트 예시
`image.png`라는 테스트용 이미지 파일이 현재 디렉토리에 있다고 가정합니다.

```bash
curl -X 'POST' \
  'http://localhost:8000/warp' \
  -H 'accept: image/png' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@image.png;type=image/png' \
  -F 'alpha=40' \
  -F 'sigma=6' \
  -F 'epsilon=0.3' \
  -F 'random_seed=42' \
  --output warped_result.png
```
명령어 실행 후 동일 디렉토리에 왜곡된 이미지인 `warped_result.png` 파일이 생성됩니다.

### 2. Python `requests`를 이용한 테스트 코드
파이썬 스크립트를 작성하여 테스트할 수 있습니다. (`test_api.py` 파일로 저장 후 실행)

```python
import requests

url = "http://localhost:8000/warp"
file_path = "image.png" # 테스트에 사용할 원본 이미지 경로

# 왜곡 강도 조절 파라미터 설정
data = {
    "alpha": 40.0,
    "sigma": 6.0,
    "epsilon": 0.3,
    "random_seed": 42
}

try:
    # 파일 열기 및 POST 요청
    with open(file_path, "rb") as image_file:
        files = {"file": (file_path, image_file, "image/png")}
        print("API 요청 중...")
        response = requests.post(url, data=data, files=files)

    # 결과 저장
    if response.status_code == 200:
        with open("warped_result.png", "wb") as out_file:
            out_file.write(response.content)
        print("성공: 왜곡된 이미지가 warped_result.png 파일로 저장되었습니다.")
    else:
        print(f"실패: 상태 코드 {response.status_code}")
        print(response.json())
except FileNotFoundError:
    print(f"오류: 테스트용 {file_path} 파일이 현재 디렉토리에 존재하지 않습니다.")
except Exception as e:
    print(f"오류가 발생했습니다: {e}")
```
