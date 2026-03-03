
import math
import traceback

from timeit import default_timer as timer

class CalcTimeoutException(Exception):
    def __init__(self, timelimit, stoppedAt):
        self.timelimit = timelimit
        self.stopped = stoppedAt
    
    def __str__(self):
        return "Calculation took more than {0} seconds, please simplify your term.".format(self.timelimit)



ID = "pycalc"
permission = 0


# pycalc command by Yoshi2
# Based on arith.py by Glenn Linderman found on 
# http://pyparsing.wikispaces.com/Examples
# Added functionality:
# - Evaluate hexadecimal and binary numbers
# - trigonometric functions (sin, cos, tan, asin, acos, atan)
# - conversion to binary/hexadecimal with bin() or hex()
# - bitwise operators (AND &,OR |, XOR ^, leftshift <<, rightshift >>
# - base 10 and base e logarithm 
# - factorial with ! (e.g. 5! -> 120)

## See license text in pyparsing.py
#
## Modifications by Glenn Linderman, same license
##
## Python 3.2
## Eliminate LE and friends, stick with Python comparison ops
## Merge separate precedence lists
## Make a single class Arith to be the interface
## Keep vars_ in Arith instances, so multiple instances could have
##   different vars/values
## Add // and % to multOp & EvalMultOp
## Keep integer values as integers until something converts them
## Allow longer var names
#
## Based on:
##
## eval_arith.py
##
## Copyright 2009, Paul McGuire
##
## Expansion on the pyparsing example simpleArith.py, to include evaluation
## of the parsed tokens.


from pyparsing import Word, nums, alphas, Combine, oneOf, Optional, \
    opAssoc, operatorPrecedence, hexnums
    

from types import MethodType
from pyparsing import ParserElement

ParserElement.enablePackrat()

# We wrap this method with added functionality that
# raises an exception after some time has passed.
def _parseNoCache(self, instring, loc, doActions=True, callPreParse=True):
    if timer() - self.__startTime > 10:
        raise CalcTimeoutException(10, loc)
    
    result = ParserElement._parseNoCache(self, instring, loc, doActions, callPreParse)
    return result


class EvalConstant():
    "Class to evaluate a parsed constant or variable"
    def __init__(self, tokens):
        self.value = tokens[0]
        
    def eval(self, vars_):
        if self.value in vars_:
            return vars_[self.value]
        else:
            if self.value.startswith("0x"):
                return int(self.value, 16)
            elif self.value.startswith("0b"):
                return int(self.value, 2)
            else:
                try:
                    return int( self.value )
                except:
                    return float(self.value)

class EvalPow():
    def __init__(self, tokens):
        self.value = tokens[0]
        print self.value
    def eval(self, vars_):
        prod = self.value[0].eval( vars_ )
        
        for op,val in operatorOperands(self.value[1:]):
            prod = math.pow(prod, val.eval( vars_ ))
        
        return prod
        
class EvalSignOp():
    "Class to evaluate expressions with a leading + or - sign"
    def __init__(self, tokens):
        self.sign, self.value = tokens[0]
    def eval(self, vars_):
        mult = {'+':1, '-':-1}[self.sign]
        return mult * self.value.eval(vars_)

def operatorOperands(tokenlist):
    "generator to extract operators and operands in pairs"
    it = iter(tokenlist)
    while 1:
        try:
            o1 = next(it)
            o2 = next(it)
            yield ( o1, o2 )
        except StopIteration:
            break
            
class EvalMultOp():
    "Class to evaluate multiplication and division expressions"
    def __init__(self, tokens):
        self.value = tokens[0]
    def eval(self, vars_ ):
        prod = self.value[0].eval( vars_ )
        for op,val in operatorOperands(self.value[1:]):
            if op == '*':
                prod *= val.eval( vars_ )
            if op == '/':
                prod /= val.eval( vars_ )
            if op == '//':
                prod //= val.eval( vars_ )
            if op == '%':
                prod %= val.eval( vars_ )
        return prod
    
class EvalAddOp():
    "Class to evaluate addition and subtraction expressions"
    def __init__(self, tokens):
        self.value = tokens[0]
    def eval(self, vars_ ):
        sum = self.value[0].eval( vars_ )
        for op,val in operatorOperands(self.value[1:]):
            if op == '+':
                sum += val.eval( vars_ )
            if op == '-':
                sum -= val.eval( vars_ )
        return sum



trigFunctions = {   "sin" : math.sin, "cos" : math.cos, "tan" : math.tan,
                    "asin" :math.asin, "acos" : math.acos, "atan" : math.atan}
class EvalTrig():
    "An additional class for evaluating trigonometric functions"
    def __init__(self, tokens):
        self.sign, self.value = tokens[0]
    def eval(self, vars_):
        return trigFunctions[self.sign](math.radians(self.value.eval( vars_ )))

class EvalHexBinDisp():
    "An additional class for converting numbers to binary/hexadecimal"
    def __init__(self, tokens):
        self.value = tokens[0]
        print self.value
    def eval(self, vars_):
        sign = self.value[0]
        if sign == "bin":
            return bin(int(self.value[1].eval( vars_ )))
        if sign == "hex":
            result = hex(int(self.value[1].eval( vars_ )))
            result = result.rstrip("L")
            return result
        
