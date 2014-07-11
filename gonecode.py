# gonecode.py
'''
Project 4 - Part 1
==================
Code generation for the Gone language.  In this project, you are going to turn
the AST into an intermediate machine code known as Single Static Assignment (SSA).
There are a few important parts you'll need to make this work.  Please read
carefully before beginning:

Single Static Assignment
========================
The first problem is how to decompose complex expressions into
something that can be handled more simply.  One way to do this is
to decompose all expressions into a sequence of simple assignments
involving binary or unary operations.

As an example, suppose you had a mathematical expression like this:

        2 + 3*4 - 5

Here is one possible way to decompose the expression into simple
operations:

        int_1 = 2
        int_2 = 3
        int_3 = 4
        int_4 = int_2 * int_3
        int_5 = int_1 + int_4
        int_6 = 5
        int_7 = int_5 - int_6

In this code, the int_n variables are simply temporaries used while
carrying out the calculation.  A critical feature of SSA is that such
temporary variables are only assigned once (single assignment) and
never reused.  Thus, if you were to evaluate another expression, you
would simply keep incrementing the numbers. For example, if you were
to evaluate 10+20+30, you would have code like this:

        int_8 = 10
        int_9 = 20
        int_10 = int_8 + int_9
        int_11 = 30
        int_12 = int_11 + int_11

SSA is meant to mimic the low-level instructions one might carry out
on a CPU.  For example, the above instructions might be translated to
low-level machine instructions (for a hypothetical CPU) like this:

        MOVI   #2, R1
        MOVI   #3, R2
        MOVI   #4, R3
        MUL    R2, R3, R4
        ADD    R4, R1, R5
        MOVI   #5, R6
        SUB    R5, R6, R7

Another benefit of SSA is that it is very easy to encode and
manipulate using simple data structures such as tuples. For example,
you could encode the above sequence of operations as a list like this:

       [
         ('movi', 2, 'int_1'),
         ('movi', 3, 'int_2'),
         ('movi', 4, 'int_3'),
         ('mul', 'int_2', 'int_3', 'int_4'),
         ('add', 'int_1', 'int_4', 'int_5'),
         ('movi', 5, 'int_6'),
         ('sub', 'int_5','int_6','int_7'),
       ]

Dealing with Variables
======================
In your program, you are probably going to have some variables that get
used and assigned different values.  For example:

       a = 10 + 20;
       b = 2 * a;
       a = a + 1;

In "pure SSA", all of your variables would actually be versioned just
like temporaries in the expressions above.  For example, you would
emit code like this:

       int_1 = 10
       int_2 = 20
       a_1 = int_1 + int_2
       int_3 = 2
       b_1 = int_3 * a_1
       int_4 = 1
       a_2 = a_1 + int_4
       ...

For reasons that will make sense later, we're going to treat declared
variables as memory locations and access them using load/store
instructions.  For example:

       int_1 = 10
       int_2 = 20
       int_3 = int_1 + int_2
       store(int_3, "a")
       int_4 = 2
       int_5 = load("a")
       int_6 = int_4 * int_5
       store(int_6,"b")
       int_7 = load("a")
       int_8 = 1
       int_9 = int_7 + int_8
       store(int_9, "a")

A Word About Types
==================
At a low-level, CPUs can only operate a few different kinds of
data such as ints and floats.  Because the semantics of the
low-level types might vary slightly, you'll need to take
some steps to handle them separately.

In our intermediate code, we're simply going to tag temporary variable
names and instructions with an associated type low-level type.  For
example:

      2 + 3*4          (ints)
      2.0 + 3.0*4.0    (floats)

The generated intermediate code might look like this:

      ('literal_int', 2, 'int_1')
      ('literal_int', 3, 'int_2')
      ('literal_int', 4, 'int_3')
      ('mul_int', 'int_2', 'int_3', 'int_4')
      ('add_int', 'int_1', 'int_4', 'int_5')

      ('literal_float', 2.0, 'float_1')
      ('literal_float', 3.0, 'float_2')
      ('literal_float', 4.0, 'float_3')
      ('mul_float', 'float_2', 'float_3', 'float_4')
      ('add_float', 'float_1', 'float_4', 'float_5')

Note: These types may or may not correspond directly to the type names
used in the input program.   For example, during translation, higher
level data structures would be reduced to a low-level operations.

Your Task
=========
Your task is as follows: Write a AST Visitor() class that takes an
Gone program and flattens it to a single sequence of SSA code instructions
represented as tuples of the form

       (operation, operands, ..., destination)

To start, your SSA code should only contain the following operators:

       ('alloc_type',varname)             # Allocate a variable of a given type
       ('literal_type', value, target)    # Load a literal value into target
       ('load_type', varname, target)     # Load the value of a variable into target
       ('store_type',source, varname)     # Store the value of source into varname
       ('add_type', left, right, target ) # target = left + right
       ('sub_type',left,right,target)     # target = left - right
       ('mul_type',left,right,target)     # target = left * right
       ('div_type',left,right,target)     # target = left / right  (integer truncation)
       ('uadd_type',source,target)        # target = +source
       ('uneg_type',source,target)        # target = -source
       ('print_type',source)              # Print value of source
'''

from collections import defaultdict

import goneast
import gonetype

from goneblock import BasicBlock, IfBlock, WhileBlock, FunctionBlock

# STEP 1: Map map operator symbol names such as +, -, *, /
# to actual opcode names 'add','sub','mul','div' to be emitted in
# the SSA code.   This is easy to do using dictionaries:

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

# STEP 2: Implement the following Node Visitor class so that it creates
# a sequence of SSA instructions in the form of tuples.  Use the
# above description of the allowed op-codes as a guide.
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
        entry_fn = FunctionBlock()
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

        output.append(entry_fn)
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
        self.current_block.append(('alloc_{}'.format(node.expression.type.name), node.name))
        self.visit(node.expression)
        self.current_block.append(('store_{}'.format(node.expression.type.name),
                          node.expression.gen_location,
                          node.name))

    def visit_VarDeclaration(self, node):
        self.current_block.append(('alloc_{}'.format(node.typename.type.name), node.name))
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
            'return__{}'.format(node.expression.type.name),
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
        inst = ('declare_func',
                fn.name, fn.output_typename.type.name,
                ) + tuple(p.type.name for p in fn.parameters)
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


# STEP 3: Testing
#
# Try running this program on the input file Project4/Tests/good.g and viewing
# the resulting SSA code sequence.
#
#     bash % python gonecode.py good.g
#     ... look at the output ...
#
# Sample output can be found in Project4/Tests/good.out.  While coding,
# you may want to break the code down into more manageable chunks.
# Think about unit testing.

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
