import asyncio,aiomysql
from models import User
@asyncio.coroutine
def test():  #这里使用aiomysql文档的示例写法，直接执行insert语句方式插入数据
    pool = yield from aiomysql.create_pool(host='localhost', port=3306,
              user='www-data', password='www-data',
              db='awesome', maxsize=10,minsize=1,loop=loop)
    with (yield from  pool) as conn:
        cursor=yield from conn.cursor()
        user = User(id='1',name='Administer',admin='1',email='admin@example.com',passwd='123456',image='about:blank',created_at='20161211')
        args = list(map(user.getValueOrDefault, user.__fields__))
        args.append(user.getValueOrDefault(user.__primary_key__))
        yield from cursor.execute(user.__insert__.replace('?','%s') , args )
        yield from cursor.close()
        yield from conn.commit()
    pool.close()
    yield from pool.wait_closed()

loop = asyncio.get_event_loop()
loop.run_until_complete(test())
loop.close()
