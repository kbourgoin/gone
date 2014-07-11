# gonellvm.py
from collections import ChainMap

import goneast

# LLVM imports. Don't change this.
from llvm import core
from llvm.core import Module, Builder, Function, Type, Constant, GlobalVariable

int_type    = Type.int()         # 32-bit integer
float_type  = Type.double()      # 64-bit float
bool_type   = Type.int(1)        # 1-bit bools
string_type = Type.pointer(Type.int(8)) # using c-style strings

typemap = {
    'int' : int_type,
    'float' : float_type,
    'string' : string_type,
    'bool': bool_type,
}

class LLVMBlockVisitor(goneast.NodeVisitor):

    def __init__(self, name="module"):
        self.llvm = GenerateLLVM()
        self._next_block = 0

    def generate_llvm(self, functions):
        # Make sure the function signatures exist
        for fn in functions:
            self.llvm.declare_function(fn)

        # Actually make the blocks for the functions
        for fn in functions:
            self.visit(fn)

    def visit_BasicBlock(self, block):
        print('visit_BasicBlock')
        # Start a new block
        block_llvm = self.llvm.function.append_basic_block('bl')
        self.llvm.builder.branch(block_llvm)
        self.llvm.builder.position_at_end(block_llvm)
        # Add instructions and move on
        self.llvm.generate_code(block.instructions)
        self.visit(block.next_block)

    def visit_FunctionBlock(self, block, initializer_fn=False):
        # Set up the builder to the top of this function
        name = block.instructions[0][1]
        self.llvm.function = self.llvm.vars[name]
        start_llvm = self.llvm.function.append_basic_block('start')
        self.llvm.builder = Builder.new(start_llvm)

        # Make some scope for the function and add parameters
        if not initializer_fn:
            self.llvm.vars = self.llvm.vars.new_child()
        function = self.llvm.vars[name]
        for arg in function.args:
            arg_v = self.llvm.builder.alloca(arg.type, name=arg.name)
            self.llvm.builder.store(arg, arg_v)
            self.llvm.vars[arg.name] = arg_v

        # Visit the block like normal
        self.visit(block.body)
        if not initializer_fn:
            self.llvm.vars = self.llvm.vars.parents # pop local scope off

    def visit_IfBlock(self, block):
        print('visit_IfBlock')
        # Make blocks
        if_llvm = self.llvm.function.append_basic_block('if')
        then_llvm = self.llvm.function.append_basic_block('tt')
        if block.else_branch:
            else_llvm = self.llvm.function.append_basic_block('ff')
        if block.is_terminal:
            merge_llvm = None
        else:
            merge_llvm = self.llvm.function.append_basic_block('fi')

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
        if not block.is_terminal:
            self.llvm.builder.branch(merge_llvm)

        # Else Block
        if block.else_branch:
            self.llvm.builder.position_at_end(else_llvm)
            self.visit(block.else_branch)
            if not block.is_terminal:
                self.llvm.builder.branch(merge_llvm)

        # Finish at the end of the merge block
        if block.is_terminal:
            self.llvm.builder.position_at_end(if_llvm) # shouldn't matter
        else:
            self.llvm.builder.position_at_end(merge_llvm)
            self.visit(block.next_block)

    def visit_InitializerFunctionBlock(self, block, initializer_fn=True):
        self.visit_FunctionBlock(block, initializer_fn=True)

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
        self.vars = ChainMap()
        self.temps = {}
        self.declare_runtime_library()

    def declare_runtime_library(self):
        self.runtime = {}
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

    def declare_function(self, func_block):
        """Declare a Function and add it to self.vars"""
        _, name, ret_type, *args = func_block.instructions[0]
        args = [] if args == [[]] else args
        if not ret_type:
            ret_type = args[0]
            arg_types = []
        else:
            arg_types = [typemap[t] for t in args[1::2]]
        ret_type = typemap[ret_type]
        function = Function.new(
            self.module, Type.function(ret_type, arg_types, False), name
        )
        for i, argname in enumerate(args[0::2]):
            function.args[i].name = argname
        self.vars[name] = function

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

    # Allocation of global variables
    def emit_global_int(self, name):
        var = GlobalVariable.new(self.module, int_type, name)
        var.initializer = Constant.int(int_type, 0)
        self.vars[name] = var

    def emit_global_float(self, name):
        var = GlobalVariable.new(self.module, float_type, name)
        var.initializer = Constant.real(float_type, 0)
        self.vars[name] = var

    def emit_global_bool(self, name):
        var = GlobalVariable.new(self.module, bool_type, name)
        var.initializer = Constant.int(bool_type, 0)
        self.vars[name] = var

    def emit_global_string(self, name):
        var = GlobalVariable.new(self.module, string_type, name)
        var.initializer = Constant.null(string_type)
        self.vars[name] = var

    # Allocation of local variables
    def emit_local_int(self, name):
        self.vars[name] = self.builder.alloca(int_type, name=name)

    def emit_local_float(self, name):
        self.vars[name] = self.builder.alloca(float_type, name=name)

    def emit_local_bool(self, name):
        self.vars[name] = self.builder.alloca(bool_type, name=name)

    # Load/Store variables
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

        self.temps[target] = self.builder.or_(self.temps[left], self.temps[right])

    # Binary && operator
    def emit_and_bool(self, left, right, target):
        self.temps[target] = self.builder.and_(self.temps[left], self.temps[right])

    # Return statements
    def emit_return_int(self, target):
        self.builder.ret(self.temps[target])

    def emit_return_float(self, target):
        self.builder.ret(self.temps[target])

    def emit_return_bool(self, target):
        self.builder.ret(self.temps[target])


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
            functions = gonecode.generate_code(program)
            # Emit the code sequence
            bv = LLVMBlockVisitor()
            bv.generate_llvm(functions)
            print(bv.llvm.module)

            # Verify and run function that was created during code generation
            print(":::: RUNNING ::::")
            bv.llvm.function.verify()
            llvm_executor = ExecutionEngine.new(bv.llvm.module)
            llvm_executor.run_function(bv.llvm.vars['__start'], [])

if __name__ == '__main__':
    main()
