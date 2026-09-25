import argparse, sqlite3, threading, time, statistics, json, os, sys, subprocess, shutil, hashlib, queue
from pathlib import Path
from collections import Counter

parser = argparse.ArgumentParser()
parser.add_argument("--out", required=True)
parser.add_argument("--threads", type=int, default=12)
parser.add_argument("--commands-per-producer", type=int, default=250)
parser.add_argument("--busy-timeout-ms", type=int, default=5000)
args = parser.parse_args()

out = Path(args.out).resolve()
if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True)

THREADS = args.threads
N = args.commands_per_producer
BUSY_MS = args.busy_timeout_ms

results = {
    "platform": sys.platform,
    "python": sys.version,
    "parameters": {
        "threads": THREADS,
        "commands_per_producer": N,
        "busy_timeout_ms": BUSY_MS
    },
    "tests": {},
    "limitations": []
}

def pctl(vals,p):
    if not vals:
        return None
    vals=sorted(vals)
    i=min(len(vals)-1,max(0,int(round((len(vals)-1)*p))))
    return vals[i]

def error_summary(errors):
    c = Counter(errors)
    return [{"error":k,"count":v} for k,v in c.most_common()]

# A. Adversarial direct multi-writer characterization
rawdb = out/"raw_multiwriter.db"
c=sqlite3.connect(rawdb)
jm=c.execute("PRAGMA journal_mode=WAL").fetchone()[0]
c.execute("PRAGMA synchronous=FULL")
c.execute("CREATE TABLE counter(id INTEGER PRIMARY KEY, v INTEGER NOT NULL, rev INTEGER NOT NULL)")
c.execute("INSERT INTO counter VALUES(1,0,0)")
c.commit(); c.close()

raw_lat=[]
raw_errors=[]
lock=threading.Lock()

def raw_worker(i):
    conn=sqlite3.connect(rawdb, timeout=BUSY_MS/1000.0, isolation_level=None, check_same_thread=False)
    conn.execute(f"PRAGMA busy_timeout={BUSY_MS}")
    for n in range(N):
        t=time.perf_counter()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE counter SET v=v+1, rev=rev+1 WHERE id=1")
            conn.execute("COMMIT")
            with lock:
                raw_lat.append((time.perf_counter()-t)*1000)
        except Exception as e:
            try: conn.execute("ROLLBACK")
            except Exception: pass
            with lock:
                raw_errors.append(f"{type(e).__name__}: {e}")
    conn.close()

ts=[threading.Thread(target=raw_worker,args=(i,)) for i in range(THREADS)]
start=time.perf_counter()
for t in ts:t.start()
for t in ts:t.join()
raw_elapsed=time.perf_counter()-start

c=sqlite3.connect(rawdb)
raw_v,raw_rev=c.execute("SELECT v,rev FROM counter").fetchone()
raw_integrity=c.execute("PRAGMA integrity_check").fetchone()[0]
c.close()

results["tests"]["raw_multiwriter_characterization"]={
    "purpose":"adversarial characterization; NOT production acceptance lane",
    "journal_mode":jm,
    "expected":THREADS*N,
    "committed":raw_v,
    "revision":raw_rev,
    "errors":len(raw_errors),
    "error_summary":error_summary(raw_errors),
    "elapsed_s":raw_elapsed,
    "tx_per_s":raw_v/raw_elapsed if raw_elapsed else None,
    "latency_ms_mean":statistics.mean(raw_lat) if raw_lat else None,
    "latency_ms_p95":pctl(raw_lat,.95),
    "latency_ms_max":max(raw_lat) if raw_lat else None,
    "integrity_check":raw_integrity
}

# B. Intended topology: many producers -> one DB writer
qdb = out/"single_writer_queue.db"
c=sqlite3.connect(qdb)
qjm=c.execute("PRAGMA journal_mode=WAL").fetchone()[0]
c.execute("PRAGMA synchronous=FULL")
c.execute("CREATE TABLE counter(id INTEGER PRIMARY KEY, v INTEGER NOT NULL, rev INTEGER NOT NULL)")
c.execute("INSERT INTO counter VALUES(1,0,0)")
c.commit(); c.close()

write_q=queue.Queue(maxsize=256)
writer_errors=[]
writer_lat=[]
producer_errors=[]
producer_wait_ms=[]
SENTINEL=object()

