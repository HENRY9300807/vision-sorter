# package/save_manager.py
import os
import json
from datetime import datetime


class SessionSaver:
    """세션별 저장 카운터 관리."""
    def __init__(self, max_valid_saves: int):
        self.max = int(max_valid_saves)
        self.count = 0

    def can_save(self) -> bool:
        """저장 가능 여부 확인."""
        return self.count < self.max

    def on_saved(self):
        """저장 완료 시 호출."""
        if self.count < self.max:
            self.count += 1


class RealTimeExporter:
    """자바/외부 시스템이 읽기 쉬운 파일 기반 실시간 피드."""
    def __init__(self, out_dir: str):
        self.out_dir = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.json_path = os.path.join(out_dir, "live.json")
        self.signal_path = os.path.join(out_dir, "signal.txt")

    def publish(self, *, area_cm2: float, trigger: bool, stats: dict = None, extra: dict = None):
        """실시간 상태를 파일로 내보내기."""
        data = {
            "ts": datetime.utcnow().isoformat(),
            "area_cm2": float(area_cm2),
            "trigger": int(bool(trigger)),
        }
        if stats:
            data["label_stats"] = {str(k): int(v) for k, v in stats.items()}
        if extra:
            data.update(extra)
        
        # JSON 파일 저장
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 신호 파일 저장 (0 또는 1)
        with open(self.signal_path, "w", encoding="utf-8") as f:
            f.write("1\n" if trigger else "0\n")

