# gonellvm.py
'''
Project 5 : Generate LLVM
=========================
In this project, you're going to translate the SSA intermediate code
into LLVM IR.    Once you're done, your code will be runnable.  It
is strongly advised that you do *all* of the steps of Exercise 5
prior to starting this project.   Don't rush into it.

The basic idea of this project is exactly the same as the interpreter
in Project 4.   You'll make a class that walks through the instruction
sequence and triggers a method for each kind of instruction.  Instead
of running the instruction however, you'll be generating LLVM
instructions.

Further instructions are contained in the comments.
'''

import goneast

# LLVM imports. Don't change this.
from llvm import core
from llvm.core import Module, Builder, Function, Type, Constant, GlobalVariable

# Declare the LLVM type objects that you want to use for the types
# in our intermediate code.  Basically, you're going to need to
# declare your integer, float, and string types here.

int_type    = Type.int()         # 32-bit integer
float_type  = Type.double()      # 64-bit float
bool_type   = Type.int(1)        # 1-bit bools
string_type = Type.pointer(Type.int(8)) # using c-style strings

# A dictionary that maps the typenames used in IR to the corresponding
# LLVM types defined above.   This is mainly provided for convenience
# so you can quickly look up the type object given its type name.
typemap = {
    'int' : int_type,
    'float' : float_type,
    'string' : string_type,
    'bool': bool_type,
}

# The following class is going to generate the LLVM instruction stream.
# The basic features of this class are going to mirror the experiments
# you tried in Exercise 5.  The execution module is very similar
# to the interpreter written in Project 4.  See specific comments
# in the class.

class LLVMBlockVisitor(goneast.NodeVisitor):

    def __init__(self, name="module"):
        self.llvm = GenerateLLVM()
        self._next_block = 0

    def generate_llvm(self, first_block):
        # Start a basic block to write to
        start_llvm = self.llvm.function.append_basic_block('start')
        self.llvm.builder = Builder.new(start_llvm)

         # Visit all nodes
        self.visit(first_block)

        # Return nothing
        self.llvm.builder.ret_void()

    def visit_BasicBlock(self, block):
        print('visit_BasicBlock')
        # Start a new block
        block_llvm = self.llvm.function.append_basic_block('bl')
        self.llvm.builder.branch(block_llvm)
        self.llvm.builder.position_at_end(block_llvm)
        # Add instructions and move on
        self.llvm.generate_code(block.instructions)
        self.visit(block.next_block)

    def visit_IfBlock(self, block):
        print('visit_IfBlock')
        # Make blocks
        if_llvm = self.llvm.function.append_basic_block('if')
        then_llvm = self.llvm.function.append_basic_block('it')
        merge_llvm = self.llvm.function.append_basic_block('fi')
        if block.else_branch:
            else_llvm = self.llvm.function.append_basic_block('ff')

        # Current block should jump to the conditional
        self.llvm.builder.branch(if_llvm)

        # Conditional Block
        self.llvm.builder.position_at_end(if_llvm)
        self.llvm.generate_code(block.instructions)
        if block.else_branch:
            self.llvm.builder.cbranch(self.llvm.temps[block.gen_location],
                                      then_llvm, else_llvm)
        else:
            self.llvm.builder.cbranch(self.llvm.temps[block.gen_location],
                                      then_llvm, merge_llvm)

        # Then Block
        self.llvm.builder.position_at_end(then_llvm)
        self.visit(block.if_branch)
        self.llvm.builder.branch(merge_llvm)

        # Else Block
        if block.else_branch:
            self.llvm.builder.position_at_end(else_llvm)
            self.visit(block.else_branch)
            self.llvm.builder.branch(merge_llvm)

        # Finish at the end of the merge block
        self.llvm.builder.position_at_end(merge_llvm)
        self.visit(block.next_block)

    def visit_WhileBlock(self, block):
        print('visit_WhileBlock')
        # Make blocks
        test_llvm = self.llvm.function.append_basic_block('wh')
        body_llvm = self.llvm.function.append_basic_block('wb')
        merge_llvm = self.llvm.function.append_basic_block('hw')

        # Current block should jump to the conditional
        self.llvm.builder.branch(test_llvm)

        # Conditional Block
        self.llvm.builder.position_at_end(test_llvm)
        self.llvm.generate_code(block.instructions)
        self.llvm.builder.cbranch(self.llvm.temps[block.gen_location],
                                  body_llvm, merge_llvm)

        # While Body
        self.llvm.builder.position_at_end(body_llvm)
        self.visit(block.while_body)
        self.llvm.builder.branch(test_llvm)

        # Finish at the end of the merge block
        self.llvm.builder.position_at_end(merge_llvm)
        self.visit(block.next_block)


