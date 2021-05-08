"""
pymysql连接虚拟机mysql测试
"""
import pymysql

db = pymysql.connect(
    host='192.168.31.63',
    port=3306,
    user='root',
    password='123456',
    database='books'
)
cursor = db.cursor()
sel = 'select * from book'
a = cursor.execute(sel)
print(a)

cursor.close()
db.close()


