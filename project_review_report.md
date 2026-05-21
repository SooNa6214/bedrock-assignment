# 코드 리뷰 리포트
> 생성 일시: 2025-05-21  
> 사용 모델: Claude Sonnet 4.6  
> 검사 항목: PEP8 스타일 · OWASP 보안 취약점
---
## cart_service.py (312줄)
### 스타일 검사
PEP8 및 일반적인 Python 스타일 규칙 위반 목록:

**명명 규칙 (Naming Convention)**
- [18] 스타일 위반: 클래스명 `cartHandler`가 PascalCase를 따르지 않음 → `CartHandler`로 변경 필요
- [27] 스타일 위반: 메서드명 `AddItem`이 snake_case를 따르지 않음 → `add_item`으로 변경 필요
- [36] 스타일 위반: 메서드명 `RemoveItem`이 snake_case를 따르지 않음 → `remove_item`으로 변경 필요
- [55] 스타일 위반: 메서드명 `CalcTotal`이 snake_case를 따르지 않음 → `calc_total`로 변경 필요
- [63] 스타일 위반: 메서드명 `ApplyCoupon`이 snake_case를 따르지 않음 → `apply_coupon`으로 변경 필요
- [141] 스타일 위반: 클래스명 `invoiceBuilder`가 PascalCase를 따르지 않음 → `InvoiceBuilder`로 변경 필요
- [162] 스타일 위반: 메서드명 `GenerateHtmlInvoice`가 snake_case를 따르지 않음 → `generate_html_invoice`로 변경 필요
- [174] 스타일 위반: 메서드명 `GenerateItemList`가 snake_case를 따르지 않음 → `generate_item_list`로 변경 필요
- [198] 스타일 위반: 메서드명 `GetCartSummary`가 snake_case를 따르지 않음 → `get_cart_summary`로 변경 필요

**코드 스타일**
- [56] 스타일 위반: `if price == None:` → `if price is None:`으로 작성하는 것이 Pythonic함
- [64] 스타일 위반: `if user == None:` → `if user is None:`으로 작성하는 것이 Pythonic함
- [70] 스타일 위반: `subtotal = subtotal + item["price"]` → `subtotal += item["price"]`로 작성하는 것이 Pythonic함
- [78] 스타일 위반: `def get_item(self,item_id)` — 쉼표 뒤 공백 누락
- [82] 스타일 위반: `def get_user(self,uid)` — 쉼표 뒤 공백 누락
- [97] 스타일 위반: `def update_quantity(self,item_id,qty)` — 쉼표 뒤 공백 누락
- [98~103] 스타일 위반: `if ... return True else: return False` → early return 패턴 권장
- [105] 스타일 위반: `def delete_item(self,item_id)` — 쉼표 뒤 공백 누락
- [152] 스타일 위반: `def build_html_header(self,title,subtitle)` — 쉼표 뒤 공백 누락
- [158] 스타일 위반: `def build_html_item_list(self,items)` — 쉼표 뒤 공백 누락
- [162] 스타일 위반: `lines=[]` — 대입 연산자 주위 공백 누락
- [165] 스타일 위반: `for iid,info in` — 쉼표 뒤 공백 누락
- [166] 스타일 위반: 문자열 `+` 연결 반복 사용 → f-string 사용 권장
- [187] 스타일 위반: `total = total + handler.items[iid]["price"]` → `total += ...`으로 작성하는 것이 Pythonic함
- [190] 스타일 위반: `if len(handler.items) == 0:` → `if not handler.items:`로 작성하는 것이 Pythonic함
- [199] 스타일 위반: `count[s] = count[s] + 1` → `count[s] += 1`로 작성하는 것이 Pythonic함
- [110] 스타일 위반: `get_pending_items`에서 for문 대신 리스트 컴프리헨션 권장
- [278] 스타일 위반: `round(avg,2)` — 쉼표 뒤 공백 누락

