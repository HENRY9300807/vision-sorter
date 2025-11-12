# 테스트: sip import 확인
try:
    import sip
    print('sip ok ->', type(sip))
except Exception:
    from PyQt5 import sip
    print('PyQt5.sip ok ->', type(sip))

