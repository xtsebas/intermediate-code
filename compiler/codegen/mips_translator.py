from typing import Dict, List, Optional, Tuple
from enum import Enum

from compiler.ir.triplet import Triplet, OpCode, Operand
from compiler.codegen.register_allocator import RegisterPool, RegisterType, AllocationLocation


class MIPSInstruction:
    """Representa una instrucción MIPS individual"""

    def __init__(self, opcode: str, args: List[str] = None, comment: str = None):
        self.opcode = opcode
        self.args = args or []
        self.comment = comment

    def __str__(self) -> str:
        if not self.args:
            result = self.opcode
        else:
            result = f"{self.opcode} {', '.join(self.args)}"

        if self.comment:
            result = f"{result:<40} # {self.comment}"

        return result

    def __repr__(self) -> str:
        return f"MIPSInstruction({self.opcode}, {self.args})"


class MIPSTranslator:
    """
    Traductor de TAC a MIPS Assembly.

    Maneja la traducción de tripletos TAC a instrucciones MIPS,
    incluyendo gestión de registros mediante RegisterPool.
    """

    def __init__(self, use_saved_regs: bool = False):
        """
        Inicializa el traductor MIPS.

        Args:
            use_saved_regs: Si True, usa registros s0-s7; si False, solo t0-t9
        """
        self.register_pool = RegisterPool(use_saved_regs=use_saved_regs)
        self.instructions: List[MIPSInstruction] = []
        self.operand_to_register: Dict[str, RegisterType] = {}
        self.operand_to_spill_offset: Dict[str, int] = {}
        self.next_spill_offset = -4  # Offset para spillage (relativo a $fp)

    def translate(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce un triplet TAC a instrucciones MIPS.

        Args:
            triplet: Triplet a traducir

        Returns:
            Lista de instrucciones MIPS generadas
        """
        instructions = []

        # Detectar tipo de operación y delegar
        if triplet.is_arithmetic():
            instructions = self._translate_arithmetic(triplet)
        elif triplet.is_logical():
            instructions = self._translate_logical(triplet)
        elif triplet.is_comparison():
            instructions = self._translate_comparison(triplet)
        elif triplet.op == OpCode.MOV:
            instructions = self._translate_mov(triplet)
        elif triplet.op == OpCode.LABEL:
            instructions = self._translate_label(triplet)
        else:
            # Operación no reconocida
            instructions = [MIPSInstruction("nop", comment=f"Unsupported: {triplet.op.value}")]

        return instructions

    # ========== OPERACIONES ARITMÉTICAS ==========

    def _translate_arithmetic(self, triplet: Triplet) -> List[MIPSInstruction]:
        """Traduce operaciones aritméticas (ADD, SUB, MUL, DIV, MOD, NEG)"""
        instructions = []

        if triplet.op == OpCode.ADD:
            instructions = self._translate_add(triplet)
        elif triplet.op == OpCode.SUB:
            instructions = self._translate_sub(triplet)
        elif triplet.op == OpCode.MUL:
            instructions = self._translate_mul(triplet)
        elif triplet.op == OpCode.DIV:
            instructions = self._translate_div(triplet)
        elif triplet.op == OpCode.MOD:
            instructions = self._translate_mod(triplet)
        elif triplet.op == OpCode.NEG:
            instructions = self._translate_neg(triplet)

        return instructions

    def _translate_add(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce ADD: result = arg1 + arg2

        MIPS:
            lw $t0, addr(arg1)     # Cargar arg1
            lw $t1, addr(arg2)     # Cargar arg2
            addu $t2, $t0, $t1     # Sumar
            sw $t2, addr(result)   # Guardar resultado
        """
        instructions = []

        # Obtener registros para operandos
        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2)
        reg_result = self._get_result_register(triplet.result)

        # Cargar arg1 si es necesario
        if self._is_memory_operand(triplet.arg1):
            instructions.append(
                MIPSInstruction("lw", [f"${reg_arg1.value}", self._get_operand_address(triplet.arg1)],
                              f"Load arg1: {triplet.arg1}")
            )
        else:
            instructions.extend(self._load_operand(triplet.arg1, reg_arg1))

        # Cargar arg2 si es necesario
        if self._is_memory_operand(triplet.arg2):
            instructions.append(
                MIPSInstruction("lw", [f"${reg_arg2.value}", self._get_operand_address(triplet.arg2)],
                              f"Load arg2: {triplet.arg2}")
            )
        else:
            instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        # Realizar suma
        instructions.append(
            MIPSInstruction("addu", [f"${reg_result.value}", f"${reg_arg1.value}", f"${reg_arg2.value}"],
                          f"{triplet.result} = {triplet.arg1} + {triplet.arg2}")
        )

        # Guardar resultado
        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    def _translate_sub(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce SUB: result = arg1 - arg2

        MIPS:
            lw $t0, addr(arg1)
            lw $t1, addr(arg2)
            subu $t2, $t0, $t1
            sw $t2, addr(result)
        """
        instructions = []

        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2)
        reg_result = self._get_result_register(triplet.result)

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        instructions.append(
            MIPSInstruction("subu", [f"${reg_result.value}", f"${reg_arg1.value}", f"${reg_arg2.value}"],
                          f"{triplet.result} = {triplet.arg1} - {triplet.arg2}")
        )

        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    def _translate_mul(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce MUL: result = arg1 * arg2

        MIPS:
            lw $t0, addr(arg1)
            lw $t1, addr(arg2)
            mult $t0, $t1          # Multiplicar (resultado en HI:LO)
            mflo $t2               # Mover LO a $t2
            sw $t2, addr(result)
        """
        instructions = []

        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2)
        reg_result = self._get_result_register(triplet.result)

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        # Multiplicar
        instructions.append(
            MIPSInstruction("mult", [f"${reg_arg1.value}", f"${reg_arg2.value}"],
                          "Multiply")
        )

        # Mover resultado de LO a registro
        instructions.append(
            MIPSInstruction("mflo", [f"${reg_result.value}"],
                          "Move from LO")
        )

        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    def _translate_div(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce DIV: result = arg1 / arg2

        MIPS:
            lw $t0, addr(arg1)
            lw $t1, addr(arg2)
            div $t0, $t1           # Dividir
            mflo $t2               # Cociente en LO
            sw $t2, addr(result)
        """
        instructions = []

        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2)
        reg_result = self._get_result_register(triplet.result)

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        # Dividir
        instructions.append(
            MIPSInstruction("div", [f"${reg_arg1.value}", f"${reg_arg2.value}"],
                          "Divide")
        )

        # Mover cociente a registro
        instructions.append(
            MIPSInstruction("mflo", [f"${reg_result.value}"],
                          "Move quotient from LO")
        )

        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    def _translate_mod(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce MOD: result = arg1 % arg2

        MIPS:
            lw $t0, addr(arg1)
            lw $t1, addr(arg2)
            div $t0, $t1           # Dividir
            mfhi $t2               # Resto en HI
            sw $t2, addr(result)
        """
        instructions = []

        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2)
        reg_result = self._get_result_register(triplet.result)

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        # Dividir
        instructions.append(
            MIPSInstruction("div", [f"${reg_arg1.value}", f"${reg_arg2.value}"],
                          "Divide")
        )

        # Mover resto a registro
        instructions.append(
            MIPSInstruction("mfhi", [f"${reg_result.value}"],
                          "Move remainder from HI")
        )

        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    def _translate_neg(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce NEG: result = -arg1

        MIPS:
            lw $t0, addr(arg1)
            negu $t1, $t0          # O: subu $t1, $zero, $t0
            sw $t1, addr(result)
        """
        instructions = []

        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_result = self._get_result_register(triplet.result)

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))

        # Negar (equivalente a: 0 - arg1)
        instructions.append(
            MIPSInstruction("subu", [f"${reg_result.value}", "$zero", f"${reg_arg1.value}"],
                          f"{triplet.result} = -{triplet.arg1}")
        )

        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    # ========== OPERACIONES LÓGICAS ==========

    def _translate_logical(self, triplet: Triplet) -> List[MIPSInstruction]:
        """Traduce operaciones lógicas (AND, OR, NOT)"""
        instructions = []

        if triplet.op == OpCode.AND:
            instructions = self._translate_and(triplet)
        elif triplet.op == OpCode.OR:
            instructions = self._translate_or(triplet)
        elif triplet.op == OpCode.NOT:
            instructions = self._translate_not(triplet)

        return instructions

    def _translate_and(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce AND: result = arg1 & arg2

        MIPS:
            lw $t0, addr(arg1)
            lw $t1, addr(arg2)
            and $t2, $t0, $t1
            sw $t2, addr(result)
        """
        instructions = []

        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2)
        reg_result = self._get_result_register(triplet.result)

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        instructions.append(
            MIPSInstruction("and", [f"${reg_result.value}", f"${reg_arg1.value}", f"${reg_arg2.value}"],
                          f"{triplet.result} = {triplet.arg1} & {triplet.arg2}")
        )

        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    def _translate_or(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce OR: result = arg1 | arg2

        MIPS:
            lw $t0, addr(arg1)
            lw $t1, addr(arg2)
            or $t2, $t0, $t1
            sw $t2, addr(result)
        """
        instructions = []

        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2)
        reg_result = self._get_result_register(triplet.result)

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        instructions.append(
            MIPSInstruction("or", [f"${reg_result.value}", f"${reg_arg1.value}", f"${reg_arg2.value}"],
                          f"{triplet.result} = {triplet.arg1} | {triplet.arg2}")
        )

        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    def _translate_not(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce NOT: result = !arg1

        MIPS:
            lw $t0, addr(arg1)
            nor $t1, $t0, $zero    # NOT logico
            sw $t1, addr(result)
        """
        instructions = []

        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_result = self._get_result_register(triplet.result)

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))

        instructions.append(
            MIPSInstruction("nor", [f"${reg_result.value}", f"${reg_arg1.value}", "$zero"],
                          f"{triplet.result} = !{triplet.arg1}")
        )

        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    # ========== COMPARACIONES ==========

    def _translate_comparison(self, triplet: Triplet) -> List[MIPSInstruction]:
        """Traduce comparaciones (EQ, NE, LT, LE, GT, GE)"""
        instructions = []

        if triplet.op == OpCode.EQ:
            instructions = self._translate_eq(triplet)
        elif triplet.op == OpCode.NE:
            instructions = self._translate_ne(triplet)
        elif triplet.op == OpCode.LT:
            instructions = self._translate_lt(triplet)
        elif triplet.op == OpCode.LE:
            instructions = self._translate_le(triplet)
        elif triplet.op == OpCode.GT:
            instructions = self._translate_gt(triplet)
        elif triplet.op == OpCode.GE:
            instructions = self._translate_ge(triplet)

        return instructions

    def _translate_eq(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce EQ: result = (arg1 == arg2) ? 1 : 0

        MIPS:
            lw $t0, addr(arg1)
            lw $t1, addr(arg2)
            seq $t2, $t0, $t1      # Set if equal (pseudo-instrucción)
            sw $t2, addr(result)
        """
        instructions = []

        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2)
        reg_result = self._get_result_register(triplet.result)

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        # seq es una pseudo-instrucción que se expande a:
        # subu $t2, $t0, $t1; nor $t2, $t2, $zero
        instructions.append(
            MIPSInstruction("subu", [f"${reg_result.value}", f"${reg_arg1.value}", f"${reg_arg2.value}"],
                          "Subtract for equality check")
        )
        instructions.append(
            MIPSInstruction("nor", [f"${reg_result.value}", f"${reg_result.value}", "$zero"],
                          f"{triplet.result} = ({triplet.arg1} == {triplet.arg2})")
        )

        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    def _translate_ne(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce NE: result = (arg1 != arg2) ? 1 : 0

        MIPS:
            lw $t0, addr(arg1)
            lw $t1, addr(arg2)
            sne $t2, $t0, $t1
            sw $t2, addr(result)
        """
        instructions = []

        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2)
        reg_result = self._get_result_register(triplet.result)

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        # sne se expande a: subu $t2, $t0, $t1; sltu $t2, $zero, $t2
        instructions.append(
            MIPSInstruction("subu", [f"${reg_result.value}", f"${reg_arg1.value}", f"${reg_arg2.value}"],
                          "Subtract for inequality check")
        )
        instructions.append(
            MIPSInstruction("sltu", [f"${reg_result.value}", "$zero", f"${reg_result.value}"],
                          f"{triplet.result} = ({triplet.arg1} != {triplet.arg2})")
        )

        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    def _translate_lt(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce LT: result = (arg1 < arg2) ? 1 : 0

        MIPS:
            lw $t0, addr(arg1)
            lw $t1, addr(arg2)
            slt $t2, $t0, $t1
            sw $t2, addr(result)
        """
        instructions = []

        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2)
        reg_result = self._get_result_register(triplet.result)

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        instructions.append(
            MIPSInstruction("slt", [f"${reg_result.value}", f"${reg_arg1.value}", f"${reg_arg2.value}"],
                          f"{triplet.result} = ({triplet.arg1} < {triplet.arg2})")
        )

        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    def _translate_le(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce LE: result = (arg1 <= arg2) ? 1 : 0

        MIPS:
            lw $t0, addr(arg1)
            lw $t1, addr(arg2)
            slt $t2, $t1, $t0      # arg2 < arg1
            nor $t2, $t2, $zero    # NOT (arg2 < arg1)
            sw $t2, addr(result)
        """
        instructions = []

        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2)
        reg_result = self._get_result_register(triplet.result)

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        # arg1 <= arg2 es equivalente a NOT(arg2 < arg1)
        instructions.append(
            MIPSInstruction("slt", [f"${reg_result.value}", f"${reg_arg2.value}", f"${reg_arg1.value}"],
                          "Check if arg2 < arg1")
        )
        instructions.append(
            MIPSInstruction("nor", [f"${reg_result.value}", f"${reg_result.value}", "$zero"],
                          f"{triplet.result} = ({triplet.arg1} <= {triplet.arg2})")
        )

        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    def _translate_gt(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce GT: result = (arg1 > arg2) ? 1 : 0

        MIPS:
            lw $t0, addr(arg1)
            lw $t1, addr(arg2)
            slt $t2, $t1, $t0      # arg2 < arg1
            sw $t2, addr(result)
        """
        instructions = []

        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2)
        reg_result = self._get_result_register(triplet.result)

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        # arg1 > arg2 es equivalente a arg2 < arg1
        instructions.append(
            MIPSInstruction("slt", [f"${reg_result.value}", f"${reg_arg2.value}", f"${reg_arg1.value}"],
                          f"{triplet.result} = ({triplet.arg1} > {triplet.arg2})")
        )

        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    def _translate_ge(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce GE: result = (arg1 >= arg2) ? 1 : 0

        MIPS:
            lw $t0, addr(arg1)
            lw $t1, addr(arg2)
            slt $t2, $t0, $t1      # arg1 < arg2
            nor $t2, $t2, $zero    # NOT (arg1 < arg2)
            sw $t2, addr(result)
        """
        instructions = []

        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2)
        reg_result = self._get_result_register(triplet.result)

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        # arg1 >= arg2 es equivalente a NOT(arg1 < arg2)
        instructions.append(
            MIPSInstruction("slt", [f"${reg_result.value}", f"${reg_arg1.value}", f"${reg_arg2.value}"],
                          "Check if arg1 < arg2")
        )
        instructions.append(
            MIPSInstruction("nor", [f"${reg_result.value}", f"${reg_result.value}", "$zero"],
                          f"{triplet.result} = ({triplet.arg1} >= {triplet.arg2})")
        )

        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    # ========== MOV Y ASIGNACIONES ==========

    def _translate_mov(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce MOV: result = arg1

        MIPS:
            lw $t0, addr(arg1)
            sw $t0, addr(result)
        """
        instructions = []

        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_result = self._get_result_register(triplet.result)

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))

        # Si arg1 es constante, podemos usar addiu
        if triplet.arg1.is_constant():
            instructions = [
                MIPSInstruction("addiu", [f"${reg_result.value}", "$zero", str(triplet.arg1.value)],
                              f"{triplet.result} = {triplet.arg1}")
            ]
        else:
            instructions.append(
                MIPSInstruction("addu", [f"${reg_result.value}", f"${reg_arg1.value}", "$zero"],
                              f"{triplet.result} = {triplet.arg1}")
            )

        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    def _translate_label(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce LABEL: etiqueta

        MIPS:
            label_name:
        """
        label_name = str(triplet.arg1.value) if triplet.arg1 else "unknown_label"
        return [MIPSInstruction(f"{label_name}:", comment="Label")]

    # ========== UTILIDADES ==========

    def _get_operand_register(self, operand: Operand) -> RegisterType:
        """Obtiene un registro para un operando"""
        operand_name = str(operand.value)

        if operand_name not in self.operand_to_register:
            reg_type, _ = self.register_pool.getReg(operand_name)
            self.operand_to_register[operand_name] = reg_type

        return self.operand_to_register[operand_name]

    def _get_result_register(self, operand: Operand) -> RegisterType:
        """Obtiene un registro para el resultado"""
        operand_name = str(operand.value)

        if operand_name not in self.operand_to_register:
            reg_type, _ = self.register_pool.getReg(operand_name)
            self.operand_to_register[operand_name] = reg_type

        return self.operand_to_register[operand_name]

    def _is_memory_operand(self, operand: Operand) -> bool:
        """Verifica si un operando está en memoria (variable)"""
        return operand.is_variable()

    def _get_operand_address(self, operand: Operand) -> str:
        """Obtiene la dirección de un operando en memoria"""
        operand_name = str(operand.value)

        # Si está spilleado, retornar su offset
        if operand_name in self.operand_to_spill_offset:
            offset = self.operand_to_spill_offset[operand_name]
            return f"{offset}($fp)"

        # Si no, asumir que es una variable en memoria
        return f"0($fp)  # {operand_name}"

    def _load_operand(self, operand: Operand, reg: RegisterType) -> List[MIPSInstruction]:
        """Carga un operando en un registro"""
        instructions = []

        if operand.is_constant():
            # Cargar constante con addiu
            instructions.append(
                MIPSInstruction("addiu", [f"${reg.value}", "$zero", str(operand.value)],
                              f"Load constant: {operand.value}")
            )
        elif operand.is_variable():
            # Cargar variable de memoria
            instructions.append(
                MIPSInstruction("lw", [f"${reg.value}", self._get_operand_address(operand)],
                              f"Load variable: {operand.value}")
            )
        elif operand.is_temporary():
            # El temporal ya está en un registro, nada que hacer
            pass

        return instructions

    def _store_result(self, result: Operand, reg: RegisterType) -> List[MIPSInstruction]:
        """Almacena un resultado desde un registro"""
        instructions = []

        if result.is_variable():
            instructions.append(
                MIPSInstruction("sw", [f"${reg.value}", self._get_operand_address(result)],
                              f"Store result: {result.value}")
            )

        return instructions

    def emit(self, instruction: MIPSInstruction):
        """Emite una instrucción MIPS"""
        self.instructions.append(instruction)

    def emit_instructions(self, instructions: List[MIPSInstruction]):
        """Emite múltiples instrucciones MIPS"""
        self.instructions.extend(instructions)

    def get_instructions(self) -> List[MIPSInstruction]:
        """Obtiene todas las instrucciones emitidas"""
        return self.instructions.copy()

    def get_assembly(self) -> str:
        """Retorna el código assembly completo"""
        return "\n".join(str(instr) for instr in self.instructions)

    def reset(self):
        """Reinicia el traductor"""
        self.register_pool.reset()
        self.instructions.clear()
        self.operand_to_register.clear()
        self.operand_to_spill_offset.clear()
        self.next_spill_offset = -4

    def __str__(self) -> str:
        return f"MIPSTranslator({len(self.instructions)} instructions)"
