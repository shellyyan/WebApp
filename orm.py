#!/usr/bin/env python3
# -*- coding: utf-8 -*-


__author__ = 'shellyyan' 

import logging
import asyncio
import aiomysql

def log(sql, args=()):
    logging.info("SQL: %s" % sql)
#创建全局数据库连接池，使得每个http请求都能从连接池中直接获取数据库连接，避免频繁的打开和关闭数据库连接
@asyncio.coroutine
def create_pool(loop,**kw):
    logging.info("create database connection pool...")
    global __pool
    #调用一个子协程创建全局连接池，create_pool的返回值是一个__pool实例对象
    _pool=yield from aiomysql.create_pool(
        #设置连接的属性
        host=kw.get("host","localhost"),
        port=kw.get("port",3306),
        user=kw["user"],
        password=kw["password"],
        db=kw["database"],
        charset=kw.get["charset","utf8"],
        autocommit=kw.get("autocommit",True),
        maxsize=kw.get("maxsize",10),
        minsize=kw.get("minsize",1),
        loop=loop
        )
#将数据库的select操作封装在select函数中

    
@asyncio.coroutine
def select(sql,args,size=None):
    log(sql,args)
    global __pool
    with (yield from __pool) as conn:
        #打开一个dictcursor,此游标以dict形式返回
        cur=yield from conn.cursor(aiomysql.DictCursor)
        yield from cur.execute(sql.replace("?","%s"),args or ())
        if size:
            rs=yield from cur.fetchmany(size)

        else:
            rs=yield from cur.fetchall()
        yield from cur.close()
        logging.info("rows return %s" %len(rs))
        return rs

#增删改都是对数据库的修改，因此封装到一个函数中
@asyncio.coroutine
def execute(sql,args):
    log(sql)
    with (yield from __pool) as conn:
        try:
            #此处打开的是一个普通游标
            cur=yield from conn.cursor()
            yield from cur.execute(sql.replace("?","%s"),args)
            affected=cur.rowcount #增删改，返回影响的行数
            yield from cur.close()
        except BaseException as e:
            raise
        return affected

#构造占位符
def create_args_string(num):
    L=[]
    for n in range(num):
        L.append("?")
    return ','.join(L)
#父域，可被其他域继承
class Field(object):
    #域的初始化，包括属性（列）名，属性的类型，是否主键
    def __init__(self,name,column_type,primary_key,default):
        self.name=name
        self.column_type=column_type
        self.primary_key=primary_key
        self.default=default

        #用于打印消息，依次为类名（域名），属性类型，属性名
        def __str__(self):
            return "<%s,%s:%s>"%(self.__class__.__name__,self.column_type,self.name)
#字符串域
class StringField(Field):
    def __init__(self,name=None,primary_key=False,default=None,ddl="varchar(100)"):
        super().__init__(name,ddl,primary_key,default)

# 整数域
class IntegerField(Field):
    
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, "bigint", primary_key, default)

# 布尔域
class BooleanField(Field):
    
    def __init__(self, name=None, default=False):
        super().__init__(name, "boolean", False, default)

# 浮点数域
class FloatField(Field):
    
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, "real", primary_key, default)

# 文本域
class TextField(Field):
    
    def __init__(self, name=None, default=None):
        super().__init__(name, "text", False, default)
#定义元类，它定义了如何来构造一个类，任何定义了__metaclass__属性或指定了metaclass的都会通过元类定义的构造方法构造
class ModelMetaclass(type):
    def __new__(cls,name,bases,attrs):
        if name=="Model":
            return type.__new__(cls,name,bases,attrs)
        tableName=attrs.get("__table__",None) or name
        logging.info("found model:%s(table:%s)"%(name,tableName))
        mappings=dict()
        fields=[]
        primarykey=None
        for k,v in attrs.items():
            if isinstance(v,Field):
                logging.info("found mapping:%s==>%s"%(k,v))
                mapping[k]=v
                if v.primary_key:
                    if primarykey:
                        raise RuntimeError("Duplicate primary key for field:%s"%s)
                    primarykey=k
                else:
                    fields.append(k)
        if not primarykey:
            raise RuntimeError("Primary key not found")
        for k in mappings.keys():
            attrs.pop(k)
            escaped_fields=list(map(lambda f:"`%s`"%f,fields))
            attrs["__mappings__"]=mappings
            attrs["__table__"]=tableName
            attrs["__primary_key__"]=primarykey
            attrs["__fields__"]=fields
            # 构造默认的select, insert, update, delete语句,使用?作为占位符
            attrs["__select__"] = "select `%s`, %s from `%s`" % (primaryKey, ', '.join(escaped_fields), tableName)
            # 此处利用create_args_string生成的若干个?占位
            # 插入数据时,要指定属性名,并对应的填入属性值(数据库的知识都要忘光了,我这句怎么难看懂- -,惭愧惭愧)
            attrs["__insert__"] = "insert into `%s` (%s, `%s`) values (%s)" % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1 ))
            # 通过主键查找到记录并更新
            attrs["__update__"] = "update `%s` set %s where `%s`=?" % (tableName, ', '.join(map(lambda f: "`%s`" % (mappings.get(f).name or f), fields)), primaryKey)
            # 通过主键删除
            attrs["__delete__"] = "delete from `%s` where `%s`=?" % (tableName, primaryKey)
            return type.__new__(cls, name, bases, attrs)
