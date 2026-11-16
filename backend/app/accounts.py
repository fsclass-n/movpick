"""테스트(데모) 계정 정의. 테스트 관리자는 관리자 화면 조회만 가능한 읽기 전용 계정이다."""

DEMO_ACCOUNTS = {
    "user": {"email": "user@movpick.app", "password": "Movpick!2026", "name": "일반 회원(테스트)", "role": "user"},
    "admin": {"email": "admin@movpick.app", "password": "Admin!2026", "name": "시스템 관리자(테스트)", "role": "admin"},
}
DEMO_EMAILS = {v["email"] for v in DEMO_ACCOUNTS.values()}
READ_ONLY_EMAILS = {DEMO_ACCOUNTS["admin"]["email"]}
