import  mysql.connector

conn=mysql.connector.connect(
    host='localhost',
    username='root',
    password='Ma@461398',
    database='fyp'
)
my_cursor=conn.cursor()
conn.commit()
conn.close()
print("success")