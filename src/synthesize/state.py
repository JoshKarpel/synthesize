from __future__ import annotations

from collections import defaultdict
from collections.abc import Collection, Iterator, Mapping
from dataclasses import dataclass
from enum import Enum

from networkx import DiGraph, ancestors, descendants
from networkx.algorithms.cycles import find_cycle
from networkx.exception import NetworkXNoCycle

from synthesize.config import After, RepeatingTrigger, ResolvedFlow, ResolvedNode


class CyclicFlowDetected(Exception):
    def __init__(self, cycle: tuple[str, ...]):
        super().__init__()

        self.cycle = cycle

    def cycle_path(self) -> str:
        return " -> ".join((*self.cycle, self.cycle[0]))


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

        try:
            cycle = find_cycle(graph)
            raise CyclicFlowDetected(tuple(start for start, _end in cycle))
        except NetworkXNoCycle:
            pass

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

    def parents(self, node: ResolvedNode) -> Collection[ResolvedNode]:
        return tuple(self.flow.nodes[id] for id in self.graph.predecessors(node.id))

    def children(self, node: ResolvedNode) -> Collection[ResolvedNode]:
        return tuple(self.flow.nodes[id] for id in self.graph.successors(node.id))

    def descendants(self, node: ResolvedNode) -> Collection[ResolvedNode]:
        return tuple(self.flow.nodes[id] for id in descendants(self.graph, node.id))

    def all_succeeded(self) -> bool:
        return all(status is Status.Succeeded for status in self.statuses.values())

    def no_more_work_possible(self) -> bool:
        # If any node has a repeating trigger,
        # there might be work to do in the future
        # even if there isn't any to do right now.
        for node in self.flow.nodes.values():
            if any(isinstance(t, RepeatingTrigger) for t in node.triggers):  # type: ignore[misc,arg-type]
                return False

        # Otherwise, if there are no ready nodes and no running or starting nodes, we must be done.
        nodes_by_status = self.nodes_by_status()
        return not self.ready_nodes() and not nodes_by_status[Status.Running] and not nodes_by_status[Status.Starting]

    def nodes(self) -> Iterator[ResolvedNode]:
        yield from self.flow.nodes.values()


class Status(Enum):
    Pending = "pending"
    Waiting = "waiting"
    Starting = "starting"
    Running = "running"
    Succeeded = "succeeded"
    Failed = "failed"

    def display(self) -> str:
        return self.value.capitalize()
