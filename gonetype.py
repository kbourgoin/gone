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
        return self.__class__.__name__

    def check_type(self, python_var):
        return isinstance(python_var, self.pytype)

    def validate_binop(self, op, other):
        """Return (valid, ret_type) for the binary operation

        :param op: token name of the operation
        :param other: type of the other type involved
        """
        if op in self.binops and other == self:
            return True, _types_by_name[self.binops[op]]
        else:
            return False, None

    def validate_unaop(self, op):
        """Return (valid, ret_type) for the unary operation

        :param op: token name of the operation
        """
        if op in self.unaops:
            return True, _types_by_name[self.unaops[op]]
        else:
            return False, None


class IntType(GoneType):
    binops = {'+': 'int',
              '-': 'int',
              '*': 'int',
              '/': 'int'}
    unaops = {'+': 'int',
              '-': 'int'}
    pytype = int
    name   = 'int'
    default = None

class FloatType(GoneType):
    binops = {'+': 'float',
              '-': 'float',
              '*': 'float',
              '/': 'float'}
    unaops = {'+': 'float',
              '-': 'float'}
    pytype = float
    name   = 'float'
    default = None

class StringType(GoneType):
    binops = {'+': 'string'}
    unaops = {}
    name = 'string'
    pytype = str
    default = None

# Create specific instances of types. You will need to add
# appropriate arguments depending on your definition of GoneType
int_type = IntType()
float_type = FloatType()
string_type = StringType()

_types_by_name = {
    'int': int_type,
    'float': float_type,
    'string': string_type,
}

def get_type(python_var):
    """Get the GoneType corresponding to the python var's type"""
    for gtype in _types_by_name.values():
        if gtype.check_type(python_var):
            return gtype
    raise Exception("Unable to match type to {}", type(python_var))