def writer():
    conn=sqlite3.connect(qdb, timeout=BUSY_MS/1000.0, isolation_level=None, check_same_thread=False)
    conn.execute(f"PRAGMA busy_timeout={BUSY_MS}")
    try:
        while True:
            item=write_q.get()
            try:
                if item is SENTINEL:
                    return
                t=time.perf_counter()
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    conn.execute("UPDATE counter SET v=v+1, rev=rev+1 WHERE id=1")
                    conn.execute("COMMIT")
                    writer_lat.append((time.perf_counter()-t)*1000)
                except Exception as e:
                    try: conn.execute("ROLLBACK")
                    except Exception: pass
                    writer_errors.append(f"{type(e).__name__}: {e}")
            finally:
                write_q.task_done()
    finally:
        conn.close()

def producer(i):
    for n in range(N):
        t=time.perf_counter()
        try:
            write_q.put((i,n), timeout=10)
            producer_wait_ms.append((time.perf_counter()-t)*1000)
        except Exception as e:
            producer_errors.append(f"{type(e).__name__}: {e}")

wt=threading.Thread(target=writer)
wt.start()
pts=[threading.Thread(target=producer,args=(i,)) for i in range(THREADS)]
qstart=time.perf_counter()
for t in pts:t.start()
for t in pts:t.join()
write_q.join()
write_q.put(SENTINEL)
write_q.join()
wt.join()
qelapsed=time.perf_counter()-qstart

c=sqlite3.connect(qdb)
qv,qrev=c.execute("SELECT v,rev FROM counter").fetchone()
qintegrity=c.execute("PRAGMA integrity_check").fetchone()[0]
c.close()

results["tests"]["single_writer_queue"]={
    "purpose":"V1 production acceptance lane",
    "journal_mode":qjm,
    "producer_threads":THREADS,
    "commands_per_producer":N,
    "expected":THREADS*N,
    "committed":qv,
    "revision":qrev,
    "writer_errors":len(writer_errors),
    "writer_error_summary":error_summary(writer_errors),
    "producer_errors":len(producer_errors),
    "producer_error_summary":error_summary(producer_errors),
    "elapsed_s":qelapsed,
    "tx_per_s":qv/qelapsed if qelapsed else None,
    "writer_latency_ms_mean":statistics.mean(writer_lat) if writer_lat else None,
    "writer_latency_ms_p95":pctl(writer_lat,.95),
    "writer_latency_ms_max":max(writer_lat) if writer_lat else None,
    "producer_queue_wait_ms_mean":statistics.mean(producer_wait_ms) if producer_wait_ms else None,
    "producer_queue_wait_ms_p95":pctl(producer_wait_ms,.95),
    "producer_queue_wait_ms_max":max(producer_wait_ms) if producer_wait_ms else None,
    "integrity_check":qintegrity
}

# C. Abrupt process exit
crashdb=out/"crash.db"
setup=f"""
import sqlite3
p=r'{crashdb}'
c=sqlite3.connect(p)
c.execute('PRAGMA journal_mode=WAL')
c.execute('PRAGMA synchronous=FULL')
c.execute('CREATE TABLE t(k TEXT PRIMARY KEY,v TEXT)')
c.commit()
"""
subprocess.run([sys.executable,"-c",setup],check=True)

committed=f"""
import sqlite3,os
p=r'{crashdb}'
c=sqlite3.connect(p)
c.execute('PRAGMA synchronous=FULL')
c.execute("INSERT INTO t VALUES('committed','yes')")
c.commit()
os._exit(91)
"""
subprocess.run([sys.executable,"-c",committed],check=False)

uncommitted=f"""
import sqlite3,os
p=r'{crashdb}'
c=sqlite3.connect(p)
c.execute('BEGIN IMMEDIATE')
c.execute("INSERT INTO t VALUES('uncommitted','no')")
os._exit(92)
"""
subprocess.run([sys.executable,"-c",uncommitted],check=False)

c=sqlite3.connect(crashdb)
rows=dict(c.execute("SELECT k,v FROM t"))
integ=c.execute("PRAGMA integrity_check").fetchone()[0]
c.close()
results["tests"]["abrupt_exit"]={
    "committed_survived":rows.get("committed")=="yes",
    "uncommitted_absent":"uncommitted" not in rows,
    "integrity_check":integ
}

# D. Interrupted migration / resume
migdb=out/"migration.db"
c=sqlite3.connect(migdb)
c.executescript("""
CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY,status TEXT NOT NULL,phase INTEGER NOT NULL DEFAULT 0);
CREATE TABLE item(id INTEGER PRIMARY KEY,payload TEXT NOT NULL,new_payload TEXT);
INSERT INTO schema_migrations VALUES(1,'COMPLETED',1);
""")
c.executemany("INSERT INTO item(payload) VALUES(?)",[(f"row-{i}",) for i in range(1,1001)])
c.commit(); c.close()

