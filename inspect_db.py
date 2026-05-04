import os, sqlite3

db = 'data/credit_scoring.db'
print(f"Database: {os.path.abspath(db)}")
print(f"Size: {os.path.getsize(db) / 1024:.1f} KB")
print()

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

# List tables
tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f"Tables: {tables}")
print()

for t in tables:
    count = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
    print(f"  {t}: {count} rows")

print("\n--- SAMPLE: assessment_sessions ---")
rows = conn.execute("SELECT session_id, name, status, final_score, decision, risk_tier, created_at FROM assessment_sessions ORDER BY created_at DESC LIMIT 5").fetchall()
for r in rows:
    print(f"  {r['name']:20s} | Score: {r['final_score']} | {r['decision']:12s} | {r['risk_tier']} | {r['status']} | {r['created_at']}")

print("\n--- SAMPLE: kg_nodes ---")
rows = conn.execute("SELECT id, type, name FROM kg_nodes LIMIT 10").fetchall()
for r in rows:
    print(f"  [{r['type']:12s}] {r['id']:25s} → {r['name']}")

print("\n--- SAMPLE: kg_edges ---")
rows = conn.execute("SELECT source_id, type, target_id FROM kg_edges LIMIT 10").fetchall()
for r in rows:
    print(f"  {r['source_id']:25s} --[{r['type']:15s}]--> {r['target_id']}")

conn.close()
