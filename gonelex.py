# gonelex.py
r'''
Project 1 - Write a Lexer
=========================
In the first project, you are going to write a simple lexer for the
Gone language. The project is presented as code that you must
read and complete (this file).  Please read the complete contents of
this file and carefully complete the steps indicated by comments.

Overview:
---------
The process of lexing is that of taking input text and breaking it
down into a stream of tokens. Each token is like a valid word from the
dictionary.  Essentially, the role of the lexer is to simply make sure
that the input text consists of valid symbols and tokens prior to any
further processing related to parsing.

Each token is defined by a regular expression.  Thus, your primary task
in this first project is to define a set of regular expressions for
the language.  The actual job of lexing will be handled by PLY
(http://www.dabeaz.com/ply).

Specification:
--------------
Your lexer must recognize the following symbols and tokens.  The name
on the left is the token name, the value on the right is the matching
text.

Reserved Keywords:
    CONST   : 'const'
    VAR     : 'var'
    PRINT   : 'print'
    LEN     : 'len'
    FUNC    : 'func'
    EXTERN  : 'extern'

Identifiers:   (Same rules as for Python)
    ID      : Text starting with a letter or '_', followed by any number
              number of letters, digits, or underscores.

Operators and Delimiters:
    PLUS     : '+'
    MINUS    : '-'
    TIMES    : '*'
    DIVIDE   : '/'
    ASSIGN   : '='
    SEMI     : ';'
    LPAREN   : '('
    RPAREN   : ')'
    LBRACE   : '{'
    RBRACE   : '}'
    COMMA    : ','

Literals:
    INTEGER : '123'
    FLOAT   : '1.234'
              '1.234e1'
              '1.234e+1'
              '1.234e-1'
              '1e2'
              '.1234'
              '1234.'

    STRING  : '"Hello World"'

Comments:  To be ignored by your lexer
     //             Skips the rest of the line
     /* ... */      Skips a block (no nesting allowed)

Errors: Your lexer must report the following error messages:

     lineno: Illegal char 'c'
     lineno: Unterminated string
     lineno: Unterminated comment

Testing
-------
For initial development, try running the lexer on a sample input file
such as:

     bash % python gonelex.py sample.g

Carefully study the output of the lexer and make sure that it makes sense.
Once you are reasonably happy with the output, try running some of the
more tricky tests:

     bash % python gonelex.py testlex1.g
     bash % python gonelex.py testlex2.g

Bonus: How would you go about turning these tests into proper unit tests?
'''

# ----------------------------------------------------------------------
# The following import loads a function error(lineno,msg) that should be
# used to report all error messages issued by your lexer.  Unit tests and
# other features of the compiler will rely on this function.  See the
# file errors.py for more documentation about the error handling mechanism.
from errors import error

# ----------------------------------------------------------------------
# Lexers are defined using the ply.lex library.
#
# See http://www.dabeaz.com/ply/ply.html#ply_nn3
from ply.lex import lex

# ----------------------------------------------------------------------
# Token list. This list identifies the complete list of token names
# to be recognized by your lexer.  Do not change any of these names.
# Doing so will break unit tests.

tokens = [
    # keywords
    'ID', 'CONST', 'VAR', 'LEN', 'PRINT', 'FUNC', 'EXTERN',

    # Operators and delimiters
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE',
    'ASSIGN', 'SEMI', 'LPAREN', 'RPAREN',
    'COMMA',

    # Literals
    'INTEGER', 'FLOAT', 'STRING',
]

# ----------------------------------------------------------------------
# Ignored characters (whitespace)
#
# The following characters are ignored completely by the lexer.
# Do not change.

t_ignore = ' \t\r'

# ----------------------------------------------------------------------
# Tokens for simple symbols: + - * / = ( ) ;

t_PLUS      = r'\+'
t_MINUS     = r'-'
t_TIMES     = r'\*'
t_DIVIDE    = r'/'
t_ASSIGN    = r'='
t_SEMI      = r';'
t_LPAREN    = r'\('
t_RPAREN    = r'\)'
t_COMMA     = r','

# ----------------------------------------------------------------------
# Tokens for literals, INTEGER, FLOAT, STRING.

