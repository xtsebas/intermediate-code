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

        # Estado de funciones y control de flujo
        self.current_function: Optional[str] = None
        self.function_param_count: Dict[str, int] = {}
        self.pending_params: List[str] = []  # Parámetros pendientes para llamada

        # Estado de memoria y arrays
        self.array_info: Dict[str, Dict] = {}  # array_name -> {size, element_size, base_addr}
        self.heap_ptr = 0x10000000  # Puntero inicial del heap (MIPS)
        self.array_to_register: Dict[str, RegisterType] = {}  # array_name -> registro con dirección

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
        elif triplet.op == OpCode.JMP:
            instructions = self._translate_jmp(triplet)
        elif triplet.op == OpCode.BEQ:
            instructions = self._translate_beq(triplet)
        elif triplet.op == OpCode.BNE:
            instructions = self._translate_bne(triplet)
        elif triplet.op == OpCode.BLT:
            instructions = self._translate_blt(triplet)
        elif triplet.op == OpCode.BLE:
            instructions = self._translate_ble(triplet)
        elif triplet.op == OpCode.BGT:
            instructions = self._translate_bgt(triplet)
        elif triplet.op == OpCode.BGE:
            instructions = self._translate_bge(triplet)
        elif triplet.op == OpCode.BZ:
            instructions = self._translate_bz(triplet)
        elif triplet.op == OpCode.BNZ:
            instructions = self._translate_bnz(triplet)
        elif triplet.op == OpCode.PARAM:
            instructions = self._translate_param(triplet)
        elif triplet.op == OpCode.CALL:
            instructions = self._translate_call(triplet)
        elif triplet.op == OpCode.RETURN:
            instructions = self._translate_return(triplet)
        elif triplet.op == OpCode.ENTER:
            instructions = self._translate_enter(triplet)
        elif triplet.op == OpCode.EXIT:
            instructions = self._translate_exit(triplet)
        elif triplet.op == OpCode.ARRAY_ALLOC:
            instructions = self._translate_array_alloc(triplet)
        elif triplet.op == OpCode.ARRAY_GET:
            instructions = self._translate_array_get(triplet)
        elif triplet.op == OpCode.ARRAY_SET:
            instructions = self._translate_array_set(triplet)
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

        # Si arg1 es constante, podemos usar addiu (solo para numéricos)
        if triplet.arg1.is_constant():
            value = triplet.arg1.value
            # Evitar inmediatos string inválidos en MIPS: usar 0 como placeholder
            imm = 0 if isinstance(value, str) else value
            instructions = [
                MIPSInstruction(
                    "addiu",
                    [f"${reg_result.value}", "$zero", str(imm)],
                    f"{triplet.result} = {triplet.arg1}",
                )
            ]
        else:
            instructions.append(
                MIPSInstruction(
                    "addu",
                    [f"${reg_result.value}", f"${reg_arg1.value}", "$zero"],
                    f"{triplet.result} = {triplet.arg1}",
                )
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

        # Asignar un offset único por operando (variable/temporal en memoria)
        # para evitar aliasing accidental entre símbolos distintos.
        if operand_name not in self.operand_to_spill_offset:
            self.operand_to_spill_offset[operand_name] = self.next_spill_offset
            self.next_spill_offset -= 4

        offset = self.operand_to_spill_offset[operand_name]
        return f"{offset}($fp)"

    def _load_operand(self, operand: Operand, reg: RegisterType) -> List[MIPSInstruction]:
        """Carga un operando en un registro"""
        instructions = []

        if operand.is_constant():
            # Cargar constante con addiu.
            # Para strings, usamos 0 como placeholder para evitar inmediatos inválidos.
            value = operand.value
            imm = 0 if isinstance(value, str) else value
            instructions.append(
                MIPSInstruction(
                    "addiu",
                    [f"${reg.value}", "$zero", str(imm)],
                    f"Load constant: {operand.value}",
                )
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

    # ========== CONTROL DE FLUJO ==========

    def _translate_jmp(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce JMP: salto incondicional

        MIPS:
            j label
        """
        label = None
        if triplet.result is not None and triplet.result.value not in (None, ""):
            label = str(triplet.result.value)

        # Evitar 'j' sin destino, que no es válido en MARS.
        if not label:
            return [MIPSInstruction("nop", comment="Unsupported: j with no target")]

        return [MIPSInstruction("j", [label], f"Jump to {label}")]

    def _translate_beq(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce BEQ: branch if equal

        MIPS:
            beq $t0, $t1, label
        """
        instructions = []
        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2) if triplet.arg2 else RegisterType.T0

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        label = str(triplet.result.value) if triplet.result else "unknown"
        instructions.append(
            MIPSInstruction("beq", [f"${reg_arg1.value}", f"${reg_arg2.value}", label],
                          f"Branch if {triplet.arg1} == {triplet.arg2}")
        )

        return instructions

    def _translate_bne(self, triplet: Triplet) -> List[MIPSInstruction]:
        """Traduce BNE: branch if not equal"""
        instructions = []
        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2) if triplet.arg2 else RegisterType.T0

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        label = str(triplet.result.value) if triplet.result else "unknown"
        instructions.append(
            MIPSInstruction("bne", [f"${reg_arg1.value}", f"${reg_arg2.value}", label],
                          f"Branch if {triplet.arg1} != {triplet.arg2}")
        )

        return instructions

    def _translate_blt(self, triplet: Triplet) -> List[MIPSInstruction]:
        """Traduce BLT: branch if less than"""
        instructions = []
        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2) if triplet.arg2 else RegisterType.T0

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        label = str(triplet.result.value) if triplet.result else "unknown"
        instructions.append(
            MIPSInstruction("slt", ["$at", f"${reg_arg1.value}", f"${reg_arg2.value}"],
                          "Check arg1 < arg2")
        )
        instructions.append(
            MIPSInstruction("bne", ["$at", "$zero", label],
                          f"Branch if {triplet.arg1} < {triplet.arg2}")
        )

        return instructions

    def _translate_ble(self, triplet: Triplet) -> List[MIPSInstruction]:
        """Traduce BLE: branch if less than or equal"""
        instructions = []
        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2) if triplet.arg2 else RegisterType.T0

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        label = str(triplet.result.value) if triplet.result else "unknown"
        # arg1 <= arg2 equivale a NOT(arg2 < arg1)
        instructions.append(
            MIPSInstruction("slt", ["$at", f"${reg_arg2.value}", f"${reg_arg1.value}"],
                          "Check arg2 < arg1")
        )
        instructions.append(
            MIPSInstruction("beq", ["$at", "$zero", label],
                          f"Branch if {triplet.arg1} <= {triplet.arg2}")
        )

        return instructions

    def _translate_bgt(self, triplet: Triplet) -> List[MIPSInstruction]:
        """Traduce BGT: branch if greater than"""
        instructions = []
        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2) if triplet.arg2 else RegisterType.T0

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        label = str(triplet.result.value) if triplet.result else "unknown"
        # arg1 > arg2 equivale a arg2 < arg1
        instructions.append(
            MIPSInstruction("slt", ["$at", f"${reg_arg2.value}", f"${reg_arg1.value}"],
                          "Check arg2 < arg1")
        )
        instructions.append(
            MIPSInstruction("bne", ["$at", "$zero", label],
                          f"Branch if {triplet.arg1} > {triplet.arg2}")
        )

        return instructions

    def _translate_bge(self, triplet: Triplet) -> List[MIPSInstruction]:
        """Traduce BGE: branch if greater than or equal"""
        instructions = []
        reg_arg1 = self._get_operand_register(triplet.arg1)
        reg_arg2 = self._get_operand_register(triplet.arg2) if triplet.arg2 else RegisterType.T0

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))
        instructions.extend(self._load_operand(triplet.arg2, reg_arg2))

        label = str(triplet.result.value) if triplet.result else "unknown"
        # arg1 >= arg2 equivale a NOT(arg1 < arg2)
        instructions.append(
            MIPSInstruction("slt", ["$at", f"${reg_arg1.value}", f"${reg_arg2.value}"],
                          "Check arg1 < arg2")
        )
        instructions.append(
            MIPSInstruction("beq", ["$at", "$zero", label],
                          f"Branch if {triplet.arg1} >= {triplet.arg2}")
        )

        return instructions

    def _translate_bz(self, triplet: Triplet) -> List[MIPSInstruction]:
        """Traduce BZ: branch if zero"""
        instructions = []
        reg_arg1 = self._get_operand_register(triplet.arg1)

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))

        label = str(triplet.result.value) if triplet.result else "unknown"
        instructions.append(
            MIPSInstruction("beq", [f"${reg_arg1.value}", "$zero", label],
                          f"Branch if {triplet.arg1} == 0")
        )

        return instructions

    def _translate_bnz(self, triplet: Triplet) -> List[MIPSInstruction]:
        """Traduce BNZ: branch if not zero"""
        instructions = []
        reg_arg1 = self._get_operand_register(triplet.arg1)

        instructions.extend(self._load_operand(triplet.arg1, reg_arg1))

        label = str(triplet.result.value) if triplet.result else "unknown"
        instructions.append(
            MIPSInstruction("bne", [f"${reg_arg1.value}", "$zero", label],
                          f"Branch if {triplet.arg1} != 0")
        )

        return instructions

    # ========== FUNCIONES Y LLAMADAS ==========

    def _translate_enter(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce ENTER: inicio de función

        MIPS:
            # Prólogo de función
            subu $sp, $sp, frame_size
            sw $ra, offset($sp)
        """
        instructions = []
        func_name = str(triplet.arg1.value) if triplet.arg1 else "unknown"
        param_count = triplet.arg2.value if triplet.arg2 else 0

        self.current_function = func_name
        self.function_param_count[func_name] = param_count

        # Comentario de entrada a función
        instructions.append(
            MIPSInstruction("", comment=f"Function: {func_name} (params: {param_count})")
        )

        # Prólogo: reservar espacio en stack (simplificado)
        frame_size = 8 + param_count * 4  # RA + FP + parámetros
        instructions.append(
            MIPSInstruction("subu", ["$sp", "$sp", str(frame_size)],
                          f"Allocate stack frame ({frame_size} bytes)")
        )

        # Guardar dirección de retorno
        instructions.append(
            MIPSInstruction("sw", ["$ra", "4($sp)"],
                          "Save return address")
        )

        # Guardar frame pointer anterior
        instructions.append(
            MIPSInstruction("sw", ["$fp", "0($sp)"],
                          "Save frame pointer")
        )

        # Establecer nuevo frame pointer
        instructions.append(
            MIPSInstruction("addu", ["$fp", "$sp", str(frame_size)],
                          "Set frame pointer")
        )

        return instructions

    def _translate_exit(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce EXIT: salida de función

        MIPS:
            # Epílogo de función
            lw $ra, offset($sp)
            lw $fp, offset($sp)
            addu $sp, $sp, frame_size
            jr $ra
        """
        instructions = []
        func_name = str(triplet.arg1.value) if triplet.arg1 else "unknown"

        # Obtener tamaño del frame (simplificado)
        frame_size = 8 + self.function_param_count.get(func_name, 0) * 4

        # Restaurar dirección de retorno
        instructions.append(
            MIPSInstruction("lw", ["$ra", "4($sp)"],
                          "Restore return address")
        )

        # Restaurar frame pointer anterior
        instructions.append(
            MIPSInstruction("lw", ["$fp", "0($sp)"],
                          "Restore frame pointer")
        )

        # Liberar stack frame
        instructions.append(
            MIPSInstruction("addu", ["$sp", "$sp", str(frame_size)],
                          f"Deallocate stack frame ({frame_size} bytes)")
        )

        # Retornar
        instructions.append(
            MIPSInstruction("jr", ["$ra"],
                          "Return from function")
        )

        self.current_function = None

        return instructions

    def _translate_param(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce PARAM: parámetro para llamada de función

        Almacena el parámetro en un registro de argumento (a0-a3)
        o en el stack si hay más de 4 parámetros.
        """
        instructions = []

        # Guardar el parámetro para la próxima llamada
        reg_arg = self._get_operand_register(triplet.arg1)
        instructions.extend(self._load_operand(triplet.arg1, reg_arg))

        # Determinar en qué registro ir: a0, a1, a2, a3
        param_index = len(self.pending_params)
        if param_index < 4:
            arg_reg_names = ["$a0", "$a1", "$a2", "$a3"]
            instructions.append(
                MIPSInstruction("addu", [arg_reg_names[param_index], f"${reg_arg.value}", "$zero"],
                              f"Set parameter {param_index}")
            )
        else:
            # Parámetro va al stack
            stack_offset = (param_index - 4) * 4
            instructions.append(
                MIPSInstruction("sw", [f"${reg_arg.value}", f"{stack_offset}($sp)"],
                              f"Push parameter {param_index}")
            )

        self.pending_params.append(str(triplet.arg1.value))

        return instructions

    def _translate_call(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce CALL: llamada a función

        MIPS:
            # Parámetros ya están en a0-a3 (y stack si es necesario)
            jal function_name
            # v0 contiene el retorno
            move $t0, $v0       # Mover resultado si es necesario
        """
        instructions = []

        func_name = str(triplet.arg1.value) if triplet.arg1 else "unknown"
        param_count = triplet.arg2.value if triplet.arg2 else 0

        # Llamada a función (jump and link)
        instructions.append(
            MIPSInstruction("jal", [func_name],
                          f"Call function {func_name} ({param_count} params)")
        )

        # Si hay resultado, moverlo desde $v0
        if triplet.result:
            reg_result = self._get_result_register(triplet.result)
            instructions.append(
                MIPSInstruction("addu", [f"${reg_result.value}", "$v0", "$zero"],
                              f"Move return value to {triplet.result}")
            )
            instructions.extend(self._store_result(triplet.result, reg_result))

        # Limpiar parámetros pendientes
        self.pending_params.clear()

        return instructions

    def _translate_return(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce RETURN: retorno de función

        MIPS:
            # Si hay valor de retorno
            lw $v0, addr(arg1)  # Cargar valor de retorno
            jr $ra              # Retornar
        """
        instructions = []

        if triplet.arg1:
            # Hay valor de retorno
            reg_arg1 = self._get_operand_register(triplet.arg1)
            instructions.extend(self._load_operand(triplet.arg1, reg_arg1))

            # Mover a $v0 (registro de retorno)
            instructions.append(
                MIPSInstruction("addu", ["$v0", f"${reg_arg1.value}", "$zero"],
                              f"Set return value: {triplet.arg1}")
            )
        else:
            # Sin valor de retorno
            instructions.append(
                MIPSInstruction("", comment="Return from function (no value)")
            )

        return instructions

    # ========== ARRAYS Y MEMORIA ==========

    def _translate_array_alloc(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce ARRAY_ALLOC: allocar array en el heap

        MIPS:
            # Calcular tamaño en bytes
            li $a0, size_in_bytes
            # Llamada a syscall 9 (sbrk) para asignar memoria
            li $v0, 9
            syscall
            # $v0 contiene la dirección base del array

        En simuladores simples, usamos pseudo-instrucciones:
            # Cargar dirección en un registro
            la $t0, array_label
        """
        instructions = []

        array_name = str(triplet.result.value) if triplet.result else "unknown_array"
        size = triplet.arg1.value if triplet.arg1 and triplet.arg1.is_constant() else 1
        element_size = triplet.arg2.value if triplet.arg2 and triplet.arg2.is_constant() else 4

        total_size = size * element_size

        # Registrar información del array
        self.array_info[array_name] = {
            'size': size,
            'element_size': element_size,
            'total_size': total_size,
            'base_addr': self.heap_ptr
        }

        # Obtener registro para almacenar dirección base
        reg_result = self._get_result_register(triplet.result)
        self.array_to_register[array_name] = reg_result

        # Cargar dirección base usando la pseudo-instrucción la (load address)
        # En MIPS real, esto sería li $t0, base_addr
        instructions.append(
            MIPSInstruction("li", [f"${reg_result.value}", f"0x{self.heap_ptr:x}"],
                          f"Load array base address for {array_name}")
        )

        # Actualizar puntero del heap
        self.heap_ptr += total_size

        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    def _translate_array_get(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce ARRAY_GET: obtener elemento del array

        MIPS:
            # Calcular dirección efectiva: base + (index * element_size)
            lw $t0, base_addr       # Cargar dirección base
            lw $t1, index           # Cargar índice
            li $t2, element_size    # Cargar tamaño de elemento
            mult $t1, $t2           # index * element_size
            mflo $t3                # Resultado en $t3
            addu $t4, $t0, $t3      # Dirección efectiva
            lw $t5, 0($t4)          # Cargar elemento
        """
        instructions = []

        # Soporte para forma generada por ArrayCodeGen:
        # ARRAY_GET addr -> result, donde addr es una dirección efectiva ya calculada.
        if triplet.arg1 is not None and triplet.arg1.is_temporary() and triplet.arg2 is None:
            reg_addr = self._get_operand_register(triplet.arg1)
            reg_result = self._get_result_register(triplet.result)

            instructions.append(
                MIPSInstruction("", comment="ARRAY_GET (addr, result)")
            )
            instructions.append(
                MIPSInstruction("lw", [f"${reg_result.value}", f"0(${reg_addr.value})"],
                                "Load array element from effective address")
            )

            instructions.extend(self._store_result(triplet.result, reg_result))
            return instructions

        array_name = str(triplet.arg1.value) if triplet.arg1 else "unknown"
        index = triplet.arg2

        # Obtener información del array
        array_info = self.array_info.get(array_name, {
            'element_size': 4,
            'base_addr': self.heap_ptr
        })

        element_size = array_info.get('element_size', 4)

        # Registros
        reg_base = self._get_operand_register(triplet.arg1)
        reg_index = self._get_operand_register(index)
        reg_result = self._get_result_register(triplet.result)
        reg_temp = RegisterType.T0  # Registro temporal para cálculos

        # Cargar dirección base del array
        if array_name in self.array_to_register:
            reg_base = self.array_to_register[array_name]

        instructions.append(
            MIPSInstruction("", comment=f"ARRAY_GET: {array_name}[index]")
        )

        # Cargar índice
        instructions.extend(self._load_operand(index, reg_index))

        # Calcular offset: index * element_size
        if element_size != 1:
            instructions.append(
                MIPSInstruction("li", ["$t2", str(element_size)],
                              f"Load element size ({element_size})")
            )
            instructions.append(
                MIPSInstruction("mult", [f"${reg_index.value}", "$t2"],
                              "Multiply index by element size")
            )
            instructions.append(
                MIPSInstruction("mflo", ["$t3"],
                              "Get offset in $t3")
            )
        else:
            instructions.append(
                MIPSInstruction("addu", ["$t3", f"${reg_index.value}", "$zero"],
                              "Offset = index (element_size = 1)")
            )

        # Calcular dirección efectiva: base + offset.
        # En modo genérico usamos $fp como base segura para evitar direcciones fuera de rango.
        instructions.append(
            MIPSInstruction("addu", ["$t4", "$fp", "$t3"],
                            "Calculate effective address")
        )

        # Cargar elemento del array
        instructions.append(
            MIPSInstruction("lw", [f"${reg_result.value}", "0($t4)"],
                          f"Load array element")
        )

        instructions.extend(self._store_result(triplet.result, reg_result))

        return instructions

    def _translate_array_set(self, triplet: Triplet) -> List[MIPSInstruction]:
        """
        Traduce ARRAY_SET: establecer elemento del array

        MIPS:
            # Calcular dirección efectiva y escribir valor
            lw $t0, base_addr       # Dirección base
            lw $t1, index           # Índice
            li $t2, element_size    # Tamaño de elemento
            mult $t1, $t2           # index * element_size
            mflo $t3                # Offset
            addu $t4, $t0, $t3      # Dirección efectiva
            lw $t5, valor           # Cargar valor a escribir
            sw $t5, 0($t4)          # Escribir en array
        """
        instructions = []

        # Soporte para forma generada por ArrayCodeGen:
        # ARRAY_SET addr, value (result es None), donde addr es dirección efectiva.
        if triplet.arg1 is not None and triplet.arg1.is_temporary() and triplet.result is None:
            addr = triplet.arg1
            value = triplet.arg2

            reg_addr = self._get_operand_register(addr)
            reg_value = self._get_operand_register(value)

            instructions.append(
                MIPSInstruction("", comment="ARRAY_SET (addr, value)")
            )
            instructions.extend(self._load_operand(value, reg_value))
            instructions.append(
                MIPSInstruction("sw", [f"${reg_value.value}", f"0(${reg_addr.value})"],
                                "Write element to array at effective address")
            )

            return instructions

        array_name = str(triplet.arg1.value) if triplet.arg1 else "unknown"
        index = triplet.arg2
        value = triplet.result

        # Obtener información del array
        array_info = self.array_info.get(array_name, {
            'element_size': 4,
            'base_addr': self.heap_ptr
        })

        element_size = array_info.get('element_size', 4)

        instructions.append(
            MIPSInstruction("", comment=f"ARRAY_SET: {array_name}[index] = value")
        )

        # Cargar índice
        reg_index = self._get_operand_register(index)
        instructions.extend(self._load_operand(index, reg_index))

        # Calcular offset: index * element_size
        if element_size != 1:
            instructions.append(
                MIPSInstruction("li", ["$t2", str(element_size)],
                              f"Load element size ({element_size})")
            )
            instructions.append(
                MIPSInstruction("mult", [f"${reg_index.value}", "$t2"],
                              "Multiply index by element size")
            )
            instructions.append(
                MIPSInstruction("mflo", ["$t3"],
                              "Get offset in $t3")
            )
        else:
            instructions.append(
                MIPSInstruction("addu", ["$t3", f"${reg_index.value}", "$zero"],
                              "Offset = index")
            )

        # Calcular dirección efectiva.
        # En modo genérico usamos $fp como base segura para evitar direcciones fuera de rango.
        instructions.append(
            MIPSInstruction("addu", ["$t4", "$fp", "$t3"],
                            "Calculate effective address")
        )

        # Cargar valor a escribir
        # Usamos un registro temporal fijo ($t5) para evitar conflictos con registros de dirección.
        instructions.extend(self._load_operand(value, RegisterType.T5))

        # Escribir en array
        instructions.append(
            MIPSInstruction("sw", ["$t5", "0($t4)"],
                          "Write element to array")
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
        self.current_function = None
        self.function_param_count.clear()
        self.pending_params.clear()
        self.array_info.clear()
        self.array_to_register.clear()
        self.heap_ptr = 0x10000000

    def __str__(self) -> str:
        return f"MIPSTranslator({len(self.instructions)} instructions)"