**보안 위반**
- [10~11] 보안 위반: `DB_PASSWORD`, `PAYMENT_SECRET` 하드코딩 — 자격증명 소스코드 노출 (OWASP A02)
- [85~90] 보안 위반: `search_items` SQL 쿼리 문자열 직접 연결 — SQL Injection (OWASP A03)
- [92~97] 보안 위반: `search_users` SQL 쿼리 문자열 직접 연결 — SQL Injection (OWASP A03)
- [115~116] 보안 위반: `ping_payment_server`에서 `subprocess.getoutput` 사용자 입력 직접 전달 — Command Injection (OWASP A03)
- [120~123] 보안 위반: `export_cart_file`에서 파일 경로 직접 연결 — Path Traversal (OWASP A01)
- [126~128] 보안 위반: `load_cart_from_file`에서 `pickle.load` 사용 — Insecure Deserialization (OWASP A08)
- [152~156] 보안 위반: `build_html_header`에서 HTML 이스케이프 없이 출력 — XSS (OWASP A03)
- [158~163] 보안 위반: `build_html_item_list`에서 상품 정보 HTML 직접 삽입 — XSS (OWASP A03)
- [166~169] 보안 위반: `debug_secrets`에 자격증명 하드코딩 및 출력 — 프로덕션 코드에 존재하면 안 됨

**독스트링 누락**
- [36] 스타일 위반: `RemoveItem` 메서드에 docstring 없음
- [44] 스타일 위반: `get_all_items` 메서드에 docstring 없음
- [50] 스타일 위반: `get_all_users` 메서드에 docstring 없음
- [55] 스타일 위반: `CalcTotal` 메서드에 docstring 없음
- [63] 스타일 위반: `ApplyCoupon` 메서드에 docstring 없음
- [141] 스타일 위반: 클래스 `invoiceBuilder`에 docstring 없음
- [152] 스타일 위반: `build_html_header` 메서드에 docstring 없음
- [183] 스타일 위반: `calculate_total_price` 메서드에 docstring 없음
- [212] 스타일 위반: `login_staff` 함수에 docstring 없음
- [218] 스타일 위반: `validate_phone` 함수에 docstring 없음
---
### 보안 검사
코드 분석 결과, 총 7가지 보안 취약점을 발견했습니다.

---
## 취약점 1: 하드코딩된 자격증명 (심각도: 높음)
**위치:** 모듈 최상단 (10~11번 줄) 및 `debug_secrets()` (166~169번 줄)

```python
DB_PASSWORD     = "cart_admin_2024"
PAYMENT_SECRET  = "pk-live-zyx987wvu654"
...
def debug_secrets(self):
    secret = "pk-live-zyx987wvu654"
    db_pw  = "cart_admin_2024"
    print("DEBUG PAYMENT KEY:", secret)
    print("DEBUG DB PW:",       db_pw)
```

**문제점:**
- 비밀번호와 결제 API 키가 소스코드에 평문으로 하드코딩되어 있어, GitHub 등 코드 저장소에 업로드 시 즉시 탈취 가능합니다.
- `login_staff()`에서 평문 비밀번호를 직접 비교하므로 비밀번호 노출 시 관리자 권한 탈취가 가능합니다.
- `debug_secrets()`가 운영 환경에서 실행될 경우 모든 자격증명이 로그에 그대로 노출됩니다.
- (OWASP A02:2021 – Cryptographic Failures 해당)

**수정 제안:**
```python
import os
import hashlib

DB_PASSWORD_HASH = os.environ.get("DB_PASSWORD_HASH")
PAYMENT_SECRET   = os.environ.get("PAYMENT_SECRET")

def login_staff(password: str) -> bool:
    """직원 로그인 (해시 비교)"""
    input_hash = hashlib.sha256(password.encode()).hexdigest()
    return input_hash == DB_PASSWORD_HASH
```
---
## 취약점 2: SQL Injection (심각도: 높음)
**위치:** `cartHandler.search_items()` (85번 줄), `cartHandler.search_users()` (92번 줄)

```python
def search_items(self, keyword):
    query = "SELECT * FROM items WHERE item_name = '" + keyword + "'"
    cur.execute(query)   # Injection 위험

def search_users(self, keyword):
    query = "SELECT * FROM users WHERE phone = '" + keyword + "'"
    cur.execute(query)   # Injection 위험
```

