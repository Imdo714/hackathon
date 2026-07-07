"""
image_warp.py

개인정보 보호를 위해 이미지에 강한 왜곡을 적용하는 모듈입니다.
Elastic Distortion과 Grid Warping 기법을 지원하며 고성능(OpenCV remap)으로 구동됩니다.
"""

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter
from typing import Optional

def decode_image(image_bytes: bytes) -> np.ndarray:
    """
    바이트 형태의 이미지 데이터를 OpenCV(NumPy 배열) 포맷으로 디코딩합니다.

    Args:
        image_bytes (bytes): 업로드된 원본 이미지의 바이트 데이터

    Returns:
        np.ndarray: 디코딩된 이미지 배열 (BGR 또는 Grayscale)
    """
    # bytes 데이터를 uint8 NumPy 배열로 변환합니다.
    nparr = np.frombuffer(image_bytes, np.uint8)
    # 메모리의 바이트 데이터를 이미지 형태로 디코딩합니다. 컬러/알파 채널을 유지합니다.
    img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    return img

def encode_image(image: np.ndarray, ext: str = ".png") -> bytes:
    """
    OpenCV(NumPy 배열) 이미지를 지정한 확장자의 바이트 스트림으로 인코딩합니다.

    Args:
        image (np.ndarray): 인코딩할 이미지 배열
        ext (str): 인코딩할 파일 확장자 (기본값: ".png")

    Returns:
        bytes: 인코딩된 이미지의 바이트 데이터
        
    Raises:
        ValueError: 이미지 인코딩에 실패했을 때 발생합니다.
    """
    # 지정한 포맷(확장자)으로 이미지를 메모리에 인코딩합니다.
    success, encoded_image = cv2.imencode(ext, image)
    if not success:
        raise ValueError("이미지 인코딩에 실패했습니다.")
    # 인코딩된 결과를 bytes 객체로 반환합니다.
    return encoded_image.tobytes()

def elastic_distortion(image: np.ndarray, alpha: float, sigma: float, random_seed: Optional[int] = None) -> np.ndarray:
    """
    이미지에 탄성 왜곡(Elastic Distortion)을 독립적으로 적용합니다.

    Args:
        image (np.ndarray): 원본 이미지
        alpha (float): 왜곡의 강도(픽셀 최대 이동 범위)를 조절하는 파라미터
        sigma (float): 가우시안 필터의 표준편차로, 왜곡의 부드러움을 조절
        random_seed (Optional[int]): 난수 시드값 (기본값: None)

    Returns:
        np.ndarray: 탄성 왜곡이 적용된 이미지
    """
    # 일관된 결과를 원할 경우를 위해 난수 생성기를 초기화합니다.
    random_state = np.random.RandomState(random_seed)
    shape = image.shape[:2]

    # -1에서 1 사이의 무작위 변위장(Displacement Field)을 생성합니다.
    dx = random_state.rand(*shape) * 2 - 1
    dy = random_state.rand(*shape) * 2 - 1

    # 가우시안 필터를 적용하여 랜덤 변위장을 부드럽게 만들고 강도(alpha)를 곱해 스케일링합니다.
    dx = gaussian_filter(dx, sigma, mode="constant", cval=0) * alpha
    dy = gaussian_filter(dy, sigma, mode="constant", cval=0) * alpha

    # 원본 이미지의 크기에 맞는 좌표 메쉬그리드를 생성합니다.
    x, y = np.meshgrid(np.arange(shape[1]), np.arange(shape[0]))

    # 기존 좌표에 생성한 변위장을 더해 새로운 픽셀 위치 좌표를 계산합니다.
    indices_x = np.float32(x + dx)
    indices_y = np.float32(y + dy)

    # cv2.remap()을 활용하여 고성능으로 픽셀을 재배치합니다. 외곽은 반사 형태로 채웁니다.
    warped_image = cv2.remap(image, indices_x, indices_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)

    return warped_image

