# gonecode.py
'''
Intermediate code generation
'''

import itertools

from collections import defaultdict

import goneast
import gonetype

from goneblock import BasicBlock, IfBlock, WhileBlock, FunctionBlock, InitializerFunctionBlock

binary_ops = {
    '+' : 'add',
    '-' : 'sub',
    '*' : 'mul',
    '/' : 'div',
    '==': 'eq',
    '!=': 'neq',
    '<': 'lte',
    '<=': 'lte',
    '>': 'gt',
    '>=': 'gte',
    '||': 'or',
    '&&': 'and',
}

unary_ops = {
    '+' : 'uadd',
    '-' : 'usub',
    '!': 'not',
}

class GenerateCode(goneast.NodeVisitor):
    '''
    Node visitor class that creates 3-address encoded instruction sequences.
    '''
    def __init__(self):
         super(GenerateCode, self).__init__()

         # version dictionary for temporaries
         self.versions = defaultdict(int)

         # The generated code (list of tuples)
         self.first_block = BasicBlock()
         self.current_block = self.first_block

         # A list of external declarations (and types)
         self.externs = []

         # A dict of functions declared
         self.functions = {}

    def __iter__(self):
        block = self.first_block
        while True:
            yield block
            block = block.next_block
            if block is None:
                break

    def new_temp(self, typeobj):
         '''
         Create a new temporary variable of a given type.
         '''
         name = "__%s_%d" % (typeobj.name, self.versions[typeobj.name])
         self.versions[typeobj.name] += 1
         return name

    def to_functions(self):
        """Convert the code tree to a list of functions

        The first function in the list will be the entry point
        """
        # Create an entry function
        entry_fn = InitializerFunctionBlock()
        entry_fn.instructions.append(('declare_func', '__start', 'int', []))
        entry_fn.body = BasicBlock()
        curr_entry_block = entry_fn.body # will keep track of entry body

        output = []
        block = self.first_block
        while block is not None:
            if isinstance(block, FunctionBlock):
                output.append(block)
                prev_block = block
                block = block.next_block
                # The old exit point is no longer relevant
                prev_block.next_block = None
            else:
                # Add to chain for entry_fn.block
                curr_entry_block.next_block = block
                curr_entry_block = block
                block = block.next_block

        # Make the `return main();` statement for the entry function
        main_fn = self.functions['main']
        entry_ret_call = goneast.FunctionCall('main', [])
        entry_ret_call.type = main_fn.output_typename.type
        entry_ret_call.fn = main_fn
        entry_ret = goneast.ReturnStatement(entry_ret_call)

        # Create a BasicBlock with that and attach that to the entry body
        self.current_block = BasicBlock()
        self.visit(entry_ret)
        curr_entry_block.next_block = self.current_block

        # Prepend so globals are created before functions
        output = [entry_fn] + output
        return output


    ##
    ## Instruction Generators
    ##

    def visit_Program(self, node):
        self.visit(node.statements)

    def visit_PrintStatement(self,node):
        self.visit(node.expression)
        inst = ('print_'+node.expression.type.name,
                node.expression.gen_location)
        self.current_block.append(inst)

    def visit_UnaryOp(self, node):
        self.visit(node.operand)

        if node.op == '+':
            # this is ultimately a no-op
            node.gen_location = node.operand.gen_location
        else:
            # Make a new temporary for storing the result
            target = self.new_temp(node.type)

            # Create the opcode and append to list
            opcode = unary_ops[node.op] + "_"+node.operand.type.name
            inst = (opcode, node.operand.gen_location, target)
            self.current_block.append(inst)

            # Store location of the result on the node
            node.gen_location = target

    def visit_BinaryOp(self,node):
        self.visit(node.left)
        self.visit(node.right)

        # Make a new temporary for storing the result
        target = self.new_temp(node.type)

        # Create the opcode and append to list
        opcode = binary_ops[node.op] + "_"+node.left.type.name
        inst = (opcode, node.left.gen_location, node.right.gen_location, target)
        self.current_block.append(inst)

        # Store location of the result on the node
        node.gen_location = target

    def visit_ExternDeclaration(self, node):
        self.visit(node.func_prototype)
        fn = node.func_prototype
        inst = ('extern_func',
                fn.name, fn.output_typename.type.name,
                ) + tuple(p.type.name for p in fn.parameters)
        self.current_block.append(inst)

    def visit_FunctionPrototype(self, node):
        pass

    def visit_Parameter(self, node):
        pass

    def visit_FunctionCall(self, node):
        for p in node.parameters:
            self.visit(p)
        target = self.new_temp(node.type)
        inst = ('call_func',
                node.fn.name,
                ) + tuple(p.gen_location for p in node.parameters) + (target,)
        self.current_block.append(inst)
        node.gen_location = target

    def visit_AssignStatement(self, node):
        self.visit(node.expression)
        self.visit(node.location)
        self.current_block.append(('store_{}'.format(node.type.name),
                          node.expression.gen_location,
                          node.location.name))

    def visit_ConstDeclaration(self, node):
        alloc_fmt = 'local_{}' if node.scope == 'local' else 'global_{}'
        self.current_block.append((alloc_fmt.format(node.expression.type.name), node.name))
        self.visit(node.expression)
        self.current_block.append(('store_{}'.format(node.expression.type.name),
                          node.expression.gen_location,
                          node.name))

    def visit_VarDeclaration(self, node):
        alloc_fmt = 'local_{}' if node.scope == 'local' else 'global_{}'
        self.current_block.append((alloc_fmt.format(node.typename.type.name), node.name))
        self.visit(node.expression)
        self.current_block.append(('store_{}'.format(node.expression.type.name),
                          node.expression.gen_location,
                          node.name))

    def visit_Typename(self, node):
        pass # nothing to do

    def visit_LoadLocation(self, node):
        target = self.new_temp(node.type)
        self.current_block.append(('load_{}'.format(node.type), node.name, target))
        node.gen_location = target

    def visit_StoreLocation(self, node):
        pass # nothing to do

    def visit_Literal(self,node):
        target = self.new_temp(node.type)
        self.current_block.append(('literal_'+node.type.name, node.value, target))
        node.gen_location = target

    def visit_ReturnStatement(self, node):
        self.visit(node.expression)
        self.current_block.append((
            'return_{}'.format(node.expression.type.name),
            node.expression.gen_location
        ))

    ##
    ## Block Generators
    ##

    def visit_Statements(self, node):
        # No need to chain together empty blocks
        if not isinstance(self.current_block, BasicBlock) or self.current_block.instructions:
            blk = BasicBlock()
            self.current_block.next_block = blk
            self.current_block = blk
        start = self.current_block
        for s in node.statement_list:
            self.visit(s)

    def visit_FunctionDeclaration(self, node):
        # Remember functions declared
        self.functions[node.prototype.name] = node.prototype

        # Create the new function block and link the current block to it
        func_block = FunctionBlock()
        self.current_block.next_block = func_block

        # Write the protype declaration to the instructions
        self.current_block = func_block
        self.visit(node.prototype)
        fn = node.prototype
        params = itertools.chain.from_iterable((p.name, p.type.name)
                                                for p in fn.parameters)
        inst = ('declare_func',
                fn.name, fn.output_typename.type.name,
                ) + tuple(params)
        func_block.instructions.append(inst)

        # Create the body block as a BasicBlock
        func_block.body = BasicBlock()
        self.current_block = func_block.body
        self.visit(node.statements)

        # Create the next block as a BasicBlock before we move on
        func_block.next_block = BasicBlock()
        self.current_block = func_block.next_block

    def visit_IfStatement(self, node):
        if_block = IfBlock()
        if_block.is_terminal = node.is_terminal
        self.current_block.next_block = if_block
        self.current_block = if_block
        # Set up the relation block
        self.visit(node.relation)
        if_block.gen_location = node.relation.gen_location
        # Set up the if block
        if_block.if_branch = BasicBlock()
        self.current_block = if_block.if_branch
        self.visit(node.if_body)
        if node.else_body:
            # set up the else block
            if_block.else_branch = BasicBlock()
            self.current_block = if_block.else_branch
            self.visit(node.else_body)
        self.current_block = if_block
        self.current_block.next_block = None # got set wrongly
        # Reset back to being on a BasicBlock
        if_block.next_block = BasicBlock()
        self.current_block = if_block.next_block

    def visit_WhileStatement(self, node):
        while_block = WhileBlock()
        self.current_block.next_block = while_block
        self.current_block = while_block
        # Set up the relation block
        self.visit(node.relation)
        while_block.gen_location = node.relation.gen_location
        # Set up the body of the while
        while_block.while_body = BasicBlock()
        self.current_block = while_block.while_body
        self.visit(node.while_body)
        self.current_block = while_block
        # Reset back to being on a BasicBlock
        while_block.next_block = BasicBlock()
        self.current_block = while_block.next_block


def generate_code(node):
    '''
    Generate SSA code from the supplied AST node.
    '''
    gen = GenerateCode()
    gen.visit(node)
    return gen.to_functions()

def main():
    import gonelex
    import goneparse
    import gonecheck
    import sys
    from errors import subscribe_errors, errors_reported
    from pprint import pformat
    lexer = gonelex.make_lexer()
    parser = goneparse.make_parser()
    with subscribe_errors(lambda msg: sys.stdout.write(msg+"\n")):
        program = parser.parse(open(sys.argv[1]).read())
        # Check the program
        gonecheck.check_program(program)
        # If no errors occurred, generate code
        if not errors_reported():
            functions = generate_code(program)
            for fn in functions:
                print(fn, '\n')

if __name__ == '__main__':
    main()
