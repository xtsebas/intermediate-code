.data
str_0: .asciiz " makes a sound."
str_1: .asciiz " barks."
str_2: .asciiz "Hello, Compiscript!"
str_3: .asciiz "5 + 1 = "
str_4: .asciiz "Greater than 5"
str_5: .asciiz "5 or less"
str_6: .asciiz "Result is now "
str_7: .asciiz "Loop index: "
str_8: .asciiz "Number: "
str_9: .asciiz "It's seven"
str_10: .asciiz "It's six"
str_11: .asciiz "Something else"
str_12: .asciiz "Risky access: "
str_13: .asciiz "Caught an error: "
str_14: .asciiz "Rex"
str_15: .asciiz "First number: "
str_16: .asciiz "Multiples of 2: "
str_17: .asciiz ", "
str_18: .asciiz "Program finished."
str_19: .asciiz "Index out of range"
numbers: .word 1, 2, 3, 4, 5
matrix: .word 1, 2, 3, 4
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

makeAdder:
    addiu $sp, $sp, -24
    sw $ra, 20($sp)
    sw $fp, 16($sp)
    move $fp, $sp
    sw $a0, -16($fp)
    lw $t0, -16($fp)
    li $t1, 1
    addu $t2, $t0, $t1
    sw $t2, -20($fp)
    lw $v0, -20($fp)
    j makeAdder__epilogue
makeAdder__epilogue:
    lw $ra, 20($sp)
    lw $fp, 16($sp)
    addiu $sp, $sp, 24
    jr $ra