class EvalBinOperators():
    "An additional class for evaluating bitwise operations"
    def __init__(self, tokens):
        self.value = tokens[0]
    def eval(self, vars_):
        prod = self.value[0].eval( vars_ )
        for op,val in operatorOperands(self.value[1:]):
            if op == '&':
                prod = prod & val.eval( vars_ )
            if op == '|':
                prod = prod | val.eval( vars_ )
            if op == '^':
                prod = prod ^ val.eval( vars_ )
            if op == '<<':
                prod = prod << val.eval( vars_ )
            if op == '>>':
                prod = prod >> val.eval( vars_ )
        return prod

class EvalLog():
    "Evaluate Log to the base of 10 or to the base of e"
    def __init__(self, tokens):
        self.sign, self.value = tokens[0]
    def eval(self, vars_):
        if self.sign == "log":
            return math.log10(self.value.eval( vars_ ))
        if self.sign == "ln":
            return math.log(self.value.eval( vars_ ))

class EvalFactorial():
    "Calculate the factorial of a number"
    def __init__(self, tokens):
        self.value, self.sign = tokens[0]
    def eval(self, vars_):
        fac_value = self.value.eval( vars_ )
        if fac_value > 100:
            raise RuntimeError("The factorial of this number is too big.")
        return math.factorial(self.value.eval( vars_ ))

class Arith():
    # define the parser
    real = (
            Combine(Word(nums)+Optional("." + Word(nums))+"e+"+Word(nums))
            | Combine(Word(nums)+Optional("." + Word(nums))+"e-"+Word(nums))
            | Combine("0x" + Word(hexnums))
            | Combine("0b" + Word("01"))
            | Combine(Word(nums) + Optional("." + Word(nums)) ) 
            | Word(alphas)) 
    
    print Word(nums)
    print nums

    operand = real 
    
    expop = oneOf('**')
    signop = oneOf('+ -')
    multop = oneOf('* / // %')
    plusop = oneOf('+ -')
    trig = oneOf('sin cos tan asin acos atan')
    binary = oneOf("bin hex")
    binOp = oneOf('& | ^ << >>') 
    logOp = oneOf("log ln")
    binhexUse = oneOf("0x 0b")
    factorial = "!"

    # use parse actions to attach EvalXXX constructors to sub-expressions
    #operand.setDebug(True)
    operand.setParseAction(EvalConstant)
    
    arith_expr = operatorPrecedence(operand,
        [
         (logOp, 1, opAssoc.RIGHT, EvalLog),
         (signop, 1, opAssoc.RIGHT, EvalSignOp),
         (expop, 2, opAssoc.RIGHT, EvalPow),
         (multop, 2, opAssoc.LEFT, EvalMultOp),
         (plusop, 2, opAssoc.LEFT, EvalAddOp),
         (trig, 1, opAssoc.RIGHT, EvalTrig),
         (binOp, 2, opAssoc.RIGHT, EvalBinOperators),
         (binary, 1, opAssoc.RIGHT, EvalHexBinDisp),
         (factorial, 1, opAssoc.LEFT, EvalFactorial)
         ])

    def __init__(self, vars_={}):
        self.vars_ = vars_

    def setvars(self, vars_):
        self.vars_ = vars_

    def setvar(self, var, val):
        self.vars_[var] = val

    def eval(self, strExpr):
        setattr(self.arith_expr, "__startTime", timer())
        
        ret = self.arith_expr.parseString( strExpr, parseAll=False)[0]
        print ret
        result = ret.eval(self.vars_)
        return result
    


arith = Arith({"pi":math.pi, "e":math.e})

# Some monkeypatching is required to replace the method with our
# wrapped one. That way we can break out of the parsing loop
# easily if more than 10 seconds pass.
modified_parse = MethodType(_parseNoCache, arith.arith_expr, ParserElement)
arith.arith_expr._parseNoCache = modified_parse
arith.arith_expr._parse = modified_parse




# Thanks to Pyker for helping with testing the command
# And thanks to spacechase0 for rescuing us when we were fighting against the evil radians.

def execute(self, name, params, channel, userdata, rank):

    if len(params) > 1 and params[0] == "#fancy":
        fancy = True
        new_params = params[1:]
    else:
        fancy = False
        new_params = params

    calc = "".join(new_params)
    
    try:
        result = arith.eval(calc)
        fin = str(result)

        if len(fin) > 300:
            raise RuntimeError(u"Result is too long ({0} characters)".format(len(fin)))
        else:
            if fancy:
                self.sendChatMessage(self.send, channel, "{:,}".format(result))
            else:
                self.sendChatMessage(self.send, channel, fin)

    except CalcTimeoutException as error:
        self.sendMessage(channel, str(error))
    except Exception as error:
        traceb = str(traceback.format_exc())
        self.sendMessage(channel, u"ParseError: '"+str(error)+u"'")
        print "error: "+str(error)
        print traceb
