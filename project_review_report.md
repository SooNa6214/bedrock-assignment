"""
=============================================================
4장. RAG로 코드 스타일/보안 검사 구현
CodeBuddy: GitHub PR 자동 리뷰 Agent

검사 대상: monitoring_client.py (393줄)
리뷰 리포트의 실제 코드 예시를 실습 샘플로 활용
=============================================================

사전 준비:
  - AWS 계정 + Bedrock Knowledge Base 설정 완료
  - Knowledge Base ID를 아래 KB_ID 변수에 입력
  - 필요 패키지: pip install boto3 redis

실행 환경: Google Colab 또는 로컬 Python 3.9+
=============================================================
"""

import boto3
import hashlib
import json
import re
import time
from pathlib import Path

# ─────────────────────────────────────────
# [필수] Knowledge Base ID 설정
# AWS Bedrock 콘솔 → Knowledge bases → ID 복사
# ─────────────────────────────────────────
KB_ID     = "여기에_KB_ID_입력"           # 예: "ABC123DEFG"
REGION    = "ap-northeast-2"             # 서울 리전
MODEL_ARN = "global.anthropic.claude-sonnet-4-6"

bedrock_agent   = boto3.client("bedrock-agent-runtime", region_name=REGION)
bedrock_runtime = boto3.client("bedrock-runtime",       region_name=REGION)


# =============================================================
# 공통 헬퍼: Knowledge Base에 질의
# =============================================================

def ask_knowledge_base(prompt: str, top_k: int = 5,
                        search_type: str = "SEMANTIC") -> dict:
    """
    Knowledge Base에 프롬프트를 전달하고 응답과 참조 문서를 반환.
    Returns:
        {"answer": str, "sources": [{"score": float, "content": str}, ...]}
    """
    response = bedrock_agent.retrieve_and_generate(
        input={"text": prompt},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": KB_ID,
                "modelArn": MODEL_ARN,
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {
                        "numberOfResults": top_k,
                        "overrideSearchType": search_type,  # SEMANTIC | HYBRID
                    }
                },
            },
        },
    )
    sources = [
        {"score": r.get("score", 0), "content": r["content"]["text"][:200]}
        for r in response.get("retrievedResults", [])
    ]
    return {"answer": response["output"]["text"], "sources": sources}


def get_claude_response(user_message: str) -> str:
    """Bedrock Converse API로 Claude에 직접 질의 (Knowledge Base 없이)."""
    response = bedrock_runtime.converse(
        modelId=MODEL_ARN,
        messages=[{"role": "user", "content": [{"text": user_message}]}],
    )
    return response["output"]["message"]["content"][0]["text"]


# =============================================================
# 실습 샘플 코드 — monitoring_client.py 리뷰 리포트 예시
# =============================================================

# [스타일 이슈 1] 함수 내부 import json 반복 호출 (PEP8 위반)
CODE_STYLE_1_IMPORT = """
def get_error_logs(self, namespace, service, start, end, limit=100):
    import json          # PEP8 위반: 함수 내부 import, 파일 최상단에 있어야 함
    logql = (
        f'{namespace="{namespace}", service="{service}"}'
        f' | json | level="error"'
    )
    results = self.query_range(logql, start, end, limit)
    entries = []
    for stream in results:
        for ts, line in stream.get("values", []):
            payload = json.loads(line)
            entries.append(payload)
    return entries
"""

# [스타일 이슈 2] healthcheck → health_check 네이밍 (PEP8 snake_case)
CODE_STYLE_2_NAMING = """
def run_stack_healthcheck(config: ObservabilityConfig) -> dict[str, bool]:
    # 'healthcheck' 복합 단어 → 'health_check' 로 분리해야 함
    results = {
        "loki":       LokiClient(config).is_healthy(),
        "prometheus": PrometheusClient(config).is_healthy(),
        "tempo":      TempoClient(config).is_healthy(),
        "argocd":     ArgoCDClient(config).is_healthy(),
    }
    return results
"""

# [스타일 이슈 3] Optional 필드 기본값 누락
CODE_STYLE_3_TYPE_HINT = """
from dataclasses import dataclass
from typing import Optional

@dataclass
class LogEntry:
    timestamp: str
    message:   str
    level:     str
    namespace: str
    service:   str
    trace_id:  Optional[str]   # 기본값 없음 → 인스턴스 생성 시 항상 전달해야 함
    span_id:   Optional[str]   # 기본값 없음
"""

