# Package Structure Decision: grepctl vs bq-semgrep

## Analysis

After reviewing both tools, it's clear that **grepctl has completely superseded bq-semgrep**.

### Feature Comparison

| Feature | bq-semgrep | grepctl |
|---------|------------|---------|
| Search | ✅ Basic | ✅ Advanced with filters |
| Ingestion | ✅ Basic | ✅ All 8 modalities |
| System Setup | ❌ Manual | ✅ One-command (`init all`) |
| API Management | ❌ | ✅ Complete |
| Index Management | ❌ | ✅ Full control |
| Error Recovery | ❌ | ✅ Auto-fix commands |
| Status Monitoring | ❌ | ✅ Comprehensive |
| Rich UI | ❌ | ✅ Progress bars, tables |
| Configuration | ✅ Basic | ✅ Advanced with persistence |

### Why grepctl is Superior

1. **Complete Lifecycle Management**: From setup to search to troubleshooting
2. **Better UX**: Rich terminal UI with progress tracking
3. **Production Ready**: Auto-recovery, error handling, status monitoring
4. **One-Command Magic**: `grepctl init all --auto-ingest` does everything

## Recommendation

**Focus entirely on grepctl** as the primary package. Here's why:

1. **Single Tool Philosophy**: One powerful tool is better than two overlapping ones
2. **User Confusion**: Having both tools creates confusion about which to use
3. **Maintenance**: Single codebase is easier to maintain and evolve
4. **Brand Clarity**: "grepctl" is a memorable, clear name for the tool's purpose

## Package Publishing Strategy

### Option 1: Pure grepctl (Recommended)
- Package name: `grepctl`
- Single entry point: `grepctl` CLI
- Clear purpose: BigQuery semantic search orchestration
- No confusion about tool choice

### Option 2: Keep bq-semgrep name but only ship grepctl
- Package name: `bq-semgrep` (for discovery)
- Only entry point: `grepctl` CLI
- Rationale: People might search for "bigquery semantic grep"

### Option 3: Transition Package
- Package name: `bq-semgrep`
- Both CLIs initially
- Deprecation warning on `bq-semgrep` CLI
- Remove `bq-semgrep` in v0.2.0

## Decision

**Go with Option 1: Pure grepctl package**

Reasons:
- Clean, focused package
- No legacy code to maintain
- Clear messaging to users
- Better brand identity

## Implementation Changes

1. **Package Name**: Change from `bq-semgrep` to `grepctl`
2. **Entry Point**: Only `grepctl` CLI command
3. **Documentation**: Focus entirely on grepctl usage
4. **Repository**: Consider renaming to `grepctl`
5. **PyPI**: Publish as `grepctl`

## Migration for Existing Users

If there are existing `bq-semgrep` users (unlikely since it's new):

```bash
# Old way (deprecated)
bq-semgrep search "query"
bq-semgrep ingest --bucket bucket

# New way (recommended)
grepctl search "query"
grepctl ingest all
grepctl init all --auto-ingest  # Much more powerful!
```

## Conclusion

**grepctl is the future**. It's more powerful, more user-friendly, and provides a complete solution. Let's focus 100% on making it the best tool for BigQuery semantic search orchestration.