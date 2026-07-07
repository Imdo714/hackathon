import uvicorn
from project.app import app  # Vercel Serverless Function이 이 'app' 객체를 찾아 실행합니다.

if __name__ == "__main__":
    print("🚀 FastAPI 메인 서버를 시작합니다...")
    # 로컬 테스트용 실행 코드
    uvicorn.run("project.app:app", host="0.0.0.0", port=8000, reload=True)
