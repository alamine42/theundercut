# Claude Code Guidelines

## Bug Fixing Workflow

When a bug is reported, don't start by trying to fix it. Instead:

1. **Write a test first** that reproduces the bug
2. **Use subagents** to attempt fixes
3. **Prove the fix** with the test passing
