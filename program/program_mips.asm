.data

PI: .word 314
flag: .word 0
numbers_len: .word 5
numbers: .word 1, 2, 3, 4, 5
matrix: .word 1, 2, 3, 4
msg_greeting: .asciiz "Hello, Compiscript!"
msg_add: .asciiz "5 + 1 = "
msg_gt5: .asciiz "Greater than 5"
msg_le5: .asciiz "5 or less"
msg_result: .asciiz "Result is now "
msg_loop_idx: .asciiz "Loop index: "
msg_number: .asciiz "Number: "
msg_seven: .asciiz "It's seven"
msg_six: .asciiz "It's six"
msg_default: .asciiz "Something else"
msg_risky: .asciiz "Risky access: "
msg_caught: .asciiz "Caught an error: "
msg_rex: .asciiz "Rex"
msg_makes_sound: .asciiz " makes a sound."
msg_barks: .asciiz " barks."
msg_first: .asciiz "First number: "
msg_multiples: .asciiz "Multiples of 2: "
msg_comma: .asciiz ", "
msg_program_done: .asciiz "Program finished."
msg_try_err: .asciiz "Index out of range"
newline_str: .asciiz "\n"

vtable_Animal: .word Animal_speak
vtable_Dog: .word Dog_speak

.text
.globl main

main:
    addiu $sp, $sp, -8
    sw $fp, 4($sp)
    move $fp, $sp

    addiu $sp, $sp, -48

    li $a0, 5
    jal makeAdder
    sw $v0, -4($fp)

    la $a0, msg_add
    jal print_string
    lw $a0, -4($fp)
    jal print_int
    jal print_newline

    lw $t0, -4($fp)
    li $t1, 5
    slt $t2, $t1, $t0
    beq $t2, $zero, IF_ELSE
    la $a0, msg_gt5
    jal print_string
    jal print_newline
    j IF_END
IF_ELSE:
    la $a0, msg_le5
    jal print_string
    jal print_newline
IF_END:

    li $t1, 10
WHILE_START:
    lw $t0, -4($fp)
    slt $t2, $t0, $t1
    beq $t2, $zero, WHILE_END
    addiu $t0, $t0, 1
    sw $t0, -4($fp)
    j WHILE_START
WHILE_END:

DO_LOOP:
    la $a0, msg_result
    jal print_string
    lw $a0, -4($fp)
    jal print_int
    jal print_newline
    lw $t0, -4($fp)
    addiu $t0, $t0, -1
    sw $t0, -4($fp)
    lw $t0, -4($fp)
    li $t1, 7
    slt $t2, $t1, $t0
    bne $t2, $zero, DO_LOOP

    li $t0, 0
    sw $t0, -8($fp)
FOR_LOOP:
    lw $t0, -8($fp)
    li $t1, 3
    slt $t2, $t0, $t1
    beq $t2, $zero, FOR_END
    la $a0, msg_loop_idx
    jal print_string
    lw $a0, -8($fp)
    jal print_int
    jal print_newline
    lw $t0, -8($fp)
    addiu $t0, $t0, 1
    sw $t0, -8($fp)
    j FOR_LOOP
FOR_END:

    li $t0, 0
    sw $t0, -12($fp)
FOREACH_LOOP:
    lw $t0, -12($fp)
    la $t1, numbers_len
    lw $t1, 0($t1)
    slt $t2, $t0, $t1
    beq $t2, $zero, FOREACH_END
    la $t3, numbers
    sll $t4, $t0, 2
    addu $t5, $t3, $t4
    lw $t6, 0($t5)
    sw $t6, -16($fp)
    li $t7, 3
    beq $t6, $t7, FOREACH_STEP
    la $a0, msg_number
    jal print_string
    move $a0, $t6
    jal print_int
    jal print_newline
    li $t7, 4
    slt $t8, $t7, $t6
    bne $t8, $zero, FOREACH_END
FOREACH_STEP:
    lw $t0, -12($fp)
    addiu $t0, $t0, 1
    sw $t0, -12($fp)
    j FOREACH_LOOP
FOREACH_END:

    lw $t0, -4($fp)
    li $t1, 7
    beq $t0, $t1, CASE_7
    li $t1, 6
    beq $t0, $t1, CASE_6
    j CASE_DEFAULT
