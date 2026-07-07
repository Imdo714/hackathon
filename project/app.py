"""
app.py

FastAPI를 활용한 이미지 왜곡 처리 및 ImgBB/PostgreSQL 연동 REST API 서버입니다.
사용자가 업로드한 이미지를 수신하여 Elastic Distortion 및 Grid Warping을 거친 후,
원본과 왜곡된 이미지를 ImgBB에 업로드하고 DB에 메타데이터를 저장합니다.
"""

import httpx
import base64
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

import os
from dotenv import load_dotenv

from project import image_warp
from project import models
from project.database import engine, get_db

# .env 파일을 읽어옵니다.
load_dotenv()

# .env 파일에서 ImgBB API 키를 가져옵니다.
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시 DB 테이블 자동 생성
    models.Base.metadata.create_all(bind=engine)
    yield

tags_metadata = [
    {
        "name": "Image Warping & Storage",
        "description": "이미지 왜곡 및 ImgBB/DB 저장 API입니다.",
    }
]

app = FastAPI(
    title="Privacy Protection Image Warping API",
    description="""
스마트글래스 환경 등에서 획득한 개인정보 포함 이미지를 안전하게 보호하기 위해 강하게 왜곡(Warping)하는 API입니다.
업로드된 이미지는 ImgBB 서버에 저장되며, 변환 내역은 PostgreSQL 데이터베이스에 기록됩니다.
    """,
    version="1.1.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan
)

# 모든 도메인(Origin)에서 이 API에 접근할 수 있도록 CORS 권한을 완전 허용합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 프론트엔드 주소 허용
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드(GET, POST, OPTIONS 등) 허용
    allow_headers=["*"],  # 모든 HTTP 헤더 허용
)

async def upload_to_imgbb(image_bytes: bytes) -> str:
    """
    ImgBB API를 사용하여 이미지를 업로드하고 URL을 반환하는 헬퍼 함수
    """
    if IMGBB_API_KEY == "여기에_API_키를_입력하세요":
        raise HTTPException(status_code=500, detail="ImgBB API 키가 설정되지 않았습니다. app.py 파일 상단을 확인하여 키를 입력하세요.")
        
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.imgbb.com/1/upload",
            data={
                "key": IMGBB_API_KEY,
                "image": encoded_image
            }
        )
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"ImgBB 업로드 실패: {response.text}")
        
        data = response.json()
        return data["data"]["url"]

