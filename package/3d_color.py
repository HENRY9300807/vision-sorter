import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
# package 폴더에서 직접 실행하는 경우
from operation import COLOR_JSON_PATH

with open(COLOR_JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

fig = plt.figure()
ax = fig.add_subplot(111, projection="3d")

colors = {"background": "blue", "product": "green", "defect": "red"}

for label, spheres in data.items():
    for center, radius in spheres:
        r, g, b = center
        ax.scatter(r, g, b, c=colors.get(label, "black"), label=label, s=50)

# 범례 중복 제거
handles, labels = ax.get_legend_handles_labels()
unique = dict(zip(labels, handles))
ax.legend(unique.values(), unique.keys())

ax.set_xlabel("Red"); ax.set_ylabel("Green"); ax.set_zlabel("Blue")
plt.show()

