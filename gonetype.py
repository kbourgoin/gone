# gonetype.py
'''
Gone Type System
================
This file implements the Gone type system.  There is a lot of
flexibility with the implementation, but start by defining a
class representing a type.

class GoneType(object):
      pass

Concrete types are then created as instances.  For example:

    int_type = GoneType("int",...)
    float_type = GoneType("float",...)
    string_type = GoneType("string", ...)

The contents of the type class is entirely up to you. However,
it must minimally provide information about the following:

   a.  What operators are supported (+, -, *, etc.).
   b.  The result type of each operator.
   c.  Default values for newly created instances of each type
   d.  Methods for type-checking of binary and unary operators
   e.  Maintain a registry mapping builtin type names (e.g. 'int', 'float')
       to type instances.

Don't forget that all of the built-in types need to be registered
with symbol tables and other code that checks for type names. This
might require some coding in 'gonecheck.py'.
'''

class GoneType(object):
    '''
    Class that represents a type in the Gone language.  Types
    are declared as singleton instances of this type.
    '''
    def __repr__(self):
        if hasattr(self, 'pytype'):
            return str(self.pytype.__name__)
        elif self.__class__.__name__.startswith('_'):
            return self.__class__.__name__[1:]
        else:
            return self.__class__.__name__

    def check_binop(self, op, left, right):
        op_fn = getattr(self, binary_ops.get(op), None)
        if op_fn is None:
            return ErrorType
        params = op_fn.__annotations__
        if left.type != typemap[params['left']] or \
           right.type != typemap[params['right']]:
               return ErrorType
        return typemap[params['return']]

    def check_unaop(self, op):
        op_fn = getattr(self, unary_ops.get(op), None)
        if op_fn is None:
            return ErrorType
        params = op_fn.__annotations__
        return typemap[params['return']]

    def check_type(self, python_var):
        return isinstance(python_var, self.pytype)


class _IntType(GoneType):
    default = 0
    pytype = int

    def add(self, left: 'int', right: 'int') -> 'int':
        pass # todo: codegen

    def sub(self, left: 'int', right: 'int') -> 'int':
        pass # todo: codegen

    def mul(self, left: 'int', right: 'int') -> 'int':
        pass # todo: codegen

    def div(self, left: 'int', right: 'int') -> 'int':
        pass # todo: codegen

    def uadd(self) -> 'int':
        pass # todo: codegen

    def usub(self) -> 'int':
        pass # todo: codegen
IntType = _IntType() # need to instantiate so we can isinstance()

class _FloatType(GoneType):
    default = 0.0
    pytype = float

    def add(self, left: 'float', right: 'float') -> 'float':
        pass # todo: codegen

    def sub(self, left: 'float', right: 'float') -> 'float':
        pass # todo: codegen

    def mul(self, left: 'float', right: 'float') -> 'float':
        pass # todo: codegen

    def div(self, left: 'float', right: 'float') -> 'float':
        pass # todo: codegen

    def uadd(self) -> 'float':
        pass # todo: codegen

    def usub(self) -> 'float':
        pass # todo: codegen
FloatType = _FloatType() # need to instantiate so we can isinstance()


class _StringType(GoneType):
    default = ''
    pytype = str

    def add(self, left: 'str', right: 'str') -> 'str':
        pass # todo: codegen
StringType = _StringType() # need to instantiate so we can isinstance()

class _ErrorType(GoneType):
    pass
ErrorType = _ErrorType()


binary_ops = {
    '+' : 'add',
    '-' : 'sub',
    '*' : 'mul',
    '/' : 'div',
}

unary_ops = {
    '+' : 'uadd',
    '-' : 'usub',
}
typemap = {'int': IntType,
           'float': FloatType,
           'str': StringType,
           }


def get_type(python_var):
    """Get the GoneType corresponding to the python var's type"""
    for gtype in typemap.values():
        if gtype.check_type(python_var):
            return gtype
    raise Exception("Unable to match type to {}", type(python_var))
