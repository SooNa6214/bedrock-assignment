"""
monitoring_client.py
Observability 스택(Loki, Prometheus, Tempo, ArgoCD) 연동 클라이언트
"""

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 유효성 검증 헬퍼
# ---------------------------------------------------------------------------

def _validate_label(value: str) -> str:
    """namespace / service 등 레이블 값에 허용되지 않은 문자가 있으면 예외 발생."""
    if not re.match(r'^[a-zA-Z0-9_\-]+$', value):
        raise ValueError(f"허용되지 않은 문자 포함: {value}")
    return value


# ---------------------------------------------------------------------------
# 설정 데이터클래스
# ---------------------------------------------------------------------------

@dataclass
class ObservabilityConfig:
    loki_url: str = field(
        default_factory=lambda: os.environ.get("LOKI_URL", "http://loki:3100")
    )
    prometheus_url: str = field(
        default_factory=lambda: os.environ.get(
            "PROMETHEUS_URL", "http://prometheus:9090"
        )
    )
    tempo_url: str = field(
        default_factory=lambda: os.environ.get("TEMPO_URL", "http://tempo:3200")
    )
    argocd_url: str = field(
        default_factory=lambda: os.environ.get(
            "ARGOCD_URL", "http://argocd-server:80"
        )
    )
    argocd_token: str = field(
        default_factory=lambda: os.environ.get("ARGOCD_TOKEN", "")
    )

    def __post_init__(self) -> None:
        if not self.argocd_token:
            raise ValueError(
                "ARGOCD_TOKEN 환경변수가 설정되지 않았습니다."
            )

    def __repr__(self) -> str:
        """토큰이 로그에 노출되지 않도록 마스킹 처리."""
        return (
            f"ObservabilityConfig("
            f"loki_url={self.loki_url!r}, "
            f"prometheus_url={self.prometheus_url!r}, "
            f"tempo_url={self.tempo_url!r}, "
            f"argocd_url={self.argocd_url!r}, "
            f"argocd_token='***')"
        )


# ---------------------------------------------------------------------------
# 로그 엔트리
# ---------------------------------------------------------------------------

@dataclass
class LogEntry:
    timestamp: str
    message: str
    level: str
    namespace: str
    service: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None


# ---------------------------------------------------------------------------
# 추상 기본 클라이언트
# ---------------------------------------------------------------------------