# [스타일 이슈 4] f-string 멀티라인 가독성 저하 (79자 초과)
CODE_STYLE_4_FSTRING = """
def get_cpu_usage(self, namespace: str) -> list[dict]:
    promql = f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}",container!=""}}[5m])) by (pod, namespace)'
    return self.query(promql)
"""

# [스타일 이슈 5] is_healthy() 중복 구현 (추상 클래스로 분리 필요)
CODE_STYLE_5_DUPLICATE = """
class LokiClient:
    def is_healthy(self) -> bool:
        try:
            r = self.session.get(self.base_url + "/ready", timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

class PrometheusClient:
    def is_healthy(self) -> bool:   # 완전히 동일한 로직 중복
        try:
            r = self.session.get(self.base_url + "/ready", timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False
"""

# [보안 이슈 1] LogQL 인젝션 — namespace/service 미검증 삽입
CODE_SECURITY_1_INJECTION = """
def get_error_logs(self, namespace, service, start, end, limit=100):
    # 외부 입력값을 검증 없이 LogQL 쿼리에 직접 삽입 (OWASP A03: Injection)
    logql = (
        f'{namespace="{namespace}", service="{service}"}'
        f' | json | level="error"'
    )
    return self.query_range(logql, start, end, limit)
"""

# [보안 이슈 2] 빈 ArgoCD 토큰 허용 (OWASP A07: 인증 실패)
CODE_SECURITY_2_TOKEN = """
@dataclass
class ObservabilityConfig:
    argocd_token: str = field(
        default_factory=lambda: os.environ.get("ARGOCD_TOKEN", "")
        # 빈 문자열 허용 → 토큰 없이 요청 전송 가능
    )
"""

# [보안 이슈 종합] 인젝션 + SSL 미설정 + 예외처리 누락
CODE_SECURITY_ALL = """
@dataclass
class ObservabilityConfig:
    argocd_token: str = field(
        default_factory=lambda: os.environ.get("ARGOCD_TOKEN", "")
    )

class LokiClient:
    def __init__(self, config):
        self.base_url = config.loki_url
        self.session  = requests.Session()   # SSL verify 명시 없음 (OWASP A02)

    def get_error_logs(self, namespace, service, start, end):
        logql = (
            f'{namespace="{namespace}", service="{service}"}'  # 인젝션 취약
            f' | json | level="error"'
        )
        response = self.session.get(self.base_url, params={"query": logql})
        response.raise_for_status()           # 예외 처리 없음
        return response.json()
"""


# =============================================================
# 실습 1 · RetrieveAndGenerate 기본 호출
# =============================================================

def check_code_style(code: str) -> str:
    """Knowledge Base를 활용해 PEP8 스타일 검사."""
    prompt = f"""
다음 코드가 PEP8 스타일 가이드를 위반하는 부분이 있다면 알려주세요.
위반 사항이 없으면 "통과"라고 답변해주세요.

코드:
{code}
"""
    return ask_knowledge_base(prompt)["answer"]


# =============================================================
# 실습 2 · 검색된 문서(참조 소스) 함께 출력
# =============================================================

def check_with_sources(code: str) -> None:
    """코드 검사 결과와 참조한 Knowledge Base 문서를 함께 출력."""
    result = ask_knowledge_base(
        f"다음 코드의 PEP8 위반사항을 찾아줘:\n{code}"
    )
    print("📚 참고한 문서:")
    for src in result["sources"]:
        print(f"  - 관련성 {src['score']:.2f}: {src['content']}...")
    print("\n🔍 최종 답변:")
    print(result["answer"])


# =============================================================
# 실습 3 · 구조화된 스타일 검사 함수
# =============================================================

def style_check(code: str) -> str:
    """코드 스타일 검사 후 위반 사항 리스트 반환."""
    prompt = f"""
당신은 코드 스타일 검사기입니다. 다음 코드에서 PEP8 또는 일반적인 스타일 규칙을
위반한 부분을 찾아주세요.

형식:
- [라인번호] 위반 유형: 설명

코드:
{code}
"""
    return ask_knowledge_base(prompt)["answer"]


# =============================================================
# 실습 4 · monitoring_client.py 스타일 이슈 5종 일괄 검사
# =============================================================

