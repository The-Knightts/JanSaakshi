import sqlite3

conn = sqlite3.connect('DATA_DB.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM Meeting_data')
count = cursor.fetchone()[0]
print(f'Total meetings in database: {count}')

cursor.execute('SELECT meeting_id, objective, meeting_date, ward FROM Meeting_data LIMIT 3')
rows = cursor.fetchall()
print('\nSample meetings:')
for row in rows:
    print(f'  - {row}')

conn.close()
