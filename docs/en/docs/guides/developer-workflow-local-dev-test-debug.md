# Developer Workflow: Local Dev, Test, Debug

This guide defines a repeatable day-to-day workflow for Lilya services.

## 1. Local development loop

1. Run app with reload
2. Run focused tests
3. Re-run full suite before push

## 2. Recommended commands

```shell
# serve app
palfrey myapp:app --reload

# run tests
hatch run test:test

# run one test file
hatch run test:test tests/test_routing.py

# lint/format
hatch run lint
```

## 3. Debugging workflow

- Start with [Troubleshooting](../troubleshooting.md)
- Inspect route graph with [Introspection](../introspection.md)
- Verify precedence with [Layering and Precedence](../concepts/layering-and-precedence.md)

## 4. Pull request checklist

- Tests for new behavior and regressions
- Docs updated for user-visible changes
- Release notes updated for behavior changes

## Related references

- [Contributing](../contributing.md)
- [Introspection](../introspection.md)
- [Troubleshooting](../troubleshooting.md)