def run_style_samples() -> None:
    """monitoring_client.py 에서 발견된 스타일 위반 코드 5종을 검사."""
    samples = [
        ("이슈1 - 함수 내부 import",          CODE_STYLE_1_IMPORT),
        ("이슈2 - healthcheck 네이밍",         CODE_STYLE_2_NAMING),
        ("이슈3 - Optional 기본값 누락",        CODE_STYLE_3_TYPE_HINT),
        ("이슈4 - f-string 멀티라인 가독성",    CODE_STYLE_4_FSTRING),
        ("이슈5 - is_healthy() 중복 구현",      CODE_STYLE_5_DUPLICATE),
    ]
    for label, code in samples:
        print(f"\n{'='*55}")
        print(f"=== {label} ===")
        print(f"[코드]\n{code.strip()[:200]}")
        result = style_check(code)
        print(f"[결과]\n{result[:300]}...")


# =============================================================
# 실습 5 · 보안 취약점 검사
# =============================================================

def check_security(code: str) -> str:
    """보안 취약점 검사 (Injection / 인증 / SSL / 예외처리)."""
    prompt = f"""
다음 코드에서 보안 취약점을 찾아주세요.
특히 LogQL/PromQL Injection, 하드코딩된 토큰/비밀번호, SSL 검증 누락을
중점적으로 검사해주세요.

코드:
{code}

취약점이 있으면 위치, 유형, 심각도, 수정 제안을 포함해 주세요.
"""
    return ask_knowledge_base(prompt)["answer"]


# =============================================================
# 실습 6 · 취약점 리포트 JSON 생성
# =============================================================

