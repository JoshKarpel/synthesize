from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from networkx import DiGraph, ancestors, descendants

from synth.config import Config, Target


class TargetStatus(Enum):
    Pending = "pending"
    Running = "running"
    Succeeded = "succeeded"
    Failed = "failed"


@dataclass(frozen=True)
class State:
    graph: DiGraph
    id_to_target: dict[str, Target]
    id_to_status: dict[str, TargetStatus]

    @classmethod
    def from_targets(cls, config: Config, target_ids: set[str]) -> State:
        id_to_target = {target.id: target for target in config.targets}

        graph = DiGraph()

        for id, target in id_to_target.items():
            graph.add_node(target.id)
            for predecessor_id in target.after:
                graph.add_edge(predecessor_id, id)

        filtered = graph.subgraph(_ancestors(graph, target_ids))

        return State(
            graph=filtered,
            id_to_target={id: target for id, target in id_to_target.items() if id in filtered},
            id_to_status={id: TargetStatus.Pending for id in filtered.nodes},
        )

    def running_targets(self) -> set[Target]:
        return {
            self.id_to_target[id]
            for id, status in self.id_to_status.items()
            if status is TargetStatus.Running
        }

    def ready_targets(self) -> set[Target]:
        pending_target_ids = {
            id
            for id, status in self.id_to_status.items()
            if status is TargetStatus.Pending or status is TargetStatus.Running
        }

        pending_subgraph: DiGraph = self.graph.subgraph(pending_target_ids)

        return {
            self.id_to_target[id]
            for id in self.graph.nodes
            if self.node_to_status[id] is TargetStatus.Pending
            and all(
                self.node_to_status[a] is TargetStatus.Succeeded
                for a in ancestors(self.graph, id)
            )
        }

    def mark_success(self, target: Target) -> None:
        self.id_to_status[target.id] = TargetStatus.Succeeded

    def mark_failure(self, target: Target, idx: int) -> None:
        self.id_to_status[target.id] = TargetStatus.Failed

    def mark_pending(self, target: Target) -> None:
        self.id_to_status[target.id] = TargetStatus.Pending

    def mark_descendants_pending(self, target: Target) -> None:
        for t in _descendants(self.graph, {target.id}):
            self.id_to_status[t] = TargetStatus.Pending

    def mark_running(self, target: Target) -> None:
        self.id_to_status[target.id] = TargetStatus.Running

    def all_done(self) -> bool:
        return all(status is TargetStatus.Succeeded for status in self.id_to_status.values())

    def num_targets(self) -> int:
        return len(self.graph)

    def targets(self) -> set[Target]:
        return set(self.id_to_target.values())


def _ancestors(graph: DiGraph, nodes: set[str]) -> set[str]:
    return nodes.union(*(ancestors(graph, n) for n in nodes))


def _descendants(graph: DiGraph, nodes: set[str]) -> set[str]:
    return nodes.union(*(descendants(graph, n) for n in nodes))
