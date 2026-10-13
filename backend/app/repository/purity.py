import ast
from dataclasses import dataclass


@dataclass
class PurityResult:
    passed: bool
    reasons: list[str]


class PurityVisitor(ast.NodeVisitor):
    FILE_CALLS = {
        "open",
    }

    FILE_METHODS = {
        "open",
        "read_text",
        "write_text",
        "read_bytes",
        "write_bytes",
        "unlink",
        "rename",
        "replace",
    }

    NETWORK_ROOTS = {
        "requests",
        "httpx",
        "urllib",
        "socket",
        "aiohttp",
    }

    def __init__(self) -> None:
        self.reasons: list[str] = []

    def visit_Global(
        self,
        node: ast.Global,
    ) -> None:
        self.reasons.append(
            "Uses the global keyword."
        )

        self.generic_visit(node)

    def visit_Assign(
        self,
        node: ast.Assign,
    ) -> None:
        for target in node.targets:
            if self._is_self_attribute(target):
                self.reasons.append(
                    "Mutates an attribute on self."
                )

        self.generic_visit(node)

    def visit_AnnAssign(
        self,
        node: ast.AnnAssign,
    ) -> None:
        if self._is_self_attribute(node.target):
            self.reasons.append(
                "Mutates an attribute on self."
            )

        self.generic_visit(node)

    def visit_AugAssign(
        self,
        node: ast.AugAssign,
    ) -> None:
        if self._is_self_attribute(node.target):
            self.reasons.append(
                "Mutates an attribute on self."
            )

        self.generic_visit(node)

    def visit_Call(
        self,
        node: ast.Call,
    ) -> None:
        call_name = self._call_name(
            node.func
        )

        if call_name in self.FILE_CALLS:
            self.reasons.append(
                f"Uses file I/O call '{call_name}'."
            )

        if isinstance(
            node.func,
            ast.Attribute,
        ):
            if (
                node.func.attr
                in self.FILE_METHODS
            ):
                self.reasons.append(
                    "Uses a file I/O method "
                    f"'{node.func.attr}'."
                )

        root = (
            call_name.split(".", 1)[0]
            if call_name
            else ""
        )

        if root in self.NETWORK_ROOTS:
            self.reasons.append(
                "Uses network-related call "
                f"'{call_name}'."
            )

        self.generic_visit(node)

    @staticmethod
    def _is_self_attribute(
        node: ast.AST,
    ) -> bool:
        return (
            isinstance(node, ast.Attribute)
            and isinstance(
                node.value,
                ast.Name,
            )
            and node.value.id == "self"
        )

    @staticmethod
    def _call_name(
        node: ast.AST,
    ) -> str:
        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Attribute):
            parent = PurityVisitor._call_name(
                node.value
            )

            if parent:
                return (
                    f"{parent}.{node.attr}"
                )

            return node.attr

        return ""


def check_function_purity(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> PurityResult:
    visitor = PurityVisitor()

    visitor.visit(node)

    reasons = sorted(
        set(visitor.reasons)
    )

    return PurityResult(
        passed=not reasons,
        reasons=reasons,
    )