def generate_security_report(code: str) -> dict:
    """
    보안 취약점을 분석하고 JSON 형식 리포트를 반환.
    결과는 security_report.json 파일로도 저장됩니다.
    """
    prompt = f"""
다음 코드의 보안 취약점을 분석하고 JSON 형식으로 보고서를 작성해주세요.

형식:
{{
  "vulnerabilities": [
    {{
      "line": 라인번호,
      "type": "취약점 유형",
      "severity": "CRITICAL/HIGH/MEDIUM/LOW",
      "description": "설명",
      "suggestion": "수정 제안"
    }}
  ],
  "summary": "전체 평가"
}}

코드:
{code}

반드시 순수 JSON만 반환하고 마크다운 코드 블록 없이 출력하세요.
"""
    raw   = ask_knowledge_base(prompt)["answer"]
    clean = re.sub(r"```(?:json)?|```", "", raw).strip()
    try:
        report = json.loads(clean)
    except json.JSONDecodeError:
        report = {"raw_response": raw}

    with open("security_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("✅ 리포트 저장 완료: security_report.json")
    return report


# =============================================================
# 실습 7 · 검색 방식 비교 (SEMANTIC vs HYBRID) + TopK 튜닝
# =============================================================

def compare_search_types(question: str) -> None:
    """SEMANTIC 검색과 HYBRID 검색 결과를 비교."""
    print("[ SEMANTIC 검색 결과 ]")
    sem = ask_knowledge_base(question, top_k=5, search_type="SEMANTIC")
    print(sem["answer"][:400])

    print("\n[ HYBRID 검색 결과 ]")
    hyb = ask_knowledge_base(question, top_k=5, search_type="HYBRID")
    print(hyb["answer"][:400])


def test_topk(question: str) -> None:
    """TopK 값(3, 5, 10)에 따른 응답 길이 비교."""
    for k in [3, 5, 10]:
        result = ask_knowledge_base(question, top_k=k)
        print(f"TopK={k:2d} | 결과 길이: {len(result['answer'])}자 "
              f"| 참조 문서 수: {len(result['sources'])}개")


# =============================================================
# 실습 8-A · Relevance Score 필터링
# =============================================================

def filter_by_relevance(question: str, threshold: float = 0.7) -> str:
    """관련성 점수 threshold 이상인 문서만 필터링하여 Claude에 전달."""
    response = bedrock_agent.retrieve(
        knowledgeBaseId=KB_ID,
        retrievalQuery={"text": question},
        retrievalConfiguration={
            "vectorSearchConfiguration": {"numberOfResults": 10}
        },
    )
    filtered_docs = [
        r["content"]["text"]
        for r in response["retrievalResults"]
        if r.get("score", 0) >= threshold
    ]
    if not filtered_docs:
        return "관련성 높은 문서를 찾지 못했습니다."

    context      = "\n\n".join(filtered_docs)
    final_prompt = f"참고 문서:\n{context}\n\n질문: {question}"
    return get_claude_response(final_prompt)


# =============================================================
# 실습 8-B · 다중 언어 지원
# =============================================================

def check_multilang(code: str, language: str) -> str:
    """언어별 스타일 가이드에 따라 코드 검사."""
    prompt = f"""
{language} 코드 스타일 가이드에 따라 다음 코드를 검사해주세요.

언어: {language}
코드:
{code}
"""
    return ask_knowledge_base(prompt)["answer"]


def run_multilang_samples() -> None:
    """JavaScript / Java / Go 샘플 코드 검사."""
    samples = {
        "JavaScript": """
function helloWorld() {
  console.log('Hello, World!');
}
""",
        "Java": """
public class HelloWorld {
  public static void main(String[] args) {
    System.out.println("Hello, World!");
  }
}
""",
        "Go": """
package main
import "fmt"
func main() {
\tfmt.Println("Hello, World!")
}
""",
    }
    for lang, code in samples.items():
        print(f"\n{'='*55}")
        print(f"--- {lang} 코드 검사 ---")
        print(check_multilang(code, lang)[:400])


# =============================================================
# 실습 9 · Redis 캐싱
# =============================================================

def setup_redis_cache():
    """
    Redis 클라이언트를 초기화합니다.
    Colab 환경:
        !apt-get install redis-server -q
        !redis-server --daemonize yes
        !pip install redis -q
    """
    try:
        import redis
        cache = redis.Redis(host="localhost", port=6379, decode_responses=True)
        cache.ping()
        print("✅ Redis 연결 성공")
        return cache
    except Exception as e:
        print(f"⚠️  Redis 연결 실패 ({e}). 캐싱 없이 진행합니다.")
        return None


def cached_code_review(code: str, cache=None, ttl_seconds: int = 3600) -> str:
    """캐시 hit 시 즉시 반환, miss 시 RAG 검사 후 캐시 저장."""
    if cache is None:
        return style_check(code)

    code_hash = hashlib.md5(code.encode()).hexdigest()
    cache_key  = f"code_review:{code_hash}"

    cached = cache.get(cache_key)
    if cached:
        print("✅ 캐시에서 결과 반환 (비용 0원)")
        return cached

    print("🔍 RAG 검사 실행...")
    result = style_check(code)
    cache.setex(cache_key, ttl_seconds, result)
    return result


# =============================================================
# 실습 10 · 성능 측정
# =============================================================

def measure_performance(code: str) -> None:
    """검사 소요 시간 및 예상 비용 출력."""
    start   = time.time()
    result  = style_check(code)
    elapsed = time.time() - start

    tokens_estimate = len(code.split()) + len(result.split())
    cost_estimate   = tokens_estimate * 0.00001

    print(f"⏱  소요 시간: {elapsed:.2f}초")
    print(f"📝 결과 길이: {len(result)}자")
    print(f"💰 예상 비용: 약 ${cost_estimate:.4f}")


# =============================================================
# 4교시 미션 · 프로젝트 전체 코드 검사 + Markdown 리포트 생성
# =============================================================

def full_project_review(project_path: str = "./") -> dict:
    """
    지정 경로의 모든 .py 파일에 대해 스타일 + 보안 검사를 실행하고
    Markdown 리포트(project_review_report.md)를 생성합니다.
    """
    results = {}

    for py_file in Path(project_path).glob("**/*.py"):
        with open(py_file, encoding="utf-8", errors="ignore") as f:
            code = f.read()
        if len(code) < 50:
            continue

        print(f"🔍 검사 중: {py_file}")
        results[py_file.name] = {
            "style":    style_check(code),
            "security": check_security(code),
            "lines":    len(code.splitlines()),
        }

    with open("project_review_report.md", "w", encoding="utf-8") as f:
        f.write("# 코드 리뷰 리포트\n\n")
        for filename, data in results.items():
            f.write(f"## {filename} ({data['lines']}줄)\n\n")
            f.write("### 스타일 검사\n")
            f.write(data["style"] + "\n\n")
            f.write("### 보안 검사\n")
            f.write(data["security"] + "\n\n")
            f.write("---\n\n")

    print("✅ 리포트 저장 완료: project_review_report.md")
    return results


# =============================================================
# 메인 실행부 — monitoring_client.py 리뷰 리포트 예시 코드 활용
# =============================================================

if __name__ == "__main__":

    # ── 실습 1: import 위치 문제 ──────────────────────────────
    print("\n" + "="*60)
    print("[실습 1] 기본 PEP8 검사 — 함수 내부 import json 문제")
    print("="*60)
    print(check_code_style(CODE_STYLE_1_IMPORT))

    # ── 실습 2: healthcheck 네이밍 + 참조 문서 출력 ───────────
    print("\n" + "="*60)
    print("[실습 2] 참조 문서 확인 — healthcheck 네이밍 문제")
    print("="*60)
    check_with_sources(CODE_STYLE_2_NAMING)

    # ── 실습 3: Optional 기본값 누락 ──────────────────────────
    print("\n" + "="*60)
    print("[실습 3] 구조화된 스타일 검사 — Optional 기본값 누락")
    print("="*60)
    print(style_check(CODE_STYLE_3_TYPE_HINT))

    # ── 실습 4: 스타일 이슈 5종 일괄 검사 ────────────────────
    print("\n" + "="*60)
    print("[실습 4] monitoring_client.py 스타일 이슈 5종 일괄 검사")
    print("="*60)
    run_style_samples()

    # ── 실습 5: LogQL 인젝션 보안 검사 ───────────────────────
    print("\n" + "="*60)
    print("[실습 5] 보안 검사 — LogQL 인젝션 취약점")
    print("="*60)
    print(check_security(CODE_SECURITY_1_INJECTION))

    print("\n" + "="*60)
    print("[실습 5] 보안 검사 — 빈 ArgoCD 토큰 허용")
    print("="*60)
    print(check_security(CODE_SECURITY_2_TOKEN))

    # ── 실습 6: 종합 JSON 리포트 ─────────────────────────────
    print("\n" + "="*60)
    print("[실습 6] JSON 보안 리포트 — monitoring_client.py 종합")
    print("="*60)
    report = generate_security_report(CODE_SECURITY_ALL)
    print(json.dumps(report, ensure_ascii=False, indent=2)[:600])

    # ── 실습 7: SEMANTIC vs HYBRID + TopK ────────────────────
    print("\n" + "="*60)
    print("[실습 7] SEMANTIC vs HYBRID — LogQL 인젝션 방어 검색")
    print("="*60)
    compare_search_types("LogQL PromQL 인젝션 방어 방법")

    print("\n[ TopK 튜닝 실험 ]")
    test_topk("Python Optional 타입 힌트 기본값")

    # ── 실습 8-A: Relevance Score 필터링 ─────────────────────
    print("\n" + "="*60)
    print("[실습 8-A] Relevance Score 필터링 — ArgoCD 토큰 검증")
    print("="*60)
    print(filter_by_relevance("ArgoCD 토큰 빈값 검증 방법", threshold=0.7))

    # ── 실습 8-B: 다중 언어 검사 ─────────────────────────────
    print("\n" + "="*60)
    print("[실습 8-B] 다중 언어 스타일 검사")
    print("="*60)
    run_multilang_samples()

    # ── 실습 9: Redis 캐싱 ────────────────────────────────────
    print("\n" + "="*60)
    print("[실습 9] Redis 캐싱 — LogQL 인젝션 코드 반복 검사")
    print("="*60)
    cache = setup_redis_cache()
    if cache:
        time.sleep(2)
    first  = cached_code_review(CODE_SECURITY_1_INJECTION, cache)  # RAG 실행
    second = cached_code_review(CODE_SECURITY_1_INJECTION, cache)  # 캐시 반환

    # ── 실습 10: 성능 측정 ────────────────────────────────────
    print("\n" + "="*60)
    print("[실습 10] 성능 측정 — monitoring_client.py 종합 코드")
    print("="*60)
    measure_performance(CODE_SECURITY_ALL)

    # ── 미션: 프로젝트 전체 Markdown 리포트 ──────────────────
    print("\n" + "="*60)
    print("[미션] 프로젝트 전체 검사 + Markdown 리포트 생성")
    print("="*60)
    full_project_review("./")
