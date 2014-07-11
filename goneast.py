# goneast.py
'''
Abstract Syntax Tree (AST) objects.

This file defines classes for different kinds of nodes of an Abstract
Syntax Tree.  During parsing, you will create these nodes and connect
them together.  In general, you will have a different AST node for
each kind of grammar rule.  A few sample AST nodes can be found at the
top of this file.  You will need to add more on your own.
'''

# DO NOT MODIFY
class AST(object):
    '''
    Base class for all of the AST nodes.  Each node is expected to
    define the _fields attribute which lists the names of stored
    attributes.   The __init__() method below takes positional
    arguments and assigns them to the appropriate fields.  Any
    additional arguments specified as keywords are also assigned.
    '''
    _fields = []
    def __init__(self,*args,**kwargs):
        assert len(args) == len(self._fields)
        for name,value in zip(self._fields,args):
            setattr(self,name,value)
        # Assign additional keyword arguments if supplied
        for name,value in kwargs.items():
            setattr(self,name,value)

    def __repr__(self):
        vals = []
        for k,v in self.__dict__.items():
            if not isinstance(v, list) and not isinstance(v, AST) and k != 'lineno':
                vals.append((k,v))
        lineno = getattr(self, 'lineno', None)
        l = '({}) '.format(lineno) if lineno else ''
        if vals:
            return '{}{} {}'.format(l, self.__class__.__name__, vals)
        else:
            return '{}{}'.format(l, self.__class__.__name__)

# ----------------------------------------------------------------------
# Specific AST nodes.
#
# For each node, you need to define a class and add the appropriate _fields = []
# specification that indicates what fields are to be stored.  Just as
# an example, for a binary operator, you might store the operator, the
# left expression, and the right expression like this:
#
#    class Binop(AST):
#        _fields = ['op','left','right']
# ----------------------------------------------------------------------

##
## Decorator stuff for later fun
##

class Expression(AST):
    pass

class Location(AST):
    _fields = ['name']

class Statement(AST):
    pass

def require(**types):
    def decorate(cls):
        print(cls.__init__)
        init = cls.__init__
        def __init__(self, *args, **kwargs):
            init(self, *args, **kwargs)
            for name, type_ in types.items():
                if isinstance(type_, list):
                    assert all(isinstance(i, type_) for i in getattr(self, name)), \
                           '{} must be all of type {}'.format(name, type_)
                elif isinstance(type_, tuple):
                    assert type(getattr(self, name)) in type_, \
                           '{} type must be one of {}'.format(name, type_.__name__)
                else:
                    assert type(getattr(self, name)) == type_, \
                           '{} must be {}'.format(name, type_.__name__)
        setattr(cls, '__init__', __init__)
        return cls
    return decorate

#@require(location=Location, expression=Expression)
class AssignStatement(AST):
    _fields = ['location', 'expression']

class BinaryOp(AST):
    _fields = ['op', 'left', 'right']

class ConstDeclaration(AST):
    _fields = ['name', 'expression']

class ExternDeclaration(AST):
    _fields = ['func_prototype']

class FunctionCall(AST):
    _fields = ['name', 'parameters']

class FunctionDeclaration(AST):
    _fields = ['prototype', 'statements']

class FunctionPrototype(AST):
    _fields = ['name', 'parameters', 'output_typename']

class IfStatement(AST):
    _fields = ['relation', 'if_body', 'else_body']

class Literal(AST):
    _fields = ['value']

class LoadLocation(Location):
    _fields = ['name']

class Parameter(AST):
    _fields = ['name', 'typename']

class PrintStatement(AST):
    _fields = ['expression']

class Program(AST):
    _fields = ['statements']

class ReturnStatement(AST):
    _fields = ['expression']

class Statements(AST):
    _fields = ['statement_list']

class Statement(AST):
    _fields = ['declaration']

class StoreLocation(Location):
    _fields = ['name']

class Typename(AST):
    _fields = ['name']

class UnaryOp(AST):
    _fields = ['op', 'operand']

class VarDeclaration(AST):
    _fields = ['name', 'typename', 'expression']

class WhileStatement(AST):
    _fields = ['relation', 'while_body']

# ----------------------------------------------------------------------
#                  DO NOT MODIFY ANYTHING BELOW HERE
# ----------------------------------------------------------------------

# The following classes for visiting and rewriting the AST are taken
# from Python's ast module.

# DO NOT MODIFY
class NodeVisitor(object):
    '''
    Class for visiting nodes of the parse tree.  This is modeled after
    a similar class in the standard library ast.NodeVisitor.  For each
    node, the visit(node) method calls a method visit_NodeName(node)
    which should be implemented in subclasses.  The generic_visit() method
    is called for all nodes where there is no matching visit_NodeName() method.

    Here is a example of a visitor that examines binary operators:

        class VisitOps(NodeVisitor):
            visit_Binop(self,node):
                print("Binary operator", node.op)
                self.visit(node.left)
                self.visit(node.right)
            visit_Unaryop(self,node):
                print("Unary operator", node.op)
                self.visit(node.expr)

        tree = parse(txt)
        VisitOps().visit(tree)
    '''
    def visit(self,node):
        '''
        Execute a method of the form visit_NodeName(node) where
        NodeName is the name of the class of a particular node.
        '''
        if node:
            method = 'visit_' + node.__class__.__name__
            visitor = getattr(self, method, self.generic_visit)
            #if 'GenerateCode' in self.__class__.__name__:
            #    print('calling: {} with {} on line {}'.format(visitor.__name__, node, node.lineno))
            return visitor(node)
        else:
            return None

    def generic_visit(self,node):
        '''
        Method executed if no applicable visit_ method can be found.
        This examines the node to see if it has _fields, is a list,
        or can be further traversed.
        '''
        for field in getattr(node,"_fields"):
            value = getattr(node,field,None)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item,AST):
                        self.visit(item)
            elif isinstance(value, AST):
                self.visit(value)

# DO NOT MODIFY
class NodeTransformer(NodeVisitor):
    '''
    Class that allows nodes of the parse tree to be replaced/rewritten.
    This is determined by the return value of the various visit_() functions.
    If the return value is None, a node is deleted. If any other value is returned,
    it replaces the original node.

    The main use of this class is in code that wants to apply transformations
    to the parse tree.  For example, certain compiler optimizations or
    rewriting steps prior to code generation.
    '''
    def generic_visit(self,node):
        for field in getattr(node,"_fields"):
            value = getattr(node,field,None)
            if isinstance(value,list):
                newvalues = []
                for item in value:
                    if isinstance(item,AST):
                        newnode = self.visit(item)
                        if newnode is not None:
                            newvalues.append(newnode)
                    else:
                        newvalues.append(n)
                value[:] = newvalues
            elif isinstance(value,AST):
                newnode = self.visit(value)
                if newnode is None:
                    delattr(node,field)
                else:
                    setattr(node,field,newnode)
        return node

# DO NOT MODIFY
def flatten(top):
    '''
    Flatten the entire parse tree into a list for the purposes of
    debugging and testing.  This returns a list of tuples of the
    form (depth, node) where depth is an integer representing the
    parse tree depth and node is the associated AST node.
    '''
    class Flattener(NodeVisitor):
        def __init__(self):
            self.depth = 0
            self.nodes = []
        def generic_visit(self,node):
            self.nodes.append((self.depth,node))
            self.depth += 1
            NodeVisitor.generic_visit(self,node)
            self.depth -= 1

    d = Flattener()
    d.visit(top)
    return d.nodes
