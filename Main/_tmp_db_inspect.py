import sqlite3, json, os, sys
path='..\\DB\\Main_DB.db'
print('DB exists?', os.path.exists(path))
if not os.path.exists(path):
    sys.exit(0)
con=sqlite3.connect(path)
cur=con.cursor()
cur.execute( SELECT name FROM sqlite_master WHERE type=table ORDER BY name)
print('Tables:', [r[0] for r in cur.fetchall()])
for table in ['flight_searches','flight_search','searches','api_queries','price_insights']:
    try:
        cur.execute(f'SELECT COUNT(*) FROM {table}')
        cnt=cur.fetchone()[0]
        print(f'Table {table} count:', cnt)
        if cnt:
            cur.execute(f'PRAGMA table_info({table})')
            cols=[c[1] for c in cur.fetchall()]
            cur.execute(f'SELECT * FROM {table} ORDER BY rowid DESC LIMIT 1')
            row=cur.fetchone()
            print('Last row columns:', cols)
            print('Last row values:', row)
    except Exception as e:
        pass
