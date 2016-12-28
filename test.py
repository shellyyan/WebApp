import orm
import asyncio
from models import User,Blog,Comment
@asyncio.coroutine
def test():
    yield from orm.create_pool(loop,host='127.0.0.1',user='www-data',password='www-data',database='awesome')
    u=User(name='Test4',email='test4@example.com',passwd='1234567890',image='about:blank')
    yield from u.save()
    yield from pool.wait_closed()
loop=asyncio.get_event_loop()
loop.run_until_complete(test())
loop.run_forever()
