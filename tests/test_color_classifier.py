# tests/test_color_classifier.py

import numpy as np
from package.color_classifier import bgr_to_lab, classify_lab_sphere, ColorDef


def test_classify_basic_red():
    # 2x2 빨강 이미지 (BGR: 0,0,255)
    img = np.zeros((2, 2, 3), dtype=np.uint8)
    img[:, :] = (0, 0, 255)
    lab = bgr_to_lab(img)

    red = ColorDef("RED", tuple(lab[0,0].astype(float)), radius=5.0)
    labels = classify_lab_sphere(lab, [red], default_radius=5.0)
    # 모두 0(RED)로 분류되어야 함
    assert (labels == 0).all()

