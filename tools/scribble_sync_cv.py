# tools/scribble_sync_cv.py

import cv2 as cv
import numpy as np


left = cv.imread("left.jpg")
assert left is not None
h1, w1 = left.shape[:2]
right = cv.imread("right.jpg")
if right is None:
    right = cv.resize(left, (w1//4, h1//4), interpolation=cv.INTER_AREA)
h2, w2 = right.shape[:2]

left_mask  = np.zeros((h1, w1), np.uint8)
right_mask = np.zeros((h2, w2), np.uint8)

brush = 8
drawing = False


def to_right(x1, y1):
    return int(x1 * w2 / w1), int(y1 * h2 / h1)


def cb(event, x, y, flags, param):
    global drawing
    if event == cv.EVENT_LBUTTONDOWN: drawing = True
    if event == cv.EVENT_MOUSEMOVE and drawing:
        cv.circle(left_mask, (x, y), brush, 255, -1)
        rx, ry = to_right(x, y)
        r_brush = max(1, int(brush * (w2/w1 + h2/h1)/2))
        cv.circle(right_mask, (rx, ry), r_brush, 255, -1)
    if event == cv.EVENT_LBUTTONUP: drawing = False


cv.namedWindow("LEFT");  cv.setMouseCallback("LEFT", cb)
cv.namedWindow("RIGHT")


while True:
    l = left.copy();  l[left_mask==255] = (0,0,255)
    r = right.copy(); r[right_mask==255] = (0,0,255)
    cv.imshow("LEFT", l); cv.imshow("RIGHT", r)
    if cv.waitKey(1) == 27: break
cv.destroyAllWindows()

