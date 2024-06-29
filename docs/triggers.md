# Triggers

## Trigger Types

### Once

"Once" triggers run the node just one time during the flow.
This is the default trigger.

Use this trigger when a command needs to run only one time during a flow.

```yaml
--8<-- "docs/examples/once.yaml"
```

@mermaid(docs/examples/once.yaml)

### After

"After" triggers run the node after some other nodes have completed.

Use this trigger when a node depends on the output of another node.

```yaml
--8<-- "docs/examples/after.yaml"
```

@mermaid(docs/examples/after.yaml)

### Restart

"Restart" triggers run the node every time the node is completed.

Use this trigger when you want to keep the node's command running.

```yaml
--8<-- "docs/examples/restart.yaml"
```

@mermaid(docs/examples/restart.yaml)

### Watch

"Watch" triggers run the node every time one of the watched files changes
(directories are watched recursively).

Use this trigger to run a node in reaction to changes in the filesystem.

```yaml
--8<-- "docs/examples/watch.yaml"
```

@mermaid(docs/examples/watch.yaml)

## Combining Triggers

```yaml
--8<-- "docs/examples/restart-after.yaml"
```

@mermaid(docs/examples/restart-after.yaml)

```yaml
--8<-- "synth.yaml"
```

@mermaid(synth.yaml)
