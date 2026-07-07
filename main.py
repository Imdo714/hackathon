import uvicorn

if __name__ == "__main__":
    print("🚀 FastAPI 메인 서버를 시작합니다...")
    # project 폴더 내의 app.py 파일에 정의된 app(FastAPI 인스턴스)을 실행합니다.
    uvicorn.run("project.app:app", host="0.0.0.0", port=8000, reload=True)