@app.post(
    "/warp_and_save", 
    summary="이미지 왜곡 및 DB 저장 API", 
    description="원본 이미지와 파라미터(공격 방식 등)를 받아 왜곡한 후, 두 이미지를 ImgBB에 저장하고 해당 URL을 DB에 기록합니다.",
    tags=["Image Warping & Storage"],
    responses={
        200: {
            "description": "성공적으로 저장 및 처리됨",
            "content": {
                "application/json": {
                    "example": {
                        "message": "이미지가 성공적으로 변환 및 저장되었습니다.",
                        "record_id": 1,
                        "original_url": "https://i.ibb.co/...",
                        "warped_url": "https://i.ibb.co/...",
                        "attack_method": "DB접근",
                        "created_at": "2026-07-07T12:00:00.000000+00:00"
                    }
                }
            }
        },
        400: {"description": "잘못된 요청 (이미지 파일 오류 등)"},
        500: {"description": "서버 내부 처리 오류 (ImgBB 연동 실패, DB 오류 등)"}
    }
)
async def warp_image_and_save_api(
    file: UploadFile = File(..., description="원본 이미지 파일 (예: PNG, JPEG 등)"),
    attack_method: str = Form(..., description="공격 방식 (예: DB접근, 패킷 탈취)"),
    alpha: float = Form(30.0, description="Elastic Distortion 왜곡 강도 (예: 30.0)"),
    sigma: float = Form(6.0, description="Elastic Distortion 가우시안 스무딩 강도 (부드러움, 예: 6.0)"),
    epsilon: float = Form(10.0, description="Grid Warping 추가 왜곡 강도 (전체 이미지 스케일 대비 비율, 예: 10.0)"),
    random_seed: int = Form(0, description="선택사항: 항상 동일한 결과를 원할 경우 지정 (예: 0)"),
    db: Session = Depends(get_db)
):
    try:
        # 1. 원본 이미지 파일 비동기 읽기
        image_bytes = await file.read()
        
        # 2. 원본 이미지 ImgBB 업로드
        original_url = await upload_to_imgbb(image_bytes)
        
        # 3. 업로드된 바이트 데이터를 OpenCV 이미지로 디코딩
        image = image_warp.decode_image(image_bytes)
        if image is None:
            raise HTTPException(status_code=400, detail="유효한 이미지 파일이 아닙니다. 이미지를 다시 확인해주세요.")
        
        # 4. 고성능 통합 왜곡 알고리즘 수행
        warped_image = image_warp.warp_image(
            image=image,
            alpha=alpha,
            sigma=sigma,
            epsilon=epsilon,
            random_seed=random_seed
        )
        
        # 5. 왜곡 처리된 이미지를 PNG 바이트 데이터로 인코딩
        warped_bytes = image_warp.encode_image(warped_image, ext=".png")
        
        # 6. 왜곡된 이미지 ImgBB 업로드
        warped_url = await upload_to_imgbb(warped_bytes)
        
        # 7. 데이터베이스에 기록 저장
        new_record = models.ImageRecord(
            original_image_url=original_url,
            warped_image_url=warped_url,
            attack_method=attack_method
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        
        # 8. 최종 결과 반환 (JSON)
        return JSONResponse(content={
            "message": "이미지가 성공적으로 변환 및 저장되었습니다.",
            "record_id": new_record.id,
            "original_url": original_url,
            "warped_url": warped_url,
            "attack_method": new_record.attack_method,
            "created_at": new_record.created_at.isoformat() if new_record.created_at else None
        })

    except HTTPException:
        # HTTP 에러는 그대로 다시 발생
        raise
    except Exception as e:
        db.rollback()
        # 기타 모든 예외는 서버 내부 오류(500)로 응답
        raise HTTPException(status_code=500, detail=f"서버 오류가 발생했습니다: {str(e)}")

@app.get(
    "/records",
    summary="저장된 변환 기록 전체 조회",
    description="DB에 저장된 원본/왜곡 이미지 URL 및 공격 방식, 생성 시간 등 모든 기록을 최신순으로 조회합니다.",
    tags=["Image Warping & Storage"]
)
def get_all_records(db: Session = Depends(get_db)):
    # DB에서 ImageRecord 테이블의 모든 데이터를 최신순(id 역순)으로 조회합니다.
    records = db.query(models.ImageRecord).order_by(models.ImageRecord.id.desc()).all()
    
    result = []
    for r in records:
        result.append({
            "id": r.id,
            "original_url": r.original_image_url,
            "warped_url": r.warped_image_url,
            "attack_method": r.attack_method,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
        
    return {
        "total_count": len(result),
        "records": result
    }

@app.post(
    "/upload_image",
    summary="단일 이미지 단순 업로드 API",
    description="왜곡 처리나 DB 저장 없이, 이미지를 그대로 ImgBB 서버에 업로드하고 생성된 이미지 URL만 즉시 반환합니다.",
    tags=["Image Warping & Storage"]
)
async def upload_single_image(
    file: UploadFile = File(..., description="업로드할 이미지 파일")
):
    try:
        # 1. 파일 비동기 읽기
        image_bytes = await file.read()
        
        # 2. ImgBB 업로드 헬퍼 함수 재사용
        image_url = await upload_to_imgbb(image_bytes)
        
        # 3. URL 결과 반환
        return JSONResponse(content={
            "message": "이미지가 성공적으로 업로드되었습니다.",
            "url": image_url
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 업로드 중 오류가 발생했습니다: {str(e)}")
