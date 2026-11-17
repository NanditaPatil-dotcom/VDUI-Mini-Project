"""Tiny TMDL (Tabular Model Definition Language) writer used by build_pbip.py."""
import re

T = "\t"


def q(name: str) -> str:
    """Quote an identifier for TMDL when it contains anything but [A-Za-z0-9_]."""
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else "'" + name.replace("'", "''") + "'"


def _block(expr: str, base: int) -> str:
    """Render a multi-line expression body indented `base` tabs."""
    lines = expr.strip("\n").split("\n")
    # normalise: strip common leading whitespace, convert remaining 4-space groups to tabs
    nonempty = [l for l in lines if l.strip()]
    indent = min(len(l) - len(l.lstrip()) for l in nonempty) if nonempty else 0
    out = []
    for l in lines:
        l = l[indent:] if l.strip() else ""
        lead = len(l) - len(l.lstrip(" "))
        l = T * (lead // 4) + l.lstrip(" ")
        out.append((T * base + l) if l else "")
    return "\n".join(out)


def column(name, dtype="string", source=None, hidden=False, summarize=None, sort_by=None,
           fmt=None, expr=None, folder=None, desc=None, category=None):
    s = T + "column " + q(name)
    if expr is not None:
        if "\n" in expr:
            s += " =\n" + _block(expr, 3)
        else:
            s += " = " + expr
    s += "\n"
    s += f"{T*2}dataType: {dtype}\n"
    if fmt:
        s += f"{T*2}formatString: {fmt}\n"
    if hidden:
        s += f"{T*2}isHidden\n"
    if desc:
        s += f"{T*2}description: {desc}\n"
    if folder:
        s += f"{T*2}displayFolder: {folder}\n"
    if category:
        s += f"{T*2}dataCategory: {category}\n"
    if summarize is None:
        summarize = "none" if dtype in ("string", "boolean") or hidden else "none"
    s += f"{T*2}summarizeBy: {summarize}\n"
    if sort_by:
        s += f"{T*2}sortByColumn: {q(sort_by)}\n"
    if expr is None:
        s += f"{T*2}sourceColumn: {source or name}\n"
    return s


def measure(name, expr, fmt=None, folder=None, desc=None, hidden=False):
    s = T + "measure " + q(name) + " ="
    if "\n" in expr.strip():
        s += "\n" + _block(expr, 3) + "\n"
    else:
        s += " " + expr.strip() + "\n"
    if fmt:
        s += f"{T*2}formatString: {fmt}\n"
    if folder:
        s += f"{T*2}displayFolder: {folder}\n"
    if desc:
        s += f"{T*2}description: {desc}\n"
    if hidden:
        s += f"{T*2}isHidden\n"
    return s


def partition(name, m_code, mode="import"):
    return (f"{T}partition {q(name)} = m\n{T*2}mode: {mode}\n{T*2}source =\n"
            + _block(m_code, 4) + "\n")


def table(name, columns, m_code=None, measures=(), hidden=False, desc=None):
    s = f"table {q(name)}\n"
    if hidden:
        s += f"{T}isHidden\n"
    if desc:
        s += f"{T}description: {desc}\n"
    s += "\n"
    for c in columns:
        s += c + "\n"
    for m in measures:
        s += m + "\n"
    if m_code is not None:
        s += partition(name, m_code)
    return s


def expression(name, m_code, parameter=False, result="Table"):
    if parameter:
        return (f"expression {q(name)} = {m_code} meta [IsParameterQuery=true, Type=\"Text\", "
                f"IsParameterQueryRequired=true]\n{T}annotation PBI_ResultType = Text\n")
    return (f"expression {q(name)} =\n" + _block(m_code, 2) + f"\n{T}annotation PBI_ResultType = {result}\n")


def relationship(name, from_col, to_col):
    return (f"relationship {name}\n{T}fromColumn: {from_col}\n{T}toColumn: {to_col}\n")