class BaseObservabilityClient(ABC):
    """모든 Observability 클라이언트의 공통 기반 클래스."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests.Session()
        self.session.verify = os.environ.get("CA_BUNDLE_PATH", True)  # type: ignore[assignment]

    def is_healthy(
        self, health_path: str = "/ready", timeout: int = 5
    ) -> bool:
        """헬스체크 엔드포인트에 GET 요청 후 200 여부 반환."""
        try:
            url = urljoin(self.base_url, health_path)
            response = self.session.get(url, timeout=timeout)
            return response.status_code == 200
        except requests.RequestException as exc:
            logger.warning("%s 헬스체크 실패: %s", self.__class__.__name__, exc)
            return False


# ---------------------------------------------------------------------------
# Loki 클라이언트
# ---------------------------------------------------------------------------

class LokiClient(BaseObservabilityClient):
    """Loki 로그 조회 클라이언트."""

    def __init__(self, config: ObservabilityConfig) -> None:
        super().__init__(config.loki_url)

    def query_range(
        self,
        logql: str,
        start: str,
        end: str,
        limit: int = 100,
    ) -> list[dict]:
        """LogQL 쿼리로 지정 시간 범위의 로그를 조회합니다."""
        url = urljoin(self.base_url, "/loki/api/v1/query_range")
        params = {"query": logql, "start": start, "end": end, "limit": limit}
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
        except (ValueError, KeyError) as exc:
            logger.error("Loki 응답 파싱 실패: %s", exc)
            return []

    def get_error_logs(
        self,
        namespace: str,
        service: str,
        start: str,
        end: str,
        limit: int = 100,
    ) -> list[LogEntry]:
        """특정 namespace/service의 에러 로그를 조회하여 LogEntry 목록으로 반환."""
        namespace = _validate_label(namespace)
        service = _validate_label(service)

        logql = (
            f'{{namespace="{namespace}", service="{service}"}}'
            f' | json | level="error"'
        )
        raw_results = self.query_range(logql, start, end, limit)
        entries: list[LogEntry] = []
        for stream in raw_results:
            labels = stream.get("stream", {})
            for ts, line in stream.get("values", []):
                try:
                    payload = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    payload = {"message": line}
                entries.append(
                    LogEntry(
                        timestamp=ts,
                        message=payload.get("message", line),
                        level=payload.get("level", "error"),
                        namespace=labels.get("namespace", namespace),
                        service=labels.get("service", service),
                        trace_id=payload.get("traceId"),
                        span_id=payload.get("spanId"),
                    )
                )
        return entries

    def get_active_namespaces(self) -> list[str]:
        """현재 로그가 존재하는 namespace 목록을 반환합니다."""
        url = urljoin(self.base_url, "/loki/api/v1/label/namespace/values")
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json().get("data", [])
        except requests.RequestException as exc:
            logger.error("Loki namespace 목록 조회 실패: %s", exc)
            return []
        except (ValueError, KeyError) as exc:
            logger.error("Loki namespace 응답 파싱 실패: %s", exc)
            return []


# ---------------------------------------------------------------------------
# Prometheus 클라이언트
# ---------------------------------------------------------------------------

class PrometheusClient(BaseObservabilityClient):
    """Prometheus 메트릭 조회 클라이언트."""

    def __init__(self, config: ObservabilityConfig) -> None:
        super().__init__(config.prometheus_url)

    def query(self, promql: str, time: Optional[str] = None) -> list[dict]:
        """즉시 쿼리(instant query)를 실행합니다."""
        url = urljoin(self.base_url, "/api/v1/query")
        params: dict = {"query": promql}
        if time:
            params["time"] = time
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json().get("data", {}).get("result", [])
        except requests.Timeout:
            logger.error("Prometheus 요청 타임아웃: url=%s", url)
            return []
        except requests.RequestException as exc:
            logger.error("Prometheus 요청 실패: %s", exc)
            return []
        except (ValueError, KeyError) as exc:
            logger.error("Prometheus 응답 파싱 실패: %s", exc)
            return []

    def get_cpu_usage(self, namespace: str) -> list[dict]:
        """namespace별 Pod CPU 사용량을 조회합니다."""
        namespace = _validate_label(namespace)
        promql = (
            f'sum(rate(container_cpu_usage_seconds_total'
            f'{{namespace="{namespace}",container!=""}}[5m]))'
            f' by (pod, namespace)'
        )
        return self.query(promql)


# ---------------------------------------------------------------------------
# Tempo 클라이언트
# ---------------------------------------------------------------------------

class TempoClient(BaseObservabilityClient):
    """Tempo 트레이스 조회 클라이언트."""

    def __init__(self, config: ObservabilityConfig) -> None:
        super().__init__(config.tempo_url)

    def get_trace(self, trace_id: str) -> dict:
        """트레이스 ID로 상세 트레이스 정보를 조회합니다."""
        url = urljoin(self.base_url, f"/api/traces/{trace_id}")
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            logger.error("Tempo 요청 타임아웃: trace_id=%s", trace_id)
            return {}
        except requests.RequestException as exc:
            logger.error("Tempo 요청 실패: %s", exc)
            return {}
        except ValueError as exc:
            logger.error("Tempo 응답 파싱 실패: %s", exc)
            return {}


# ---------------------------------------------------------------------------
# ArgoCD 클라이언트
# ---------------------------------------------------------------------------

class ArgoCDClient(BaseObservabilityClient):
    """ArgoCD 애플리케이션 상태 조회 클라이언트."""

    def __init__(self, config: ObservabilityConfig) -> None:
        super().__init__(config.argocd_url)
        self.session.headers.update(
            {"Authorization": f"Bearer {config.argocd_token}"}
        )

    def list_applications(self) -> list[dict]:
        """배포된 ArgoCD 애플리케이션 목록을 반환합니다."""
        url = urljoin(self.base_url, "/api/v1/applications")
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.json().get("items", [])
        except requests.Timeout:
            logger.error("ArgoCD 요청 타임아웃: url=%s", url)
            return []
        except requests.RequestException as exc:
            logger.error("ArgoCD 요청 실패: %s", exc)
            return []
        except (ValueError, KeyError) as exc:
            logger.error("ArgoCD 응답 파싱 실패: %s", exc)
            return []


# ---------------------------------------------------------------------------
# 스택 헬스체크
# ---------------------------------------------------------------------------

def run_stack_health_check(config: ObservabilityConfig) -> dict[str, bool]:
    """전체 Observability 스택 헬스체크를 실행하고 결과를 반환합니다."""
    results: dict[str, bool] = {
        "loki": LokiClient(config).is_healthy(),
        "prometheus": PrometheusClient(config).is_healthy(),
        "tempo": TempoClient(config).is_healthy(),
        "argocd": ArgoCDClient(config).is_healthy(),
    }
    return results
