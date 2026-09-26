import psycopg, urllib.parse
from psycopg import errors as pe
import pgserver

srv = pgserver.get_server('/home/user/sde2/agentops-practice/.pgdata-demo')
base = urllib.parse.urlparse(srv.get_uri())
with psycopg.connect(srv.get_uri(), autocommit=True) as admin:
    admin.execute("DROP DATABASE IF EXISTS sqldemo WITH (FORCE)")
    admin.execute("CREATE DATABASE sqldemo")
uri = urllib.parse.urlunparse(base._replace(path='/sqldemo'))
conn = psycopg.connect(uri, autocommit=True)

def section(t): print(f"\n{'='*60}\n{t}\n{'='*60}")
def show(tag, sql, params=None):
    print(f"\n>>> {tag}\n    {sql.strip().splitlines()[0]} ...")
    try:
        r = conn.execute(sql, params)
        rows = r.fetchall() if r.description else []
        for row in rows: print("    ->", row)
        if not rows: print("    -> OK")
        return r
    except pe.UniqueViolation as e:
        print(f"    !! UniqueViolation: {e.diag.constraint_name}")
        print(f"       ({e.diag.message_primary})")
        return None

section("A. CREATE — the table with BOTH uniqueness layers")
conn.execute("""
CREATE TABLE runs (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       uuid NOT NULL,
  idempotency_key text NOT NULL,
  entity_type     text,
  entity_id       text,
  status          text NOT NULL DEFAULT 'queued',
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_run_idem UNIQUE (tenant_id, idempotency_key)
)""")
conn.execute("""
CREATE UNIQUE INDEX uq_one_active_run_per_entity
ON runs (tenant_id, entity_type, entity_id)
WHERE status IN ('queued','running')""")
print("table + partial index created")

section("B. INSERT — request A wins (the 202)")
show("first submit, key 'k1', ticket 123",
"""INSERT INTO runs (tenant_id, idempotency_key, entity_type, entity_id)
VALUES ('11111111-1111-1111-1111-111111111111', 'k1', 'ticket', '123')
RETURNING id, status""")

section("C. INSERT — SAME key again (the double-click) -> refused by uq_run_idem")
show("second submit, same key 'k1'",
"""INSERT INTO runs (tenant_id, idempotency_key, entity_type, entity_id)
VALUES ('11111111-1111-1111-1111-111111111111', 'k1', 'ticket', '123')""")

section("D. SELECT — what the API returns instead (the 200)")
show("find the original by (tenant_id, key)",
"""SELECT id, status, created_at FROM runs
WHERE tenant_id='11111111-1111-1111-1111-111111111111' AND idempotency_key='k1'""")

section("E. INSERT — DIFFERENT key, same ACTIVE ticket -> refused by partial index")
show("other agent tries ticket 123 while it's queued",
"""INSERT INTO runs (tenant_id, idempotency_key, entity_type, entity_id)
VALUES ('11111111-1111-1111-1111-111111111111', 'k2', 'ticket', '123')""")

section("F. UPDATE to terminal -> the slot frees -> new run allowed")
show("finish the original run",
"""UPDATE runs SET status='succeeded'
WHERE idempotency_key='k1' RETURNING status""")
show("now a NEW run on ticket 123 works",
"""INSERT INTO runs (tenant_id, idempotency_key, entity_type, entity_id)
VALUES ('11111111-1111-1111-1111-111111111111', 'k3', 'ticket', '123')
RETURNING id, status""")

section("G. NULL entities never collide (NULLs are distinct in Postgres)")
show("run with no entity, key k4",
"""INSERT INTO runs (tenant_id, idempotency_key) 
VALUES ('11111111-1111-1111-1111-111111111111', 'k4') RETURNING id""")
show("run with no entity, key k5 — also fine?",
"""INSERT INTO runs (tenant_id, idempotency_key)
VALUES ('11111111-1111-1111-1111-111111111111', 'k5') RETURNING id""")

section("H. BONUS — reading the error from Python (what your API will do)")
conn.execute("DELETE FROM runs WHERE idempotency_key IN ('k4','k5')")
try:
    conn.execute("""INSERT INTO runs (tenant_id, idempotency_key, entity_type, entity_id)
                    VALUES ('11111111-1111-1111-1111-111111111111','k1','ticket','123')""")
except pe.UniqueViolation as e:
    print("caught UniqueViolation")
    print("  e.diag.constraint_name =", e.diag.constraint_name)
    print("  -> that attribute is the switch your API branches on")
