# 코드 리뷰 리포트
## main_app.php (184줄)

### 스타일 검사
코드 스타일 가이드 정보가 없어 스타일 검사는 생략합니다. OWASP Top 10 기준으로 분석한 보안 취약점은 다음과 같습니다.

---
## OWASP 기준 보안 취약점 분석

### 🔴 A03:2021 – Injection (인젝션)
- DB 모드에서 `uniqid()` 결과를 SQL 쿼리에 직접 삽입 중이며 Prepared Statement를 쓰지 않습니다.
- 현재 코드: `"INSERT INTO access_logs (log_id) VALUES ('LOG_" . uniqid() . "')"` — 당장은 안전해도 외부 입력값 추가 시 SQL 인젝션에 취약해집니다.

### 🔴 A01:2021 – Broken Access Control (접근 제어 오류)
- `$_GET['action']` 파라미터에 대한 화이트리스트 검증이 없습니다.
- 누구나 `?action=clear_session`을 호출해 세션을 날리고 쿠키를 삭제할 수 있는 인가 누락 문제가 있습니다.

### 🔴 A05:2021 – Security Misconfiguration (보안 설정 오류)
- `config.inc.php`가 없으면 `$db_pass = 'password'`와 `$db_user = 'dbadmin'`이 기본값으로 들어가는 위험한 구조입니다.
- DB 연결 오류(`$db->error`)가 화면에 그대로 노출되어 시스템 정보가 샙니다.

### 🟡 A02:2021 – Cryptographic Failures (암호화 오류)
- Secure/HttpOnly 플래그 없이 쿠키를 설정/삭제합니다.
- `setcookie('SESSION_TRACKER', '', time() - 3600, '/')` — 보안 옵션이 누락되었습니다.

### 🟡 A09:2021 – Security Logging and Monitoring Failures (로깅 오류)
- 500 에러 시에만 로그를 남기고, DB 접속 실패나 비정상 접근 시도 같은 중요 이벤트는 기록하지 않습니다.

### 🟠 XSS (출력값 이스케이프 미흡)
- `$client_ip`, `$region_code`, `$alert_msg` 등을 출력할 때 `htmlspecialchars()` 처리가 없어 XSS에 취약합니다.

---
## 주요 보안 검사 요약 및 조치 방안

### 1. ❌ XSS (Cross-Site Scripting) — 심각도: 높음
- 위치: `echo $client_ip;`, `echo $region_code;`, `echo $alert_msg;`
- 설명: 외부 메타데이터를 이스케이프 없이 화면에 바로 찍습니다.
- 조치: `echo htmlspecialchars($client_ip, ENT_QUOTES, 'UTF-8');` 적용

### 2. ❌ Open Redirect — 심각도: 중간
- 위치: `header("Location: " . explode('?', $_SERVER["REQUEST_URI"])[0]);`
- 설명: 클라이언트가 조작할 수 있는 값으로 리다이렉트를 수행합니다.
- 조치: `parse_url()`을 사용해 안전한 경로(path)인지 검증 후 이동

### 3. ⚠️ DB 연결 정보 폴백 하드코딩 — 심각도: 중간
- 위치: `$db_user = 'dbadmin'; $db_pass = 'password';`
- 설명: 설정 파일 누락 시 취약한 계정으로 DB에 접근합니다.
- 조치: 기본값 세팅을 지우고, 설정 파일이 없으면 에러를 띄우고 실행 중단

### 4. ⚠️ DB 오류 메시지 노출 — 심각도: 중간
- 위치: `echo $db->error;`
- 설명: DB 스키마나 내부 정보가 화면에 노출될 수 있습니다.
- 조치: 화면에는 "DB 오류 발생" 정도만 띄우고 실제 에러는 `error_log()`로 처리

### 5. ✅ SQL Injection — 해당 없음
- 쿼리에 사용자 입력값이 직접 들어가지 않고 `uniqid()`만 들어가서 당장 인젝션 위험은 없습니다.

---
## 요약 테이블

| # | 유형 | 위치 | 심각도 |
|---|------|------|--------|
| 1 | XSS | echo $client_ip, $region_code 등 | 높음 |
| 2 | Open Redirect | header("Location: ... REQUEST_URI) | 중간 |
| 3 | 하드코딩 폴백 | $db_user = 'dbadmin' | 중간 |
| 4 | DB 오류 노출 | echo $db->error | 중간 |
| 5 | SQL Injection | 해당 없음 | — |
