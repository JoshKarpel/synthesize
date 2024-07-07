from asyncio import Queue
from pathlib import Path

import pytest

from synthesize.config import Envs, ResolvedNode, Target, random_color
from synthesize.execution import Execution
from synthesize.messages import ExecutionCompleted, ExecutionOutput, ExecutionStarted, Message

color = random_color()


async def test_execution_lifecycle(tmp_path: Path) -> None:
    node = ResolvedNode(
        id="foo",
        target=Target(commands="echo 'hi'"),
        color=color,
    )

    q: Queue[Message] = Queue()
    ex = await Execution.start(
        node=node,
        args={},
        envs={},
        tmp_dir=tmp_path,
        width=80,
        events=q,
    )

    assert await ex.wait() is ex

    assert ex.has_exited

    msg = await q.get()

    assert isinstance(msg, ExecutionStarted)
    assert msg.node is node
    assert msg.pid == ex.pid

    msg = await q.get()

    assert isinstance(msg, ExecutionOutput)
    assert msg.node is node
    assert msg.text == "hi"

    msg = await q.get()

    assert isinstance(msg, ExecutionCompleted)
    assert msg.node is node
    assert msg.pid == ex.pid
    assert msg.exit_code == ex.exit_code == 0
    assert msg.duration.total_seconds() > 0


async def test_termination_before_completion(tmp_path: Path) -> None:
    node = ResolvedNode(
        id="foo",
        target=Target(commands="sleep 10 && echo 'hi'"),
        color=color,
    )

    q: Queue[Message] = Queue()
    ex = await Execution.start(
        node=node,
        args={},
        envs={},
        tmp_dir=tmp_path,
        width=80,
        events=q,
    )

    ex.terminate()

    assert await ex.wait() is ex

    assert ex.has_exited

    msg = await q.get()

    assert isinstance(msg, ExecutionStarted)
    assert msg.node is node
    assert msg.pid == ex.pid

    msg = await q.get()

    assert isinstance(msg, ExecutionCompleted)
    assert msg.node is node
    assert msg.pid == ex.pid
    assert msg.exit_code == ex.exit_code == -15


async def test_termination_after_completion(tmp_path: Path) -> None:
    node = ResolvedNode(
        id="foo",
        target=Target(commands="echo 'hi'"),
        color=color,
    )

    q: Queue[Message] = Queue()
    ex = await Execution.start(
        node=node,
        args={},
        envs={},
        tmp_dir=tmp_path,
        width=80,
        events=q,
    )

    assert await ex.wait() is ex

    assert ex.has_exited

    ex.terminate()  # noop


async def test_execution_kill(tmp_path: Path) -> None:
    node = ResolvedNode(
        id="foo",
        target=Target(commands="sleep 10 && echo 'hi'"),
        color=color,
    )

    q: Queue[Message] = Queue()
    ex = await Execution.start(
        node=node,
        args={},
        envs={},
        tmp_dir=tmp_path,
        width=80,
        events=q,
    )

    ex.kill()

    assert await ex.wait() is ex

    assert ex.has_exited

    msg = await q.get()

    assert isinstance(msg, ExecutionStarted)
    assert msg.node is node
    assert msg.pid == ex.pid

    msg = await q.get()

    assert isinstance(msg, ExecutionCompleted)
    assert msg.node is node
    assert msg.pid == ex.pid
    assert msg.exit_code == ex.exit_code == -9


async def test_kill_after_completion(tmp_path: Path) -> None:
    node = ResolvedNode(
        id="foo",
        target=Target(commands="echo 'hi'"),
        color=color,
    )

    q: Queue[Message] = Queue()
    ex = await Execution.start(
        node=node,
        args={},
        envs={},
        tmp_dir=tmp_path,
        width=80,
        events=q,
    )

    assert await ex.wait() is ex

    assert ex.has_exited

    ex.kill()  # noop


@pytest.mark.parametrize(
    ("node", "envs", "expected"),
    (
        (
            ResolvedNode(
                id="foo",
                target=Target(commands="echo $FORCE_COLOR"),
                color=color,
            ),
            Envs(),
            "1",
        ),
        (
            ResolvedNode(
                id="foo",
                target=Target(commands="echo $COLUMNS"),
                color=color,
            ),
            Envs(),
            "111",  # set in test body below
        ),
        (
            ResolvedNode(
                id="foo",
                target=Target(commands="echo $SYNTH_NODE_ID"),
                color=color,
            ),
            Envs(),
            "foo",
        ),
        (
            ResolvedNode(
                id="foo",
                target=Target(commands="echo $FOO"),
                envs=Envs({"FOO": "bar"}),
                color=color,
            ),
            Envs(),
            "bar",
        ),
        (
            ResolvedNode(
                id="foo",
                target=Target(commands="echo $FOO"),
                color=color,
            ),
            Envs({"FOO": "baz"}),
            "baz",
        ),
        (
            ResolvedNode(
                id="foo",
                target=Target(commands="echo $FOO", envs={"FOO": "bar"}),
                color=color,
            ),
            Envs({"FOO": "baz"}),
            "bar",
        ),
        (
            ResolvedNode(
                id="foo",
                target=Target(
                    commands="echo $A $B $C",
                    envs={
                        "A": "2",
                        "B": "2",
                    },
                ),
                envs={
                    "A": "1",
                },
                color=color,
            ),
            Envs(
                {
                    "A": "3",
                    "B": "3",
                    "C": "3",
                }
            ),
            "1 2 3",
        ),
    ),
)
async def test_envs(
    tmp_path: Path,
    node: ResolvedNode,
    envs: Envs,
    expected: str,
) -> None:
    q: Queue[Message] = Queue()
    ex = await Execution.start(
        node=node,
        args={},
        envs=envs,
        tmp_dir=tmp_path,
        width=111,
        events=q,
    )

    await ex.wait()

    await q.get()
    msg = await q.get()

    assert isinstance(msg, ExecutionOutput)
    assert msg.text == expected