def grid_warp(image: np.ndarray, epsilon: float, random_seed: Optional[int] = None) -> np.ndarray:
    """
    이미지에 그리드 왜곡(Grid Warping)을 독립적으로 적용합니다.
    사인파(Sine wave) 기반의 변위장을 생성하여 텍스트 등의 형태를 기하학적으로 무너뜨립니다.

    Args:
        image (np.ndarray): 원본 이미지
        epsilon (float): 왜곡의 강도를 조절하는 스케일 파라미터 (전체 해상도 대비 비율)
        random_seed (Optional[int]): 난수 시드값 (기본값: None)

    Returns:
        np.ndarray: 그리드 왜곡이 적용된 이미지
    """
    # 일관된 결과를 원할 경우를 위해 난수 생성기를 초기화합니다.
    random_state = np.random.RandomState(random_seed)
    shape = image.shape[:2]

    # 원본 이미지의 크기에 맞는 좌표 메쉬그리드를 생성합니다.
    x, y = np.meshgrid(np.arange(shape[1]), np.arange(shape[0]))

    # 무작위 공간 주파수(Frequency) 및 위상(Phase)을 생성하여 예측할 수 없는 패턴을 형성합니다.
    freq_x = random_state.uniform(0.01, 0.05)
    freq_y = random_state.uniform(0.01, 0.05)
    phase_x = random_state.uniform(0, 2 * np.pi)
    phase_y = random_state.uniform(0, 2 * np.pi)

    # 화면 크기에 비례하여 왜곡의 절대적 스케일을 결정합니다.
    scale = epsilon * max(shape)

    # 사인 및 코사인 곡선을 이용한 그리드 변위장을 계산합니다.
    dx = scale * np.sin(y * freq_y + phase_y)
    dy = scale * np.cos(x * freq_x + phase_x)

    # 기존 좌표에 변위장을 더하여 매핑 좌표를 계산합니다.
    indices_x = np.float32(x + dx)
    indices_y = np.float32(y + dy)

    # cv2.remap()을 활용하여 픽셀을 재배치합니다.
    warped_image = cv2.remap(image, indices_x, indices_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)

    return warped_image

def warp_image(image: np.ndarray, alpha: float, sigma: float, epsilon: float, random_seed: Optional[int] = None) -> np.ndarray:
    """
    Elastic Distortion과 Grid Warping을 모두 결합하여 단 한 번의 매핑(remap)으로
    이미지를 고성능으로 강하게 왜곡시키는 함수입니다.

    Args:
        image (np.ndarray): 원본 이미지
        alpha (float): 탄성 왜곡 강도
        sigma (float): 탄성 왜곡 부드러움(가우시안 필터 편차)
        epsilon (float): 그리드 왜곡 강도
        random_seed (Optional[int]): 난수 시드값 (기본값: None)

    Returns:
        np.ndarray: 두 가지 왜곡 알고리즘이 통합 적용된 이미지
    """
    # 일관된 결과를 원할 경우를 위해 난수 생성기를 초기화합니다.
    random_state = np.random.RandomState(random_seed)
    shape = image.shape[:2]

    # 1. 탄성 왜곡(Elastic Distortion) 변위장 계산
    # 무작위 노이즈 생성 후 가우시안 필터로 스무딩 처리합니다.
    dx_elastic = random_state.rand(*shape) * 2 - 1
    dy_elastic = random_state.rand(*shape) * 2 - 1
    dx_elastic = gaussian_filter(dx_elastic, sigma, mode="constant", cval=0) * alpha
    dy_elastic = gaussian_filter(dy_elastic, sigma, mode="constant", cval=0) * alpha

    # 2. 그리드 왜곡(Grid Warping) 변위장 계산
    # 좌표 공간을 기반으로 무작위 사인/코사인 파동을 생성합니다.
    x, y = np.meshgrid(np.arange(shape[1]), np.arange(shape[0]))
    freq_x = random_state.uniform(0.01, 0.05)
    freq_y = random_state.uniform(0.01, 0.05)
    phase_x = random_state.uniform(0, 2 * np.pi)
    phase_y = random_state.uniform(0, 2 * np.pi)
    scale = epsilon * max(shape)
    
    dx_grid = scale * np.sin(y * freq_y + phase_y)
    dy_grid = scale * np.cos(x * freq_x + phase_x)

    # 3. 변위장 병합 및 최종 매핑 좌표 계산
    # 두 변위장의 X, Y 오프셋을 더하여 한 번의 연산으로 통합합니다.
    indices_x = np.float32(x + dx_elastic + dx_grid)
    indices_y = np.float32(y + dy_elastic + dy_grid)

    # 4. cv2.remap()을 활용한 고성능 픽셀 재배치
    # 두 번의 remap() 호출을 한 번으로 줄여 속도 및 메모리 사용량을 크게 최적화합니다.
    warped_image = cv2.remap(image, indices_x, indices_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)

    return warped_image