CASE_7:
    la $a0, msg_seven
    jal print_string
    jal print_newline
    j CASE_6_BODY
CASE_6:
CASE_6_BODY:
    la $a0, msg_six
    jal print_string
    jal print_newline
    j CASE_FALL
CASE_DEFAULT:
    la $a0, msg_default
    jal print_string
    jal print_newline
    j CASE_DONE
CASE_FALL:
    la $a0, msg_default
    jal print_string
    jal print_newline
CASE_DONE:

    li $t0, 10
    la $t1, numbers_len
    lw $t1, 0($t1)
    slt $t2, $t0, $t1
    bne $t2, $zero, TRY_SAFE
    j TRY_CATCH
TRY_SAFE:
    la $t3, numbers
    sll $t4, $t0, 2
    addu $t5, $t3, $t4
    lw $t6, 0($t5)
    sw $t6, -20($fp)
    la $a0, msg_risky
    jal print_string
    move $a0, $t6
    jal print_int
    jal print_newline
    j TRY_DONE
TRY_CATCH:
    jal raise_bounds_error
    sw $v0, -24($fp)
    la $a0, msg_caught
    jal print_string
    lw $a0, -24($fp)
    jal print_string
    jal print_newline
TRY_DONE:

    li $a0, 8
    jal alloc_object
    move $t0, $v0
    la $a1, vtable_Dog
    move $a0, $t0
    jal install_vtable
    move $t0, $v0
    la $a1, msg_rex
    move $a0, $t0
    jal Dog_constructor
    move $t0, $v0
    sw $t0, -28($fp)

    lw $t0, -28($fp)
    lw $t1, 0($t0)
    lui $t3, 0x1000
    sltu $t4, $t1, $t3
    beq $t4, $zero, DISPATCH_VTABLE
    move $t2, $t1
    j DISPATCH_CALL
DISPATCH_VTABLE:
    lw $t2, 0($t1)
DISPATCH_CALL:
    move $a0, $t0
    jalr $t2
    move $a0, $v0
    jal print_string
    jal print_newline

    la $t0, numbers
    lw $t1, 0($t0)
    sw $t1, -32($fp)
    la $a0, msg_first
    jal print_string
    move $a0, $t1
    jal print_int
    jal print_newline

    li $a0, 2
    jal getMultiples
    sw $v0, -36($fp)
    lw $t0, -36($fp)
    lw $t1, 0($t0)
    lw $t2, 4($t0)
    la $a0, msg_multiples
    jal print_string
    move $a0, $t1
    jal print_int
    la $a0, msg_comma
    jal print_string
    move $a0, $t2
    jal print_int
    jal print_newline

    la $a0, msg_program_done
    jal print_string
    jal print_newline

    addiu $sp, $sp, 48
    move $sp, $fp
    lw $fp, 4($sp)
    addiu $sp, $sp, 8
    li $v0, 10
    syscall

makeAdder:
    addiu $sp, $sp, -16
    sw $ra, 12($sp)
    sw $fp, 8($sp)
    move $fp, $sp
    sw $a0, 0($fp)
    lw $t0, 0($fp)
    addiu $t0, $t0, 1
    move $v0, $t0
    lw $ra, 12($sp)
    lw $fp, 8($sp)
    addiu $sp, $sp, 16
    jr $ra

getMultiples:
    addiu $sp, $sp, -40
    sw $ra, 36($sp)
    sw $fp, 32($sp)
    move $fp, $sp
    sw $a0, 0($fp)
    li $a0, 5
    jal array_alloc
    sw $v0, 4($fp)
    lw $t0, 0($fp)
    lw $t1, 4($fp)
    move $t2, $t0
    sw $t2, 0($t1)
    addu $t2, $t0, $t0
    sw $t2, 4($t1)
    addu $t2, $t2, $t0
    sw $t2, 8($t1)
    sll $t3, $t0, 2
    sw $t3, 12($t1)
    addu $t4, $t3, $t0
    sw $t4, 16($t1)
    move $v0, $t1
    lw $ra, 36($sp)
    lw $fp, 32($sp)
    addiu $sp, $sp, 40
    jr $ra

