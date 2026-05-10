# Settings

Settings can be configured in the config file under the `settings` key,
or overridden at run time with one or more `-s`/`--setting` flags using dotted paths:

```
synth run -s timestamps.sub_second_digits=3 -s timestamps.include_date=true
```

@schema(synthesize.config, Settings)

## Timestamps

@schema(synthesize.config, TimestampSettings)