class GenerateLLVM(object):
    def __init__(self,name="module"):
        self.module = Module.new(name)
        self.function = Function.new(self.module,
                                     Type.function(Type.void(), [], False),
                                     "main")
        self.vars = {}
        self.temps = {}
        self.declare_runtime_library()

    def declare_runtime_library(self):
        """
        Certain functions such as I/O and string handling are often easier
        to implement in an external C library.  This method should make
        the LLVM declarations for any runtime functions to be used
        during code generation.    Please note that runtime function
        functions are implemented in C in a separate file gonert.c
        """
        self.runtime = {}

        # Declare printing functions
        self.runtime['_print_int'] = Function.new(self.module,
                                                 Type.function(Type.void(), [int_type], False),
                                                 "_print_int")

        self.runtime['_print_float'] = Function.new(self.module,
                                                   Type.function(Type.void(), [float_type], False),
                                                   "_print_float")

        self.runtime['_print_bool'] = Function.new(self.module,
                                                   Type.function(Type.void(), [bool_type], False),
                                                   "_print_bool")

        self.runtime['_print_string'] = Function.new(self.module,
                                                   Type.function(Type.void(), [string_type], False),
                                                   "_print_string")

    def generate_code(self, ircode):
        for op in ircode:
            opcode = op[0]
            if hasattr(self, "emit_"+opcode):
                getattr(self, "emit_"+opcode)(*op[1:])
            else:
                print("Warning: No emit_"+opcode+"() method")

    # Creation of literal values.  Simply define as LLVM constants.
    def emit_literal_int(self, value, target):
        self.temps[target] = Constant.int(int_type, value)

    def emit_literal_float(self, value, target):
        self.temps[target] = Constant.real(float_type, value)

    def emit_literal_bool(self, value, target):
        self.temps[target] = Constant.int(bool_type, int(value))

    def emit_literal_string(self, value, target):
        pass

    # Allocation of variables.  Declare as global variables and set to
    # a sensible initial value.
    def emit_alloc_int(self, name):
        var = GlobalVariable.new(self.module, int_type, name)
        var.initializer = Constant.int(int_type, 0)
        self.vars[name] = var

    def emit_alloc_float(self, name):
        var = GlobalVariable.new(self.module, float_type, name)
        var.initializer = Constant.real(float_type, 0)
        self.vars[name] = var

    def emit_alloc_bool(self, name):
        var = GlobalVariable.new(self.module, bool_type, name)
        var.initializer = Constant.int(bool_type, 0)
        self.vars[name] = var

    def emit_alloc_string(self, name):
        var = GlobalVariable.new(self.module, string_type, name)
        var.initializer = Constant.null(string_type)
        self.vars[name] = var


    # Load/store instructions for variables.  Load needs to pull a
    # value from a global variable and store in a temporary. Store
    # goes in the opposite direction.
    def emit_load_int(self, name, target):
        self.temps[target] = self.builder.load(self.vars[name], target)

    def emit_load_float(self, name, target):
        self.temps[target] = self.builder.load(self.vars[name], target)

    def emit_load_bool(self, name, target):
        self.temps[target] = self.builder.load(self.vars[name], target)

    def emit_load_string(self, name, target):
        self.temps[target] = self.builder.load(self.vars[name], target)

    def emit_store_int(self, source, target):
        self.builder.store(self.temps[source], self.vars[target])

    def emit_store_float(self, source, target):
        self.builder.store(self.temps[source], self.vars[target])

    def emit_store_bool(self, source, target):
        self.builder.store(self.temps[source], self.vars[target])

    def emit_store_string(self, source, target):
        self.builder.store(self.temps[source], self.vars[target])


    # Binary + operator
    def emit_add_int(self, left, right, target):
        self.temps[target] = self.builder.add(self.temps[left], self.temps[right], target)

    def emit_add_float(self, left, right, target):
        self.temps[target] = self.builder.fadd(self.temps[left], self.temps[right], target)

    # Binary - operator
    def emit_sub_int(self, left, right, target):
        self.temps[target] = self.builder.sub(self.temps[left], self.temps[right], target)

    def emit_sub_float(self, left, right, target):
        self.temps[target] = self.builder.fsub(self.temps[left], self.temps[right], target)

    # Binary * operator
    def emit_mul_int(self, left, right, target):
        self.temps[target] = self.builder.mul(self.temps[left], self.temps[right], target)

    def emit_mul_float(self, left, right, target):
        self.temps[target] = self.builder.fmul(self.temps[left], self.temps[right], target)

    # Binary / operator
    def emit_div_int(self, left, right, target):
        self.temps[target] = self.builder.sdiv(self.temps[left], self.temps[right], target)

    def emit_div_float(self, left, right, target):
        self.temps[target] = self.builder.fdiv(self.temps[left], self.temps[right], target)

    # Unary + operator
    def emit_uadd_int(self, source, target):
        self.temps[target] = self.builder.add(
            Constant.int(int_type, 0),
            self.temps[source],
            target
        )

    def emit_uadd_float(self, source, target):
        self.temps[target] = self.builder.fadd(
            Constant.real(float_type, 0.0),
            self.temps[source],
            target
        )

    # Unary - operator
    def emit_usub_int(self, source, target):
        self.temps[target] = self.builder.sub(
            Constant.int(int_type, 0),
            self.temps[source],
            target
        )

    def emit_usub_float(self, source, target):
        self.temps[target] = self.builder.fsub(
            Constant.real(float_type, 0.0),
            self.temps[source],
            target
        )

    # Unary ! operator
    def emit_not_bool(self, source, target):
        self.temps[target] = self.builder.not_(self.temps[source])

    # Print statements
    def emit_print_int(self, source):
        self.builder.call(self.runtime['_print_int'], [self.temps[source]])

    def emit_print_float(self, source):
        self.builder.call(self.runtime['_print_float'], [self.temps[source]])

    def emit_print_bool(self, source):
        self.builder.call(self.runtime['_print_bool'], [self.temps[source]])

    def emit_print_string(self, source):
        self.builder.call(self.runtime['_print_string'], [self.temps[source]])

    # Extern function declaration.
    def emit_extern_func(self, name, rettypename, *parmtypenames):
        rettype = typemap[rettypename]
        parmtypes = [typemap[pname] for pname in parmtypenames]
        func_type = Type.function(rettype, parmtypes, False)
        self.vars[name] = Function.new(self.module, func_type, name)

    # Call an external function.
    def emit_call_func(self, name, *params):
        *params, target = params
        params = [self.temps[p] for p in params]
        self.temps[target] = self.builder.call(self.vars[name], params)

    # Binary == operator

    def emit_eq_int(self, left, right, target):
        self.temps[target] = self.builder.icmp(core.ICMP_EQ, self.temps[left], self.temps[right])

    def emit_eq_float(self, left, right, target):
        self.temps[target] = self.builder.fcmp(core.FCMP_UEQ, self.temps[left], self.temps[right])

    def emit_eq_bool(self, left, right, target):
        self.temps[target] = self.builder.icmp(core.ICMP_EQ, self.temps[left], self.temps[right])

    # Binary != operator

    def emit_neq_int(self, left, right, target):
        self.temps[target] = self.builder.icmp(core.ICMP_NE, self.temps[left], self.temps[right])

    def emit_neq_float(self, left, right, target):
        self.temps[target] = self.builder.fcmp(core.FCMP_UNE, self.temps[left], self.temps[right])

    def emit_neq_bool(self, left, right, target):
        self.temps[target] = self.builder.icmp(core.ICMP_NE, self.temps[left], self.temps[right])

    # Binary > operator

    def emit_gt_int(self, left, right, target):
        self.temps[target] = self.builder.icmp(core.ICMP_SGT, self.temps[left], self.temps[right])

    def emit_gt_float(self, left, right, target):
        self.temps[target] = self.builder.fcmp(core.FCMP_UGT, self.temps[left], self.temps[right])

    def emit_gt_bool(self, left, right, target):
        self.temps[target] = self.builder.icmp(core.ICMP_SGT, self.temps[left], self.temps[right])

    # Binary >= operator

    def emit_gte_int(self, left, right, target):
        self.temps[target] = self.builder.icmp(core.ICMP_SGE, self.temps[left], self.temps[right])

    def emit_gte_float(self, left, right, target):
        self.temps[target] = self.builder.fcmp(core.FCMP_UGE, self.temps[left], self.temps[right])

    def emit_gte_bool(self, left, right, target):
        self.temps[target] = self.builder.icmp(core.ICMP_SGE, self.temps[left], self.temps[right])

    # Binary < operator

    def emit_lt_int(self, left, right, target):
        self.temps[target] = self.builder.icmp(core.ICMP_SLT, self.temps[left], self.temps[right])

    def emit_lt_float(self, left, right, target):
        self.temps[target] = self.builder.fcmp(core.FCMP_ULT, self.temps[left], self.temps[right])

    def emit_lt_bool(self, left, right, target):
        self.temps[target] = self.builder.icmp(core.ICMP_SLT, self.temps[left], self.temps[right])

    # Binary <= operator

    def emit_lte_int(self, left, right, target):
        self.temps[target] = self.builder.icmp(core.ICMP_SLE, self.temps[left], self.temps[right])

    def emit_lte_float(self, left, right, target):
        self.temps[target] = self.builder.fcmp(core.FCMP_ULE, self.temps[left], self.temps[right])

    def emit_lte_bool(self, left, right, target):
        self.temps[target] = self.builder.icmp(core.ICMP_SLE, self.temps[left], self.temps[right])

    # Binary || operator

    def emit_or_bool(self, left, right, target):
        self.temps[target] = self.builder.or_(self.temps[left], self.temps[right])

    # Binary && operator

    def emit_and_bool(self, left, right, target):
        self.temps[target] = self.builder.and_(self.temps[left], self.temps[right])


