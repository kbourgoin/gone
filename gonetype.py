# gonetype.py
class GoneType(object):
    '''
    Class that represents a type in the Gone language.  Types
    are declared as singleton instances of this type.
    '''
    def __repr__(self):
        if hasattr(self, 'name'):
            return self.name
        elif self.__class__.__name__.startswith('_'):
            return self.__class__.__name__[1:]
        else:
            return self.__class__.__name__

    def check_binop(self, op, left, right):
        if op not in self.binops:
            return ErrorType
        elif left.type != right.type:
            # type coersion checking could go here
            return ErrorType
        return typemap[self.binops[op]]

    def check_unaop(self, op):
        if op not in self.unaops:
            return ErrorType
        # type coersion checking could go here
        return typemap[self.unaops[op]]


    def check_type(self, python_var):
        if self.pytype == int and (python_var is True or python_var is False):
            return False # wtf
        return isinstance(python_var, self.pytype)

class _IntType(GoneType):
    default = 0
    name = 'int'
    pytype = int
    unaops = {'+':  'int',
              '-':  'int',
              }
    binops = {'+':  'int',
              '-':  'int',
              '*':  'int',
              '/':  'int',
              '-':  'int',
              '==': 'bool',
              '!=': 'bool',
              '<':  'bool',
              '<=': 'bool',
              '>':  'bool',
              '>=': 'bool',
              }
IntType = _IntType() # need to instantiate so we can isinstance()

class _FloatType(GoneType):
    default = 0.0
    name = 'float'
    pytype = float
    unaops = {'+':  'float',
              '-':  'float',
              }
    binops = {'+':  'float',
              '-':  'float',
              '*':  'float',
              '/':  'float',
              '-':  'float',
              '==': 'bool',
              '!=': 'bool',
              '<':  'bool',
              '<=': 'bool',
              '>':  'bool',
              '>=': 'bool',
              }
FloatType = _FloatType() # need to instantiate so we can isinstance()

class _StringType(GoneType):
    default = ''
    name = 'string'
    pytype = str
    unaops = {}
    binops = {'+':  'int',
              '==': 'bool',
              '!=': 'bool',
              }
StringType = _StringType() # need to instantiate so we can isinstance()

class _BoolType(GoneType):
    default = False
    name = 'bool'
    pytype = bool
    unaops = {'!':  'bool',
              }
    binops = {'==': 'bool',
              '!=': 'bool',
              '||': 'bool',
              '&&': 'bool',
              }
BoolType = _BoolType() # need to instantiate so we can isinstance()

class _ErrorType(GoneType):
    pass
ErrorType = _ErrorType()


binary_ops = {
    '+' : 'add_op',
    '-' : 'sub_op',
    '*' : 'mul_op',
    '/' : 'div_op',
    '==' : 'eq_op',
    '!=' : 'neq_op',
    '<' : 'lt_op',
    '<=' : 'lte_op',
    '>' : 'gt_op',
    '>=' : 'gte_op',
    '||' : 'or_op',
    '&&' : 'and_op',
}

unary_ops = {
    '+' : 'uadd_op',
    '-' : 'usub_op',
    '!' : 'not_op',
}
typemap = {'int': IntType,
           'float': FloatType,
           'str': StringType,
           'bool': BoolType,
           }


def get_type(python_var):
    """Get the GoneType corresponding to the python var's type"""
    for gtype in typemap.values():
        if gtype.check_type(python_var):
            return gtype
    raise Exception("Unable to match type: {}".format(python_var))
