.data
str_0: .asciiz " makes a sound."
str_1: .asciiz " barks."
str_2: .asciiz "Testing typed strings"
str_3: .asciiz "Inferred hello"
str_4: .asciiz "triple(10) = "
str_5: .asciiz "PI value = "
str_6: .asciiz " / "
str_7: .asciiz "Feature flag is enabled"
str_8: .asciiz "computeValues(7) = "
str_9: .asciiz "factorial(5) = "
str_10: .asciiz "triple is larger"
str_11: .asciiz "computeValues is larger"
str_12: .asciiz "counter = "
str_13: .asciiz "do-while counter = "
str_14: .asciiz "for loop i = "
str_15: .asciiz "foreach n = "
str_16: .asciiz "counter is five"
str_17: .asciiz "counter is six"
str_18: .asciiz "counter is something else"
str_19: .asciiz "Rex"
str_20: .asciiz "Dog says: "
str_21: .asciiz "Buddy"
str_22: .asciiz "Dog renamed: "
str_23: .asciiz "Milo"
str_24: .asciiz "Animal says: "
str_25: .asciiz "Polymorphic call: "
str_26: .asciiz "First: "
str_27: .asciiz "Second multiple: "
str_28: .asciiz "Foreach new -> "
numbers: .word 1, 2, 3
PI: .word 314
newline_str: .asciiz "\n"

