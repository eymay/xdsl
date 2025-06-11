"""
LWE (Learning With Errors) dialect implementation for xDSL
Provides LWE cryptographic types and operations
"""

from collections.abc import Sequence

from xdsl.dialects.builtin import IntegerAttr, IntegerType, ArrayAttr, StringAttr
from xdsl.ir import Attribute, Dialect, ParametrizedAttribute, TypeAttribute
from xdsl.irdl import (
    ParameterDef,
    irdl_attr_definition,
)
from xdsl.parser import Parser
from xdsl.printer import Printer

# Import our custom dialects
from xdsl.dialects.polynomial import RingAttr



@irdl_attr_definition
class InverseCanonicalEncodingAttr(ParametrizedAttribute):
    """
    An encoding attribute for inverse canonical embedding.
    
    Syntax: #lwe.inverse_canonical_encoding<scaling_factor = value>
    Example: #lwe.inverse_canonical_encoding<scaling_factor = 0>
    """
    name = "lwe.inverse_canonical_encoding"
    
    scaling_factor: ParameterDef[IntegerAttr]
    assembly_format = "`<` `scaling_factor` `=` $scaling_factor `>` attr-dict" 

@irdl_attr_definition
class FullCRTPackingEncodingAttr(ParametrizedAttribute):
    """
    An encoding attribute for full CRT packing.
    
    This encoding maps a list of integers via the Chinese Remainder Theorem (CRT) 
    into the plaintext space. This attribute can only be used in the context of 
    full CRT packing, where the polynomial f(x) splits completely (into linear 
    factors) and the number of slots equals the degree of f(x). This happens 
    when q is prime and q = 1 mod n.
    
    Syntax: #lwe.full_crt_packing_encoding<scaling_factor = value>
    Example: #lwe.full_crt_packing_encoding<scaling_factor = 0>
    """
    name = "lwe.full_crt_packing_encoding"
    
    scaling_factor: ParameterDef[IntegerAttr]
    assembly_format = "`<` `scaling_factor` `=` $scaling_factor `>` attr-dict"


@irdl_attr_definition
class KeyAttr(ParametrizedAttribute):
    """
    An attribute describing cryptographic keys.
    
    Syntax: #lwe.key<>
    Example: #lwe.key<>
    """
    name = "lwe.key"
    


@irdl_attr_definition
class ModulusChainAttr(ParametrizedAttribute):
    """
    An attribute describing modulus chains for RLWE schemes.
    
    Syntax: #lwe.modulus_chain<elements = <val1, val2, ...>, current = idx>
    Example: #lwe.modulus_chain<elements = <1095233372161 : i64, 1032955396097 : i64>, current = 0>
    """
    name = "lwe.modulus_chain"
    
    elements: ParameterDef[ArrayAttr]
    current: ParameterDef[IntegerAttr]
    assembly_format = "`<` `elements` `=` $elements `,` `current` `=` $current `>` attr-dict"

@irdl_attr_definition
class PlaintextSpaceAttr(ParametrizedAttribute):
    """
    An attribute describing the plaintext space.
    
    Syntax: #lwe.plaintext_space<ring = ring_attr, encoding = encoding_attr>
    Example: #lwe.plaintext_space<ring = #ring_Z65537_i64_1_x1024_, encoding = #inverse_canonical_encoding>
    """
    name = "lwe.plaintext_space"
    
    ring: ParameterDef[RingAttr]
    encoding: ParameterDef[Attribute]  # Could be various encoding types
    assembly_format = "`<` `ring` `=` $ring `,` `encoding` `=` $encoding `>` attr-dict"


@irdl_attr_definition
class CiphertextSpaceAttr(ParametrizedAttribute):
    """
    An attribute describing the ciphertext space.
    
    Syntax: #lwe.ciphertext_space<ring = ring_attr, encryption_type = type, size = value>
    Example: #lwe.ciphertext_space<ring = #ring_rns_L1_1_x1024_, encryption_type = lsb, size = 3>
    """
    name = "lwe.ciphertext_space"
    
    ring: ParameterDef[RingAttr]
    encryption_type: ParameterDef[StringAttr]  # "lsb", "msb", etc.
    size: ParameterDef[IntegerAttr]
    
    assembly_format = "`<` `ring` `=` $ring `,` `encryption_type` `=` $encryption_type `,` `size` `=` $size `>` attr-dict"

    def get_alias_suffix(self, os) -> None:
        """Helper method for generating type aliases."""
        self.ring.get_alias_suffix(os)
        if self.size.data != 2:
            os.write(f"_D{self.size.value}")


@irdl_attr_definition
class ApplicationDataAttr(ParametrizedAttribute):
    """
    An attribute describing application data semantics.
    
    Syntax: #lwe.application_data<message_type = type>
    Example: <message_type = i3>
    """
    name = "lwe.application_data"
    
    message_type: ParameterDef[Attribute]
    
    assembly_format = "`<` `message_type` `=` $message_type `>` attr-dict"


@irdl_attr_definition
class NewLWEPlaintextType(ParametrizedAttribute, TypeAttribute):
    """
    A type representing LWE plaintexts.
    
    Syntax: !lwe.new_lwe_plaintext<application_data = app_data, plaintext_space = space>
    Example: !lwe.new_lwe_plaintext<application_data = <message_type = i3>, plaintext_space = #plaintext_space>
    """
    name = "lwe.new_lwe_plaintext"
    
    application_data: ParameterDef[ApplicationDataAttr]
    plaintext_space: ParameterDef[PlaintextSpaceAttr]
    
    assembly_format = "`<` `application_data` `=` $application_data `,` `plaintext_space` `=` $plaintext_space `>` attr-dict"

@irdl_attr_definition
class NewLWECiphertextType(ParametrizedAttribute, TypeAttribute):
    """
    A type representing LWE ciphertexts.
    
    Syntax: !lwe.new_lwe_ciphertext<application_data = app_data, plaintext_space = space, 
                                   ciphertext_space = c_space, key = key_attr, modulus_chain = chain>
    """
    name = "lwe.new_lwe_ciphertext"
    
    application_data: ParameterDef[ApplicationDataAttr]
    plaintext_space: ParameterDef[PlaintextSpaceAttr]
    ciphertext_space: ParameterDef[CiphertextSpaceAttr]
    key: ParameterDef[KeyAttr]
    modulus_chain: ParameterDef[ModulusChainAttr]
    
    assembly_format = "`<` `application_data` `=` $application_data `,` `plaintext_space` `=` $plaintext_space `,` `ciphertext_space` `=` $ciphertext_space `,` `key` `=` $key `,` `modulus_chain` `=` $modulus_chain `>` attr-dict"

LWE = Dialect(
    "lwe",
    [
        # Operations would go here
    ],
    [
        InverseCanonicalEncodingAttr,
        FullCRTPackingEncodingAttr,
        KeyAttr,
        ModulusChainAttr,
        PlaintextSpaceAttr,
        CiphertextSpaceAttr,
        ApplicationDataAttr,
        NewLWEPlaintextType,
        NewLWECiphertextType,
    ],
)
