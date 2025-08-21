import sqlite3

conn = sqlite3.connect("data/wb.sqlite")

# ключевая строчка ↓
conn.row_factory = sqlite3.Row

cur = conn.cursor()
cur.execute("SELECT * FROM products")

for row in cur.fetchall():
    print(dict(row))   # превращаем Row в dict

conn.close()
