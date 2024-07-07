# Triggers

## Trigger Types

### Once

"Once" triggers run the node just one time during the flow.
This is the default trigger, so it does not need to be specified.

Use this trigger when a command needs to run only one time during a flow.

```yaml
--8<-- "docs/examples/once.yaml"
```

@mermaid(docs/examples/once.yaml)

### After

"After" triggers run the node after some other nodes have completed.

Use this trigger when a node depends on the output of another node.

@schema(synthesize.config, After)

```yaml
--8<-- "docs/examples/after.yaml"
```

@mermaid(docs/examples/after.yaml)

### Restart

"Restart" triggers run the node every time the node is completed.

Use this trigger when you want to keep the node's command running.

@schema(synthesize.config, Restart)

```yaml
--8<-- "docs/examples/restart.yaml"
```

@mermaid(docs/examples/restart.yaml)

### Watch

"Watch" triggers run the node every time one of the watched files changes
(directories are watched recursively).

Use this trigger to run a node in reaction to changes in the filesystem.

@schema(synthesize.config, Watch)

```yaml
--8<-- "docs/examples/watch.yaml"
```

@mermaid(docs/examples/watch.yaml)

## Using Multiple Triggers

### Example: Restarting on Completion or Config Changes

Synthesize uses `mkdocs` for documentation.
`mkdocs` comes with a built-in command `mkdocs serve` to watch for
configuration and documentation changes and rebuild the site in response,
but it doesn't automatically restart the whole process when
[*hooks*](https://www.mkdocs.org/user-guide/configuration/#hooks)
are changed.
Since hooks are imported Python code, the `mkdocs` process needs to
be restarted when they change in order to pick up changes to them.

However, if the hooks (or any other configuration) are malformed,
`mkdocs` will exit with an error on startup.
If we were just running `mkdocs serve` by hand on the command line,
we would have to manually restart it every time we changed the hooks,
potentially multiple times if we are debugging.

To get a hands-off developer flow to enable fast iteration cycles,
we want the following things to all happen:

- If `mkdocs` exits (for any reason), restart it.
- If any of the hook files changes, restart `mkdocs`.
- If neither of those happen, let `mkdocs serve` keep running forever.

This is straightforward to express with Synthesize by using both restart and watch triggers
for a target that run `mkdocs serve` (which blocks):

```yaml
--8<-- "docs/examples/restart-and-watch.yaml"
```

@mermaid(docs/examples/restart-and-watch.yaml)
