# SlateDB Setup Guide

## Understanding SlateDB Initialization

### What Happens on First Run?

When SlateDB initializes for the first time, it:

1. **Connects to S3** (requires credentials)
2. **Checks for existing manifest** at `s3://bucket/prefix/manifest.json`
3. **If no database exists:**
   - Creates initial manifest file in S3
   - Writes manifest to S3 (this is what takes 10-30 seconds)
   - Sets up local cache directory
4. **If database exists:**
   - Reads manifest from S3 (~1-2 seconds)
   - Loads metadata into memory
   - Ready to use

**Important:** SlateDB does NOT read all your data on startup. It's lazy-loading!

### S3 File Structure

With our configuration, each runner creates files like:

```
s3://nuon-dev/
  └── slatedb/
      ├── runner-46432fbb/           ← Runner 1's SlateDB files
      │   ├── manifest-00001.json    ← Database metadata
      │   ├── wal-00001.log          ← Write-ahead log
      │   └── compacted-00001.sst    ← Sorted string tables (data)
      │
      └── runner-xyz123/             ← Runner 2's SlateDB files
          ├── manifest-00001.json
          ├── wal-00001.log
          └── compacted-00001.sst
```

**Why prefix is important:**
- Without prefix: `s3://nuon-dev/manifest-00001.json` (pollutes bucket root!)
- With prefix: `s3://nuon-dev/slatedb/runner-id/manifest-00001.json` (clean!)
- Multiple runners won't conflict

### Your Application Data Structure

Your actual application data (state files, terraform states) is separate:

```
s3://nuon-dev/
  ├── slatedb/                       ← SlateDB internal files
  │   └── runner-46432fbb/
  │       └── manifest-00001.json
  │
  └── (application data stored via SlateDB put/get)
      ├── runner-state/runner-46432fbb/state.json
      ├── states/job-123/terraform.tfstate
      └── outputs/job-123.txt
```

When you call `slate_storage.put("runner-state/...", data)`, SlateDB:
1. Writes to local WAL
2. Buffers in memory
3. Periodically flushes to S3 as `.sst` files
4. Your data lives inside the `.sst` files, indexed by the manifest

## Setup Steps

### 1. Create `.env` File

```bash
cp .env.example .env
```

Edit `.env` and set:

```bash
# Required
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_ENDPOINT_URL=https://your-s3-endpoint
AWS_REGION=us-west-2

# Bucket name
SLATE_RUNNER_BUCKET=nuon-dev
```

### 2. Test Environment

```bash
./check_env.sh
```

Should show all ✓ marks.

### 3. Test SlateDB Connection

```bash
source venv/bin/activate
python test_slatedb_minimal.py
```

**Expected output:**
```
SlateDB Minimal Connection Test
==================================================

Environment Check:
  AWS_ACCESS_KEY_ID: ✓ Set
  AWS_SECRET_ACCESS_KEY: ✓ Set
  AWS_ENDPOINT_URL: https://your-endpoint
  AWS_REGION: us-west-2
  SLATE_RUNNER_BUCKET: nuon-dev

Importing SlateDB...
✓ SlateDB import successful

Attempting SlateDB initialization...
(This may take 10-30 seconds on first connection)

  Local path: /tmp/slatedb-test
  S3 URL: s3://nuon-dev/slatedb/test-runner
  S3 files will be stored at: nuon-dev/slatedb/test-runner/manifest-*.json
  AWS Config: aws_region, aws_access_key_id, aws_secret_access_key

Initializing...
(First time may take 10-30s to create manifest in S3)
✓ SlateDB initialized successfully!

Testing basic operations...
✓ Put operation successful
✓ Get operation successful
✓ Close operation successful

==================================================
SUCCESS: SlateDB is working correctly!
==================================================
```

**If it hangs:**
- Check credentials in `.env`
- Verify S3 endpoint is reachable
- Check bucket exists and you have permissions
- Test with: `curl -I $AWS_ENDPOINT_URL`

### 4. Run the Runner

```bash
source venv/bin/activate
python runner/main.py
```

**Expected output:**
```
[Runner] Initializing SlateDB...
[SlateDB] Importing SlateDB modules...
[SlateDB] ✓ Import successful
[SlateDB] Initializing at path: /tmp/slatedb/runner-46432fbb
[SlateDB] Using S3 bucket: s3://nuon-dev/slatedb/runner-46432fbb
[SlateDB] AWS Region: us-west-2
[SlateDB] AWS Endpoint: https://your-endpoint
[SlateDB] Credentials provided: True  ← Must be True!
[SlateDB] Creating SlateDB instance...
[SlateDB] This may take a moment if connecting to S3 for the first time...
[SlateDB] ✓ SlateDB instance created (took ~15s first time)
[SlateDB] Testing connection...
[SlateDB] ✓ Connection test successful
[SlateDB] ✓ SlateDBAdmin instance created
[SlateDB] ✓ Initialized successfully for runner: runner-46432fbb
[Runner] Found 0 recovery checkpoints
```

## Performance Characteristics

### First Run (No existing database)
- **Time:** 10-30 seconds
- **What happens:** Creating manifest, initializing S3 structure
- **Network:** 1-2 S3 API calls (CreateObject, PutObject)

### Subsequent Runs (Database exists)
- **Time:** 1-5 seconds
- **What happens:** Reading manifest from S3
- **Network:** 1 S3 API call (GetObject for manifest)

### During Operation
- **WAL flush:** ~50-200ms (S3 write latency)
- **Checkpoint creation:** ~100-500ms (manifest write)
- **Get operation:** ~1-10ms (local cache) or ~50-100ms (S3 read if not cached)
- **Put operation:** ~1ms (writes to local WAL, async to S3)

## Troubleshooting

### "Credentials provided: False"
**Fix:** Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in `.env`

### Hangs at "Creating SlateDB instance..."
**Causes:**
1. No credentials
2. S3 endpoint unreachable
3. Bucket doesn't exist
4. No permissions to bucket

**Debug:**
```bash
# Test S3 connectivity
curl -I $AWS_ENDPOINT_URL

# Test with minimal script (has 30s timeout)
python test_slatedb_minimal.py
```

### "Access Denied" errors
**Fix:** Verify bucket permissions. Need:
- `s3:GetObject`
- `s3:PutObject`
- `s3:ListBucket`
- `s3:DeleteObject` (for cleanup/GC)

### Multiple runners conflict
**Should not happen** - each runner uses isolated prefix:
- Runner 1: `s3://bucket/slatedb/runner-abc123/`
- Runner 2: `s3://bucket/slatedb/runner-xyz789/`

## S3 Storage Usage

Estimate for typical usage:

```
Manifest files:     ~10 KB each, 1-10 files
WAL files:          ~1 MB each while active
Compacted files:    Depends on data volume
Total overhead:     ~10-50 MB per runner for SlateDB internals
```

Your actual data size depends on:
- Number of jobs
- Size of terraform states
- Checkpoint retention (keeping last 20)

## Next Steps

1. ✅ Set up `.env` with credentials
2. ✅ Run `test_slatedb_minimal.py` to verify
3. ✅ Start runner with `python runner/main.py`
4. ✅ Check S3 bucket to see SlateDB files created
5. ✅ Run a test job and verify WAL flush + checkpoint creation

## Additional Resources

- [SlateDB Documentation](https://slatedb.io/)
- [SlateDB Python API](https://slatedb.readthedocs.io/)
- [Checkpoints RFC](https://slatedb.io/rfcs/0004-checkpoints/)
