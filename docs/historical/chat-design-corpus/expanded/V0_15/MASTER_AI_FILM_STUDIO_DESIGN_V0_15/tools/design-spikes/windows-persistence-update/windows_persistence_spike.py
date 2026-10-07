import argparse, sqlite3, threading, time, statistics, json, os, sys, subprocess, shutil, hashlib
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--out", required=True)
args = parser.parse_args()

out = Path(args.out).resolve()
if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True)

results = {
    "platform": sys.platform,
    "python": sys.version,
    "tests": {},
    "limitations": []
}

def pctl(vals,p):
    vals=sorted(vals)
    i=min(len(vals)-1,max(0,int(round((len(vals)-1)*p))))
    return vals[i]

# 1. WAL concurrency on actual target OS/hardware
db = out/"wal.db"
c=sqlite3.connect(db)
jm=c.execute("PRAGMA journal_mode=WAL").fetchone()[0]
c.execute("PRAGMA synchronous=FULL")
c.execute("PRAGMA foreign_keys=ON")
c.execute("CREATE TABLE counter(id INTEGER PRIMARY KEY, v INTEGER NOT NULL, rev INTEGER NOT NULL)")
c.execute("INSERT INTO counter VALUES(1,0,0)")
c.commit(); c.close()

THREADS=12
N=250
lat=[]
errs=[]
lock=threading.Lock()

def worker(i):
    conn=sqlite3.connect(db,timeout=5,isolation_level=None,check_same_thread=False)
    conn.execute("PRAGMA busy_timeout=5000")
    for n in range(N):
        t=time.perf_counter()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE counter SET v=v+1, rev=rev+1 WHERE id=1")
            conn.execute("COMMIT")
            with lock: lat.append((time.perf_counter()-t)*1000)
        except Exception as e:
            try: conn.execute("ROLLBACK")
            except Exception: pass
            with lock: errs.append(repr(e))
    conn.close()

ts=[threading.Thread(target=worker,args=(i,)) for i in range(THREADS)]
start=time.perf_counter()
for t in ts:t.start()
for t in ts:t.join()
elapsed=time.perf_counter()-start

c=sqlite3.connect(db)
v,rev=c.execute("SELECT v,rev FROM counter").fetchone()
integrity=c.execute("PRAGMA integrity_check").fetchone()[0]
c.close()

results["tests"]["wal_concurrency"]={
    "journal_mode":jm,
    "expected":THREADS*N,
    "committed":v,
    "revision":rev,
    "errors":len(errs),
    "elapsed_s":elapsed,
    "tx_per_s":(THREADS*N)/elapsed if elapsed else None,
    "latency_ms_mean":statistics.mean(lat) if lat else None,
    "latency_ms_p95":pctl(lat,.95) if lat else None,
    "latency_ms_max":max(lat) if lat else None,
    "integrity_check":integrity,
}

# 2. Abrupt process exit transaction behavior
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
    "integrity_check":integ,
}

# 3. Migration interruption / resume marker
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

# Resume from rows still null.
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
    "integrity_check":mig_integrity,
}

# 4. Backup/restore hash
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

# 5. Newer schema gate
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

results["all_required_checks_pass"] = (
    results["tests"]["wal_concurrency"]["committed"] == THREADS*N
    and results["tests"]["wal_concurrency"]["errors"] == 0
    and results["tests"]["abrupt_exit"]["committed_survived"]
    and results["tests"]["abrupt_exit"]["uncommitted_absent"]
    and results["tests"]["migration_interrupt_resume"]["detected_status_after_crash"] == "RUNNING"
    and results["tests"]["migration_interrupt_resume"]["rows_converted_after_resume"] == 1000
    and results["tests"]["backup_restore"]["restored_rows"] == 100
    and results["tests"]["newer_schema_gate"]["write_allowed"] is False
)

(out/"windows_persistence_spike_results.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
print(json.dumps(results,indent=2))
