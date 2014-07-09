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

import goneast
from collections import defaultdict

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
         self.code = []

         # A list of external declarations (and types)
         self.externs = []

    def new_temp(self, typeobj):
         '''
         Create a new temporary variable of a given type.
         '''
         name = "__%s_%d" % (typeobj.name, self.versions[typeobj.name])
         self.versions[typeobj.name] += 1
         return name

    # You must implement visit_Nodename methods for all of the other
    # AST nodes.  In your code, you will need to make instructions
    # and append them to the self.code list.
    #
    # A few sample methods follow.  You may have to adjust depending
    # on the names of the AST nodes you've defined.

    def visit_Program(self, node):
        self.visit(node.statements)

    def visit_Statements(self, node):
        for s in node.statement_list:
            self.visit(s)

    def visit_PrintStatement(self,node):
        self.visit(node.expression)
        inst = ('print_'+node.expression.type.name,
                node.expression.gen_location)
        self.code.append(inst)

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
            self.code.append(inst)

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
        self.code.append(inst)

        # Store location of the result on the node
        node.gen_location = target

    def visit_ExternDeclaration(self, node):
        self.visit(node.func_prototype)
        fn = node.func_prototype
        inst = ('extern_func',
                fn.name, fn.output_typename.type.name,
                ) + tuple(p.type.name for p in fn.parameters)
        self.code.append(inst)

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
        self.code.append(inst)
        node.gen_location = target

    def visit_AssignStatement(self, node):
        self.visit(node.expression)
        self.visit(node.location)
        self.code.append(('store_{}'.format(node.type.name),
                          node.expression.gen_location,
                          node.location.name))

    def visit_ConstDeclaration(self, node):
        self.code.append(('alloc_{}'.format(node.expression.type.name), node.name))
        self.visit(node.expression)
        self.code.append(('store_{}'.format(node.expression.type.name),
                          node.expression.gen_location,
                          node.name))

    def visit_VarDeclaration(self, node):
        self.code.append(('alloc_{}'.format(node.typename.type.name), node.name))
        self.visit(node.expression)
        self.code.append(('store_{}'.format(node.expression.type.name),
                          node.expression.gen_location,
                          node.name))

    def visit_Typename(self, node):
        pass # nothing to do

    def visit_LoadLocation(self, node):
        target = self.new_temp(node.type)
        self.code.append(('load_{}'.format(node.type), node.name, target))
        node.gen_location = target

    def visit_StoreLocation(self, node):
        pass # nothing to do

    def visit_Literal(self,node):
        target = self.new_temp(node.type)
        self.code.append(('literal_'+node.type.name, node.value, target))
        node.gen_location = target

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

# ----------------------------------------------------------------------
#                       DO NOT MODIFY ANYTHING BELOW
# ----------------------------------------------------------------------
def generate_code(node):
    '''
    Generate SSA code from the supplied AST node.
    '''
    gen = GenerateCode()
    gen.visit(node)
    return gen

def main():
    import gonelex
    import goneparse
    import gonecheck
    import sys
    from errors import subscribe_errors, errors_reported
    lexer = gonelex.make_lexer()
    parser = goneparse.make_parser()
    with subscribe_errors(lambda msg: sys.stdout.write(msg+"\n")):
        program = parser.parse(open(sys.argv[1]).read())
        # Check the program
        gonecheck.check_program(program)
        # If no errors occurred, generate code
        if not errors_reported():
            code = generate_code(program)
            # Emit the code sequence
            for inst in code.code:
                print(inst)

if __name__ == '__main__':
    main()
