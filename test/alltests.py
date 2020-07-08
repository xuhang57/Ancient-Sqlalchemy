import testbase
import unittest

testbase.echo = False

def suite():
    modules_to_test = (
        # core utilities
        'historyarray', 
        'attributes', 
        'dependency',
        
        # connectivity
        'pool', 
        
        # schema/tables
        'engines', 
        'types',
        
        # SQL syntax
        'select',
        'selectable',
        
        # assorted round-trip tests
        'query',
        
        # sequences (postgres/oracle)
        'sequence',
        
        # ORM selecting
        'mapper',
        
        # ORM persistence
        'objectstore',
        
        # cyclical ORM persistence
        'cycles',
        
        # more select/persistence, backrefs
        'manytomany',
        #'onetoone',
        
        # extensions
        'proxy_engine',
        #'wsgi_test',
        
        )

    alltests = unittest.TestSuite()
    for module in map(__import__, modules_to_test):
        alltests.addTest(unittest.findTestCases(module, suiteClass=None))
    return alltests

import sys
sys.stdout = sys.stderr

if __name__ == '__main__':
    testbase.runTests(suite())