getMultiples:
    addiu $sp, $sp, -104
    sw $ra, 100($sp)
    sw $fp, 96($sp)
    move $fp, $sp
    sw $a0, -96($fp)
    li $a0, 20
    li $v0, 9
    syscall
    sw $v0, -20($fp)
    lw $t0, -20($fp)
    sw $t0, -104($fp)
    lw $t0, -96($fp)
    li $t1, 1
    mul $t2, $t0, $t1
    sw $t2, -36($fp)
    lw $t0, -104($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, -36($fp)
    sw $t2, 0($t0)
    lw $t0, -96($fp)
    li $t1, 2
    mul $t2, $t0, $t1
    sw $t2, -52($fp)
    lw $t0, -104($fp)
    li $t1, 1
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, -52($fp)
    sw $t2, 0($t0)
    lw $t0, -96($fp)
    li $t1, 3
    mul $t2, $t0, $t1
    sw $t2, -68($fp)
    lw $t0, -104($fp)
    li $t1, 2
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, -68($fp)
    sw $t2, 0($t0)
    lw $t0, -96($fp)
    li $t1, 4
    mul $t2, $t0, $t1
    sw $t2, -84($fp)
    lw $t0, -104($fp)
    li $t1, 3
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, -84($fp)
    sw $t2, 0($t0)
    lw $t0, -96($fp)
    li $t1, 5
    mul $t2, $t0, $t1
    sw $t2, -100($fp)
    lw $t0, -104($fp)
    li $t1, 4
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, -100($fp)
    sw $t2, 0($t0)
    lw $v0, -104($fp)
    j getMultiples__epilogue
getMultiples__epilogue:
    lw $ra, 100($sp)
    lw $fp, 96($sp)
    addiu $sp, $sp, 104
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

main:
    addiu $sp, $sp, -456
    sw $ra, 452($sp)
    sw $fp, 448($sp)
    move $fp, $sp
    la $t0, str_2
    sw $t0, -4($fp)
    li $a0, 5
    jal makeAdder
    sw $v0, -24($fp)
    lw $t0, -24($fp)
    sw $t0, -280($fp)
    la $a0, str_3
    jal print_string
    lw $a0, -280($fp)
    jal print_int
    jal print_newline
    lw $t0, -280($fp)
    li $t1, 5
    sgt $t2, $t0, $t1
    sw $t2, -44($fp)
    lw $t0, -44($fp)
    bne $t0, $zero, if_true_3
    j if_false_4
if_true_3:
    la $a0, str_4
    jal print_string
    jal print_newline
    j if_end_5
if_false_4:
    la $a0, str_5
    jal print_string
    jal print_newline
if_end_5:
while_start_6:
    lw $t0, -280($fp)
    li $t1, 10
    slt $t2, $t0, $t1
    sw $t2, -60($fp)
    lw $t0, -60($fp)
    bne $t0, $zero, while_body_7
    j while_end_8
while_body_7:
    lw $t0, -280($fp)
    li $t1, 1
    addu $t2, $t0, $t1
    sw $t2, -80($fp)
    lw $t0, -80($fp)
    sw $t0, -280($fp)
    j while_start_6
while_end_8:
do_body_9:
    la $a0, str_6
    jal print_string
    lw $a0, -280($fp)
    jal print_int
    jal print_newline
    lw $t0, -280($fp)
    li $t1, 1
    subu $t2, $t0, $t1
    sw $t2, -104($fp)
    lw $t0, -104($fp)
    sw $t0, -280($fp)
do_continue_10:
    lw $t0, -280($fp)
    li $t1, 7
    sgt $t2, $t0, $t1
    sw $t2, -120($fp)
    lw $t0, -120($fp)
    bne $t0, $zero, do_body_9
do_end_11:
    li $t0, 0
    sw $t0, -160($fp)
for_start_12:
    lw $t0, -160($fp)
    li $t1, 3
    slt $t2, $t0, $t1
    sw $t2, -140($fp)
    lw $t0, -140($fp)
    bne $t0, $zero, for_body_13
    j for_end_15
for_body_13:
    la $a0, str_7
    jal print_string
    lw $a0, -160($fp)
    jal print_int
    jal print_newline
for_continue_14:
    lw $t0, -160($fp)
    li $t1, 1
    addu $t2, $t0, $t1
    sw $t2, -164($fp)
    lw $t0, -164($fp)
    sw $t0, -160($fp)
    j for_start_12
for_end_15:
    li $t0, 0
    sw $t0, -252($fp)
foreach_start_16:
    lw $t0, -252($fp)
    li $t1, 5
    slt $t2, $t0, $t1
    sw $t2, -188($fp)
    lw $t0, -188($fp)
    bne $t0, $zero, foreach_body_17
    j foreach_end_19
foreach_body_17:
    la $t0, numbers
    lw $t1, -252($fp)
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -208($fp)
    lw $t0, -208($fp)
    sw $t0, -240($fp)
    lw $t0, -240($fp)
    li $t1, 3
    seq $t2, $t0, $t1
    sw $t2, -224($fp)
    lw $t0, -224($fp)
    bne $t0, $zero, if_true_20
    j if_end_22
if_true_20:
    j foreach_continue_18
    j if_end_22
if_end_22:
    la $a0, str_8
    jal print_string
    lw $a0, -240($fp)
    jal print_int
    jal print_newline
    lw $t0, -240($fp)
    li $t1, 4
    sgt $t2, $t0, $t1
    sw $t2, -244($fp)
    lw $t0, -244($fp)
    bne $t0, $zero, if_true_23
    j if_end_25
if_true_23:
    j foreach_end_19
    j if_end_25
if_end_25:
foreach_continue_18:
    lw $t0, -252($fp)
    li $t1, 1
    addu $t2, $t0, $t1
    sw $t2, -252($fp)
    j foreach_start_16
foreach_end_19:
    lw $t0, -280($fp)
    li $t1, 7
    seq $t2, $t0, $t1
    sw $t2, -268($fp)
    lw $t0, -268($fp)
    bne $t0, $zero, switch_case_27
    lw $t0, -280($fp)
    li $t1, 6
    seq $t2, $t0, $t1
    sw $t2, -284($fp)
    lw $t0, -284($fp)
    bne $t0, $zero, switch_case_28
    j switch_default_29
switch_case_27:
    la $a0, str_9
    jal print_string
    jal print_newline
    j switch_end_26
switch_case_28:
    la $a0, str_10
    jal print_string
    jal print_newline
    j switch_end_26
switch_default_29:
    la $a0, str_11
    jal print_string
    jal print_newline
    j switch_end_26
switch_end_26:
try_block_30:
    li $t0, 10
    li $t1, 5
    slt $t2, $t0, $t1
    sw $t2, -296($fp)
    lw $t0, -296($fp)
    bne $t0, $zero, bounds_upper_ok_33
    la $t0, str_19
    sw $t0, -348($fp)
    j catch_block_31
bounds_upper_ok_33:
    li $t0, 10
    li $t1, 0
    sge $t2, $t0, $t1
    sw $t2, -316($fp)
    lw $t0, -316($fp)
    bne $t0, $zero, bounds_lower_ok_34
    la $t0, str_19
    sw $t0, -348($fp)
    j catch_block_31
bounds_lower_ok_34:
    la $t0, numbers
    li $t1, 10
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -340($fp)
    lw $t0, -340($fp)
    sw $t0, -344($fp)
    la $a0, str_12
    jal print_string
    lw $a0, -344($fp)
    jal print_int
    jal print_newline
    j try_end_32
catch_block_31:
    la $a0, str_13
    jal print_string
    lw $a0, -348($fp)
    jal print_string
    jal print_newline
try_end_32:
    li $a0, 4
    li $v0, 9
    syscall
    sw $v0, -380($fp)
    li $t0, 0
    sw $t0, -368($fp)
    lw $t0, -380($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, -368($fp)
    sw $t2, 0($t0)
    lw $a0, -380($fp)
    la $a1, str_14
    jal Animal_constructor
    lw $t0, -380($fp)
    sw $t0, -392($fp)
    lw $a0, -392($fp)
    jal Dog_speak
    sw $v0, -396($fp)
    lw $a0, -396($fp)
    jal print_string
    jal print_newline
    la $t0, numbers
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -412($fp)
    lw $t0, -412($fp)
    sw $t0, -416($fp)
    la $a0, str_15
    jal print_string
    lw $a0, -416($fp)
    jal print_int
    jal print_newline
    li $a0, 2
    jal getMultiples
    sw $v0, -432($fp)
    lw $t0, -432($fp)
    sw $t0, -428($fp)
    la $a0, str_16
    jal print_string
    lw $t0, -428($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -444($fp)
    lw $a0, -444($fp)
    jal print_int
    la $a0, str_17
    jal print_string
    lw $t0, -428($fp)
    li $t1, 1
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -456($fp)
    lw $a0, -456($fp)
    jal print_int
    jal print_newline
    la $a0, str_18
    jal print_string
    jal print_newline
    jal exit_program
main__epilogue:
    lw $ra, 452($sp)
    lw $fp, 448($sp)
    addiu $sp, $sp, 456
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