.text
.globl main
Animal_constructor:
    addiu $sp, $sp, -16
    sw $ra, 12($sp)
    sw $fp, 8($sp)
    move $fp, $sp
    sw $a0, -4($fp)
    sw $a1, -12($fp)
    lw $t0, -4($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, -12($fp)
    sw $t2, 0($t0)
Animal_constructor__epilogue:
    lw $ra, 12($sp)
    lw $fp, 8($sp)
    addiu $sp, $sp, 16
    jr $ra

Animal_speak:
    addiu $sp, $sp, -32
    sw $ra, 28($sp)
    sw $fp, 24($sp)
    move $fp, $sp
    sw $a0, -4($fp)
    lw $t0, -4($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -24($fp)
    lw $a0, -24($fp)
    la $a1, str_0
    jal concat_strings
    sw $v0, -28($fp)
    lw $v0, -28($fp)
    j Animal_speak__epilogue
Animal_speak__epilogue:
    lw $ra, 28($sp)
    lw $fp, 24($sp)
    addiu $sp, $sp, 32
    jr $ra

Dog_speak:
    addiu $sp, $sp, -32
    sw $ra, 28($sp)
    sw $fp, 24($sp)
    move $fp, $sp
    sw $a0, -4($fp)
    lw $t0, -4($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -24($fp)
    lw $a0, -24($fp)
    la $a1, str_1
    jal concat_strings
    sw $v0, -28($fp)
    lw $v0, -28($fp)
    j Dog_speak__epilogue
Dog_speak__epilogue:
    lw $ra, 28($sp)
    lw $fp, 24($sp)
    addiu $sp, $sp, 32
    jr $ra

triple:
    addiu $sp, $sp, -56
    sw $ra, 52($sp)
    sw $fp, 48($sp)
    move $fp, $sp
    sw $a0, -44($fp)
    lw $t0, -44($fp)
    lw $t1, -44($fp)
    addu $t2, $t0, $t1
    sw $t2, -28($fp)
    lw $t0, -28($fp)
    sw $t0, -40($fp)
    lw $t0, -40($fp)
    lw $t1, -44($fp)
    addu $t2, $t0, $t1
    sw $t2, -52($fp)
    lw $t0, -52($fp)
    sw $t0, -56($fp)
    lw $v0, -56($fp)
    j triple__epilogue
triple__epilogue:
    lw $ra, 52($sp)
    lw $fp, 48($sp)
    addiu $sp, $sp, 56
    jr $ra

computeValues:
    addiu $sp, $sp, -80
    sw $ra, 76($sp)
    sw $fp, 72($sp)
    move $fp, $sp
    sw $a0, -64($fp)
    lw $t0, -64($fp)
    lw $t1, -64($fp)
    addu $t2, $t0, $t1
    sw $t2, -28($fp)
    lw $t0, -28($fp)
    sw $t0, -40($fp)
    lw $t0, -40($fp)
    li $t1, 5
    addu $t2, $t0, $t1
    sw $t2, -48($fp)
    lw $t0, -48($fp)
    sw $t0, -60($fp)
    lw $t0, -60($fp)
    lw $t1, -64($fp)
    addu $t2, $t0, $t1
    sw $t2, -72($fp)
    lw $t0, -72($fp)
    sw $t0, -76($fp)
    lw $v0, -76($fp)
    j computeValues__epilogue
computeValues__epilogue:
    lw $ra, 76($sp)
    lw $fp, 72($sp)
    addiu $sp, $sp, 80
    jr $ra

factorial:
    addiu $sp, $sp, -64
    sw $ra, 60($sp)
    sw $fp, 56($sp)
    move $fp, $sp
    sw $a0, -56($fp)
    lw $t0, -56($fp)
    li $t1, 1
    sle $t2, $t0, $t1
    sw $t2, -20($fp)
    lw $t0, -20($fp)
    bne $t0, $zero, if_true_0
    j if_end_2
if_true_0:
    li $v0, 1
    j factorial__epilogue
    j if_end_2
if_end_2:
    lw $t0, -56($fp)
    li $t1, 1
    subu $t2, $t0, $t1
    sw $t2, -44($fp)
    lw $a0, -44($fp)
    jal factorial
    sw $v0, -60($fp)
    lw $t0, -56($fp)
    lw $t1, -60($fp)
    mul $t2, $t0, $t1
    sw $t2, -64($fp)
    lw $v0, -64($fp)
    j factorial__epilogue
factorial__epilogue:
    lw $ra, 60($sp)
    lw $fp, 56($sp)
    addiu $sp, $sp, 64
    jr $ra

getMultiples:
    addiu $sp, $sp, -72
    sw $ra, 68($sp)
    sw $fp, 64($sp)
    move $fp, $sp
    sw $a0, -64($fp)
    li $a0, 12
    li $v0, 9
    syscall
    sw $v0, -20($fp)
    lw $t0, -20($fp)
    sw $t0, -72($fp)
    lw $t0, -64($fp)
    li $t1, 1
    mul $t2, $t0, $t1
    sw $t2, -36($fp)
    lw $t0, -72($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, -36($fp)
    sw $t2, 0($t0)
    lw $t0, -64($fp)
    li $t1, 2
    mul $t2, $t0, $t1
    sw $t2, -52($fp)
    lw $t0, -72($fp)
    li $t1, 1
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, -52($fp)
    sw $t2, 0($t0)
    lw $t0, -64($fp)
    li $t1, 3
    mul $t2, $t0, $t1
    sw $t2, -68($fp)
    lw $t0, -72($fp)
    li $t1, 2
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, -68($fp)
    sw $t2, 0($t0)
    lw $v0, -72($fp)
    j getMultiples__epilogue
getMultiples__epilogue:
    lw $ra, 68($sp)
    lw $fp, 64($sp)
    addiu $sp, $sp, 72
    jr $ra

main:
    addiu $sp, $sp, -576
    sw $ra, 572($sp)
    sw $fp, 568($sp)
    move $fp, $sp
    la $t0, str_2
    sw $t0, -44($fp)
    la $t0, str_3
    sw $t0, -48($fp)
    li $t0, 1
    sw $t0, -52($fp)
    li $a0, 10
    jal triple
    sw $v0, -36($fp)
    lw $t0, -36($fp)
    sw $t0, -104($fp)
    la $a0, str_4
    jal print_string
    lw $a0, -104($fp)
    jal print_int
    jal print_newline
    la $a0, str_5
    jal print_string
    la $a0, PI
    lw $a0, 0($a0)
    jal print_int
    jal print_newline
    lw $a0, -44($fp)
    jal print_string
    la $a0, str_6
    jal print_string
    lw $a0, -48($fp)
    jal print_string
    jal print_newline
    lw $t0, -52($fp)
    bne $t0, $zero, if_true_3
    j if_end_5
if_true_3:
    la $a0, str_7
    jal print_string
    jal print_newline
    j if_end_5
if_end_5:
    li $a0, 7
    jal computeValues
    sw $v0, -68($fp)
    lw $t0, -68($fp)
    sw $t0, -108($fp)
    la $a0, str_8
    jal print_string
    lw $a0, -108($fp)
    jal print_int
    jal print_newline
    li $a0, 5
    jal factorial
    sw $v0, -88($fp)
    lw $t0, -88($fp)
    sw $t0, -92($fp)
    la $a0, str_9
    jal print_string
    lw $a0, -92($fp)
    jal print_int
    jal print_newline
    lw $t0, -104($fp)
    lw $t1, -108($fp)
    sgt $t2, $t0, $t1
    sw $t2, -112($fp)
    lw $t0, -112($fp)
    bne $t0, $zero, if_true_6
    j if_false_7
if_true_6:
    la $a0, str_10
    jal print_string
    jal print_newline
    j if_end_8
if_false_7:
    la $a0, str_11
    jal print_string
    jal print_newline
if_end_8:
    li $t0, 0
    sw $t0, -324($fp)
while_start_9:
    lw $t0, -324($fp)
    li $t1, 3
    slt $t2, $t0, $t1
    sw $t2, -132($fp)
    lw $t0, -132($fp)
    bne $t0, $zero, while_body_10
    j while_end_11
while_body_10:
    la $a0, str_12
    jal print_string
    lw $a0, -324($fp)
    jal print_int
    jal print_newline
    lw $t0, -324($fp)
    li $t1, 1
    addu $t2, $t0, $t1
    sw $t2, -156($fp)
    lw $t0, -156($fp)
    sw $t0, -324($fp)
    j while_start_9
while_end_11:
do_body_12:
    la $a0, str_13
    jal print_string
    lw $a0, -324($fp)
    jal print_int
    jal print_newline
    lw $t0, -324($fp)
    li $t1, 1
    addu $t2, $t0, $t1
    sw $t2, -180($fp)
    lw $t0, -180($fp)
    sw $t0, -324($fp)
do_continue_13:
    lw $t0, -324($fp)
    li $t1, 5
    slt $t2, $t0, $t1
    sw $t2, -196($fp)
    lw $t0, -196($fp)
    bne $t0, $zero, do_body_12
do_end_14:
    li $t0, 0
    sw $t0, -236($fp)
for_start_15:
    lw $t0, -236($fp)
    li $t1, 2
    slt $t2, $t0, $t1
    sw $t2, -216($fp)
    lw $t0, -216($fp)
    bne $t0, $zero, for_body_16
    j for_end_18
for_body_16:
    la $a0, str_14
    jal print_string
    lw $a0, -236($fp)
    jal print_int
    jal print_newline
for_continue_17:
    lw $t0, -236($fp)
    li $t1, 1
    addu $t2, $t0, $t1
    sw $t2, -240($fp)
    lw $t0, -240($fp)
    sw $t0, -236($fp)
    j for_start_15
for_end_18:
    li $t0, 0
    sw $t0, -296($fp)
foreach_start_19:
    lw $t0, -296($fp)
    li $t1, 3
    slt $t2, $t0, $t1
    sw $t2, -264($fp)
    lw $t0, -264($fp)
    bne $t0, $zero, foreach_body_20
    j foreach_end_22
foreach_body_20:
    la $t0, numbers
    lw $t1, -296($fp)
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -284($fp)
    lw $t0, -284($fp)
    sw $t0, -288($fp)
    la $a0, str_15
    jal print_string
    lw $a0, -288($fp)
    jal print_int
    jal print_newline
foreach_continue_21:
    lw $t0, -296($fp)
    li $t1, 1
    addu $t2, $t0, $t1
    sw $t2, -296($fp)
    j foreach_start_19
foreach_end_22:
    lw $t0, -324($fp)
    li $t1, 5
    seq $t2, $t0, $t1
    sw $t2, -312($fp)
    lw $t0, -312($fp)
    bne $t0, $zero, switch_case_24
    lw $t0, -324($fp)
    li $t1, 6
    seq $t2, $t0, $t1
    sw $t2, -328($fp)
    lw $t0, -328($fp)
    bne $t0, $zero, switch_case_25
    j switch_default_26
switch_case_24:
    la $a0, str_16
    jal print_string
    jal print_newline
    j switch_end_23
switch_case_25:
    la $a0, str_17
    jal print_string
    jal print_newline
    j switch_end_23
switch_default_26:
    la $a0, str_18
    jal print_string
    jal print_newline
    j switch_end_23
switch_end_23:
    li $a0, 4
    li $v0, 9
    syscall
    sw $v0, -360($fp)
    li $t0, 0
    sw $t0, -348($fp)
    lw $t0, -360($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, -348($fp)
    sw $t2, 0($t0)
    lw $a0, -360($fp)
    la $a1, str_19
    jal Animal_constructor
    lw $t0, -360($fp)
    sw $t0, -452($fp)
    la $a0, str_20
    jal print_string
    lw $a0, -452($fp)
    jal Dog_speak
    sw $v0, -376($fp)
    lw $a0, -376($fp)
    jal print_string
    jal print_newline
    lw $t0, -452($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    la $t2, str_21
    sw $t2, 0($t0)
    la $a0, str_22
    jal print_string
    lw $a0, -452($fp)
    jal Dog_speak
    sw $v0, -396($fp)
    lw $a0, -396($fp)
    jal print_string
    jal print_newline
    li $a0, 4
    li $v0, 9
    syscall
    sw $v0, -428($fp)
    li $t0, 0
    sw $t0, -416($fp)
    lw $t0, -428($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, -416($fp)
    sw $t2, 0($t0)
    lw $a0, -428($fp)
    la $a1, str_23
    jal Animal_constructor
    lw $t0, -428($fp)
    sw $t0, -440($fp)
    la $a0, str_24
    jal print_string
    lw $a0, -440($fp)
    jal Animal_speak
    sw $v0, -444($fp)
    lw $a0, -444($fp)
    jal print_string
    jal print_newline
    lw $t0, -452($fp)
    sw $t0, -464($fp)
    la $a0, str_25
    jal print_string
    lw $a0, -464($fp)
    jal Dog_speak
    sw $v0, -468($fp)
    lw $a0, -468($fp)
    jal print_string
    jal print_newline
    la $t0, numbers
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -484($fp)
    lw $t0, -484($fp)
    sw $t0, -504($fp)
    li $a0, 4
    jal getMultiples
    sw $v0, -500($fp)
    lw $t0, -500($fp)
    sw $t0, -496($fp)
    la $a0, str_26
    jal print_string
    lw $a0, -504($fp)
    jal print_int
    jal print_newline
    la $a0, str_27
    jal print_string
    lw $t0, -496($fp)
    li $t1, 1
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -516($fp)
    lw $a0, -516($fp)
    jal print_int
    jal print_newline
    li $t0, 0
    sw $t0, -572($fp)
foreach_start_27:
    lw $t0, -572($fp)
    li $t1, 3
    slt $t2, $t0, $t1
    sw $t2, -540($fp)
    lw $t0, -540($fp)
    bne $t0, $zero, foreach_body_28
    j foreach_end_30
foreach_body_28:
    la $t0, numbers
    lw $t1, -572($fp)
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -560($fp)
    lw $t0, -560($fp)
    sw $t0, -564($fp)
    la $a0, str_28
    jal print_string
    lw $a0, -564($fp)
    jal print_int
    jal print_newline
foreach_continue_29:
    lw $t0, -572($fp)
    li $t1, 1
    addu $t2, $t0, $t1
    sw $t2, -572($fp)
    j foreach_start_27
foreach_end_30:
    jal exit_program
main__epilogue:
    lw $ra, 572($sp)
    lw $fp, 568($sp)
    addiu $sp, $sp, 576
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

exit_program:
    addiu $sp, $sp, -16
    sw $ra, 12($sp)
    sw $fp, 8($sp)
    move $fp, $sp
    li $v0, 10
    syscall
    lw $ra, 12($sp)
    lw $fp, 8($sp)
    addiu $sp, $sp, 16
    jr $ra

concat_strings:
    addiu $sp, $sp, -48
    sw $ra, 44($sp)
    sw $fp, 40($sp)
    move $fp, $sp
    sw $a0, 36($fp)
    sw $a1, 32($fp)
    move $t0, $a0
    li $t1, 0
concat_len1_loop:
    lbu $t2, 0($t0)
    beq $t2, $zero, concat_len1_done
    addiu $t0, $t0, 1
    addiu $t1, $t1, 1
    j concat_len1_loop
concat_len1_done:
    sw $t1, 28($fp)
    move $t0, $a1
    li $t1, 0
concat_len2_loop:
    lbu $t2, 0($t0)
    beq $t2, $zero, concat_len2_done
    addiu $t0, $t0, 1
    addiu $t1, $t1, 1
    j concat_len2_loop
concat_len2_done:
    sw $t1, 24($fp)
    lw $t3, 28($fp)
    lw $t4, 24($fp)
    addu $t5, $t3, $t4
    addiu $t5, $t5, 1
    move $a0, $t5
    li $v0, 9
    syscall
    sw $v0, 20($fp)
    lw $t0, 36($fp)
    lw $t1, 20($fp)
concat_copy1_loop:
    lbu $t2, 0($t0)
    beq $t2, $zero, concat_copy1_done
    sb $t2, 0($t1)
    addiu $t0, $t0, 1
    addiu $t1, $t1, 1
    j concat_copy1_loop
concat_copy1_done:
    lw $t0, 32($fp)
concat_copy2_loop:
    lbu $t2, 0($t0)
    sb $t2, 0($t1)
    addiu $t1, $t1, 1
    beq $t2, $zero, concat_done
    addiu $t0, $t0, 1
    j concat_copy2_loop
concat_done:
    lw $v0, 20($fp)
    move $a0, $v0
    lw $ra, 44($sp)
    lw $fp, 40($sp)
    addiu $sp, $sp, 48
    jr $ra
