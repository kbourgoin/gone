# goneblock.py
from pprint import pformat

from goneast import *

class _Block(object):
    def __init__(self):
        self.instructions = []
        self.next_block = None

    def _repr_instructions(self, indent):
        return pformat(self.instructions).replace(
            '\n', '\n  {}'.format(' ' * indent)
        )

    def __repr__(self, name=None, indent=0):
        ind = ' ' * (indent+2)
        return '{cls}:\n{ind}{ins}{nxt}'.format(
            cls='{}{}'.format(' ' * indent, name or self.__class__.__name__),
            ind=ind,
            ins=self._repr_instructions(indent),
            nxt='\n{}'.format(self.next_block.__repr__(indent=indent)) if self.next_block else '',
        )

    def append(self, instruction):
        self.instructions.append(instruction)

    def __iter__(self):
        return iter(self.instructions)


class BasicBlock(_Block):
    pass # nothing interesting here


class FunctionBlock(_Block):
    def __init__(self):
        super().__init__()
        # self.instructions will contain prototype declaration?
        self.body = None

    def __repr__(self, indent=0):
        _, name, *params, ret_type = self.instructions[0]
        if self.next_block:
            nxt = '\n{}'.format(self.next_block.__repr__(indent=indent))
        else:
            nxt = ''
        return 'Function: {name} {params} {ret}\n{bdy}{nxt}'.format(
            name=name,
            params=tuple(params),
            ret=ret_type,
            bdy=self.body.__repr__(indent=indent+2),
            nxt=nxt
        )


class IfBlock(_Block):
    def __init__(self):
        super().__init__()
        # self.instructions contains the relation
        self.if_branch = None
        self.else_branch = None

    def __repr__(self, indent=0):
        ind = ' ' * (indent+2)
        if self.else_branch:
            els = '\n{ind}Else:\n{els}'.format(
                ind=ind,
                els=self.else_branch.__repr__(indent=indent+4)
            )
        else:
            els = ''
        if self.next_block:
            nxt = '\n{}'.format(self.next_block.__repr__(indent=indent))
        else:
            nxt = ''
        return '{cls}:\n{ind}Relation:\n{ind}  {rel}\n{ind}Then:\n{thn}{els}{nxt}'.format(
            cls='{}{}'.format(' ' * indent, self.__class__.__name__),
            ind=' ' * (indent+2),
            rel=self._repr_instructions(indent+2),
            thn=self.if_branch.__repr__(indent=indent+4),
            els=els,
            nxt=nxt,
        )


class InitializerFunctionBlock(FunctionBlock):
    pass # so we know when we're looking at the special one


class WhileBlock(_Block):
    def __init__(self):
        super().__init__()
        self.while_body = None

    def __repr__(self, indent=0):
        ind = ' ' * (indent+2)
        if self.next_block:
            nxt = '\n{}'.format(self.next_block.__repr__(indent=indent))
        else:
            nxt = ''
        return '{cls}:\n{ind}Relation:\n{ind}  {rel}\n{ind}Body:\n{bdy}{nxt}'.format(
            cls='{}{}'.format(' ' * indent, self.__class__.__name__),
            ind=' ' * (indent+2),
            rel=self._repr_instructions(indent+2),
            bdy=self.while_body.__repr__(indent=indent+4),
            nxt=nxt,
        )