factorial:
    addiu $sp, $sp, -32
    sw $ra, 28($sp)
    sw $fp, 24($sp)
    move $fp, $sp
    sw $a0, 0($fp)
    lw $t0, 0($fp)
    li $t1, 1
    slt $t2, $t0, $t1
    bne $t2, $zero, FACT_BASE
    beq $t0, $t1, FACT_BASE
    lw $t0, 0($fp)
    addiu $t0, $t0, -1
    move $a0, $t0
    jal factorial
    lw $t1, 0($fp)
    mul $t2, $t1, $v0
    move $v0, $t2
    j FACT_END
FACT_BASE:
    li $v0, 1
FACT_END:
    lw $ra, 28($sp)
    lw $fp, 24($sp)
    addiu $sp, $sp, 32
    jr $ra

print_string:
    addiu $sp, $sp, -16
    sw $ra, 12($sp)
    sw $fp, 8($sp)
    move $fp, $sp
    li $v0, 4
    syscall
    lw $ra, 12($sp)
    lw $fp, 8($sp)
    addiu $sp, $sp, 16
    jr $ra

print_int:
    addiu $sp, $sp, -16
    sw $ra, 12($sp)
    sw $fp, 8($sp)
    move $fp, $sp
    li $v0, 1
    syscall
    lw $ra, 12($sp)
    lw $fp, 8($sp)
    addiu $sp, $sp, 16
    jr $ra

print_newline:
    addiu $sp, $sp, -16
    sw $ra, 12($sp)
    sw $fp, 8($sp)
    move $fp, $sp
    la $a0, newline_str
    li $v0, 4
    syscall
    lw $ra, 12($sp)
    lw $fp, 8($sp)
    addiu $sp, $sp, 16
    jr $ra

read_int:
    addiu $sp, $sp, -16
    sw $ra, 12($sp)
    sw $fp, 8($sp)
    move $fp, $sp
    li $v0, 5
    syscall
    lw $ra, 12($sp)
    lw $fp, 8($sp)
    addiu $sp, $sp, 16
    jr $ra

alloc_bytes:
    addiu $sp, $sp, -24
    sw $ra, 20($sp)
    sw $fp, 16($sp)
    move $fp, $sp
    sw $a0, 0($fp)
    lw $a0, 0($fp)
    li $v0, 9
    syscall
    lw $ra, 20($sp)
    lw $fp, 16($sp)
    addiu $sp, $sp, 24
    jr $ra

alloc_object:
    addiu $sp, $sp, -24
    sw $ra, 20($sp)
    sw $fp, 16($sp)
    move $fp, $sp
    sw $a0, 0($fp)
    lw $a0, 0($fp)
    jal alloc_bytes
    lw $ra, 20($sp)
    lw $fp, 16($sp)
    addiu $sp, $sp, 24
    jr $ra

install_vtable:
    addiu $sp, $sp, -24
    sw $ra, 20($sp)
    sw $fp, 16($sp)
    move $fp, $sp
    sw $a0, 0($fp)
    sw $a1, 4($fp)
    lw $t0, 0($fp)
    lw $t1, 4($fp)
    sw $t1, 0($t0)
    move $v0, $t0
    lw $ra, 20($sp)
    lw $fp, 16($sp)
    addiu $sp, $sp, 24
    jr $ra

array_alloc:
    addiu $sp, $sp, -32
    sw $ra, 28($sp)
    sw $fp, 24($sp)
    move $fp, $sp
    sw $a0, 0($fp)
    lw $t0, 0($fp)
    addiu $t1, $t0, 1
    sll $a0, $t1, 2
    jal alloc_bytes
    sw $v0, 4($fp)
    lw $t0, 0($fp)
    lw $t2, 4($fp)
    sw $t0, 0($t2)
    addiu $v0, $t2, 4
    lw $ra, 28($sp)
    lw $fp, 24($sp)
    addiu $sp, $sp, 32
    jr $ra

string_length:
    addiu $sp, $sp, -24
    sw $ra, 20($sp)
    sw $fp, 16($sp)
    move $fp, $sp
    sw $a0, 0($fp)
    move $t0, $zero
    lw $t1, 0($fp)