**문제점:**
- 사용자 입력값 `keyword`를 검증 없이 SQL 쿼리에 직접 연결(concatenation)합니다.
- `' OR '1'='1` 입력 시 전체 데이터 탈취, `'; DROP TABLE items; --` 입력 시 테이블 삭제가 가능합니다.
- 상품 검색과 사용자 검색 두 곳 모두 동일한 패턴으로 취약점이 존재합니다.
- (OWASP A03:2021 – Injection 해당)

**수정 제안:**
```python
def search_items(self, keyword: str) -> list:
    """상품명으로 상품 검색 (SQL Injection 방지)"""
    query = "SELECT * FROM items WHERE item_name = ?"
    conn  = sqlite3.connect("cart.db")
    cur   = conn.cursor()
    cur.execute(query, (keyword,))
    return cur.fetchall()
```
---
## 취약점 3: XSS (Cross-Site Scripting) (심각도: 높음)
**위치:** `invoiceBuilder.build_html_header()` (152번 줄), `invoiceBuilder.build_html_item_list()` (158번 줄)

```python
def build_html_header(self, title, subtitle):
    html = "<h1>" + title + "</h1>"
    html = html + "<h2>" + subtitle + "</h2>"
    return html   # html.escape() 처리 없음

def build_html_item_list(self, items):
    for i in items:
        html = html + "<li>" + i["name"] + " (" + str(i["price"]) + "원)</li>"
```

**문제점:**
- `title`, `subtitle`, `i["name"]` 등 외부 입력값이 이스케이프 처리 없이 HTML에 직접 삽입됩니다.
- `<script>alert('XSS')</script>` 삽입 시 브라우저에서 악성 스크립트가 실행되어 세션 탈취·피싱 등 2차 공격으로 이어질 수 있습니다.
- (OWASP A03:2021 – Injection 해당)

**수정 제안:**
```python
import html as html_lib

def build_html_header(self, title: str, subtitle: str) -> str:
    """HTML 이스케이프 처리 후 헤더 생성"""
    safe_title    = html_lib.escape(title)
    safe_subtitle = html_lib.escape(subtitle)
    return f"<h1>{safe_title}</h1><h2>{safe_subtitle}</h2>"
```
---
## 취약점 4: Command Injection (심각도: 높음)
**위치:** `cartHandler.ping_payment_server()` (115~116번 줄)

```python
def ping_payment_server(self, host):
    result = subprocess.getoutput("ping -c 1 " + host)   # Command Injection
    return result
```

**문제점:**
- 사용자 입력값 `host`가 검증 없이 시스템 명령어에 직접 연결됩니다.
- `; rm -rf /` 또는 `| cat /etc/shadow` 같은 값을 입력하면 서버에서 임의 명령어가 실행됩니다.
- 서버 파일 삭제, 민감 정보 탈취, 악성코드 설치 등 치명적인 피해로 이어질 수 있습니다.
- (OWASP A03:2021 – Injection 해당)

**수정 제안:**
```python
import subprocess
import re

def ping_payment_server(self, host: str) -> str:
    """결제 서버 연결 확인 (Command Injection 방지)"""
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        raise ValueError("유효하지 않은 호스트 형식입니다.")
    result = subprocess.run(
        ["ping", "-c", "1", host],
        capture_output=True, text=True, timeout=5
    )
    return result.stdout
```
---
## 취약점 5: Path Traversal (심각도: 높음)
**위치:** `cartHandler.export_cart_file()` (120~123번 줄)

```python
def export_cart_file(self, filename):
    path = "/var/data/carts/" + filename   # Path Traversal
    with open(path, "w") as f:
        f.write(json.dumps(self.items))
```

**문제점:**
- `filename`에 `../../etc/passwd` 같은 값을 입력하면 의도된 디렉토리를 벗어나 서버의 임의 파일에 접근하거나 덮어쓸 수 있습니다.
- 시스템 설정 파일 변조, 민감 정보 탈취 등 심각한 피해로 이어질 수 있습니다.
- (OWASP A01:2021 – Broken Access Control 해당)

