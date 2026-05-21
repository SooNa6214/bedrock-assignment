# 프로젝트 코드 리뷰 리포트

## 검사 대상
- 파일명: `monitoring_client.py`
- 총 라인 수: 393줄

---

## 스타일 검사 결과

## 1. Import 위치 문제

**문제점:** `get_error_logs` 메서드 내부에서 `import json`이 반복 호출됨

**이유:** PEP 8에 따르면 모든 import 문은 파일 최상단에 위치해야 함. 함수 내부 import는 반복 호출 시 불필요한 오버헤드 및 가독성 저하 발생

**개선 방법:**
```python
# 파일 최상단에 배치
import json
import os
import logging
import requests
```

---

## 2. 변수명/함수명 네이밍 규칙

**문제점:** 전반적으로 snake_case는 잘 지켜지고 있으나, `run_stack_healthcheck` 함수명에서 `healthcheck`는 `health_check`로 분리하는 것이 더 명확함

**이유:** PEP 8 snake_case 규칙상 복합 단어는 언더스코어로 구분하는 것이 권장됨

**개선 방법:**
```python
def run_stack_health_check(config: ObservabilityConfig) -> dict[str, bool]:
    ...
```

---

## 3. 타입 힌트 누락

**문제점:** `LogEntry` 데이터클래스의 필드에 타입 힌트는 있으나, `Optional` 필드들의 기본값(`field(default=None)`)이 명시되지 않음

**이유:** `Optional[str]` 타입으로 선언된 `trace_id`, `span_id`는 기본값이 없어 인스턴스 생성 시 항상 명시적으로 전달해야 하므로 유연성이 낮음

**개선 방법:**
```python
@dataclass
class LogEntry:
    timestamp: str
    message: str
    level: str
    namespace: str
    service: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
```

---

## 4. 들여쓰기 및 가독성

**문제점:** 코드 전반의 들여쓰기(4 spaces)와 라인 길이는 대체로 준수하고 있으나, 일부 f-string 멀티라인 작성 시 가독성이 다소 낮음

**이유:** PEP 8 기준 최대 79자 라인 길이를 유지해야 하며, 긴 문자열은 괄호를 활용한 암묵적 줄 이음(implicit line continuation)을 활용하는 것이 권장됨

**개선 방법:**
```python
# 개선: 문자열 연결을 하나의 f-string으로 통합
promql = (
    f'sum(rate(container_cpu_usage_seconds_total'
    f'{{namespace="{namespace}",container!=""}}[5m]))'
    f' by (pod, namespace)'
)
```

---

## 5. 함수 분리 및 유지보수성

**문제점:** `LokiClient`, `PrometheusClient`, `TempoClient`, `ArgoCDClient` 각 클라이언트마다 `is_healthy()` 메서드가 중복 구현됨

**이유:** 동일한 패턴의 헬스체크 로직이 반복되면 유지보수 시 일관성 유지가 어려움. 공통 인터페이스(추상 클래스)로 분리하면 코드 중복을 줄일 수 있음

**개선 방법:**
```python
from abc import ABC, abstractmethod

class BaseObservabilityClient(ABC):
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests.Session()

    def is_healthy(self, health_path: str = "/ready", timeout: int = 5) -> bool:
        try:
            url = urljoin(self.base_url, health_path)
            response = self.session.get(url, timeout=timeout)
            return response.status_code == 200
        except requests.RequestException as exc:
            logger.warning("%s 헬스체크 실패: %s", self.__class__.__name__, exc)
            return False

class LokiClient(BaseObservabilityClient):
    def __init__(self, config: ObservabilityConfig) -> None:
        super().__init__(config.loki_url)
```

---

## 6. 코드 파일 미완성

**문제점:** `run_stack_healthcheck` 함수가 중간에 잘림 (`"temp` 이후 코드 없음)

**이유:** 코드가 불완전하여 실제 동작 여부 확인 불가. 완전한 코드를 제공해야 리뷰 및 테스트가 가능함

**개선 방법:**
```python
def run_stack_health_check(config: ObservabilityConfig) -> dict[str, bool]:
    """전체 Observability 스택 헬스체크 실행"""
    results = {
        "loki": LokiClient(config).is_healthy(),
        "prometheus": PrometheusClient(config).is_healthy(),
        "tempo": TempoClient(config).is_healthy(),
        "argocd": ArgoCDClient(config).is_healthy(),
    }
    return results
```

### 스타일 검사 참고 문서

- 참고 문서 1
- 참고 문서 2

---

## 보안 검사 결과

## 🔴 [위험도: 높음] LogQL / PromQL 인젝션 취약점

**문제점:**
`get_error_logs()` 메서드에서 `namespace`, `service`, `query()` 메서드에서 `namespace` 파라미터가 문자열 f-string으로 직접 쿼리에 삽입됩니다.