STR_LEN_LOOP:
    lbu $t2, 0($t1)
    beq $t2, $zero, STR_LEN_DONE
    addiu $t1, $t1, 1
    addiu $t0, $t0, 1
    j STR_LEN_LOOP
STR_LEN_DONE:
    move $v0, $t0
    lw $ra, 20($sp)
    lw $fp, 16($sp)
    addiu $sp, $sp, 24
    jr $ra

concat_strings:
    addiu $sp, $sp, -48
    sw $ra, 44($sp)
    sw $fp, 40($sp)
    move $fp, $sp
    sw $a0, 0($fp)
    sw $a1, 4($fp)
    lw $a0, 0($fp)
    jal string_length
    sw $v0, 8($fp)
    lw $a0, 4($fp)
    jal string_length
    sw $v0, 12($fp)
    lw $t0, 8($fp)
    lw $t1, 12($fp)
    addiu $t2, $t0, 1
    addu $t2, $t2, $t1
    move $a0, $t2
    jal alloc_bytes
    sw $v0, 16($fp)
    lw $t4, 16($fp)
    move $t5, $t4
    lw $t6, 0($fp)
CONCAT_COPY_FIRST:
    lbu $t7, 0($t6)
    beq $t7, $zero, CONCAT_COPY_SECOND
    sb $t7, 0($t5)
    addiu $t6, $t6, 1
    addiu $t5, $t5, 1
    j CONCAT_COPY_FIRST
CONCAT_COPY_SECOND:
    lw $t6, 4($fp)
CONCAT_COPY_SECOND_LOOP:
    lbu $t7, 0($t6)
    beq $t7, $zero, CONCAT_DONE
    sb $t7, 0($t5)
    addiu $t6, $t6, 1
    addiu $t5, $t5, 1
    j CONCAT_COPY_SECOND_LOOP
CONCAT_DONE:
    sb $zero, 0($t5)
    lw $v0, 16($fp)
    lw $ra, 44($sp)
    lw $fp, 40($sp)
    addiu $sp, $sp, 48
    jr $ra

Animal_constructor:
    addiu $sp, $sp, -24
    sw $ra, 20($sp)
    sw $fp, 16($sp)
    move $fp, $sp
    sw $a0, 0($fp)
    sw $a1, 4($fp)
    lw $t0, 0($fp)
    lw $t1, 4($fp)
    sw $t1, 4($t0)
    move $v0, $t0
    lw $ra, 20($sp)
    lw $fp, 16($sp)
    addiu $sp, $sp, 24
    jr $ra

Dog_constructor:
    addiu $sp, $sp, -24
    sw $ra, 20($sp)
    sw $fp, 16($sp)
    move $fp, $sp
    sw $a0, 0($fp)
    sw $a1, 4($fp)
    lw $a0, 0($fp)
    lw $a1, 4($fp)
    jal Animal_constructor
    lw $v0, 0($fp)
    lw $ra, 20($sp)
    lw $fp, 16($sp)
    addiu $sp, $sp, 24
    jr $ra

Animal_speak:
    addiu $sp, $sp, -24
    sw $ra, 20($sp)
    sw $fp, 16($sp)
    move $fp, $sp
    sw $a0, 0($fp)
    lw $t0, 0($fp)
    lw $t1, 4($t0)
    la $a1, msg_makes_sound
    move $a0, $t1
    jal concat_strings
    lw $ra, 20($sp)
    lw $fp, 16($sp)
    addiu $sp, $sp, 24
    jr $ra

Dog_speak:
    addiu $sp, $sp, -24
    sw $ra, 20($sp)
    sw $fp, 16($sp)
    move $fp, $sp
    sw $a0, 0($fp)
    lw $t0, 0($fp)
    lw $t1, 4($t0)
    la $a1, msg_barks
    move $a0, $t1
    jal concat_strings
    lw $ra, 20($sp)
    lw $fp, 16($sp)
    addiu $sp, $sp, 24
    jr $ra

raise_bounds_error:
    addiu $sp, $sp, -16
    sw $ra, 12($sp)
    sw $fp, 8($sp)
    move $fp, $sp
    la $v0, msg_try_err
    lw $ra, 12($sp)
    lw $fp, 8($sp)
    addiu $sp, $sp, 16
    jr $ra
