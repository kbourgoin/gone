# goneblock.py
'''
Project 7: Basic Blocks and Control Flow
----------------------------------------
This file defines classes and functions for creating and navigating
basic blocks.  You need to write all of the code needed yourself.

See Exercise 7.
'''

from pprint import pformat

from goneast import *

class _Block(object):
    def __init__(self):
        self.instructions = []
        self.next_block = None

    def __repr__(self):
        out = '{}: {}'.format(self.__class__.__name__, pformat(self.instructions))
        if self.next_block:
            out += '\n\n{}'.format(self.next_block)
        return out

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

    def __repr__(self):
        out = self.__class__.__name__
        # Instructions are the relation test
        inst_str = pformat(self.instructions)
        inst_str = inst_str.replace('\n', '\n\t    ')
        out += '\n  Prototype: {}'.format(inst_str)
        # Print out the body
        body = self.body.__repr__()
        body = body.replace('\n', '\n  ')
        out += '\n  Body: {}'.format(body)
        # There may be nothing afterwards
        if self.next_block:
            out += '\n\n{}'.format(self.next_block)
        return out


class IfBlock(_Block):
    def __init__(self):
        super().__init__()
        # self.instructions contains the relation
        self.if_branch = None
        self.else_branch = None

    def __repr__(self):
        out = self.__class__.__name__
        # Instructions are the relation test
        inst_str = pformat(self.instructions)
        inst_str = inst_str.replace('\n', '\n\t    ')
        out += '\n  Relation: {}'.format(inst_str)
        # If branch is always present
        if_str = self.if_branch.__repr__()
        if_str = if_str.replace('\n', '\n  ')
        out += '\n  If: {}'.format(if_str)
        # Else may not be
        if self.else_branch:
            else_str = self.else_branch.__repr__()
            else_str = else_str.replace('\n', '\n  ')
            out += '\n  Else: {}'.format(else_str)
        # There may be nothing afterwards
        if self.next_block:
            out += '\n\n{}'.format(self.next_block)
        return out


class WhileBlock(_Block):
    def __init__(self):
        super().__init__()
        self.while_body = None

    def __repr__(self):
        out = self.__class__.__name__
        # Instructions are the relation test
        inst_str = pformat(self.instructions)
        inst_str = inst_str.replace('\n', '\n\t    ')
        out += '\n  Relation: {}'.format(inst_str)
        # If branch is always present
        body = self.while_body.__repr__()
        body = body.replace('\n', '\n  ')
        out += '\n  Body: {}'.format(body)
        # There may be nothing afterwards
        if self.next_block:
            out += '\n\n{}'.format(self.next_block)
        return out
