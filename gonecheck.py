# gonecheck.py
"""Type checker for Gone"""
from collections import ChainMap

import gonetype as types

from errors import error
from goneast import *

class CheckProgramVisitor(NodeVisitor):
    def __init__(self):
        self.symtab = ChainMap({
            'int': types.IntType,
            'float': types.FloatType,
            'string': types.StringType,
            'bool': types.BoolType,
        })

    def visit_Program(self, node):
        self.visit(node.statements)
        # Make sure we have a main func
        main = self.symtab.get('main')
        if not isinstance(main, FunctionPrototype):
            error(0, 'No main() defined')

    def visit_Statements(self, node):
        for s in node.statement_list:
            self.visit(s)

    def visit_PrintStatement(self, node):
        self.visit(node.expression)
        node.type = node.expression.type

    def visit_UnaryOp(self, node):
        self.visit(node.operand)

        ret_type = node.operand.type.check_unaop(node.op)
        if ret_type is types.ErrorType:
            error(node.lineno, 'Unsupported operation: {} {}'.format(
                  node.op, node.operand.type))
        node.type = ret_type

    def visit_BinaryOp(self, node):
        self.visit(node.left)
        self.visit(node.right)
        ret_type = node.left.type.check_binop(node.op, node.left, node.right)
        if ret_type is types.ErrorType:
            error(node.lineno, 'Unsupported operation: {} {} {}'.format(
                  node.left.type, node.op, node.right.type))
        node.type = ret_type

    def visit_ExternDeclaration(self, node):
        self.visit(node.func_prototype)
        node.type = node.func_prototype.type

    def visit_FunctionDeclaration(self, node):
        self.visit(node.prototype)

        # Create a local scope with declared vars and check statements
        self.symtab = self.symtab.new_child() # push local scope on
        for p in node.prototype.parameters:
            self.symtab[p.name] = Literal(None)
            self.symtab[p.name].type = p.typename.type
        self.visit(node.statements)
        self.symtab = self.symtab.parents # pop local scope off

        # Make sure we return from this function someday
        return_type = node.prototype.output_typename.type
        if not node.statements.is_terminal(return_type):
            error(node.lineno, 'Function {} may not return'.format(node.prototype.name))

    def visit_ReturnStatement(self, node):
        self.visit(node.expression)
        node.type = node.expression.type

    def visit_FunctionPrototype(self, node):
        sym = self.symtab.get(node.name)
        if sym is not None:
            error(node.lineno, "{} is already defined".format(node.name))
        else:
            for p in node.parameters:
                self.visit(p)
            self.visit(node.output_typename)
            node.type = node.output_typename.type
            self.symtab[node.name] = node

    def visit_Parameter(self, node):
        self.visit(node.typename)
        node.type = node.typename.type

    def visit_FunctionCall(self, node):
        for p in node.parameters:
            self.visit(p)

        sym = self.symtab.get(node.name)
        if sym is None:
            error(node.lineno, '{} is not defined'.format(node.name))
            node.type = types.ErrorType
        elif not isinstance(sym, FunctionPrototype):
            error(node.lineno, '{} is not a function'.format(node.name))
            node.type = types.ErrorType
        elif len(node.parameters) != len(sym.parameters):
            error(node.lineno, '{} expected {} parameters, but got {}'.format(
                node.name, len(sym.parameters), len(node.parameters)))
            node.type = types.ErrorType
        else:
            func_types = [p.type for p in sym.parameters]
            node_types = [p.type for p in node.parameters]
            for i, (func_t,node_t) in enumerate(zip(func_types,node_types)):
                if func_t != node_t:
                    error(node.lineno,
                          'Argument {}: expected {} but got {}'.format(i+1, func_t, node_t))
                    node.type = types.ErrorType
            else:
                node.fn = sym
                node.type = sym.output_typename.type

    def visit_AssignStatement(self, node):
        self.visit(node.location)
        self.visit(node.expression)

        if node.location.type != node.expression.type:
            if node.location.type != types.ErrorType and node.expression.type != types.ErrorType:
                error(node.lineno, '{} is not type {}'.format(node.location.name, node.expression.type))
        elif node.location.name not in self.symtab:
            error(node.lineno, 'Name is not defined: {}'.format(node.location.name))
        elif isinstance(self.symtab[node.location.name], ConstDeclaration):
            error(node.lineno, '{} is a constant.'.format(node.location.name))
        else:
            node.type = node.expression.type

    def visit_ConstDeclaration(self, node):
        self.visit(node.expression)

        # Make sure we aren't in the symtab already
        if node.name in self.symtab:
            error(node.lineno, '{} is already defined'.format(node.name))
        else:
            self.symtab[node.name] = node
            node.type = node.expression.type
            node.scope = 'local' if self.symtab.parents else 'global'

    def visit_VarDeclaration(self, node):
        self.visit(node.typename)
        self.visit(node.expression)

        if node.name in self.symtab:
            error(node.lineno, '{} is already defined'.format(node.name))
        elif node.typename.type == types.ErrorType:
            node.type = types.ErrorType
        elif node.expression:
            if node.expression.type == types.ErrorType:
                node.type = types.ErrorType
            elif node.expression.type != node.typename.type:
                error(node.lineno, '{} is not type {}'.format(node.name, node.typename.name))
            else:
                node.type = node.expression.type
                self.symtab[node.name] = node.expression
                node.scope = 'local' if self.symtab.parents else 'global'
        else: # no expression -- use default (?)
            sym = Literal(node.typename.type.default, lineno=node.lineno)
            sym.type = node.typename.type
            self.symtab[node.name] = sym
            node.expression = sym
            node.scope = 'local' if self.symtab.parents else 'global'

    def visit_Typename(self, node):
        if not isinstance(self.symtab.get(node.name), types.GoneType):
            error(node.lineno, 'Undefined type: {}'.format(node.name))
            node.type = types.ErrorType
        else:
            node.type = self.symtab[node.name]

    def visit_LoadLocation(self, node):
        sym = self.symtab.get(node.name)
        if sym is None:
            error(node.lineno, '{} is not defined.'.format(node.name))
            node.type = types.ErrorType
        elif isinstance(sym, types.GoneType) or isinstance(sym, FunctionPrototype):
            error(node.lineno, '{} is not a valid location'.format(node.name))
            node.type = types.ErrorType
        elif isinstance(sym, VarDeclaration) and not sym.assigned:
            error(node.lineno, '{} accessed beore assignment'.format(sym.name))
            node.type = types.ErrorType
        else:
            node.type = sym.type

    def visit_StoreLocation(self, node):
        sym = self.symtab.get(node.name)
        if sym is None:
            error(node.lineno, '{} is not defined.'.format(node.name))
            node.type = types.ErrorType
        else:
            node.type = sym.type
            sym.assigned = True

    def visit_Literal(self, node):
        node.type = types.get_type(node.value)

    def visit_IfStatement(self, node):
        self.visit(node.relation)
        self.visit(node.if_body)
        self.visit(node.else_body)

        if node.relation.type != types.BoolType:
            error(node.lineno, 'If statement must use bool test')
            node.type = TypeError

    def visit_WhileStatement(self, node):
        self.visit(node.relation)
        self.visit(node.while_body)

        if node.relation.type != types.BoolType:
            error(node.lineno, 'If statement must use bool test')
            node.type = TypeError


def check_program(node):
    '''
    Check the supplied program (in the form of an AST)
    '''
    checker = CheckProgramVisitor()
    checker.visit(node)

def main():
    import gonelex
    import goneparse
    import sys
    from errors import subscribe_errors
    lexer = gonelex.make_lexer()
    parser = goneparse.make_parser()
    with subscribe_errors(lambda msg: sys.stdout.write(msg+"\n")):
        program = parser.parse(open(sys.argv[1]).read())
        # Check the program
        check_program(program)
        print(program)

if __name__ == '__main__':
    main()
