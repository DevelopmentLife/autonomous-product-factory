"""Pipeline DAG definition and quality gate enforcement."""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

PIPELINE_STAGES = [
    "prd", "architect", "market", "ux", "engineering",
    "developer", "qa", "regression", "review", "devops", "readme",
]

STAGE_DEPS: dict[str, list[str]] = {
    "prd": [],
    "architect": ["prd"],
    "market": ["prd"],
    "ux": ["prd"],
    "engineering": ["architect", "market", "ux"],
    "developer": ["engineering"],
    "qa": ["developer"],
    "regression": ["qa"],
    "review": ["qa"],
    "devops": ["review"],
    "readme": ["review"],
}


@dataclass
class GateResult:
    passed: bool
    reason: str = ""


class PipelineDAG:
    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()
        for stage in PIPELINE_STAGES:
            self.graph.add_node(stage)
        for stage, deps in STAGE_DEPS.items():
            for dep in deps:
                self.graph.add_edge(dep, stage)

    def get_ready_stages(
        self,
        completed: set[str],
        running: set[str],
        skipped: set[str],
    ) -> list[str]:
        """Return stages whose dependencies are all complete and haven't been started."""
        started = completed | running | skipped
        ready = []
        for stage in PIPELINE_STAGES:
            if stage in started:
                continue
            if all(dep in completed for dep in STAGE_DEPS[stage]):
                ready.append(stage)
        return ready

    def validate_qa_gate(self, qa_artifact: dict) -> GateResult:
        critical = qa_artifact.get("critical_bug_count", 0)
        high = qa_artifact.get("high_bug_count", 0)
        if critical > 0:
            return GateResult(False, f"{critical} critical bug(s) found — regression required")
        if high > 0:
            return GateResult(False, f"{high} high-severity bug(s) found — regression required")
        return GateResult(True, "QA gate passed")

    def needs_regression(self, qa_artifact: dict) -> bool:
        return len(qa_artifact.get("bugs", [])) > 0

    def is_terminal(self, stage: str) -> bool:
        return self.graph.out_degree(stage) == 0