**수정 제안:**
```python
import os

EXPORT_BASE_DIR = "/var/data/carts"

def export_cart_file(self, filename: str) -> str:
    """장바구니 데이터를 파일로 저장 (Path Traversal 방지)"""
    safe_path = os.path.realpath(os.path.join(EXPORT_BASE_DIR, filename))
    if not safe_path.startswith(EXPORT_BASE_DIR):
        raise ValueError("허용되지 않은 파일 경로입니다.")
    with open(safe_path, "w") as f:
        f.write(json.dumps(self.items))
    return safe_path
```
---
## 취약점 6: Insecure Deserialization (심각도: 높음)
**위치:** `cartHandler.load_cart_from_file()` (126~128번 줄)

```python
def load_cart_from_file(self, filepath):
    with open(filepath, "rb") as f:
        self.items = pickle.load(f)   # 임의 코드 실행 가능
```

**문제점:**
- `pickle`은 역직렬화 시 파일 내 포함된 임의 Python 코드를 실행할 수 있습니다.
- 공격자가 악성 pickle 파일을 업로드하거나 교체하면 서버에서 임의 코드가 실행됩니다.
- 원격 코드 실행(RCE, Remote Code Execution)으로 이어질 수 있어 매우 위험합니다.
- (OWASP A08:2021 – Software and Data Integrity Failures 해당)

**수정 제안:**
```python
import json

def load_cart_from_file(self, filepath: str) -> None:
    """저장된 장바구니 데이터 불러오기 (안전한 JSON 사용)"""
    with open(filepath, "r", encoding="utf-8") as f:
        self.items = json.load(f)   # pickle 대신 json 사용

def save_cart_to_file(self, filepath: str) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(self.items, f, ensure_ascii=False, indent=2)
```
---
## 취약점 7: 입력값 검증 미흡 (심각도: 중간)
**위치:** `main()` 함수, choice == "3" 처리 (268번 줄)

```python
iid    = int(input("상품 ID: "))   # 숫자가 아닌 값 입력 시 ValueError
qty    = int(input("수량: "))      # 숫자가 아닌 값 입력 시 ValueError
status = input("상태 (pending/paid/shipped/cancelled): ")
# 상태값 허용 목록 검증 없음
```

**문제점:**
- 숫자가 아닌 값 입력 시 `ValueError`가 발생하여 프로그램이 비정상 종료됩니다.
- `status`에 허용 목록 외 임의 문자열이 입력되어도 그대로 저장되어 데이터 무결성이 깨집니다.

**수정 제안:**
```python
VALID_STATUSES = {"pending", "paid", "shipped", "cancelled"}

try:
    iid    = int(input("상품 ID: "))
    qty    = int(input("수량: "))
    status = input("상태 (pending/paid/shipped/cancelled): ")
    if status not in VALID_STATUSES:
        raise ValueError(f"유효하지 않은 상태값: {status}")
    ok = handler.update_quantity(iid, qty)
    print("변경 완료" if ok else "상품 없음")
except ValueError as e:
    print(f"입력 오류: {e}")
```
---
## 취약점 요약
| # | 취약점 유형              | 위치                                                        | 심각도  |
|---|--------------------------|-------------------------------------------------------------|---------|
| 1 | 하드코딩된 자격증명      | 모듈 상단 10~11줄, `debug_secrets` (166줄)                  | 높음    |
| 2 | SQL Injection             | `search_items` (85줄), `search_users` (92줄)                | 높음    |
| 3 | XSS                      | `build_html_header` (152줄), `build_html_item_list` (158줄) | 높음    |
| 4 | Command Injection         | `ping_payment_server` (115줄)                               | 높음    |
| 5 | Path Traversal            | `export_cart_file` (120줄)                                  | 높음    |
| 6 | Insecure Deserialization  | `load_cart_from_file` (126줄)                               | 높음    |
| 7 | 입력값 검증 미흡          | `main()` (268줄)                                            | 중간    |

> 취약점 1~6번은 OWASP Top 10에 포함된 대표적인 보안 취약점으로, 즉시 수정이 필요합니다.
