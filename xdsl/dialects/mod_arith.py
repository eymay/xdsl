"""
mod_arith dialect implementation for xDSL
Provides modular arithmetic types (no operations, just the type)
"""

from xdsl.dialects.builtin import IntegerAttr, IntegerType
from xdsl.ir import Attribute, Dialect, ParametrizedAttribute, TypeAttribute
from xdsl.irdl import (
    ParameterDef,
    irdl_attr_definition,
)
from xdsl.parser import Parser
from xdsl.printer import Printer


@irdl_attr_definition
class ModArithType(ParametrizedAttribute, TypeAttribute):
    """
    A type representing integers modulo some value.
    
    Syntax: !mod_arith.int<modulus : type>
    Example: !mod_arith.int<1032955396097 : i64>
    """
    name = "mod_arith.int"
    
    modulus: ParameterDef[IntegerAttr]
    

ModArith = Dialect(
    "mod_arith",
    [
        # No operations - only the type
    ],
    [
        ModArithType,
    ],
)
