import os
from collections import ChainMap

from goneblock import FunctionBlock, IfBlock, WhileBlock

# C stdlib functions we need
_hack_fns = {
    'putchar': lambda x: os.write(1, chr(x).encode('ascii'))
}

class Interpreter(object):
    def __init__(self, functions, name="module"):
        self.vars = ChainMap()
        self.vars.update({fn.instructions[0][1]: fn for fn in functions})

        # List of Python modules to search for external decls
        external_libs = [ 'math', 'os' ]
        self.external_libs = [ __import__(name) for name in external_libs]

    def run(self, function, *args):
        '''
        Run intermediate code in the interpreter.  ircode is a list
        of instruction tuples.  Each instruction (opcode, *args) is
        dispatched to a method self.run_opcode(*args)
        '''
        # Create local scope and add args to it
        self.vars = self.vars.new_child()
        if args:
            argnames = function.instructions[0][3::2]
            for i, argname in enumerate(argnames):
                self.vars[argname] = self.vars[args[i]]

        # Run the body
        retval = self.run_block(function.body)
        self.vars = self.vars.parents # pop off scope
        return retval

    def run_block(self, block):
        kind = block.__class__.__name__
        runner = getattr(self, 'run_{}'.format(kind), None)
        if runner:
            return runner(block)
        else:
            print("Warning: No run_{}() method".format(kind))

    def run_BasicBlock(self, block):
        retval = self.run_instructions(block.instructions)
        if retval is not None:
            return retval
        elif block.next_block:
            return self.run_block(block.next_block)

    def run_IfBlock(self, block):
        # Run the test then it's a simple if/else here
        self.run_instructions(block.instructions)
        retval = None
        if self.vars[block.gen_location]:
            retval = self.run_BasicBlock(block.if_branch)
        elif block.else_branch:
            retval = self.run_BasicBlock(block.else_branch)

        if retval is not None:
            return retval
        if block.next_block:
            return self.run_block(block.next_block)

    def run_WhileBlock(self, block):
        def run_test():
            self.run_instructions(block.instructions)
            return self.vars[block.gen_location]
        while run_test():
            retval = self.run_BasicBlock(block.while_body)
            if retval is not None:
                return retval
        if block.next_block:
            return self.run_block(block.next_block)

    def run_instructions(self, instructions):
        """Run a set of instructions in the interpreter"""
        for op in instructions:
            opcode = op[0]
            if hasattr(self, "run_"+opcode):
                retval = getattr(self, "run_"+opcode)(*op[1:])
                if retval is not None:
                    return retval
            else:
                # match a bit fuzzier
                parts = opcode.split('_')
                if hasattr(self, "run_"+parts[0]):
                    retval = getattr(self, "run_"+parts[0])(*op[1:])
                    if retval is not None:
                        return retval
                else:
                    print("Warning: No run_"+opcode+"() method")


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

    def run_global(self, target):
        self.vars.maps[-1][target] = None

    def run_local(self, target):
        self.vars[target] = None

    def run_extern_func(self, name, ret_type, *params):
        fn = None
        # Check imported libs
        for exlib in self.external_libs:
            fn = getattr(exlib, name, None)
            if fn is not None:
                break
        # Check our map 'o hacks
        if fn is None:
            fn = _hack_fns.get(name, None)

        # save it or raise an error
        if fn is not None:
            self.vars[name] = lambda params: fn(*(self.vars[p] for p in params))
        else:
            raise Exception('Unable to find {}. We may need a hack fn'.format(name))

    def run_call_func(self, name, *params):
        *params, target = params
        fn = self.vars[name]
        if isinstance(fn, FunctionBlock):
            res = self.run(fn, *params)
        else:
            res = fn(params)
        self.vars[target] = res

    def run_literal(self, value, target):
        self.vars[target] = value

    def run_print(self, source):
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

    def run_return(self, source):
        return self.vars[source]

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
            functions = gonecode.generate_code(program)
            functions = list(functions) # just be sure it doesn't exhause
            interpreter = Interpreter(functions)
            interpreter.run(functions[0]) # first func is the place to start

if __name__ == '__main__':
    main()