#######################################################################
#                 DO NOT MODIFY ANYTHING BELOW HERE
#######################################################################

def main():
    import gonelex
    import goneparse
    import gonecheck
    import gonecode
    import goneblock
    import sys
    import ctypes
    from errors import subscribe_errors, errors_reported
    from llvm.ee import ExecutionEngine

    # Load the Gone runtime library (see Makefile)
    ctypes._dlopen('./gonert.so', ctypes.RTLD_GLOBAL)

    lexer = gonelex.make_lexer()
    parser = goneparse.make_parser()
    with subscribe_errors(lambda msg: sys.stdout.write(msg+"\n")):
        program = parser.parse(open(sys.argv[1]).read())
        # Check the program
        gonecheck.check_program(program)
        # If no errors occurred, generate code
        if not errors_reported():
            blocks = gonecode.generate_code(program)
            # Emit the code sequence
            bv = LLVMBlockVisitor()
            bv.generate_llvm(blocks.first_block)
            print(bv.llvm.module)

            # Verify and run function that was created during code generation
            print(":::: RUNNING ::::")
            bv.llvm.function.verify()
            llvm_executor = ExecutionEngine.new(bv.llvm.module)
            llvm_executor.run_function(bv.llvm.function, [])

if __name__ == '__main__':
    main()







