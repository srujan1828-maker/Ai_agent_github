from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    TEST_FAILURES = "test_failures"
    TIMEOUT = "timeout"
    SANDBOX_ERROR = "sandbox_error"


class TestFailure(BaseModel):
    test_name: str
    message: str


class TestResults(BaseModel):
    passed: int = 0
    failed: int = 0
    failures: list[TestFailure] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    status: ExecutionStatus
    exit_code: Optional[int] = None
    execution_time_ms: Optional[int] = None
    resource_usage: Optional[dict] = None
    stdout: Optional[str] = ""
    stderr: Optional[str] = ""
    diff: Optional[str] = None
    files_changed: list[str] = Field(default_factory=list)
    test_results: Optional[TestResults] = None


class RepoContext(BaseModel):
    language: str
    framework: Optional[str] = None


class AnalyzeRequest(BaseModel):
    job_id: str
    diff: str
    execution_result: ExecutionResult
    repo_context: RepoContext


class IssueType(str, Enum):
    SECURITY = "security"
    BUG = "bug"
    PERFORMANCE = "performance"
    QUALITY = "quality"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Recommendation(str, Enum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    BLOCK = "block"


class Issue(BaseModel):
    type: IssueType
    severity: Severity
    file: str
    line: int
    description: str
    suggested_fix: str


class AnalyzeResponse(BaseModel):
    job_id: str
    merge_readiness_score: int = Field(ge=0, le=100)
    summary: str
    issues: list[Issue] = Field(default_factory=list)
    recommendation: Recommendation

    @field_validator("merge_readiness_score", mode="before")
    @classmethod
    def clamp_score(cls, v: int) -> int:
        return max(0, min(100, v))


# --- Internal models for LLM structured output ---


class LLMIssue(BaseModel):
    """Issue as returned by LLM (before mapping to output schema)."""

    severity: str
    file: str
    line: Optional[int] = 1
    description: str
    suggested_fix: str

    @field_validator("line", mode="before")
    @classmethod
    def default_line(cls, value):
        if value is None:
            return 1
        return value


class LLMAnalysisResult(BaseModel):
    """Structured output from a single analysis branch."""

    issues: list[LLMIssue] = Field(default_factory=list)


# --- FileDiff for parsed diffs ---


class FileDiff(BaseModel):
    filename: str
    content: str


def safe_default_response(job_id: str) -> AnalyzeResponse:
    """Return safe fallback when automated review fails."""
    return AnalyzeResponse(
        job_id=job_id,
        merge_readiness_score=0,
        summary="Automated review failed",
        issues=[],
        recommendation=Recommendation.BLOCK,
    )
