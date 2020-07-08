from sqlalchemy import *
import string,datetime, re, sys
from testbase import PersistTest, AssertMixin
import testbase
    
db = testbase.db

class OverrideTest(PersistTest):
    """tests user-defined types, including a full type as well as a TypeDecorator"""

    def testprocessing(self):
        class MyType(types.TypeEngine):
            def get_col_spec(self):
                return "VARCHAR(100)"
            def convert_bind_param(self, value, engine):
                return "BIND_IN"+ value
            def convert_result_value(self, value, engine):
                return value + "BIND_OUT"
            def adapt(self, typeobj):
                return typeobj()
            def adapt_args(self):
                return self

        class MyDecoratedType(types.TypeDecorator, types.String):
            def convert_bind_param(self, value, engine):
                return "BIND_IN"+ value
            def convert_result_value(self, value, engine):
                return value + "BIND_OUT"

        global users
        users = Table('users', db, 
            Column('user_id', Integer, primary_key = True),
            # totall custom type
            Column('goofy', MyType, nullable = False),
            
            # decorated type with an argument, so its a String
            Column('goofy2', MyDecoratedType(50), nullable = False),
            
            # decorated type without an argument, it will adapt_args to TEXT
            Column('goofy3', MyDecoratedType, nullable = False),
        )
        
        users.create()
        
        users.insert().execute(user_id = 2, goofy = 'jack', goofy2='jack', goofy3='jack')
        users.insert().execute(user_id = 3, goofy = 'lala', goofy2='lala', goofy3='lala')
        users.insert().execute(user_id = 4, goofy = 'fred', goofy2='fred', goofy3='fred')
        
        l = users.select().execute().fetchall()
        print repr(l)
        self.assert_(l == [(2, 'BIND_INjackBIND_OUT', 'BIND_INjackBIND_OUT', 'BIND_INjackBIND_OUT'), (3, 'BIND_INlalaBIND_OUT', 'BIND_INlalaBIND_OUT', 'BIND_INlalaBIND_OUT'), (4, 'BIND_INfredBIND_OUT', 'BIND_INfredBIND_OUT', 'BIND_INfredBIND_OUT')])


    def tearDownAll(self):
        global users
        users.drop()


class ColumnsTest(AssertMixin):

    def testcolumns(self):
        expectedResults = { 'int_column': 'int_column INTEGER',
                            'smallint_column': 'smallint_column SMALLINT',
                                   'varchar_column': 'varchar_column VARCHAR(20)',
                                   'numeric_column': 'numeric_column NUMERIC(12, 3)',
                                   'float_column': 'float_column NUMERIC(25, 2)'
                                 }

        if not db.engine.__module__.endswith('sqlite'):
            expectedResults['float_column'] = 'float_column FLOAT(25)'
    
        print db.engine.__module__
        testTable = Table('testColumns', db,
            Column('int_column', Integer),
            Column('smallint_column', Smallinteger),
            Column('varchar_column', String(20)),
            Column('numeric_column', Numeric(12,3)),
            Column('float_column', Float(25)),
        )

        for aCol in testTable.c:
            self.assertEquals(expectedResults[aCol.name], db.schemagenerator(None).get_column_specification(aCol))
        
class UnicodeTest(AssertMixin):
    """tests the Unicode type.  also tests the TypeDecorator with instances in the types package."""
    def setUpAll(self):
        global unicode_table
        unicode_table = Table('unicode_table', db, 
            Column('id', Integer, primary_key=True),
            Column('unicode_data', Unicode(50)),
            Column('plain_data', String)
            )
        unicode_table.create()
    def tearDownAll(self):
        unicode_table.drop()
    def testbasic(self):
        rawdata = 'Alors vous imaginez ma surprise, au lever du jour, quand une dr\xc3\xb4le de petit voix m\xe2\x80\x99a r\xc3\xa9veill\xc3\xa9. Elle disait: \xc2\xab S\xe2\x80\x99il vous pla\xc3\xaet\xe2\x80\xa6 dessine-moi un mouton! \xc2\xbb\n'
        unicodedata = rawdata.decode('utf-8')
        unicode_table.insert().execute(unicode_data=unicodedata, plain_data=rawdata)
        x = unicode_table.select().execute().fetchone()
        self.echo(repr(x['unicode_data']))
        self.echo(repr(x['plain_data']))
        self.assert_(isinstance(x['unicode_data'], unicode) and x['unicode_data'] == unicodedata)
        if isinstance(x['plain_data'], unicode):
            # SQLLite returns even non-unicode data as unicode
            self.assert_(sys.modules[db.engine.__module__].descriptor()['name'] == 'sqlite')
            self.echo("its sqlite !")
        else:
            self.assert_(not isinstance(x['plain_data'], unicode) and x['plain_data'] == rawdata)
            
    
