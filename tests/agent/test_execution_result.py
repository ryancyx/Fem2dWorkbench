from __future__ import annotations

import pytest

from agent.execution_result import ExecutionResult


def test_execution_result_captures_exception_without_changing_solver() -> None:
    error = RuntimeError("singular matrix")

    result = ExecutionResult.failed("SOLVE", error)

    assert result.success is False
    assert result.error_type == "RuntimeError"
    assert result.error_message == "singular matrix"


def test_failed_execution_result_requires_message() -> None:
    with pytest.raises(ValueError, match="error_message"):
        ExecutionResult(success=False, stage="SOLVE")
