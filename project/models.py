from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from project.database import Base

class ImageRecord(Base):
    __tablename__ = "image_records"

    id = Column(Integer, primary_key=True, index=True)
    original_image_url = Column(String, nullable=False, comment="원본 이미지 ImgBB URL")
    warped_image_url = Column(String, nullable=False, comment="왜곡된 이미지 ImgBB URL")
    attack_method = Column(String, nullable=False, comment="공격 방식 (DB접근, 패킷 탈취 등)")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성 시간")