# ORM映射基类,继承自dict,通过ModelMetaclass元类来构造类
class Model(dict, metaclass=ModelMetaclass):
    
    # 初始化函数,调用其父类(dict)的方法
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    # 增加__getattr__方法,使获取属性更方便,即可通过"a.b"的形式
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute'%s'" % key)

    # 增加__setattr__方法,使设置属性更方便,可通过"a.b=c"的形式
    def __setattr__(self, key, value):
        self[key] = value

    # 通过键取值,若值不存在,返回None
    def getValue(self, key):
        return getattr(self, key, None)

    # 通过键取值,若值不存在,则返回默认值
    # 这个函数很好玩!
    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key] # field是一个定义域!比如FloatField
            # default这个属性在此处再次发挥作用了!
            if field.default is not None:
                # 看例子你就懂了
                # id的StringField.default=next_id,因此调用该函数生成独立id
                # FloatFiled.default=time.time数,因此调用time.time函数返回当前时间
                # 普通属性的StringField默认为None,因此还是返回None
                value = field.default() if callable(field.default) else field.default
                logging.debug("using default value for %s: %s" % (key, str(value)))
                # 通过default取到值之后再将其作为当前值
                setattr(self, key, value)
        return value
    @classmethod
    @asyncio.coroutine
    def find(cls,pk):
        'find object by primary key'
        # 我们之前已将将数据库的select操作封装在了select函数中,以下select的参数依次就是sql, args, size
        rs = yield from select("%s where `%s`=?" % (cls.__select__, cls.primary_key), [pk], 1)
        if len(rs) == 0:
            return None
        # **表示关键字参数,我当时还疑惑怎么用到了指针?知识交叉了- -
        # 注意,我们在select函数中,打开的是DictCursor,它会以dict的形式返回结果
        return cls(**rs[0])
    @classmethod
    @asyncio.coroutine
    def findAll(cls, where=None, args=None, **kw):
        sql = [cls.__select__]
        # 我们定义的默认的select语句是通过主键查询的,并不包括where子句
        # 因此若指定有where,需要在select语句中追加关键字
        if where:
            sql.append("where")
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get("orderBy", None)
        # 解释同where, 此处orderBy通过关键字参数传入
        if orderBy:
            sql.append("order by")
            sql.append(orderBy)
        # 解释同where
        limit = kw.get("limit", None)
        if limit is not None:
            sql.append("limit")
            if isinstance(limit, int):
                sql.append("?")
                args.append(limit)
            elif isinstance(limint, tuple) and len(limint) == 2:
                sql.append("?, ?")
                args.extend(limit)
            else:
                raise ValueError("Invalid limit value: %s" % str(limit))
        rs = yield from select(' '.join(sql), args) #没有指定size,因此会fetchall
        return [cls(**r) for r in rs]
    @classmethod
    @asyncio.coroutine
    def findNumber(cls, selectField, where=None, args=None):
        sql = ["select %s _num_ from `%s`" % (selectField, cls.__table__)]
        if where:
            sql.append("where")
            sql.append(where)
        rs = yield from select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]["_num_"]
        

    @asyncio.coroutine
    def save(self):
        # 我们在定义__insert__时,将主键放在了末尾.因为属性与值要一一对应,因此通过append的方式将主键加在最后
        args = list(map(self.getValueOrDefault, self.__fields__)) #使用getValueOrDefault方法,可以调用time.time这样的函数来获取值
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = yield from execute(self.__insert__, args)
        if rows != 1: #插入一条记录,结果影响的条数不等于1,肯定出错了
            logging.warn("failed to insert recored: affected rows: %s" % rows)


    @asyncio.coroutine
    def update(self):
        # 像time.time,next_id之类的函数在插入的时候已经调用过了,没有其他需要实时更新的值,因此调用getValue
        args = list(map(self.getValue, self.__fields__)) 
        args.append(self.getValue(self.__primary_key__))
        rows = yield from execute(self.__update__, args)
        if rows != 1:
            logging.warn("failed to update by primary key: affected rows %s" % rows)
        

    @asyncio.coroutine
    def remove(self):
        args = [self.getValue(self.__primary_key__)] # 取得主键作为参数
        rows = yield from execute(self.__delete__, args) # 调用默认的delete语句
        if rows != 1:
            logging.warn("failed to remove by primary key: affected rows %s" % rows)

    

            
























        


























        


























