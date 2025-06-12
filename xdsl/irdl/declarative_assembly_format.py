"""
This file contains the data structures necessary for the parsing and printing
of the MLIR declarative assembly format defined at
https://mlir.llvm.org/docs/DefiningDialects/Operations/#declarative-assembly-format .
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from typing_extensions import TypeVar

from xdsl.dialects.builtin import UnitAttr
from xdsl.ir import (
    Attribute,
    Data,
    ParametrizedAttribute,
    Region,
    SSAValue,
    TypedAttribute,
)
from xdsl.irdl import (
    ConstraintContext,
    IRDLOperation,
    IRDLOperationInvT,
    OpDef,
    OptionalDef,
    Successor,
    VariadicDef,
)
from xdsl.parser import Parser, UnresolvedOperand
from xdsl.printer import Printer
from xdsl.utils.mlir_lexer import PunctuationSpelling


@dataclass
class AttributeParsingState:
    """
    State carried during the parsing of an attribute using the declarative assembly
    format. Similar to ParsingState but designed for attributes with parameters.
    """
    
    parameters: dict[str, Attribute]
    """Parameters that have been parsed."""
    
    def __init__(self, attr_def):
        self.parameters = {}

@dataclass
class AttributePrintingState:
    """
    State carried during the printing of an attribute using the declarative assembly
    format.
    """

    last_was_punctuation: bool = field(default=False)
    should_emit_space: bool = field(default=True)


@dataclass
class ParsingState:
    """
    State carried during the parsing of an operation using the declarative assembly
    format.
    It contains the elements that have already been parsed.
    """

    operands: list[UnresolvedOperand | None | Sequence[UnresolvedOperand]]
    operand_types: list[Attribute | None | Sequence[Attribute]]
    result_types: list[Attribute | None | Sequence[Attribute]]
    regions: list[Region | None | Sequence[Region]]
    successors: list[Successor | None | Sequence[Successor]]
    attributes: dict[str, Attribute]
    properties: dict[str, Attribute]
    context: ConstraintContext

    def __init__(self, op_def: OpDef):
        self.operands = [None] * len(op_def.operands)
        self.operand_types = [None] * len(op_def.operands)
        self.result_types = [None] * len(op_def.results)
        self.regions = [None] * len(op_def.regions)
        self.successors = [None] * len(op_def.successors)
        self.attributes = {}
        self.properties = {}
        self.context = ConstraintContext()


@dataclass
class PrintingState:
    """
    State carried during the printing of an operation using the declarative assembly
    format.
    It contains information on the last token, to know if a space should be emitted.
    """

    last_was_punctuation: bool = field(default=False)
    """Was the last element parsed a punctuation."""
    should_emit_space: bool = field(default=True)
    """
    Should the printer emit a space before the next element.
    Depending on the directive, the space might not be printed
    (for instance for some punctuations).
    """


@dataclass(frozen=True)
class FormatProgram:
    """
    The toplevel data structure of a declarative assembly format program.
    It is used to parse and print an operation.
    """

    stmts: tuple[FormatDirective, ...]
    """The statements composing the program. They are executed in order."""

    @staticmethod
    def from_str(input: str, op_def: OpDef) -> FormatProgram:
        """
        Create the assembly format data program from its string representation.
        This might raise a ParseError exception if the string is invalid.
        """
        from xdsl.irdl.declarative_assembly_format_parser import FormatParser

        return FormatParser(input, op_def).parse_format()

    def parse(
        self, parser: Parser, op_type: type[IRDLOperationInvT]
    ) -> IRDLOperationInvT:
        """
        Parse the operation with this format.
        The given operation type is expected to be the operation type represented by
        the operation definition passed to the FormatParser that created this
        FormatProgram.
        """
        # Parse elements one by one
        op_def = op_type.get_irdl_definition()
        state = ParsingState(op_def)
        for stmt in self.stmts:
            stmt.parse(parser, state)

        # Get constraint variables from the parsed operand and result types
        self.resolve_constraint_variables(state, op_def)

        # Infer operand types that should be inferred
        unresolved_operands = state.operands
        self.resolve_operand_types(state, op_def)
        operand_types = state.operand_types
        assert None not in operand_types

        # Infer result types that should be inferred
        self.resolve_result_types(state, op_def)
        result_types = state.result_types
        assert None not in result_types

        # Resolve all operands
        operands: Sequence[SSAValue | Sequence[SSAValue]] = []
        for uo, ot in zip(unresolved_operands, operand_types, strict=True):
            assert uo is not None
            if isinstance(uo, UnresolvedOperand):
                assert isinstance(ot, Attribute), (
                    "Something went wrong with the declarative assembly format parser."
                )
                "Single operand has no type or variadic/optional type"
                operands.append(parser.resolve_operand(uo, ot))
            else:
                assert isinstance(ot, Sequence), (
                    f"Something went wrong with the declarative assembly format parser. {type(ot)} {ot}"
                )
                "Variadic or optional operand has no type or a single type "
                operands.append(parser.resolve_operands(uo, ot, parser.pos))

        return op_type.build(
            result_types=result_types,
            operands=operands,
            attributes=state.attributes,
            properties=state.properties,
            regions=state.regions,
            successors=state.successors,
        )

    def parse_attribute(
        self, parser: Parser, attr_class: type['ParametrizedAttribute']
    ) -> 'ParametrizedAttribute':
        """
        Parse an attribute with this format.
        This is the attribute equivalent of the parse method for operations.
        """
        # Get the attribute definition
        attr_def = attr_class.get_irdl_definition()
        
        # Create attribute parsing state
        state = AttributeParsingState(attr_def)
        
        # Parse elements one by one
        for stmt in self.stmts:
            stmt.parse_attribute(parser, state, attr_def)
        
        # Extract parameters in the correct order
        parameters = []
        for param_name, _ in attr_def.parameters:
            if param_name not in state.parameters:
                parser.raise_error(f"Parameter '{param_name}' was not parsed")
            parameters.append(state.parameters[param_name])
        
        return attr_class.new(parameters)

    def parse_attribute_parameters(
            self, parser: Parser, attr_class, attr_def
        ) -> list[Attribute]:
            """
            Parse attribute parameters using the declarative assembly format.
            
            This is the fixed version that properly handles assembly format parsing.
            """
            # Create attribute parsing state
            state = AttributeParsingState(attr_def)
            
            try:
                # Parse elements one by one using the format directives
                for stmt in self.stmts:
                    if hasattr(stmt, 'parse_attribute'):
                        stmt.parse_attribute(parser, state, attr_def)
                    else:
                        # Handle directives that don't support parse_attribute yet
                        if isinstance(stmt, PunctuationDirective):
                            parser.parse_punctuation(stmt.punctuation)
                        elif isinstance(stmt, KeywordDirective):
                            parser.parse_keyword(stmt.keyword)
                        elif isinstance(stmt, AttrDictDirective):
                            # For attr-dict in attributes, just parse optional dict
                            parser.parse_optional_attr_dict()
                        else:
                            parser.raise_error(f"Directive {type(stmt)} not supported for attributes")
            except Exception as e:
                parser.raise_error(f"Error parsing attribute assembly format: {e}")
            
            # Extract parameters in the correct order
            parameters = []
            for param_name, _ in attr_def.parameters:
                if param_name not in state.parameters:
                    parser.raise_error(f"Parameter '{param_name}' was not parsed by assembly format")
                parameters.append(state.parameters[param_name])
            
            return parameters

    def print_attribute(self, printer: Printer, attr) -> None:
        """
        Print an attribute using this format.
        """
        state = AttributePrintingState()
        attr_def = attr.get_irdl_definition()
        
        # Print elements one by one
        for stmt in self.stmts:
            stmt.print_attribute(printer, state, attr, attr_def)

    def resolve_constraint_variables(self, state: ParsingState, op_def: OpDef):
        """
        Runs verification on the parsed parts of the operation, adding the resolved value
        of each constraint variable to the `ConstraintContext` `state.context`.
        """
        ctx = state.context

        for operand, operand_type, (_, operand_def) in zip(
            state.operands, state.operand_types, op_def.operands, strict=True
        ):
            length = len(operand) if isinstance(operand, Sequence) else 1
            operand_def.constr.verify_length(length, ctx)
            if operand_type is None:
                continue
            if isinstance(operand_type, Attribute):
                operand_type = (operand_type,)
            operand_def.constr.verify(operand_type, ctx)

        for result_type, (_, result_def) in zip(
            state.result_types, op_def.results, strict=True
        ):
            if result_type is None:
                continue
            if isinstance(result_type, Attribute):
                result_type = (result_type,)
            result_def.constr.verify(result_type, ctx)

        for prop_name, prop_def in op_def.properties.items():
            if isinstance(prop_def, OptionalDef) and prop_def.default_value is None:
                continue
            attr = state.properties.get(prop_name, prop_def.default_value)
            if attr is None:
                continue
            prop_def.constr.verify(attr, ctx)

        for attr_name, attr_def in op_def.attributes.items():
            if isinstance(attr_def, OptionalDef) and attr_def.default_value is None:
                continue
            attr = state.attributes.get(attr_name, attr_def.default_value)
            if attr is None:
                continue
            attr_def.constr.verify(attr, ctx)

    def resolve_operand_types(self, state: ParsingState, op_def: OpDef) -> None:
        """
        Use the inferred type resolutions to fill missing operand types from other parsed
        types.
        """
        for i, (operand_type, (_, operand_def)) in enumerate(
            zip(state.operand_types, op_def.operands, strict=True)
        ):
            if operand_type is None:
                operand = state.operands[i]
                range_length = len(operand) if isinstance(operand, Sequence) else 1
                operand_type = operand_def.constr.infer(
                    state.context,
                    length=range_length,
                )
                resolved_operand_type: Attribute | Sequence[Attribute]
                if isinstance(operand_def, OptionalDef):
                    resolved_operand_type = operand_type[0] if operand_type else ()
                elif isinstance(operand_def, VariadicDef):
                    resolved_operand_type = operand_type
                else:
                    resolved_operand_type = operand_type[0]
                state.operand_types[i] = resolved_operand_type

    def resolve_result_types(self, state: ParsingState, op_def: OpDef) -> None:
        """
        Use the inferred type resolutions to fill missing result types from other parsed
        types.
        """
        for i, (result_type, (_, result_def)) in enumerate(
            zip(state.result_types, op_def.results, strict=True)
        ):
            if result_type is None:
                inferred_result_types = result_def.constr.infer(
                    state.context, length=None
                )
                resolved_result_type: Attribute | Sequence[Attribute]
                if isinstance(result_def, OptionalDef):
                    resolved_result_type = (
                        inferred_result_types[0] if inferred_result_types else ()
                    )
                elif isinstance(result_def, VariadicDef):
                    resolved_result_type = inferred_result_types
                else:
                    resolved_result_type = inferred_result_types[0]
                state.result_types[i] = resolved_result_type

    def print(self, printer: Printer, op: IRDLOperation) -> None:
        """
        Print the operation with this format.
        The given operation is expected to be defined using the operation definition
        passed to the FormatParser that created this FormatProgram.
        """
        state = PrintingState()
        for stmt in self.stmts:
            stmt.print(printer, state, op)


@dataclass(frozen=True)
class Directive(ABC):
    """An assembly format directive"""

    def is_present(self, op: IRDLOperation) -> bool:
        """
        Check if the directive is present in the input.
        """
        return True

    def is_anchorable(self) -> bool:
        """
        Can appear as an anchor in an optional group.
        """
        return False

    def is_variadic_like(self) -> bool:
        """
        Variadic-like format directives parse a comma separated list, and cannot be
        followed by `,` directive.
        """
        return False

    def is_optional_like(self) -> bool:
        """
        Directives that successfully parse the empty string.
        """
        return self.is_variadic_like()


class FormatDirective(Directive, ABC):
    """A format directive for operation format."""

    @abstractmethod
    def parse(self, parser: Parser, state: ParsingState) -> bool:
        """
        Parses the directive, returning True if input was consumed.
        """
        ...

    def parse_attribute(self, parser: Parser, state: AttributeParsingState, attr_def) -> None:
        """Parse the directive for attributes. Default implementation raises error."""
        raise ValueError(f"Directive {type(self)} does not support attribute parsing")


    def print_attribute(self, printer: Printer, state: AttributePrintingState, attr, attr_def) -> None:
        """Print the directive for attributes. Default implementation raises error."""
        raise ValueError(f"Directive {type(self)} does not support attribute printing")


    @abstractmethod
    def print(
        self, printer: Printer, state: PrintingState, op: IRDLOperation
    ) -> None: ...

    def set_empty(self, state: ParsingState):
        """
        Set the appropriate field of the parsing state to be empty.
        Used when a variable appears in an optional group which is not parsed.
        """
        return


class TypeableDirective(Directive, ABC):
    """
    Directives which can be used to set or get types.
    """

    @abstractmethod
    def parse_types(self, parser: Parser, state: ParsingState) -> bool:
        """
        Parses types for the directive, returning True if input was consumed.
        """
        ...

    @abstractmethod
    def parse_single_type(self, parser: Parser, state: ParsingState) -> None:
        """
        Parse exactly one type for the directive.
        """

    @abstractmethod
    def get_types(self, op: IRDLOperation) -> Sequence[Attribute]: ...

    def set_types_empty(self, state: ParsingState) -> None:
        return


@dataclass(frozen=True)
class TypeDirective(FormatDirective):
    """
    A directive which parses the type of a typeable directive, with format:
      type-directive ::= type(typeable-directive)
    """

    inner: TypeableDirective

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        return self.inner.parse_types(parser, state)

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        types = self.inner.get_types(op)
        if not types:
            return
        if state.should_emit_space or not state.last_was_punctuation:
            printer.print(" ")
        printer.print_list(types, printer.print_attribute)
        state.last_was_punctuation = False
        state.should_emit_space = True

    def is_present(self, op: IRDLOperation) -> bool:
        return self.inner.is_present(op)

    def is_anchorable(self) -> bool:
        return self.inner.is_anchorable()

    def is_variadic_like(self) -> bool:
        return self.inner.is_variadic_like()

    def is_optional_like(self) -> bool:
        return self.inner.is_optional_like()

    def set_empty(self, state: ParsingState):
        self.inner.set_types_empty(state)


@dataclass(frozen=True)
class VariableDirective(Directive, ABC):
    """
    A variable directive, with the following format:
      variable-directive ::= dollar-ident
    The directive will request a space to be printed after.
    """

    name: str
    """The variable name. This is only used for error message reporting."""
    index: int
    """Index of the variable(operand or result) definition."""


class VariadicVariable(VariableDirective, ABC):
    def is_present(self, op: IRDLOperation) -> bool:
        return bool(getattr(op, self.name))

    def is_anchorable(self) -> bool:
        return True

    def is_variadic_like(self) -> bool:
        return True


class OptionalVariable(VariableDirective, ABC):
    def is_present(self, op: IRDLOperation) -> bool:
        return getattr(op, self.name) is not None

    def is_anchorable(self) -> bool:
        return True

    def is_optional_like(self) -> bool:
        return True


@dataclass(frozen=True)
class AttrDictDirective(FormatDirective):
    """
    An attribute dictionary directive, with the following format:
       attr-dict-directive ::= attr-dict
       attr-dict-with-format-directive ::= `attributes` attr-dict
    The directive (with and without the keyword) will always print a space before, and
    will not request a space to be printed after.
    """

    with_keyword: bool
    """If this is set, the format starts with the `attributes` keyword."""

    reserved_attr_names: set[str]
    """
    The set of attributes that should not be printed.
    These attributes are printed in other places in the format, and thus would be
    printed twice otherwise.
    """

    expected_properties: set[str]
    """
    Properties that should be printed and parsed as part of this attr-dict.
    This is used to keep compatibility with MLIR which allows that.
    """

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        if self.with_keyword:
            res = parser.parse_optional_attr_dict_with_keyword()
            if res is None:
                res = {}
            else:
                res = dict(res.data)
        else:
            res = parser.parse_optional_attr_dict()
        defined_reserved_keys = self.reserved_attr_names & res.keys()
        if defined_reserved_keys:
            parser.raise_error(
                f"attributes {', '.join(defined_reserved_keys)} are defined in other parts of the "
                "assembly format, and thus should not be defined in the attribute "
                "dictionary."
            )

        props = tuple(k for k in res.keys() if k in self.expected_properties)
        for name in props:
            state.properties[name] = res.pop(name)
        state.attributes |= res
        return bool(res) or bool(props)

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        if not op.attributes.keys().isdisjoint(self.expected_properties):
            raise ValueError(
                "Cannot print attributes and properties with the same name "
                "in a single dictionary"
            )
        op_def = op.get_irdl_definition()
        dictionary = op.attributes | {
            k: v for k, v in op.properties.items() if k in self.expected_properties
        }
        defs = {
            x: op_def.properties[x] for x in self.expected_properties
        } | op_def.attributes

        reserved_or_default = self.reserved_attr_names.union(
            name
            for name, d in defs.items()
            if d.default_value is not None and dictionary.get(name) == d.default_value
        )

        printed = printer.print_op_attributes(
            dictionary,
            reserved_attr_names=reserved_or_default,
            print_keyword=self.with_keyword,
        )

        if printed:
            state.last_was_punctuation = False
            state.should_emit_space = True

    def parse_attribute(self, parser: Parser, state: AttributeParsingState, attr_def) -> None:
        # Parse attribute dictionary (typically empty for attribute parameters)
        attrs = parser.parse_optional_attr_dict()

    def print_attribute(self, printer: Printer, state: AttributePrintingState, attr, attr_def) -> None:
        # For attributes, attr-dict is typically empty
        pass

    def is_optional_like(self) -> bool:
        return True


class OperandDirective(FormatDirective, TypeableDirective, ABC):
    """
    Base class for operand directives to aid typechecking.
    """

    pass


@dataclass(frozen=True)
class OperandVariable(VariableDirective, OperandDirective):
    """
    An operand variable, with the following format:
      operand-directive ::= dollar-ident
    The directive will request a space to be printed after.
    """

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        operand = parser.parse_unresolved_operand()
        state.operands[self.index] = operand
        return True

    def parse_types(self, parser: Parser, state: ParsingState) -> bool:
        state.operand_types[self.index] = parser.parse_type()
        return True

    def parse_single_type(self, parser: Parser, state: ParsingState) -> None:
        self.parse_types(parser, state)

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        if state.should_emit_space or not state.last_was_punctuation:
            printer.print(" ")
        printer.print_ssa_value(getattr(op, self.name))
        state.last_was_punctuation = False
        state.should_emit_space = True

    def get_types(self, op: IRDLOperation) -> Sequence[Attribute]:
        return (getattr(op, self.name).type,)


@dataclass(frozen=True)
class VariadicOperandVariable(VariadicVariable, OperandDirective):
    """
    A variadic operand variable, with the following format:
      operand-directive ::= ( percent-ident ( `,` percent-id )* )?
    The directive will request a space to be printed after.
    """

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        operands = parser.parse_optional_undelimited_comma_separated_list(
            parser.parse_optional_unresolved_operand, parser.parse_unresolved_operand
        )
        if operands is None:
            operands = []
        state.operands[self.index] = operands
        return bool(operands)

    def parse_types(self, parser: Parser, state: ParsingState) -> bool:
        types = parser.parse_optional_undelimited_comma_separated_list(
            parser.parse_optional_type, parser.parse_type
        )
        ret = types is None
        if ret:
            types = ()
        state.operand_types[self.index] = types
        return ret

    def parse_single_type(self, parser: Parser, state: ParsingState) -> None:
        state.operand_types[self.index] = (parser.parse_type(),)

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        operand = getattr(op, self.name)
        if not operand:
            return
        if state.should_emit_space or not state.last_was_punctuation:
            printer.print(" ")
        printer.print_list(operand, printer.print_ssa_value)
        state.last_was_punctuation = False
        state.should_emit_space = True

    def get_types(self, op: IRDLOperation) -> Sequence[Attribute]:
        return getattr(op, self.name).types

    def set_empty(self, state: ParsingState):
        state.operands[self.index] = ()

    def set_types_empty(self, state: ParsingState) -> None:
        state.operand_types[self.index] = ()


class OptionalOperandVariable(OptionalVariable, OperandDirective):
    """
    An optional operand variable, with the following format:
      operand-directive ::= ( percent-ident )?
    The directive will request a space to be printed after.
    """

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        operand = parser.parse_optional_unresolved_operand()
        if operand is None:
            operand = ()
        state.operands[self.index] = operand
        return bool(operand)

    def parse_types(self, parser: Parser, state: ParsingState) -> bool:
        type = parser.parse_optional_type()
        ret = type is None
        if ret:
            type = ()
        state.operand_types[self.index] = type
        return ret

    def parse_single_type(self, parser: Parser, state: ParsingState) -> None:
        state.operand_types[self.index] = parser.parse_type()

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        operand = getattr(op, self.name)
        if not operand:
            return
        if state.should_emit_space or not state.last_was_punctuation:
            printer.print(" ")
        printer.print_ssa_value(operand)
        state.last_was_punctuation = False
        state.should_emit_space = True

    def get_types(self, op: IRDLOperation) -> Sequence[Attribute]:
        operand = getattr(op, self.name)
        if operand:
            return (operand.type,)
        return ()

    def set_empty(self, state: ParsingState):
        state.operands[self.index] = ()

    def set_types_empty(self, state: ParsingState) -> None:
        state.operand_types[self.index] = ()


_T = TypeVar("_T")


@dataclass(frozen=True)
class OperandsOrResultDirective(TypeableDirective, ABC):
    """
    Base class for the 'operands' and 'results' directives.
    """

    variadic_index: tuple[bool, int] | None
    """
    Represents the position of a (single) variadic variable, with the boolean
    representing whether it is optional
    """

    def is_variadic_like(self) -> bool:
        return True

    def is_anchorable(self) -> bool:
        return True

    def _set_using_variadic_index(
        self,
        field: list[_T | None | Sequence[_T]],
        field_name: str,
        set_to: Sequence[_T],
    ) -> str | None:
        if self.variadic_index is None:
            if len(set_to) != len(field):
                return f"Expected {len(field)} {field_name} but found {len(set_to)}"
            field[:] = set_to
            return

        is_optional, var_position = self.variadic_index
        var_length = len(set_to) - len(field) + 1
        if var_length < 0:
            return f"Expected at least {len(field) - 1} {field_name} but found {len(set_to)}"
        if var_length > 1 and is_optional:
            return f"Expected at most {len(field)} {field_name} but found {len(set_to)}"
        field[:var_position] = set_to[:var_position]
        field[var_position] = set_to[var_position : var_position + var_length]
        field[var_position + 1 :] = set_to[var_position + var_length :]


class OperandsDirective(OperandsOrResultDirective, FormatDirective):
    """
    An operands directive, with the following format:
      operands-directive ::= operands
    Prints each operand of the operation, inserting a comma between each.
    """

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        pos_start = parser.pos
        operands = (
            parser.parse_optional_undelimited_comma_separated_list(
                parser.parse_optional_unresolved_operand,
                parser.parse_unresolved_operand,
            )
            or []
        )

        if s := self._set_using_variadic_index(state.operands, "operands", operands):
            parser.raise_error(s, at_position=pos_start, end_position=parser.pos)
        return bool(operands)

    def parse_types(self, parser: Parser, state: ParsingState) -> bool:
        pos_start = parser.pos
        types = (
            parser.parse_optional_undelimited_comma_separated_list(
                parser.parse_optional_type, parser.parse_type
            )
            or []
        )

        if s := self._set_using_variadic_index(
            state.operand_types, "operand types", types
        ):
            parser.raise_error(s, at_position=pos_start, end_position=parser.pos)
        return bool(types)

    def parse_single_type(self, parser: Parser, state: ParsingState) -> None:
        pos_start = parser.pos
        if s := self._set_using_variadic_index(
            state.operand_types, "operand types", (parser.parse_type(),)
        ):
            parser.raise_error(s, at_position=pos_start, end_position=parser.pos)

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        if op.operands:
            if state.should_emit_space or not state.last_was_punctuation:
                printer.print(" ")
            printer.print_list(op.operands, printer.print_ssa_value)
            state.last_was_punctuation = False
            state.should_emit_space = True

    def set_types_empty(self, state: ParsingState) -> None:
        state.operand_types = [() for _ in state.operand_types]

    def get_types(self, op: IRDLOperation) -> Sequence[Attribute]:
        return op.operand_types

    def set_empty(self, state: ParsingState):
        state.operands = [() for _ in state.operands]

    def is_present(self, op: IRDLOperation) -> bool:
        return bool(op.operands)


@dataclass(frozen=True)
class ResultVariable(VariableDirective, TypeableDirective):
    """
    An result variable, with the following format:
      result-directive ::= dollar-ident
    This directive can not be used for parsing and printing directly, as result
    parsing is not handled by the custom operation parser.
    """

    def parse_types(self, parser: Parser, state: ParsingState) -> bool:
        state.result_types[self.index] = parser.parse_type()
        return True

    def parse_single_type(self, parser: Parser, state: ParsingState) -> None:
        self.parse_types(parser, state)

    def get_types(self, op: IRDLOperation) -> Sequence[Attribute]:
        return (getattr(op, self.name).type,)


@dataclass(frozen=True)
class VariadicResultVariable(VariadicVariable, TypeableDirective):
    """
    A variadic result variable, with the following format:
      result-directive ::= percent-ident (( `,` percent-id )* )?
    This directive can not be used for parsing and printing directly, as result
    parsing is not handled by the custom operation parser.
    """

    def parse_types(self, parser: Parser, state: ParsingState) -> bool:
        types = parser.parse_optional_undelimited_comma_separated_list(
            parser.parse_optional_type, parser.parse_type
        )
        ret = types is None
        if ret:
            types = ()
        state.result_types[self.index] = types
        return ret

    def parse_single_type(self, parser: Parser, state: ParsingState) -> None:
        state.result_types[self.index] = (parser.parse_type(),)

    def get_types(self, op: IRDLOperation) -> Sequence[Attribute]:
        return getattr(op, self.name).types

    def set_types_empty(self, state: ParsingState) -> None:
        state.result_types[self.index] = ()


class OptionalResultVariable(OptionalVariable, TypeableDirective):
    """
    An optional result variable, with the following format:
      result-directive ::= ( percent-ident )?
    This directive can not be used for parsing and printing directly, as result
    parsing is not handled by the custom operation parser.
    """

    def parse_types(self, parser: Parser, state: ParsingState) -> bool:
        type = parser.parse_optional_type()
        ret = type is None
        if ret:
            type = ()
        state.result_types[self.index] = type
        return ret

    def parse_single_type(self, parser: Parser, state: ParsingState) -> None:
        state.result_types[self.index] = (parser.parse_type(),)

    def get_types(self, op: IRDLOperation) -> Sequence[Attribute]:
        res = getattr(op, self.name)
        if res:
            return (res.type,)
        return ()

    def set_types_empty(self, state: ParsingState) -> None:
        state.result_types[self.index] = ()


class ResultsDirective(OperandsOrResultDirective):
    """
    A results directive, with the following format:
      results-directive ::= results
    A typeable directive which processes the result types of the operation.
    """

    def parse_types(self, parser: Parser, state: ParsingState) -> bool:
        pos_start = parser.pos
        types = (
            parser.parse_optional_undelimited_comma_separated_list(
                parser.parse_optional_type, parser.parse_type
            )
            or []
        )

        if s := self._set_using_variadic_index(
            state.result_types, "result types", types
        ):
            parser.raise_error(s, at_position=pos_start, end_position=parser.pos)
        return bool(types)

    def parse_single_type(self, parser: Parser, state: ParsingState) -> None:
        pos_start = parser.pos
        if s := self._set_using_variadic_index(
            state.result_types, "result types", (parser.parse_type(),)
        ):
            parser.raise_error(s, at_position=pos_start, end_position=parser.pos)

    def set_types_empty(self, state: ParsingState) -> None:
        state.result_types = [() for _ in state.operand_types]

    def get_types(self, op: IRDLOperation) -> Sequence[Attribute]:
        return op.result_types

    def is_present(self, op: IRDLOperation) -> bool:
        return bool(op.results)


@dataclass(frozen=True)
class FunctionalTypeDirective(FormatDirective):
    """
    A directive which parses a functional type, with format:
      functional-type-directive ::= functional-type(typeable-directive, typeable-directive)
    A functional type is either of the form
      `(` type-list `)` `->` `(` type-list `)`
    or
      `(` type-list `)` `->` type
    where type-list is a comma separated list of types (or the empty string to signify the empty list).
    The second format is preferred for printing when possible.
    """

    operand_typeable_directive: TypeableDirective
    result_typeable_directive: TypeableDirective

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        if not parser.parse_optional_punctuation("("):
            return False
        self.operand_typeable_directive.parse_types(parser, state)
        parser.parse_punctuation(")")
        parser.parse_punctuation("->")
        if parser.parse_optional_punctuation("("):
            self.result_typeable_directive.parse_types(parser, state)
            parser.parse_punctuation(")")
        else:
            self.result_typeable_directive.parse_single_type(parser, state)
        return True

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        if state.should_emit_space or not state.last_was_punctuation:
            printer.print_string(" ")
        state.should_emit_space = True
        printer.print_string("(")
        printer.print_list(
            self.operand_typeable_directive.get_types(op), printer.print_attribute
        )
        printer.print_string(") -> ")
        result_types = self.result_typeable_directive.get_types(op)
        if len(result_types) == 1:
            printer.print_attribute(result_types[0])
            state.last_was_punctuation = False
        else:
            printer.print_string("(")
            printer.print_list(result_types, printer.print_attribute)
            printer.print_string(")")
            state.last_was_punctuation = True


class RegionDirective(FormatDirective, ABC):
    """
    Baseclass to help keep typechecking simple.
    """


@dataclass(frozen=True)
class RegionVariable(RegionDirective, VariableDirective):
    """
    A region variable, with the following format:
      region-directive ::= dollar-ident
    The directive will request a space to be printed after.
    """

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        region = parser.parse_region()
        state.regions[self.index] = region
        return True

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        if state.should_emit_space or not state.last_was_punctuation:
            printer.print(" ")
        printer.print_region(getattr(op, self.name))
        state.last_was_punctuation = False
        state.should_emit_space = True


@dataclass(frozen=True)
class VariadicRegionVariable(RegionDirective, VariadicVariable):
    """
    A variadic region variable, with the following format:
      region-directive ::= dollar-ident

    The directive will request a space to be printed after.
    """

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        regions: list[Region] = []
        current_region = parser.parse_optional_region()
        while current_region is not None:
            regions.append(current_region)
            current_region = parser.parse_optional_region()

        state.regions[self.index] = regions
        return bool(regions)

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        region = getattr(op, self.name)
        if not region:
            return
        if state.should_emit_space or not state.last_was_punctuation:
            printer.print(" ")
        printer.print_list(region, printer.print_region, delimiter=" ")
        state.last_was_punctuation = False
        state.should_emit_space = True

    def set_empty(self, state: ParsingState):
        state.regions[self.index] = ()


class OptionalRegionVariable(RegionDirective, OptionalVariable):
    """
    An optional region variable, with the following format:
      region-directive ::= dollar-ident
    The directive will request a space to be printed after.
    """

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        region = parser.parse_optional_region()
        if region is None:
            region = list[Region]()
        state.regions[self.index] = region
        return bool(region)

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        region = getattr(op, self.name)
        if not region:
            return
        if state.should_emit_space or not state.last_was_punctuation:
            printer.print(" ")
        printer.print_region(region)
        state.last_was_punctuation = False
        state.should_emit_space = True

    def set_empty(self, state: ParsingState):
        state.regions[self.index] = ()


class SuccessorDirective(FormatDirective, ABC):
    """
    Base class for type checking.
    A variadic successor directive cannot follow another variadic successor directive.
    """


class SuccessorVariable(VariableDirective, SuccessorDirective):
    """
    A successor variable, with the following format:
      successor-directive ::= dollar-ident
    The directive will request a space to be printed after.
    """

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        successor = parser.parse_optional_successor()

        state.successors[self.index] = successor

        return successor is not None

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        if state.should_emit_space or not state.last_was_punctuation:
            printer.print(" ")
        printer.print_block_name(getattr(op, self.name))
        state.last_was_punctuation = False
        state.should_emit_space = True


class VariadicSuccessorVariable(VariadicVariable, SuccessorDirective):
    """
    A variadic successor variable, with the following format:
      successor-directive ::= dollar-ident
    The directive will request a space to be printed after.
    """

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        successors = parser.parse_optional_undelimited_comma_separated_list(
            parser.parse_optional_successor, parser.parse_successor
        )
        if successors is None:
            successors = []
        state.successors[self.index] = successors

        return bool(successors)

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        successor = getattr(op, self.name)
        if not successor:
            return
        if state.should_emit_space or not state.last_was_punctuation:
            printer.print(" ")
        printer.print_list(successor, printer.print_block_name)
        state.last_was_punctuation = False
        state.should_emit_space = True

    def set_empty(self, state: ParsingState):
        state.successors[self.index] = ()


class OptionalSuccessorVariable(OptionalVariable, SuccessorDirective):
    """
    An optional successor variable, with the following format:
      successor-directive ::= dollar-ident
    The directive will request a space to be printed after.
    """

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        successor = parser.parse_optional_successor()
        if successor is None:
            successor = list[Successor]()
        state.successors[self.index] = successor
        return bool(successor)

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        successor = getattr(op, self.name)
        if not successor:
            return
        if state.should_emit_space or not state.last_was_punctuation:
            printer.print(" ")
        printer.print_block_name(successor)
        state.last_was_punctuation = False
        state.should_emit_space = True

    def set_empty(self, state: ParsingState):
        state.successors[self.index] = ()


@dataclass(frozen=True)
class AttributeVariable(FormatDirective):
    """
    An attribute variable, with the following format:
      result-directive ::= dollar-ident
    The directive will request a space to be printed right after.
    """

    name: str
    """The attribute name as it should be in the attribute or property dictionary."""
    is_property: bool
    """Should this attribute be put in the attribute or property dictionary."""
    unique_base: type[Attribute] | None
    """The known base class of the Attribute, if any."""
    unique_type: Attribute | None
    """The known type of the Attribute, if any."""

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        unique_base = self.unique_base

        if unique_base is None:
            try:
                attr = parser.parse_attribute()
            except Exception as e:
                # If parsing fails and we're looking at '<', provide helpful error
                if parser._current_token.kind == MLIRTokenKind.LESS:
                    parser.raise_error(
                        f"Inline attribute definition found, but expected explicit attribute reference. "
                        f"Use '#dialect.attr<...>' syntax or define the attribute separately."
                    )
                raise e
        elif self.unique_type is not None:
            assert issubclass(unique_base, TypedAttribute)
            attr = unique_base.parse_with_type(parser, self.unique_type)
        elif issubclass(
            unique_base,
            ParametrizedAttribute,
        ):
            attr = unique_base.new(unique_base.parse_parameters(parser))
        elif issubclass(unique_base, Data):
            attr = unique_base.new(  # pyright: ignore[reportUnknownVariableType]
                unique_base.parse_parameter(parser)
            )
        else:
            raise ValueError("Attributes must be Data or ParameterizedAttribute.")
        if self.is_property:
            state.properties[self.name] = attr
        else:
            state.attributes[self.name] = attr
        return True

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        if state.should_emit_space or not state.last_was_punctuation:
            printer.print(" ")
        state.should_emit_space = True
        state.last_was_punctuation = False

        if self.is_property:
            attr = op.properties[self.name]
        else:
            attr = op.attributes[self.name]

        if self.unique_type is not None:
            assert isinstance(attr, TypedAttribute)
            return attr.print_without_type(printer)
        if self.unique_base is None:
            return printer.print_attribute(attr)
        if isinstance(attr, ParametrizedAttribute):
            return attr.print_parameters(printer)
        if isinstance(attr, Data):
            return attr.print_parameter(printer)
        raise ValueError("Attributes must be Data or ParameterizedAttribute!")

    def parse_attribute(self, parser: Parser, state: AttributeParsingState, attr_def: 'ParamAttrDef') -> None:
            param_name = self.name
            
            # Find the parameter constraint
            param_constraint = None
            for name, constraint in attr_def.parameters:
                if name == param_name:
                    param_constraint = constraint
                    break
            
            if param_constraint is None:
                parser.raise_error(f"Unknown parameter '{param_name}'")
            
            if param_name in state.parameters:
                parser.raise_error(f"Parameter '{param_name}' already parsed")
            
            # Parse the parameter value based on constraint
            if hasattr(param_constraint, 'get_bases'):
                bases = param_constraint.get_bases()
                if bases and len(bases) == 1:
                    unique_base = list(bases)[0]
                    if issubclass(unique_base, ParametrizedAttribute):
                        value = unique_base.new(unique_base.parse_parameters(parser))
                    else:
                        value = parser.parse_attribute()
                else:
                    value = parser.parse_attribute()
            else:
                value = parser.parse_attribute()
            
            state.parameters[param_name] = value


    def print_attribute(self, printer: Printer, state: AttributePrintingState, attr: 'ParametrizedAttribute', attr_def: 'ParamAttrDef') -> None:
        param_name = self.name
        
        # Find parameter index
        param_index = None
        for i, (name, _) in enumerate(attr_def.parameters):
            if name == param_name:
                param_index = i
                break
        
        if param_index is None:
            raise ValueError(f"Unknown parameter '{param_name}'")
        
        if state.should_emit_space and not state.last_was_punctuation:
            printer.print_string(" ")
        
        # Print the parameter value
        param_value = attr.parameters[param_index]
        printer.print_attribute(param_value)
        
        state.last_was_punctuation = False
        state.should_emit_space = True



@dataclass(frozen=True)
class DefaultValuedAttributeVariable(AttributeVariable):
    """
    An attribute variable with default value, with the following format:
      result-directive ::= dollar-ident
    The directive will request a space to be printed right after.
    """

    default_value: Attribute

    def is_present(self, op: IRDLOperation) -> bool:
        if self.is_property:
            attr = op.properties.get(self.name)
        else:
            attr = op.attributes.get(self.name)
        return attr is not None and attr != self.default_value

    def is_anchorable(self) -> bool:
        return True


class OptionalAttributeVariable(AttributeVariable):
    """
    An optional attribute variable, with the following format:
      operand-directive ::= ( percent-ident )?
    The directive will request a space to be printed after.
    """

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        # Only qualified optional attributes can be optionally parsed currently.
        # Other attributes are parsed as required attributes.
        if self.unique_base is None:
            attr = parser.parse_optional_attribute()
            if attr is None:
                return False
            if self.is_property:
                state.properties[self.name] = attr
            else:
                state.attributes[self.name] = attr
            return True
        return super().parse(parser, state)

    def is_present(self, op: IRDLOperation) -> bool:
        if self.is_property:
            attr = op.properties.get(self.name)
        else:
            attr = op.attributes.get(self.name)
        return attr is not None

    def is_anchorable(self) -> bool:
        return True

    def is_optional_like(self) -> bool:
        return self.unique_base is None


class OptionalUnitAttrVariable(OptionalAttributeVariable):
    """
    An optional UnitAttr variable that holds no value and derives its meaning from its existence. Holds a parse
    and print method to reflect this.

      operand-directive ::= (`unit_attr` unit_attr^)?

    Also see: https://mlir.llvm.org/docs/DefiningDialects/Operations/#unit-attributes
    """

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        if self.is_property:
            state.properties[self.name] = UnitAttr()
        else:
            state.attributes[self.name] = UnitAttr()
        return True

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        return


@dataclass(frozen=True)
class WhitespaceDirective(FormatDirective):
    """
    A whitespace directive, with the following format:
      whitespace-directive ::= `\n` | ` ` | ``
    This directive is only applied during printing, and has no effect during
    parsing.
    The directive will not request any space to be printed after.
    """

    whitespace: Literal[" ", "\n", ""]
    """The whitespace that should be printed."""

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        return False

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        printer.print(self.whitespace)
        state.last_was_punctuation = self.whitespace == ""
        state.should_emit_space = False


@dataclass(frozen=True)
class PunctuationDirective(FormatDirective):
    """
    A punctuation directive, with the following format:
      punctuation-directive ::= punctuation
    The directive will request a space to be printed right after, unless the punctuation
    is `<`, `(`, `{`, or `[`.
    It will also print a space before if a space is requested, and that the punctuation
    is neither `>`, `)`, `}`, `]`, or `,` if the last element was a punctuation, and
    additionally neither `<`, `(`, `}`, `]`, if the last element was not a punctuation.
    """

    punctuation: PunctuationSpelling
    """The punctuation that should be printed/parsed."""

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        return parser.parse_optional_punctuation(self.punctuation) is not None

    def parse_attribute(self, parser: Parser, state: AttributeParsingState, attr_def) -> None:
        parser.parse_punctuation(self.punctuation)

    def print_attribute(self, printer: Printer, state: AttributePrintingState, attr, attr_def) -> None:
        emit_space = False
        if state.should_emit_space:
            if state.last_was_punctuation:
                if self.punctuation not in (">", ")", "}", "]", ","):
                    emit_space = True
            elif self.punctuation not in ("<", ">", "(", ")", "{", "}", "[", "]", ","):
                emit_space = True

            if emit_space:
                printer.print(" ")

        printer.print(self.punctuation)
        state.should_emit_space = self.punctuation not in ("<", "(", "{", "[")
        state.last_was_punctuation = True


    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        emit_space = False
        if state.should_emit_space:
            if state.last_was_punctuation:
                if self.punctuation not in (">", ")", "}", "]", ","):
                    emit_space = True
            elif self.punctuation not in ("<", ">", "(", ")", "{", "}", "[", "]", ","):
                emit_space = True

            if emit_space:
                printer.print(" ")

        printer.print(self.punctuation)

        state.should_emit_space = self.punctuation not in ("<", "(", "{", "[")
        state.last_was_punctuation = True

    def is_optional_like(self) -> bool:
        return True


@dataclass(frozen=True)
class KeywordDirective(FormatDirective):
    """
    A keyword directive, with the following format:
      keyword-directive ::= bare-ident
    The directive expects a specific identifier, and will request a space to be printed
    after.
    """

    keyword: str
    """The identifier that should be printed."""

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        return parser.parse_optional_keyword(self.keyword) is not None

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        if state.should_emit_space:
            printer.print(" ")
        printer.print(self.keyword)
        state.should_emit_space = True
        state.last_was_punctuation = False

    def is_optional_like(self) -> bool:
        return True

    def parse_attribute(self, parser: Parser, state: AttributeParsingState, attr_def) -> None:
        parser.parse_keyword(self.keyword)

    def print_attribute(self, printer: Printer, state: AttributePrintingState, attr, attr_def) -> None:
        if state.should_emit_space:
            printer.print(" ")
        printer.print(self.keyword)
        state.should_emit_space = True
        state.last_was_punctuation = False


@dataclass(frozen=True)
class OptionalGroupDirective(FormatDirective):
    anchor: Directive
    then_whitespace: tuple[WhitespaceDirective, ...]
    then_first: FormatDirective
    then_elements: tuple[FormatDirective, ...]

    def parse(self, parser: Parser, state: ParsingState) -> bool:
        # If the first element was parsed, parse the then-elements as usual
        if ret := self.then_first.parse(parser, state):
            for element in self.then_elements:
                element.parse(parser, state)
        # Otherwise, just explicitly set the variadic/optional variables and
        # type to empty
        else:
            for element in self.then_elements:
                element.set_empty(state)
        return ret

    def print(self, printer: Printer, state: PrintingState, op: IRDLOperation) -> None:
        if self.anchor.is_present(op):
            for element in (
                *self.then_whitespace,
                self.then_first,
                *self.then_elements,
            ):
                element.print(printer, state, op)

    def set_empty(self, state: ParsingState) -> None:
        self.then_first.set_empty(state)
        for element in self.then_elements:
            element.set_empty(state)

@dataclass(frozen=True)
class AttributeParameterVariable(FormatDirective):
    """
    A parameter variable for attributes, with the following format:
      parameter-directive ::= dollar-ident
    """

    name: str
    """The parameter name."""
    unique_base: type[Attribute] | None
    """The known base class of the Attribute parameter, if any."""
    unique_type: Attribute | None
    """The known type of the Attribute parameter, if any."""

    def parse_attribute(self, parser: Parser, state: AttributeParsingState, attr_def) -> None:
        """Parse an attribute parameter - this is where the magic happens."""
        if self.name in state.parameters:
            parser.raise_error(f"Parameter '{self.name}' already parsed")
        
        # The key insight: We need to parse the attribute based on the context
        if self.unique_base is not None:
            if issubclass(self.unique_base, ParametrizedAttribute):
                # For ParametrizedAttribute, check if we're parsing inline syntax
                if parser._current_token.kind == MLIRTokenKind.LESS:
                    # This is inline syntax - parse it using the attribute's own parser
                    # But we need to be careful about the syntax
                    value = self._parse_inline_attribute_smart(parser, self.unique_base)
                else:
                    # This is explicit syntax like #dialect.attr<...>
                    value = parser.parse_attribute()
            elif issubclass(self.unique_base, Data):
                # For Data attributes
                if parser._current_token.kind == MLIRTokenKind.LESS:
                    value = self.unique_base.new(self.unique_base.parse_parameter(parser))
                else:
                    value = parser.parse_attribute()
            else:
                # Generic attribute
                value = parser.parse_attribute()
        else:
            # No type constraint - parse generically
            value = parser.parse_attribute()
        
        # Validate the type if we have a constraint
        if self.unique_base is not None and not isinstance(value, self.unique_base):
            parser.raise_error(
                f"Expected {self.unique_base.__name__} for parameter '{self.name}', "
                f"got {type(value).__name__}"
            )
        
        state.parameters[self.name] = value

    def _parse_inline_attribute_smart(self, parser: Parser, attr_class) -> Attribute:
        """
        Smart parsing for inline attributes that handles assembly format correctly.
        """
        # Try to use the attribute's assembly format if it has one
        if hasattr(attr_class, 'parse_parameters_with_format'):
            try:
                # Use assembly format parsing
                parameters = attr_class.parse_parameters_with_format(parser)
                return attr_class.new(parameters)
            except Exception:
                # If assembly format fails, fall back to manual parsing
                pass
        
        # Manual parsing for attributes without assembly format or when it fails
        return self._parse_inline_manual(parser, attr_class)

    def _parse_inline_manual(self, parser: Parser, attr_class) -> Attribute:
        """Manual parsing for inline attribute syntax."""
        attr_def = attr_class.get_irdl_definition()
        
        parser.parse_punctuation("<")
        
        if parser.parse_optional_punctuation(">"):
            # Empty attribute
            if len(attr_def.parameters) == 0:
                return attr_class.new([])
            else:
                parser.raise_error(f"Expected parameters for {attr_class.__name__}")
        
        parameters = []
        
        # Handle single parameter specially (common case)
        if len(attr_def.parameters) == 1:
            param_name, _ = attr_def.parameters[0]
            
            # Try to parse "key = value" syntax first
            checkpoint = parser.pos
            try:
                if (parser._current_token.kind == MLIRTokenKind.BARE_IDENT and 
                    parser._current_token.text == param_name):
                    parser._consume_token()  # consume key
                    parser.parse_punctuation("=")
                    value = parser.parse_attribute()
                    parameters.append(value)
                else:
                    # Reset and parse as positional
                    parser._resume_from(checkpoint)
                    value = parser.parse_attribute()
                    parameters.append(value)
            except:
                # If key=value parsing fails, try positional
                parser._resume_from(checkpoint)
                value = parser.parse_attribute()
                parameters.append(value)
        else:
            # Multiple parameters - require key=value syntax
            parsed_params = {}
            
            while True:
                key = parser.parse_identifier("Expected parameter name")
                parser.parse_punctuation("=", "Expected '=' after parameter name")
                value = parser.parse_attribute()
                parsed_params[key] = value
                
                if parser.parse_optional_punctuation(">"):
                    break
                elif parser.parse_optional_punctuation(","):
                    continue
                else:
                    parser.raise_error("Expected ',' or '>' in attribute parameters")
            
            # Convert to ordered parameter list
            for param_name, _ in attr_def.parameters:
                if param_name not in parsed_params:
                    parser.raise_error(f"Missing parameter '{param_name}' in inline attribute")
                parameters.append(parsed_params[param_name])
        
        parser.parse_punctuation(">")
        return attr_class.new(parameters)

    def print_attribute(self, printer: Printer, state: AttributePrintingState, attr, attr_def) -> None:
        """Print an attribute parameter."""
        # Find parameter index
        param_index = None
        for i, (name, _) in enumerate(attr_def.parameters):
            if name == self.name:
                param_index = i
                break
        
        if param_index is None:
            raise ValueError(f"Unknown parameter '{self.name}'")
        
        param_value = attr.parameters[param_index]
        
        if state.should_emit_space and not state.last_was_punctuation:
            printer.print(" ")
        
        # Print based on unique_base
        if self.unique_base is None:
            printer.print_attribute(param_value)
        elif issubclass(self.unique_base, ParametrizedAttribute):
            # For ParametrizedAttribute, print inline parameters
            param_value.print_parameters(printer)
        elif issubclass(self.unique_base, Data):
            param_value.print_parameter(printer)
        else:
            printer.print_attribute(param_value)
        
        state.last_was_punctuation = False
        state.should_emit_space = True


