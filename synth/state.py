from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import islice

from networkx import DiGraph, ancestors, descendants

from synth.config import Config, Target


class NodeStatus(Enum):
    Pending = "pending"
    Running = "running"
    Succeeded = "succeeded"
    Failed = "failed"


Node = tuple[str, int]


@dataclass(frozen=True)
class State:
    graph: DiGraph
    id_to_target: dict[str, Target]
    node_to_status: dict[Node, NodeStatus]

    @classmethod
    def from_targets(cls, config: Config, target_ids: set[str]) -> State:
        id_to_target = {target.id: target for target in config.targets}

        graph = DiGraph()

        for id, target in id_to_target.items():
            for command_idx in range(len(target.commands)):
                graph.add_node((target.id, command_idx))

            for command_idx in islice(range(len(target.commands)), 1, None):
                graph.add_edge((target.id, command_idx - 1), (target.id, command_idx))

            for predecessor_id in target.after:
                graph.add_edge(
                    (predecessor_id, len(id_to_target[predecessor_id].commands) - 1),
                    (id, 0),
                )

        filtered = graph.subgraph(
            _ancestors(
                graph,
                {(id, idx) for id in target_ids for idx in range(len(id_to_target[id].commands))},
            )
        )

        filtered_ids = {id for id, _ in filtered.nodes}

        return State(
            graph=filtered,
            id_to_target={id: target for id, target in id_to_target.items() if id in filtered_ids},
            node_to_status={node: NodeStatus.Pending for node in filtered.nodes},
        )

    def running_targets(self) -> set[Target]:
        return {
            self.id_to_target[id]
            for (id, idx), status in self.node_to_status.items()
            if status is NodeStatus.Running
        }

    def ready_commands(self) -> set[tuple[Target, int]]:
        return {
            (self.id_to_target[id], idx)
            for id, idx in self.graph.nodes
            if self.node_to_status[(id, idx)] is NodeStatus.Pending
            and all(
                self.node_to_status[a] is NodeStatus.Succeeded
                for a in ancestors(self.graph, (id, idx))
            )
        }

    def mark_success(self, target: Target, idx: int) -> None:
        self.node_to_status[target.id, idx] = NodeStatus.Succeeded

    def mark_failure(self, target: Target, idx: int) -> None:
        self.node_to_status[target.id, idx] = NodeStatus.Failed

    def mark_pending(self, target: Target, idx: int) -> None:
        self.node_to_status[target.id, idx] = NodeStatus.Pending

    def mark_descendants_pending(self, target: Target, idx: int) -> None:
        for t in _descendants(self.graph, {(target.id, idx)}):
            self.node_to_status[t] = NodeStatus.Pending

    def mark_running(self, target: Target, idx: int) -> None:
        self.node_to_status[target.id, idx] = NodeStatus.Running

    def all_done(self) -> bool:
        return all(status is NodeStatus.Succeeded for status in self.node_to_status.values())

    def num_targets(self) -> int:
        return len(self.graph)

    def targets(self) -> set[Target]:
        return set(self.id_to_target.values())


def _ancestors(graph: DiGraph, nodes: set[Node]) -> set[Node]:
    return nodes.union(*(ancestors(graph, n) for n in nodes))


def _descendants(graph: DiGraph, nodes: set[Node]) -> set[Node]:
    return nodes.union(*(descendants(graph, n) for n in nodes))