```python
# 취약한 코드
logql = (
    f'{{namespace="{namespace}", service="{service}"}} '
    f'| json | level="error"'
)
```

**원인:**
외부 입력값에 대한 검증 없이 쿼리 문자열에 직접 포함시키면, 신뢰할 수 없는 데이터가 쿼리의 일부로 해석될 수 있습니다. 이는 OWASP Top 10의 A03:2021 – Injection 항목에 해당합니다.

**개선 방법:**
- 입력값에 대해 허용된 문자만 통과시키는 화이트리스트 검증 적용
- 정규식으로 namespace/service 이름 형식 검증 (`^[a-z0-9-]+$` 등)
- 파라미터화된 쿼리 방식 또는 인코딩 처리 적용

```python
import re

def _validate_label(value: str) -> str:
    if not re.match(r'^[a-zA-Z0-9_\-]+$', value):
        raise ValueError(f"허용되지 않은 문자 포함: {value}")
    return value
```

---

## 🔴 [위험도: 높음] 인증 토큰 처리 방식 취약점

**문제점:**
ArgoCD 토큰이 `ObservabilityConfig` 데이터클래스에 평문 문자열로 저장되며, 기본값이 빈 문자열(`""`)로 설정되어 있습니다. 토큰 미설정 시 인증 없이 동작할 가능성이 있습니다.

```python
argocd_token: str = field(
    default_factory=lambda: os.environ.get("ARGOCD_TOKEN", "")
)
```

**원인:**
인증 토큰이 빈 값일 때의 예외 처리가 없어, 인증이 누락된 채로 요청이 전송될 수 있습니다. OWASP A07:2021 – Identification and Authentication Failures에 해당합니다.

**개선 방법:**
- 토큰이 빈 문자열인 경우 초기화 단계에서 예외 발생
- 토큰 값을 로그에 출력하지 않도록 `__repr__`/`__str__` 마스킹 처리
- `dataclass`에 `repr=False` 또는 별도 SecretStr 타입 활용

```python
def __post_init__(self):
    if not self.argocd_token:
        raise ValueError("ARGOCD_TOKEN 환경변수가 설정되지 않았습니다.")
```

---

## 🟠 [위험도: 중간] SSL/TLS 검증 미적용

**문제점:**
모든 `requests.Session()` 호출에서 SSL 인증서 검증 설정이 명시되어 있지 않습니다. 내부 클러스터 통신이더라도 `verify` 옵션이 명시적으로 관리되지 않습니다.

**원인:**
`requests` 기본값은 `verify=True`이지만, 코드 내에서 명시하지 않으면 이후 유지보수 중 `verify=False`로 잘못 변경될 위험이 있습니다. 또한 자체 서명 인증서 환경에서 무분별한 검증 비활성화는 암호화 실패로 이어질 수 있습니다(OWASP A02:2021).

**개선 방법:**
- Session 생성 시 CA 번들 경로를 명시적으로 설정
- 환경변수로 CA 경로 또는 검증 여부를 주입받아 관리

```python
self.session = requests.Session()
self.session.verify = os.environ.get("CA_BUNDLE_PATH", True)
```

---

## 🟠 [위험도: 중간] 예외 처리 일관성 부족

**문제점:**
`is_healthy()` 메서드는 `requests.RequestException`을 잡아 처리하지만, `query_range()`, `query()`, `get_active_namespaces()` 등 다른 메서드는 예외 처리가 전혀 없습니다.

```python
# 예외 처리 없는 메서드 예시
def query_range(self, ...):
    response = self.session.get(url, params=params, timeout=30)
    response.raise_for_status()  # 예외가 상위로 전파됨
    return response.json().get("data", {}).get("result", [])
```

**원인:**
네트워크 오류, 서비스 다운, 잘못된 응답 형식 등의 상황에서 처리되지 않은 예외가 애플리케이션 전체를 중단시킬 수 있습니다.

**개선 방법:**
- 각 퍼블릭 메서드에 `try/except` 추가 및 의미 있는 예외 클래스 정의
- `response.json()` 파싱 실패에 대한 방어 코드 추가

```python
def query_range(self, ...) -> list[dict]:
    try:
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json().get("data", {}).get("result", [])
    except requests.Timeout:
        logger.error("Loki 요청 타임아웃: url=%s", url)
        return []
    except requests.RequestException as exc:
        logger.error("Loki 요청 실패: %s", exc)
        return []
    except ValueError as exc:
        logger.error("Loki 응답 파싱 실패: %s", exc)
        return []
```

### 보안 검사 참고 문서

- 참고 문서 1
- 참고 문서 2
- 참고 문서 3
- 참고 문서 4

---

## 종합 평가

Knowledge Base 기반 RAG 검색을 활용하여 Python 코드의 스타일 및 보안 검사를 수행하였습니다.
