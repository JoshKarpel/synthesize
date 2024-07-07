from __future__ import annotations

from collections import defaultdict
from collections.abc import Collection, Iterator, Mapping
from dataclasses import dataclass
from enum import Enum

from networkx import DiGraph, ancestors, descendants

from synthesize.config import After, ResolvedFlow, ResolvedNode


@dataclass(frozen=True)
class FlowState:
    graph: DiGraph
    flow: ResolvedFlow
    statuses: dict[str, Status]

    @classmethod
    def from_flow(cls, flow: ResolvedFlow) -> FlowState:
        graph = DiGraph()

        for id, node in flow.nodes.items():
            graph.add_node(id)
            for t in node.triggers:
                if isinstance(t, After):
                    for predecessor_id in t.after:
                        graph.add_edge(predecessor_id, id)

        return FlowState(
            graph=graph,
            flow=flow,
            statuses={id: Status.Pending for id in graph.nodes},
        )

    def nodes_by_status(self) -> Mapping[Status, Collection[ResolvedNode]]:
        d = defaultdict(list)
        for id, s in self.statuses.items():
            d[s].append(self.flow.nodes[id])
        return d

    def ready_nodes(self) -> Collection[ResolvedNode]:
        return tuple(
            self.flow.nodes[id]
            for id in self.graph.nodes
            if self.statuses[id] is Status.Pending
            and all(
                self.statuses[a]
                in (
                    Status.Succeeded,
                    Status.Waiting,
                )
                for a in ancestors(self.graph, id)
            )
        )

    def mark_success(self, *nodes: ResolvedNode) -> None:
        self.mark(*nodes, status=Status.Succeeded)

    def mark_failure(self, *nodes: ResolvedNode) -> None:
        self.mark(*nodes, status=Status.Failed)

    def mark_pending(self, *nodes: ResolvedNode) -> None:
        self.mark(*nodes, status=Status.Pending)

    def mark_running(self, *nodes: ResolvedNode) -> None:
        self.mark(*nodes, status=Status.Running)

    def mark(self, *nodes: ResolvedNode, status: Status) -> None:
        for node in nodes:
            self.statuses[node.id] = status

    def children(self, node: ResolvedNode) -> Collection[ResolvedNode]:
        return tuple(self.flow.nodes[id] for id in self.graph.successors(node.id))

    def descendants(self, node: ResolvedNode) -> Collection[ResolvedNode]:
        return tuple(self.flow.nodes[id] for id in descendants(self.graph, node.id))

    def all_done(self) -> bool:
        return all(status is Status.Succeeded for status in self.statuses.values())

    def nodes(self) -> Iterator[ResolvedNode]:
        yield from self.flow.nodes.values()


class Status(Enum):
    Pending = "pending"
    Waiting = "waiting"
    Starting = "starting"
    Running = "running"
    Succeeded = "succeeded"
    Failed = "failed"