class BinaryTest(AssertMixin):
    def setUpAll(self):
        global binary_table
        binary_table = Table('binary_table', db, 
        Column('primary_id', Integer, primary_key=True),
        Column('data', Binary),
        Column('data_slice', Binary(100)),
        Column('misc', String(30)))
        binary_table.create()
    def tearDownAll(self):
        binary_table.drop()
    def testbinary(self):
        stream1 =self.get_module_stream('sqlalchemy.sql')
        stream2 =self.get_module_stream('sqlalchemy.engine')
        binary_table.insert().execute(misc='sql.pyc', data=stream1, data_slice=stream1[0:100])
        binary_table.insert().execute(misc='engine.pyc', data=stream2, data_slice=stream2[0:99])
        l = binary_table.select().execute().fetchall()
        print len(stream1), len(l[0]['data']), len(l[0]['data_slice'])
        self.assert_(list(stream1) == list(l[0]['data']))
        self.assert_(list(stream1[0:100]) == list(l[0]['data_slice']))
        self.assert_(list(stream2) == list(l[1]['data']))
    def get_module_stream(self, name):
        mod = __import__(name)
        for token in name.split('.')[1:]:
            mod = getattr(mod, token)
        f = mod.__file__
        f = re.sub('\.py$', '\.pyc', f)
        return file(f).read()
        
class DateTest(AssertMixin):
    def setUpAll(self):
        global users_with_date, insert_data

        insert_data =  [[7, 'jack', datetime.datetime(2005, 11, 10, 0, 0), datetime.date(2005,11,10), datetime.time(12,20,2)],
                        [8, 'roy', datetime.datetime(2005, 11, 10, 11, 52, 35), datetime.date(2005,10,10), datetime.time(0,0,0)],
                        [9, 'foo', datetime.datetime(2005, 11, 10, 11, 52, 35, 54839), datetime.date(1970,4,1), datetime.time(23,59,59,999)],
                        [10, 'colber', None, None, None]]

        fnames = ['user_id', 'user_name', 'user_datetime', 'user_date', 'user_time']

        collist = [Column('user_id', INT, primary_key = True), Column('user_name', VARCHAR(20)), Column('user_datetime', DateTime),
                   Column('user_date', Date), Column('user_time', Time)]


        
        if db.engine.__module__.endswith('mysql'):
            # strip microseconds -- not supported by this engine (should be an easier way to detect this)
            for d in insert_data:
                d[2] = d[2].replace(microsecond=0)
                d[4] = d[4].replace(microsecond=0)
        
        try:
            db.type_descriptor(types.TIME).get_col_spec()
            print  "HI"
        except:
            # don't test TIME type -- not supported by this engine
            insert_data = [d[:-1] for d in insert_data]
            fnames = fnames[:-1]
            collist = collist[:-1]


        users_with_date = Table('query_users_with_date', db, redefine = True, *collist)
        users_with_date.create()

        insert_dicts = [dict(zip(fnames, d)) for d in insert_data]
        for idict in insert_dicts:
            users_with_date.insert().execute(**idict) # insert the data

    def tearDownAll(self):
        users_with_date.drop()

    def testdate(self):
        global insert_data

        l = map(list, users_with_date.select().execute().fetchall())
        self.assert_(l == insert_data, 'DateTest mismatch: got:%s expected:%s' % (l, insert_data))


    def testtextdate(self):     
        x = db.text("select user_datetime from query_users_with_date", typemap={'user_datetime':DateTime}).execute().fetchall()
        
        print repr(x)
        self.assert_(isinstance(x[0][0], datetime.datetime))
        
        #x = db.text("select * from query_users_with_date where user_datetime=:date", bindparams=[bindparam('date', )]).execute(date=datetime.datetime(2005, 11, 10, 11, 52, 35)).fetchall()
        #print repr(x)
        
if __name__ == "__main__":
    testbase.main()