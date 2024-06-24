from __future__ import annotations

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
    id_to_node: dict[str, FlowNode]
    id_to_status: dict[str, FlowNodeStatus]

    @classmethod
    def from_flow(cls, flow: Flow) -> FlowState:
        id_to_node = {node.id: node for node in flow.nodes}

        graph = DiGraph()

        for id, node in id_to_node.items():
            graph.add_node(node.id)
            if isinstance(node.trigger, After):
                for predecessor_id in node.trigger.after:
                    graph.add_edge(predecessor_id, id)

        return FlowState(
            graph=graph,
            id_to_node={id: node for id, node in id_to_node.items()},
            id_to_status={id: FlowNodeStatus.Pending for id in graph.nodes},
        )

    def running_nodes(self) -> set[FlowNode]:
        return {
            self.id_to_node[id]
            for id, status in self.id_to_status.items()
            if status is FlowNodeStatus.Running
        }

    def ready_nodes(self) -> set[FlowNode]:
        return {
            self.id_to_node[id]
            for id in self.graph.nodes
            if self.id_to_status[id] is FlowNodeStatus.Pending
            and all(
                self.id_to_status[a] is FlowNodeStatus.Succeeded for a in ancestors(self.graph, id)
            )
        }

    def mark_success(self, node: FlowNode) -> None:
        self.id_to_status[node.id] = FlowNodeStatus.Succeeded

    def mark_failure(self, node: FlowNode) -> None:
        self.id_to_status[node.id] = FlowNodeStatus.Failed

    def mark_pending(self, node: FlowNode) -> None:
        self.id_to_status[node.id] = FlowNodeStatus.Pending

    def mark_descendants_pending(self, node: FlowNode) -> None:
        for t in _descendants(self.graph, {node.id}):
            self.id_to_status[t] = FlowNodeStatus.Pending

    def mark_running(self, node: FlowNode) -> None:
        self.id_to_status[node.id] = FlowNodeStatus.Running

    def all_done(self) -> bool:
        return all(status is FlowNodeStatus.Succeeded for status in self.id_to_status.values())

    def num_nodes(self) -> int:
        return len(self.graph)

    def nodes(self) -> set[FlowNode]:
        return set(self.id_to_node.values())


def _ancestors(graph: DiGraph, nodes: set[str]) -> set[str]:
    return nodes.union(*(ancestors(graph, n) for n in nodes))


def _descendants(graph: DiGraph, nodes: set[str]) -> set[str]:
    return nodes.union(*(descendants(graph, n) for n in nodes))
