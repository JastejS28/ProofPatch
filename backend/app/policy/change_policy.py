import ast
from dataclasses import dataclass
from pathlib import Path

from app.repository.analyzer import (
    analyze_target_function,
)


@dataclass
class PolicyResult:
    passed: bool
    reasons: list[str]


class CandidatePolicyVisitor(
    ast.NodeVisitor
):
    FORBIDDEN_CALLS = {
        "eval",
        "exec",
        "compile",
        "__import__",
        "open",
        "os.system",
        "os.popen",
        "subprocess.run",
        "subprocess.Popen",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
    }

    FORBIDDEN_IMPORT_ROOTS = {
        "subprocess",
        "socket",
        "requests",
        "httpx",
        "aiohttp",
        "multiprocessing",
        "threading",
    }

    NETWORK_ROOTS = {
        "requests",
        "httpx",
        "aiohttp",
        "socket",
        "urllib",
    }

    def __init__(self) -> None:
        self.reasons: list[str] = []

    def visit_Import(
        self,
        node: ast.Import,
    ) -> None:

        for alias in node.names:
            root = alias.name.split(
                ".",
                1,
            )[0]

            if (
                root
                in self.FORBIDDEN_IMPORT_ROOTS
            ):
                self.reasons.append(
                    f"Imports forbidden module "
                    f"'{root}'."
                )

        self.generic_visit(node)

    def visit_ImportFrom(
        self,
        node: ast.ImportFrom,
    ) -> None:

        module = node.module or ""

        root = module.split(
            ".",
            1,
        )[0]

        if (
            root
            in self.FORBIDDEN_IMPORT_ROOTS
        ):
            self.reasons.append(
                f"Imports forbidden module "
                f"'{root}'."
            )

        self.generic_visit(node)

    def visit_Call(
        self,
        node: ast.Call,
    ) -> None:

        call_name = self._call_name(
            node.func
        )

        if (
            call_name
            in self.FORBIDDEN_CALLS
        ):
            self.reasons.append(
                f"Uses forbidden call "
                f"'{call_name}'."
            )

        root = (
            call_name.split(
                ".",
                1,
            )[0]
            if call_name
            else ""
        )

        if root in self.NETWORK_ROOTS:
            self.reasons.append(
                f"Uses network-related "
                f"call '{call_name}'."
            )

        self.generic_visit(node)

    @staticmethod
    def _call_name(
        node: ast.AST,
    ) -> str:

        if isinstance(
            node,
            ast.Name,
        ):
            return node.id

        if isinstance(
            node,
            ast.Attribute,
        ):
            parent = (
                CandidatePolicyVisitor
                ._call_name(
                    node.value
                )
            )

            if parent:
                return (
                    f"{parent}."
                    f"{node.attr}"
                )

            return node.attr

        return ""


async def check_change_policy(
    workspace: Path,
    target_file: str,
    target_function: str,
    changed_files: list[str],
) -> PolicyResult:

    reasons: list[str] = []

    normalized_target = (
        Path(target_file).as_posix()
    )

    normalized_changed = [
        Path(path).as_posix()
        for path in changed_files
    ]

    if not normalized_changed:
        reasons.append(
            "Candidate produced no file changes."
        )

    unexpected_files = [
        path
        for path in normalized_changed
        if path != normalized_target
    ]

    if unexpected_files:
        reasons.append(
            "Candidate modified files outside "
            "the target file: "
            + ", ".join(
                unexpected_files
            )
        )

    analysis = (
        analyze_target_function(
            workspace=workspace,
            target_file=target_file,
            target_function=target_function,
        )
    )

    visitor = CandidatePolicyVisitor()

    visitor.visit(
        analysis.node
    )

    reasons.extend(
        visitor.reasons
    )

    unique_reasons = sorted(
        set(reasons)
    )

    return PolicyResult(
        passed=not unique_reasons,
        reasons=unique_reasons,
    )