# Floating point constant.   You must recognize floating point numbers in
# formats as shown in the following examples:
#
#   1.23, 1.23e1, 1.23e+1, 1.23e-1, 123., .123, 1e1, 0.
#
# The value should be converted to a Python float when lexed
def t_FLOAT(t):
    r'\d*((\.\d*)([eE][+-]?\d+)?|([eE][+-]?\d+))'
    t.value = float(t.value)               # Conversion to Python float
    return t

# Integer constant. For example:
#
#     1234
#     0x4d2  # hex
#     0o2322 # octal

# The value should be converted to a Python int when lexed.
def t_INTEGER(t):
    r'(0x[0-9a-fA-F]+|0o[0-7]+|\d+)'
    # Conversion to a Python int
    if t.value.startswith('0x'):
        t.value = int(t.value[2:], 16)
    elif t.value.startswith('0o'):
        t.value = int(t.value[2:], 8)
    else:
        t.value = int(t.value)
    return t

# String constant. You must recognize text enclosed in quotes.
# For example:
#
#     "Hello World"
#
# Allow string codes to have escape codes such as the following:
#
#       \n    = newline (10)
#       \\    = baskslash char (\)
#       \"    = quote (")
#
# The token value should be the string with all escape codes replaced by
# their corresponding raw character code.
#
def t_STRING(t):
    r'"(\\"|[^\n])*?[^\\]"'
    # Strip off the leading/trailing quotes
    t.value = t.value[1:-1]
    t.value = t.value.replace('\\n', '\n')
    t.value = t.value.replace('\\\\', '\\')
    t.value = t.value.replace(r'\"', '"')
    return t

# ----------------------------------------------------------------------
# Identifiers and keywords.

# Match a raw identifier.  Identifiers follow the same rules as Python.
# That is, they start with a letter or underscore (_) and can contain
# an arbitrary number of letters, digits, or underscores after that.
def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    keywords = {'var': 'VAR',
                'const': 'CONST',
                'print': 'PRINT',
                'func': 'FUNC',
                'extern': 'EXTERN',
                }
    t.type = keywords.get(t.value, 'ID')
    return t

# ----------------------------------------------------------------------
# Ignored text.   The following rules are used to ignore text in the
# input file.  This includes comments and blank lines

# One or more blank lines
def t_newline(t):
    r'[\r\n]+'
    t.lexer.lineno += len(t.value)

# C-style comment (/* ... */)
def t_COMMENT(t):
    r'(/\*)(.|\n)*?(\*/)'

    # Must count the number of newlines included to keep line count accurate
    t.lexer.lineno += t.value.count('\n')

# C++-style comment (//...)
def t_CPPCOMMENT(t):
    r'//.*'
    t.lexer.lineno += 1

# ----------------------------------------------------------------------
# Error handling.  The following error conditions must be handled by
# your lexer.

# Illegal character (generic error handling)
def t_error(t):
    error(t.lexer.lineno,"Illegal character %r" % t.value[0])
    t.lexer.skip(1)

# Unterminated C-style comment
def t_COMMENT_UNTERM(t):
    r'(/\*).*(?<!\*/)'
    error(t.lexer.lineno,"Unterminated comment")

# Unterminated string literal
def t_STRING_UNTERM(t):
    r'"(\\"|[^\n])*?\n'
    old = r'"[^\n]*(?!")'
    error(t.lexer.lineno,"Unterminated string literal")
    t.lexer.lineno += 1

# ----------------------------------------------------------------------
#                DO NOT CHANGE ANYTHING BELOW THIS PART
# ----------------------------------------------------------------------
def make_lexer():
    '''
    Utility function for making the lexer object
    '''
    return lex()

def main():
    import sys
    from errors import subscribe_errors

    if len(sys.argv) != 2:
        sys.stderr.write("Usage: %s filename\n" % sys.argv[0])
        raise SystemExit(1)


    lexer = make_lexer()
    with subscribe_errors(lambda msg: sys.stderr.write(msg+"\n")):
        lexer.input(open(sys.argv[1]).read())
        for tok in iter(lexer.token,None):
            sys.stdout.write("%s\n" % tok)

if __name__ == '__main__':
    main()
