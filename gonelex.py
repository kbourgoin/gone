# gonelex.py
r'''
Reserved Keywords:
    CONST   : 'const'
    VAR     : 'var'
    PRINT   : 'print'
    FUNC    : 'func'
    EXTERN  : 'extern'
    TRUE    : 'true'
    FALSE   : 'false'
    IF      : 'if'
    ELSE    : 'else'
    WHILE   : 'while'
    RETURN  : 'return'

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
    'ID', 'CONST', 'VAR', 'PRINT', 'FUNC', 'EXTERN', 'TRUE', 'FALSE',

    # Operators and delimiters
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE',
    'ASSIGN', 'SEMI', 'LPAREN', 'RPAREN',
    'COMMA', 'LBRACE', 'RBRACE',

    # Flow Control Keywords
    'IF', 'ELSE', 'WHILE', 'RETURN',

    # Boolean operators
    'LT', 'LTE', 'GT', 'GTE', 'EQ', 'NEQ', 'NOT', 'OR', 'AND',

    # Literals
    'INTEGER', 'FLOAT', 'STRING',
]

# ----------------------------------------------------------------------
# Ignored characters (whitespace)
#
# The following characters are ignored completely by the lexer.

t_ignore = ' \t\r'

# ----------------------------------------------------------------------
# Tokens for simple symbols: + - * / = ( ) ;

t_PLUS      = r'\+'
t_MINUS     = r'-'
t_TIMES     = r'\*'
t_DIVIDE    = r'/'
t_SEMI      = r';'
t_LPAREN    = r'\('
t_RPAREN    = r'\)'
t_COMMA     = r','
t_LBRACE    = r'{'
t_RBRACE    = r'}'

t_EQ        = r'=='
t_NEQ       = r'!='
t_OR        = r'\|\|'
t_AND       = r'&&'
t_ASSIGN    = r'='
t_LTE       = r'<='
t_LT        = r'<'
t_GTE       = r'>='
t_GT        = r'>'
t_NOT       = r'!'

# ----------------------------------------------------------------------
# Tokens for literals, INTEGER, FLOAT, STRING.

# Floating point constant.   You must recognize floating point numbers in
# formats as shown in the following examples:
#
#   1.23, 1.23e1, 1.23e+1, 1.23e-1, 123., .123, 1e1, 0.
#
def t_FLOAT(t):
    r'\d*((\.\d*)([eE][+-]?\d+)?|([eE][+-]?\d+))'
    t.value = float(t.value)
    return t

# Integer constant. For example:
#
#     1234
#     0x4d2  # hex
#     0o2322 # octal

def t_INTEGER(t):
    r'(0x[0-9a-fA-F]+|0o[0-7]+|\d+)'
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
def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    keywords = {'var': 'VAR',
                'const': 'CONST',
                'print': 'PRINT',
                'func': 'FUNC',
                'extern': 'EXTERN',
                'true': 'TRUE',
                'false': 'FALSE',
                'if': 'IF',
                'else': 'ELSE',
                'while': 'WHILE',
                'return': 'RETURN',
                }
    t.type = keywords.get(t.value, 'ID')
    if t.type == 'TRUE':
        t.value = True
    elif t.type == 'FALSE':
        t.value = False
    return t

# ----------------------------------------------------------------------
# Ignored text.   The following rules are used to ignore text in the
# input file.  This includes comments and blank lines

# One or more blank lines
def t_newline(t):
    r'[\r\n]+'
    t.lexer.lineno += t.value.count('\n')

# C-style comment (/* ... */)
def t_COMMENT(t):
    r'(/\*)(.|\n)*?(\*/)'

    # Must count the number of newlines included to keep line count accurate
    t.lexer.lineno += t.value.count('\n')

# C++-style comment (//...)
def t_CPPCOMMENT(t):
    r'//.*\n'
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

def make_lexer():
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
