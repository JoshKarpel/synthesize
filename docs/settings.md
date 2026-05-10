# Settings

Settings can be configured in the config file under the `settings` key,
or overridden at run time with one or more `-s`/`--setting` flags using dotted paths.
Values are parsed as YAML, so `3` is an integer, `true` is a boolean, and so on.
Dashes in key segments are normalized to underscores, so `sub-second-digits` and `sub_second_digits` are equivalent:

```
synth -s timestamps.sub-second-digits=3 -s timestamps.include-date=true
```

@schema(synthesize.config, Settings)

## Timestamps

@schema(synthesize.config, TimestampSettings)

## `.env`

@schema(synthesize.config, DotEnvSettings)
