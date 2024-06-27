from __future__ import annotations

from collections.abc import Collection, Iterator
from dataclasses import dataclass
from enum import Enum

from networkx import DiGraph, ancestors, descendants

from synthesize.config import After, Flow, FlowNode


class FlowNodeStatus(Enum):
    Pending = "pending"
    Running = "running"
    Succeeded = "succeeded"
    Failed = "failed"


@dataclass(frozen=True)
class FlowState:
    graph: DiGraph
    flow: Flow
    statuses: dict[str, FlowNodeStatus]

    @classmethod
    def from_flow(cls, flow: Flow) -> FlowState:
        graph = DiGraph()

        for id, node in flow.nodes.items():
            graph.add_node(id)
            if isinstance(node.trigger, After):
                for predecessor_id in node.trigger.after:
                    graph.add_edge(predecessor_id, id)

        return FlowState(
            graph=graph,
            flow=flow,
            statuses={id: FlowNodeStatus.Pending for id in graph.nodes},
        )

    def running_nodes(self) -> Collection[FlowNode]:
        return tuple(
            self.flow.nodes[id]
            for id, status in self.statuses.items()
            if status is FlowNodeStatus.Running
        )

    def ready_nodes(self) -> Collection[FlowNode]:
        return tuple(
            self.flow.nodes[id]
            for id in self.graph.nodes
            if self.statuses[id] is FlowNodeStatus.Pending
            and all(self.statuses[a] is FlowNodeStatus.Succeeded for a in ancestors(self.graph, id))
        )

    def mark_success(self, node: FlowNode) -> None:
        self.statuses[node.id] = FlowNodeStatus.Succeeded

    def mark_failure(self, node: FlowNode) -> None:
        self.statuses[node.id] = FlowNodeStatus.Failed

    def mark_pending(self, node: FlowNode) -> None:
        self.statuses[node.id] = FlowNodeStatus.Pending

    def mark_descendants_pending(self, node: FlowNode) -> None:
        for t in _descendants(self.graph, {node.id}):
            self.statuses[t] = FlowNodeStatus.Pending

    def mark_running(self, node: FlowNode) -> None:
        self.statuses[node.id] = FlowNodeStatus.Running

    def all_done(self) -> bool:
        return all(status is FlowNodeStatus.Succeeded for status in self.statuses.values())

    def num_nodes(self) -> int:
        return len(self.graph)

    def nodes(self) -> Iterator[FlowNode]:
        yield from self.flow.nodes.values()


def _ancestors(graph: DiGraph, nodes: set[str]) -> set[str]:
    return nodes.union(*(ancestors(graph, n) for n in nodes))


def _descendants(graph: DiGraph, nodes: set[str]) -> set[str]:
    return nodes.union(*(descendants(graph, n) for n in nodes))
