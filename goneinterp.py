# goneinterp.py
'''
Project 4 (Part 2) :  Write an Interpreter
==========================================

Once you've got your compiler emitting intermediate code, you should
be able to write a simple interpreter that runs the code.  This
can be useful for prototyping the execution environment, testing,
and other tasks involving the generated code.

Your task is simple, extend the Interpreter class below so that it
can run the code you generated in part 1.  The comments and docstrings
in the class describe it in further details.

When your done, you should be able to run simple programs by
typing:

    bash % python goneinterp.py someprogram.g
'''

class Interpreter(object):
    '''
    Runs an interpreter on the SSA intermediate code generated for
    your compiler.   The implementation idea is as follows.  Given
    a sequence of instruction tuples such as:

         code = [
              ('literal_int', 1, '_int_1'),
              ('literal_int', 2, '_int_2'),
              ('add_int', '_int_1', '_int_2, '_int_3')
              ('print_int', '_int_3')
              ...
         ]

    The class executes methods self.run_opcode(args).  For example:

             self.run_literal_int(1, '_int_1')
             self.run_literal_int(2, '_int_2')
             self.run_add_int('_int_1', '_int_2', '_int_3')
             self.run_print_int('_int_3')

    To store the values of variables created in the intermediate
    language, simply use a dictionary.

    For external function declarations, allow specific Python modules
    (e.g., math, os, etc.) to be registered with the interpreter.
    We don't have namespaces in the source language so this is going
    to be a bit of sick hack.
    '''
    def __init__(self,name="module"):
        # Dictionary of currently defined variables
        self.vars = {}

        # List of Python modules to search for external decls
        external_libs = [ 'math', 'os' ]
        self.external_libs = [ __import__(name) for name in external_libs ]

    def run(self, ircode):
        '''
        Run intermediate code in the interpreter.  ircode is a list
        of instruction tuples.  Each instruction (opcode, *args) is
        dispatched to a method self.run_opcode(*args)
        '''
        for op in ircode:
            opcode = op[0]
            if hasattr(self, "run_"+opcode):
                getattr(self, "run_"+opcode)(*op[1:])
            else:
                # match a bit fuzzier
                parts = opcode.split('_')
                if hasattr(self, "run_"+parts[0]):
                    getattr(self, "run_"+parts[0])(*op[1:])
                else:
                    print("Warning: No run_"+opcode+"() method")

    # YOU MUST IMPLEMENT:  Methods for different opcodes.  A few sample
    # opcodes are shown below to get you started.


    def run_add(self, left, right, target):
        self.vars[target] = self.vars[left] + self.vars[right]

    def run_sub(self, left, right, target):
        self.vars[target] = self.vars[left] - self.vars[right]

    def run_mul(self, left, right, target):
        self.vars[target] = self.vars[left] * self.vars[right]

    def run_div(self, left, right, target):
        self.vars[target] = self.vars[left] / self.vars[right]

    def run_uadd(self, source, target):
        self.vars[target] = +self.vars[source]

    def run_usub(self, source, target):
        self.vars[target] = -self.vars[source]

    def run_load(self, source, target):
        self.vars[target] = self.vars[source]

    def run_store(self, source, target):
        self.vars[target] = self.vars[source]

    def run_alloc(self, target):
        self.vars[target] = None

    def run_extern_func(self, name, ret_type, *params):
        for exlib in self.external_libs:
            fn = getattr(exlib, name, None)
            if fn is not None:
                self.vars[name] = lambda params: fn(*(self.vars[p] for p in params))
                return

    def run_call_func(self, name, *params):
        *params, target = params
        self.vars[target] = self.vars[name](params)

    def run_literal(self, value, target):
        '''
        Create a literal integer value
        '''
        self.vars[target] = value

    def run_print(self, source):
        '''
        Output an integer value.
        '''
        print(self.vars[source])

    def run_eq(self, left, right, target):
        self.vars[target] = self.vars[left] == self.vars[right]

    def run_neq(self, left, right, target):
        self.vars[target] = self.vars[left] != self.vars[right]

    def run_gt(self, left, right, target):
        self.vars[target] = self.vars[left] > self.vars[right]

    def run_gte(self, left, right, target):
        self.vars[target] = self.vars[left] > self.vars[right]

    def run_lt(self, left, right, target):
        self.vars[target] = self.vars[left] < self.vars[right]

    def run_lte(self, left, right, target):
        self.vars[target] = self.vars[left] <= self.vars[right]

    def run_or(self, left, right, target):
        self.vars[target] = self.vars[left] or self.vars[right]

    def run_and(self, left, right, target):
        self.vars[target] = self.vars[left] and self.vars[right]

    def run_not(self, source, target):
        self.vars[target] = not self.vars[source]


    # You must implement the rest of the operations below

# ----------------------------------------------------------------------
#                       DO NOT MODIFY ANYTHING BELOW
# ----------------------------------------------------------------------
def main():
    import gonelex
    import goneparse
    import gonecheck
    import gonecode
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
            code = gonecode.generate_code(program)
            interpreter = Interpreter()
            interpreter.run(code.code)

if __name__ == '__main__':
    main()





