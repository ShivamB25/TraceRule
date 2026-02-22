from app.ast_compiler import build_full_select, compile_ast_to_sql
from app.schemas import Condition, LogicNode


def test_simple_equality():
    cond = Condition(subject_column="age", operator="<", value=18)
    assert compile_ast_to_sql(cond) == "age < 18"


def test_string_value_quoted():
    cond = Condition(subject_column="status", operator="==", value="active")
    assert compile_ast_to_sql(cond) == "status = 'active'"


def test_equals_operator_normalizes():
    cond = Condition(subject_column="level", operator="=", value="senior")
    assert compile_ast_to_sql(cond) == "level = 'senior'"


def test_not_equals():
    cond = Condition(subject_column="role", operator="!=", value="admin")
    assert compile_ast_to_sql(cond) == "role != 'admin'"


def test_greater_equal():
    cond = Condition(subject_column="salary", operator=">=", value=50000)
    assert compile_ast_to_sql(cond) == "salary >= 50000"


def test_less_equal():
    cond = Condition(subject_column="hours", operator="<=", value=40.5)
    assert compile_ast_to_sql(cond) == "hours <= 40.5"


def test_contains_ilike():
    cond = Condition(subject_column="description", operator="CONTAINS", value="fraud")
    assert compile_ast_to_sql(cond) == "description ILIKE '%fraud%'"


def test_contains_escapes_quotes():
    cond = Condition(subject_column="notes", operator="CONTAINS", value="it's bad")
    assert compile_ast_to_sql(cond) == "notes ILIKE '%it''s bad%'"


def test_is_null():
    cond = Condition(subject_column="email", operator="IS_NULL")
    assert compile_ast_to_sql(cond) == "email IS NULL"


def test_is_not_null():
    cond = Condition(subject_column="phone", operator="IS_NOT_NULL")
    assert compile_ast_to_sql(cond) == "phone IS NOT NULL"


def test_is_vague_compiles_to_truthy():
    cond = Condition(
        subject_column="gift_value",
        operator="IS_VAGUE",
        semantic_rubric="Is this gift lavish?",
    )
    assert compile_ast_to_sql(cond) == "1=1"


def test_boolean_value():
    cond = Condition(subject_column="is_active", operator="==", value=True)
    assert compile_ast_to_sql(cond) == "is_active = TRUE"


def test_boolean_false():
    cond = Condition(subject_column="verified", operator="==", value=False)
    assert compile_ast_to_sql(cond) == "verified = FALSE"


def test_and_logic():
    node = LogicNode(
        logic_type="AND",
        children=[
            Condition(subject_column="age", operator="<", value=18),
            Condition(subject_column="status", operator="==", value="active"),
        ],
    )
    result = compile_ast_to_sql(node)
    assert result == "(age < 18 AND status = 'active')"


def test_or_logic():
    node = LogicNode(
        logic_type="OR",
        children=[
            Condition(subject_column="role", operator="==", value="intern"),
            Condition(subject_column="role", operator="==", value="temp"),
        ],
    )
    result = compile_ast_to_sql(node)
    assert result == "(role = 'intern' OR role = 'temp')"


def test_unless_defeasible():
    node = LogicNode(
        logic_type="UNLESS",
        children=[
            Condition(subject_column="age", operator="<", value=18),
            Condition(subject_column="has_waiver", operator="==", value=True),
        ],
    )
    result = compile_ast_to_sql(node)
    assert result == "(age < 18 AND NOT (has_waiver = TRUE))"


def test_unless_single_child():
    node = LogicNode(
        logic_type="UNLESS",
        children=[
            Condition(subject_column="age", operator="<", value=18),
        ],
    )
    result = compile_ast_to_sql(node)
    assert result == "age < 18"


def test_unless_empty_children():
    node = LogicNode(logic_type="UNLESS", children=[])
    result = compile_ast_to_sql(node)
    assert result == "1=1"


def test_nested_logic():
    node = LogicNode(
        logic_type="AND",
        children=[
            Condition(subject_column="department", operator="==", value="finance"),
            LogicNode(
                logic_type="OR",
                children=[
                    Condition(subject_column="amount", operator=">", value=10000),
                    Condition(subject_column="flagged", operator="==", value=True),
                ],
            ),
        ],
    )
    result = compile_ast_to_sql(node)
    assert result == "(department = 'finance' AND (amount > 10000 OR flagged = TRUE))"


def test_build_full_select():
    node = LogicNode(
        logic_type="AND",
        children=[
            Condition(subject_column="age", operator="<", value=18),
        ],
    )
    result = build_full_select("employees", node)
    assert result == "SELECT id, data_payload FROM employees WHERE (age < 18)"


def test_string_with_single_quotes_escaped():
    cond = Condition(subject_column="name", operator="==", value="O'Brien")
    assert compile_ast_to_sql(cond) == "name = 'O''Brien'"


def test_numeric_float():
    cond = Condition(subject_column="rate", operator=">", value=3.14)
    assert compile_ast_to_sql(cond) == "rate > 3.14"


def test_mixed_vague_and_deterministic():
    node = LogicNode(
        logic_type="AND",
        children=[
            Condition(subject_column="amount", operator=">", value=5000),
            Condition(
                subject_column="purpose",
                operator="IS_VAGUE",
                semantic_rubric="Is this a legitimate business expense?",
            ),
        ],
    )
    result = compile_ast_to_sql(node)
    assert result == "(amount > 5000 AND 1=1)"
