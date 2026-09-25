from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ExecutionResult:
    success: bool
    stage: str
    solve_result: Any | None = None
    error_type: str = ""
    error_message: str = ""

    def __post_init__(self) -> None:
        self.success = bool(self.success)
        self.stage = str(self.stage).strip()
        self.error_type = str(self.error_type).strip()
        self.error_message = str(self.error_message).strip()
        if not self.stage:
            raise ValueError("ExecutionResult.stage must not be empty")
        if self.success and (self.error_type or self.error_message):
            raise ValueError("Successful ExecutionResult must not contain an error")
        if not self.success and not self.error_message:
            raise ValueError("Failed ExecutionResult must contain error_message")

    @classmethod
    def succeeded(cls, stage: str, solve_result: Any | None = None) -> "ExecutionResult":
        return cls(success=True, stage=stage, solve_result=solve_result)

    @classmethod
    def failed(
        cls,
        stage: str,
        error: BaseException,
        solve_result: Any | None = None,
    ) -> "ExecutionResult":
        return cls(
            success=False,
            stage=stage,
            solve_result=solve_result,
            error_type=type(error).__name__,
            error_message=str(error) or type(error).__name__,
        )

    def to_dict(self, include_solve_result: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "success": self.success,
            "stage": self.stage,
            "errorType": self.error_type,
            "errorMessage": self.error_message,
        }
        if include_solve_result:
            data["solveResult"] = self.solve_result
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionResult":
        if not isinstance(data, dict):
            raise ValueError("ExecutionResult data must be a dictionary")
        return cls(
            success=bool(data.get("success", False)),
            stage=str(data.get("stage", "")),
            solve_result=data.get("solveResult", data.get("solve_result")),
            error_type=str(data.get("errorType", data.get("error_type", ""))),
            error_message=str(data.get("errorMessage", data.get("error_message", ""))),
        )