mig_script=f"""
import sqlite3,os
p=r'{migdb}'
c=sqlite3.connect(p)
c.execute("INSERT OR REPLACE INTO schema_migrations(version,status,phase) VALUES(2,'RUNNING',1)")
c.commit()
for lo in range(1,1001,100):
    c.execute("BEGIN IMMEDIATE")
    c.execute("UPDATE item SET new_payload=upper(payload) WHERE id>=? AND id<?",(lo,lo+100))
    c.execute("UPDATE schema_migrations SET phase=? WHERE version=2",(lo+99,))
    c.execute("COMMIT")
    if lo>=401:
        os._exit(93)
"""
subprocess.run([sys.executable,"-c",mig_script],check=False)

c=sqlite3.connect(migdb)
status,phase=c.execute("SELECT status,phase FROM schema_migrations WHERE version=2").fetchone()
converted=c.execute("SELECT COUNT(*) FROM item WHERE new_payload IS NOT NULL").fetchone()[0]
c.close()

c=sqlite3.connect(migdb)
c.execute("BEGIN IMMEDIATE")
c.execute("UPDATE item SET new_payload=upper(payload) WHERE new_payload IS NULL")
c.execute("UPDATE schema_migrations SET status='COMPLETED',phase=1000 WHERE version=2")
c.execute("COMMIT")
converted_after=c.execute("SELECT COUNT(*) FROM item WHERE new_payload IS NOT NULL").fetchone()[0]
mig_integrity=c.execute("PRAGMA integrity_check").fetchone()[0]
c.close()

results["tests"]["migration_interrupt_resume"]={
    "detected_status_after_crash":status,
    "phase_after_crash":phase,
    "rows_converted_after_crash":converted,
    "rows_converted_after_resume":converted_after,
    "integrity_check":mig_integrity
}

# E. Backup / restore
src=out/"backup_source.db"
c=sqlite3.connect(src)
c.execute("CREATE TABLE x(id INTEGER PRIMARY KEY,v TEXT)")
c.executemany("INSERT INTO x(v) VALUES(?)",[(f"value-{i}",) for i in range(100)])
c.commit()
dst=out/"backup_copy.db"
b=sqlite3.connect(dst)
c.backup(b)
b.close(); c.close()

def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

b=sqlite3.connect(dst)
cnt=b.execute("SELECT COUNT(*) FROM x").fetchone()[0]
restore_integrity=b.execute("PRAGMA integrity_check").fetchone()[0]
b.close()
results["tests"]["backup_restore"]={
    "restored_rows":cnt,
    "integrity_check":restore_integrity,
    "source_sha256":sha256(src),
    "backup_sha256":sha256(dst),
    "note":"SQLite backup files need not have identical byte hashes to prove logical equivalence."
}

# F. Newer schema gate
gate=out/"schema_gate.db"
c=sqlite3.connect(gate)
c.execute("PRAGMA user_version=999")
c.commit()
uv=c.execute("PRAGMA user_version").fetchone()[0]
c.close()
supported_max=7
results["tests"]["newer_schema_gate"]={
    "db_schema_version":uv,
    "supported_max":supported_max,
    "write_allowed":uv<=supported_max
}

production_lane=results["tests"]["single_writer_queue"]

results["all_required_checks_pass"] = (
    production_lane["committed"] == THREADS*N
    and production_lane["writer_errors"] == 0
    and production_lane["producer_errors"] == 0
    and production_lane["integrity_check"] == "ok"
    and results["tests"]["abrupt_exit"]["committed_survived"]
    and results["tests"]["abrupt_exit"]["uncommitted_absent"]
    and results["tests"]["abrupt_exit"]["integrity_check"] == "ok"
    and results["tests"]["migration_interrupt_resume"]["detected_status_after_crash"] == "RUNNING"
    and results["tests"]["migration_interrupt_resume"]["rows_converted_after_resume"] == 1000
    and results["tests"]["migration_interrupt_resume"]["integrity_check"] == "ok"
    and results["tests"]["backup_restore"]["restored_rows"] == 100
    and results["tests"]["backup_restore"]["integrity_check"] == "ok"
    and results["tests"]["newer_schema_gate"]["write_allowed"] is False
)

results["acceptance_policy"] = {
    "raw_multiwriter_characterization_is_informational": True,
    "production_acceptance_lane": "single_writer_queue",
    "production_required_committed": THREADS*N,
    "production_required_errors": 0
}

(out/"windows_persistence_spike_results_v2.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
print(json.dumps(results,indent=2))
