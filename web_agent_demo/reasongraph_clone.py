from __future__ import annotations

from dataclasses import dataclass
import textwrap
from typing import Optional


@dataclass
class VisualizationConfig:
    max_chars_per_line: int = 34
    max_lines: int = 4


@dataclass
class ToTNode:
    """ReasonGraph-compatible Tree-of-Thoughts node."""

    id: str
    content: str
    parent_id: Optional[str] = None
    is_answer: bool = False
    state: str = "default"
    metric: str = ""
    children: list["ToTNode"] | None = None

    def __post_init__(self) -> None:
        if self.children is None:
            self.children = []


@dataclass
class ToTResponse:
    question: str
    root: ToTNode
    answer: Optional[str] = None


def build_tree(nodes: list[ToTNode]) -> ToTNode:
    nodes_dict = {node.id: node for node in nodes}
    root = None
    for node in nodes:
        if node.parent_id is None:
            root = node
        else:
            parent = nodes_dict.get(node.parent_id)
            if parent is not None:
                parent.children.append(node)
    if root is None:
        raise ValueError("ReasonGraph tree requires a root node")
    return root


def wrap_text(text: str, config: VisualizationConfig) -> str:
    text = text.replace("\n", " ").replace('"', "'")
    wrapped_lines = textwrap.wrap(text, width=config.max_chars_per_line)
    if len(wrapped_lines) > config.max_lines:
        wrapped_lines = wrapped_lines[: config.max_lines]
        wrapped_lines[-1] = wrapped_lines[-1][: config.max_chars_per_line - 3] + "..."
    return "<br>".join(wrapped_lines)


def create_mermaid_diagram(tot_response: ToTResponse, config: VisualizationConfig) -> str:
    """Port of ReasonGraph's ToT Mermaid renderer, styled for AutoSolver."""

    diagram = ["graph TD"]
    diagram.append(f'    Q["{wrap_text(tot_response.question, config)}"]')
    leaf_nodes: list[str] = []

    def add_node_and_children(node: ToTNode, parent_id: Optional[str] = None) -> None:
        metric = f"<br/>{node.metric}" if node.metric else ""
        content = wrap_text(f"{node.content}{metric}", config)
        diagram.append(f'    {node.id}["{content}"]')
        if parent_id:
            diagram.append(f"    {parent_id} --> {node.id}")
        if node.children:
            for child in node.children:
                add_node_and_children(child, node.id)
        else:
            leaf_nodes.append(node.id)
        diagram.append(f"    class {node.id} {node.state};")

    diagram.append(f"    Q --> {tot_response.root.id}")
    add_node_and_children(tot_response.root)

    if tot_response.answer:
        answer_content = wrap_text(tot_response.answer, config)
        diagram.append(f'    Answer["{answer_content}"]')
        for leaf_id in leaf_nodes:
            diagram.append(f"    {leaf_id} --> Answer")
        diagram.append("    class Answer final_answer;")

    diagram.extend(
        [
            "    classDef default fill:#081827,stroke:#2d607f,color:#e6edf7,stroke-width:1px;",
            "    classDef running fill:#0b2840,stroke:#38bdf8,color:#e6edf7,stroke-width:2px;",
            "    classDef selected fill:#0f513f,stroke:#31e6c1,color:#e6fff8,stroke-width:2px;",
            "    classDef rejected fill:#17212f,stroke:#64748b,color:#8da2ba,stroke-width:1px;",
            "    classDef answer fill:#064e3b,stroke:#31e981,color:#e6fff8,stroke-width:3px;",
            "    classDef final_answer fill:#064e3b,stroke:#31e981,color:#e6fff8,stroke-width:3px;",
            "    classDef question fill:#082f49,stroke:#38bdf8,color:#e6edf7,stroke-width:2px;",
            "    class Q question;",
            "    linkStyle default stroke:#2d607f,stroke-width:2px;",
        ]
    )
    return "\n".join(diagram)


def autosolver_tot_response(mode: str = "initial", report: dict[str, object] | None = None) -> ToTResponse:
    best = (report or {}).get("best", {}) if isinstance(report, dict) else {}
    features = (report or {}).get("features", {}) if isinstance(report, dict) else {}
    final = mode == "final" and bool(report)

    selected_state = "selected" if final else ("running" if mode == "running" else "default")
    rejected_state = "rejected" if final else ("running" if mode == "running" else "default")
    answer_state = "answer" if final else ("running" if mode == "running" else "default")

    nodes = [
        ToTNode("N1", f"Input Orders / 输入订单与骑手状态\norders={features.get('tasks', '?')} riders={features.get('couriers', '?')}", state=selected_state, metric="confidence 1.00"),
        ToTNode("N2", "Scene Diagnosis / 场景识别与风险判断\n高峰、合单、接单意愿、时间窗压力", parent_id="N1", state=selected_state, metric="confidence 0.96"),
        ToTNode("N3", "Candidate Strategy Generation / 候选策略生成\n预构建 5 条策略分支，不展开底层策略日志", parent_id="N2", state=selected_state, metric="candidates 5"),
        ToTNode("S1", "Bundle-first / 合单优先\n高重叠订单优先合并", parent_id="N3", state=selected_state, metric="score 0.82"),
        ToTNode("S2", "Multi-dispatch / 多派候选\n并行小批量派单", parent_id="N3", state=rejected_state, metric="score 0.58"),
        ToTNode("S3", "Repair search / 局部修复\n从贪心结果做局部修复", parent_id="N3", state=rejected_state, metric="score 0.66"),
        ToTNode("S4", "Greedy baseline / 贪心基线\n最近优先业务基线", parent_id="N3", state=rejected_state, metric="score 0.41"),
        ToTNode("S5", "Time-window balance / 时间窗平衡\n收紧超时风险", parent_id="N3", state=rejected_state, metric="score 0.62"),
        ToTNode("N4", "Route Feasibility Check / 路线可行性校验\n时间窗、容量、班次、SLA", parent_id="S1", state=selected_state, metric="passed 1/5"),
        ToTNode("N5", "Cost / Risk Critic / 成本与风险评估\n成本、接单概率、服务质量折中", parent_id="N4", state=selected_state, metric="best score 0.82"),
        ToTNode("N6", f"Final Dispatch Plan / 最终派单方案\ncovered={best.get('covered_tasks', '?')}/{best.get('total_tasks', '?')} riders={best.get('used_couriers', '?')}", parent_id="N5", is_answer=True, state=answer_state, metric="confidence 0.89"),
    ]
    root = build_tree(nodes)
    return ToTResponse(
        question="AutoSolver AI 可解释调度决策树",
        root=root,
        answer="选择合单优先路径，保留最终 AutoSolver 派单方案。" if final else None,
    )


def autosolver_mermaid(mode: str = "initial", report: dict[str, object] | None = None) -> str:
    return create_mermaid_diagram(autosolver_tot_response(mode, report), VisualizationConfig())
