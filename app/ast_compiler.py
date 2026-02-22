"""Pure-Python recursive compiler: Deontic AST → PostgreSQL WHERE clause.

No LLM involved. Deterministic transformation only.
"""

from __future__ import annotations

from typing import Union

from app.schemas import Condition, LogicNode


def compile_ast_to_sql(node: Union[LogicNode, Condition]) -> str:
    """Walk the AST tree and emit a SQL WHERE fragment.

    IS_VAGUE conditions compile to ``1=1`` — they are resolved post-hoc by
    the RRF hybrid search + adversarial courtroom, never by SQL.
    """
    if isinstance(node, Condition):
        return _compile_condition(node)
    return _compile_logic(node)


def _compile_condition(cond: Condition) -> str:
    # Vague predicates are handled by the semantic pipeline, not SQL
    if cond.operator == "IS_VAGUE":
        return "1=1"

    op_map: dict[str, str] = {
        "==": "=",
        "=": "=",
        "!=": "!=",
        ">": ">",
        "<": "<",
        ">=": ">=",
        "<=": "<=",
        "CONTAINS": "ILIKE",
        "IS_NULL": "IS NULL",
        "IS_NOT_NULL": "IS NOT NULL",
    }

    sql_op = op_map[cond.operator]

    # Unary operators (no value needed)
    if cond.operator in {"IS_NULL", "IS_NOT_NULL"}:
        return f"{cond.subject_column} {sql_op}"

    # CONTAINS → ILIKE pattern match
    if cond.operator == "CONTAINS":
        safe_val = str(cond.value).replace("'", "''")
        return f"{cond.subject_column} {sql_op} '%{safe_val}%'"

    # Boolean literal — must check BEFORE numeric since bool subclasses int
    if isinstance(cond.value, bool):
        return f"{cond.subject_column} {sql_op} {str(cond.value).upper()}"

    # Numeric literals — no quoting
    if isinstance(cond.value, (int, float)):
        return f"{cond.subject_column} {sql_op} {cond.value}"

    # String / fallback — single-quote with basic escaping
    safe_val = str(cond.value).replace("'", "''")
    return f"{cond.subject_column} {sql_op} '{safe_val}'"


def _compile_logic(node: LogicNode) -> str:
    child_sqls = [compile_ast_to_sql(child) for child in node.children]

    if node.logic_type == "AND":
        return f"({' AND '.join(child_sqls)})"

    if node.logic_type == "OR":
        return f"({' OR '.join(child_sqls)})"

    if node.logic_type == "UNLESS":
        # Defeasible logic: A UNLESS B  →  A AND NOT (B)
        if len(child_sqls) < 2:
            return child_sqls[0] if child_sqls else "1=1"
        return f"({child_sqls[0]} AND NOT ({child_sqls[1]}))"

    # Should never reach here due to Literal type constraint
    return "1=1"


def build_full_select(target_table: str, logic_tree: LogicNode) -> str:
    """Compile a complete SELECT statement from the AST root."""
    where_clause = compile_ast_to_sql(logic_tree)
    return f"SELECT id, data_payload FROM {target_table} WHERE {where_clause}"
