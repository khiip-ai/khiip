"""Probe 3 — SQLite WITH RECURSIVE 2-hop traversal at 50K-edge scale.
Validates Lens 1's claim: 'single-digit ms' for filtered 2-hop on the Option Δ schema.
"""
import sqlite3, time, random, statistics, os
random.seed(42)
DB='/tmp/khiip-probe3/khiip-bench.sqlite'
if os.path.exists(DB): os.remove(DB)
con = sqlite3.connect(DB)
con.executescript('''
CREATE TABLE nodes (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE edges (
  id INTEGER PRIMARY KEY,
  src INTEGER NOT NULL,
  dst INTEGER NOT NULL,
  edge_type TEXT NOT NULL,
  vocab_match INTEGER NOT NULL DEFAULT 1,
  evidence_span TEXT NOT NULL,
  confidence REAL NOT NULL,
  recorded_at INTEGER NOT NULL,
  valid_from INTEGER NOT NULL,
  valid_to INTEGER
);
CREATE INDEX idx_src_type_vt ON edges(src, edge_type, valid_to);
CREATE INDEX idx_dst_type_vt ON edges(dst, edge_type, valid_to);
CREATE INDEX idx_conf_vf ON edges(confidence, valid_from);
''')

# 5000 nodes
N_NODES = 5000
con.executemany('INSERT INTO nodes(id,name) VALUES (?,?)',
                [(i, f'entity_{i}') for i in range(N_NODES)])

# 50000 edges across 21 canonical edge types
EDGE_TYPES = ['GEN','CON','REQ','SUP','MAP','OPR','TRN','INS','VAL','IDE','EXP','MOT',
              'ANA','TES','CHA','ISO','INV','TEN','COM','DUA','SUP_V']
N_EDGES = 50_000
NOW = 1715000000
batch=[]
for eid in range(N_EDGES):
    src = random.randint(0, N_NODES-1)
    dst = random.randint(0, N_NODES-1)
    et = random.choice(EDGE_TYPES)
    vm = 1 if random.random() > 0.15 else 0
    conf = round(random.uniform(0.4, 1.0), 2)
    rec = NOW - random.randint(0, 86400*30)
    vf  = rec - random.randint(0, 86400*365)
    vt  = None if random.random() > 0.05 else (vf + random.randint(86400, 86400*180))
    batch.append((eid,src,dst,et,vm,f'span{eid}',conf,rec,vf,vt))
con.executemany('INSERT INTO edges VALUES (?,?,?,?,?,?,?,?,?,?)', batch)
con.commit()

# 2-hop CON paths from random nodes with conf>0.7 at point-in-time
QUERY = '''
WITH RECURSIVE walk(src, dst, depth, conf_min) AS (
  SELECT src, dst, 1, confidence FROM edges
   WHERE src=? AND edge_type='CON' AND confidence>0.7
     AND (valid_to IS NULL OR valid_to > ?)
     AND valid_from <= ?
  UNION ALL
  SELECT w.src, e.dst, w.depth+1, MIN(w.conf_min, e.confidence) FROM walk w
    JOIN edges e ON e.src = w.dst
   WHERE e.edge_type='CON' AND e.confidence>0.7 AND w.depth<2
     AND (e.valid_to IS NULL OR e.valid_to > ?)
     AND e.valid_from <= ?
)
SELECT * FROM walk WHERE depth=2 LIMIT 100;
'''
# 200 random query-source nodes
samples = random.sample(range(N_NODES), 200)
times = []
total_rows = 0
for s in samples:
    pit = NOW - 86400*7
    t0 = time.perf_counter_ns()
    rows = con.execute(QUERY, (s, pit, pit, pit, pit)).fetchall()
    t1 = time.perf_counter_ns()
    times.append((t1-t0)/1_000_000)  # ms
    total_rows += len(rows)
con.close()
times.sort()
print(f'Schema:       nodes={N_NODES}, edges={N_EDGES} (21 canonical types, 15% vocab_match=0, 5% invalidated)')
print(f'Query shape:  2-hop CON traversal, confidence>0.7, point-in-time filter')
print(f'Samples:      {len(times)} random source nodes; {total_rows} total 2-hop paths returned')
print(f'p50:          {statistics.median(times):.3f} ms')
print(f'p95:          {times[int(len(times)*0.95)]:.3f} ms')
print(f'p99:          {times[int(len(times)*0.99)]:.3f} ms')
print(f'max:          {max(times):.3f} ms')
print(f'mean:         {statistics.mean(times):.3f} ms')
