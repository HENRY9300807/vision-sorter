import time
from pathlib import Path
import sys
import cv2
from pypylon import pylon
import shutil

# === 루트 경로 추가 ===
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# === 설정 import ===
from package.operation import (
    CAPTURE_COUNT, CAPTURE_TIMEOUT, PICTURE_DIR,
    JPEG_QUALITY, INTERVAL_SEC,
    CAMERA_BINNING_H, CAMERA_BINNING_V,
    CAMERA_DECIM_H, CAMERA_DECIM_V,
)

# === 기본 설정 ===
SAVE_DIR  = PICTURE_DIR
MAX_FILES = CAPTURE_COUNT


def ensure_clean_dir(p: Path):
    """폴더를 아예 비우고 새로 생성"""
    if p.exists():
        try:
            shutil.rmtree(p)
            print(f"폴더 삭제 완료: {p}")
        except Exception as e:
            print(f"폴더 삭제 실패: {e}")
    p.mkdir(parents=True, exist_ok=True)
    print(f"폴더 새로 생성됨: {p}")


def _try_set_int_feature(node, value, name):
    """카메라 정수형 피처를 안전하게 설정"""
    try:
        v = int(value)
        if v <= 1:
            return
        node.SetValue(v)
        print(f"[cam] {name} = {node.GetValue()}")
    except Exception as e:
        print(f"[cam] skip {name}: {e}")


def configure_camera(camera: pylon.InstantCamera):
    """binning/decimation만 시도 (ROI 제외)"""
    # TODO: mm/px 정밀 캘리브레이션 파이프라인 추가
    # Issue URL: https://github.com/HENRY9300807/vision-sorter/issues/3
    #  assignees: your-github-id
    #  labels: calibration, vision
    #  milestone: MVP-v1
    #  (본문) 체스보드 10장 이상 촬영 → 전역/행별 스케일 산출
    camera.Open()

    # --- Binning ---
    if hasattr(camera, "BinningHorizontal"):
        _try_set_int_feature(camera.BinningHorizontal, CAMERA_BINNING_H, "BinningH")
    if hasattr(camera, "BinningVertical"):
        _try_set_int_feature(camera.BinningVertical, CAMERA_BINNING_V, "BinningV")

    # --- Decimation ---
    if hasattr(camera, "DecimationHorizontal"):
        _try_set_int_feature(camera.DecimationHorizontal, CAMERA_DECIM_H, "DecimationH")
    if hasattr(camera, "DecimationVertical"):
        _try_set_int_feature(camera.DecimationVertical, CAMERA_DECIM_V, "DecimationV")

    # 픽셀 포맷 컨버터
    converter = pylon.ImageFormatConverter()
    converter.OutputPixelFormat = pylon.PixelType_BGR8packed
    converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
    return converter


def capture_images(camera, converter):
    """폴더 비어있을 때 MAX_FILES장 캡처"""
    for i in range(MAX_FILES):
        grab = camera.RetrieveResult(CAPTURE_TIMEOUT, pylon.TimeoutHandling_ThrowException)
        if grab.GrabSucceeded():
            img = converter.Convert(grab).GetArray()

            # 🔥 binning/decimation 안 먹힐 때 대비 → 소프트웨어 다운스케일 추가
            img = cv2.resize(
                img,
                (img.shape[1] // 2, img.shape[0] // 2),
                interpolation=cv2.INTER_AREA
            )

            fname = f"frame_{i:03d}.jpg"
            fpath = SAVE_DIR / fname
            cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])[1].tofile(str(fpath))
            print(f"저장됨: {fpath} ({i+1}/{MAX_FILES})")
        grab.Release()
        time.sleep(INTERVAL_SEC)


def main():
    # ✅ 실행 시 폴더 비우고 새로 생성
    ensure_clean_dir(SAVE_DIR)

    # 카메라 준비
    camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
    converter = configure_camera(camera)
    camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    print("실행 시작: 폴더 감시 중...")

    try:
        while True:
            files = list(SAVE_DIR.glob("*.jpg"))
            if len(files) == 0:
                print("폴더 비어 있음 → 촬영 시작")
                time.sleep(1)
                capture_images(camera, converter)
                print(f"{MAX_FILES}장 촬영 완료 → 대기 모드")
            else:
                time.sleep(1)

    except KeyboardInterrupt:
        print("사용자 중지 요청.")
    finally:
        camera.StopGrabbing()
        camera.Close()


if __name__ == "__main__":
    main()
