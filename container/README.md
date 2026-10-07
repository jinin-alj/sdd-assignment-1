# Assignment 1: container template

Two files, provided to everyone:

| File | What you do with it |
|---|---|
| `Dockerfile` | Copy to your repo root and fill in the four `TODO` lines. Nothing else. |
| `run.sh` | Run it against your repo. It checks the contract and prints your §7 evidence. |

## Use it

```bash
cp Dockerfile /path/to/your/repo/Dockerfile   # then fill in the TODOs
./run.sh /path/to/your/repo                   # check the contract
./run.sh /path/to/your/repo --keep            # ...and leave the app running
```

`run.sh` needs Docker running. It builds a throwaway image, container and
volume, checks them, and cleans up after itself.

## The four TODOs

1. **Base image.** The `-slim` variant of your language.
2. **Dependency install.** Your one root manifest, installed *above* the source
   copy so the layer cache survives a source edit. `pip` is the default; a `uv`
   variant is in the comments if that is already how you work.
3. **Source copy.** List your own files explicitly. Not `COPY . .`.
4. **Start command.** The one command from your README (§7.1).

Everything else in the file is the contract. Leave it alone.

## What `run.sh` checks

| Check | Contract |
|---|---|
| One Dockerfile and exactly one manifest at the root | §1a, §7.7 |
| Builds clean, with no build args | §7.4, §7.7 |
| No `.env`, `.git`, `.venv` or `node_modules` inside the image | §7.9 |
| Answers on `http://localhost:8000/` from the host | §7.2, §7.10 |
| Writes its SQLite file under `DATA_DIR` | §7.5 |
| Data survives the container being deleted and recreated | §7.5 |
| Row counts unchanged on a second boot, so seeding is idempotent | §7.11 |
| Comes up on `PORT=9123` too, so `PORT` is read and not hardcoded | §7.3 |

A green run is what you paste into your README. A red run names the §7 clause
your app fails, and the fix is in your application code, not in the Dockerfile.

## Common failures

**Bound to `127.0.0.1`.** Works on your laptop, unreachable from outside the
container. Bind `0.0.0.0` (§7.2).

**Port hardcoded to 8000.** Passes the first check, fails the override check.
Read `PORT` from the environment and default to 8000 (§7.3).

**SQLite written next to your source.** The file lands in `/app`, not `/data`,
so it disappears when the container is recreated. Build your database path from
`DATA_DIR` (§7.5).

## If your app ships starter data

Commit it as a text file (`seed.sql`, `seed.json`, `seed.csv`), copy that file
into the image in TODO 3, and load it on first boot only when the target table
is empty. Never commit a prebuilt `.db`.

A baked-in `.db` is copied into a named volume only while that volume is still
empty, so it works exactly once and is ignored forever after, and under a bind
mount or an Azure file share it is never visible at all. §7.11 of the assignment
has the full table of what happens when.

Two ways to get the loading wrong:

```
seed on every boot          rows double on every restart; run.sh fails
DROP TABLE, then re-seed    counts look stable so run.sh passes, but every
                            restart wipes whatever your users entered
```

Create what is missing; leave what already exists alone.
