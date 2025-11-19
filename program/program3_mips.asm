.data
str_0: .asciiz "BaseCounter"
str_1: .asciiz "FancyCounter"
str_2: .asciiz "Fancy ready"
str_3: .asciiz "Welcome to Program3"
str_4: .asciiz ", LIMIT = "
str_5: .asciiz "factorial(6) = "
str_6: .asciiz "fibonacci(7) = "
str_7: .asciiz "While probe = "
str_8: .asciiz "Do-while probe = "
str_9: .asciiz "For index = "
str_10: .asciiz "Foreach value = "
str_11: .asciiz "Foreach sum = "
str_12: .asciiz "Sum is six"
str_13: .asciiz "Sum reached fifteen"
str_14: .asciiz "Sum default hit"
str_15: .asciiz "Risky value = "
str_16: .asciiz "Caught error message: "
str_17: .asciiz "Matrix corners: "
str_18: .asciiz " & "
str_19: .asciiz "Series[0] = "
str_20: .asciiz "Series[4] = "
str_21: .asciiz "Base label: "
str_22: .asciiz "Base tick value = "
str_23: .asciiz "Fancy label: "
str_24: .asciiz "Fancy tick value = "
str_25: .asciiz "Updated base current = "
str_26: .asciiz "Poly label: "
str_27: .asciiz "Fancy flair: "
str_28: .asciiz "numbers sum = "
str_29: .asciiz "Program3 finished."
str_30: .asciiz "Index out of range"
numbers: .word 1, 2, 3, 4, 5, 6
matrix: .word 1, 2, 3, 4, 5, 6
LIMIT: .word 42
newline_str: .asciiz "\n"

.text
.globl main
Counter_constructor:
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
Counter_constructor__epilogue:
    lw $ra, 12($sp)
    lw $fp, 8($sp)
    addiu $sp, $sp, 16
    jr $ra

Counter_tick:
    addiu $sp, $sp, -40
    sw $ra, 36($sp)
    sw $fp, 32($sp)
    move $fp, $sp
    sw $a0, -4($fp)
    lw $t0, -4($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -24($fp)
    lw $t0, -24($fp)
    li $t1, 1
    addu $t2, $t0, $t1
    sw $t2, -28($fp)
    lw $t0, -4($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, -28($fp)
    sw $t2, 0($t0)
    lw $t0, -4($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -40($fp)
    lw $v0, -40($fp)
    j Counter_tick__epilogue
Counter_tick__epilogue:
    lw $ra, 36($sp)
    lw $fp, 32($sp)
    addiu $sp, $sp, 40
    jr $ra

Counter_current:
    addiu $sp, $sp, -16
    sw $ra, 12($sp)
    sw $fp, 8($sp)
    move $fp, $sp
    sw $a0, -4($fp)
    lw $t0, -4($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -16($fp)
    lw $v0, -16($fp)
    j Counter_current__epilogue
Counter_current__epilogue:
    lw $ra, 12($sp)
    lw $fp, 8($sp)
    addiu $sp, $sp, 16
    jr $ra

Counter_label:
    addiu $sp, $sp, -16
    sw $ra, 12($sp)
    sw $fp, 8($sp)
    move $fp, $sp
    sw $a0, -4($fp)
    la $v0, str_0
    j Counter_label__epilogue
Counter_label__epilogue:
    lw $ra, 12($sp)
    lw $fp, 8($sp)
    addiu $sp, $sp, 16
    jr $ra

FancyCounter_tick:
    addiu $sp, $sp, -40
    sw $ra, 36($sp)
    sw $fp, 32($sp)
    move $fp, $sp
    sw $a0, -4($fp)
    lw $t0, -4($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -24($fp)
    lw $t0, -24($fp)
    li $t1, 2
    addu $t2, $t0, $t1
    sw $t2, -28($fp)
    lw $t0, -4($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, -28($fp)
    sw $t2, 0($t0)
    lw $t0, -4($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -40($fp)
    lw $v0, -40($fp)
    j FancyCounter_tick__epilogue
FancyCounter_tick__epilogue:
    lw $ra, 36($sp)
    lw $fp, 32($sp)
    addiu $sp, $sp, 40
    jr $ra

FancyCounter_label:
    addiu $sp, $sp, -16
    sw $ra, 12($sp)
    sw $fp, 8($sp)
    move $fp, $sp
    sw $a0, -4($fp)
    la $v0, str_1
    j FancyCounter_label__epilogue
FancyCounter_label__epilogue:
    lw $ra, 12($sp)
    lw $fp, 8($sp)
    addiu $sp, $sp, 16
    jr $ra

FancyCounter_flair:
    addiu $sp, $sp, -16
    sw $ra, 12($sp)
    sw $fp, 8($sp)
    move $fp, $sp
    sw $a0, -4($fp)
    la $v0, str_2
    j FancyCounter_flair__epilogue
FancyCounter_flair__epilogue:
    lw $ra, 12($sp)
    lw $fp, 8($sp)
    addiu $sp, $sp, 16
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

fibonacci:
    addiu $sp, $sp, -96
    sw $ra, 92($sp)
    sw $fp, 88($sp)
    move $fp, $sp
    sw $a0, -64($fp)
    lw $t0, -64($fp)
    li $t1, 1
    sle $t2, $t0, $t1
    sw $t2, -20($fp)
    lw $t0, -20($fp)
    bne $t0, $zero, if_true_3
    j if_end_5
if_true_3:
    lw $v0, -64($fp)
    j fibonacci__epilogue
    j if_end_5
if_end_5:
    lw $t0, -64($fp)
    li $t1, 1
    subu $t2, $t0, $t1
    sw $t2, -48($fp)
    lw $a0, -48($fp)
    jal fibonacci
    sw $v0, -84($fp)
    lw $t0, -64($fp)
    li $t1, 2
    subu $t2, $t0, $t1
    sw $t2, -72($fp)
    lw $a0, -72($fp)
    jal fibonacci
    sw $v0, -88($fp)
    lw $t0, -84($fp)
    lw $t1, -88($fp)
    addu $t2, $t0, $t1
    sw $t2, -92($fp)
    lw $v0, -92($fp)
    j fibonacci__epilogue
fibonacci__epilogue:
    lw $ra, 92($sp)
    lw $fp, 88($sp)
    addiu $sp, $sp, 96
    jr $ra

sumNumbers:
    addiu $sp, $sp, -88
    sw $ra, 84($sp)
    sw $fp, 80($sp)
    move $fp, $sp
    li $t0, 0
    sw $t0, -84($fp)
    li $t0, 0
    sw $t0, -80($fp)
foreach_start_6:
    lw $t0, -80($fp)
    li $t1, 6
    slt $t2, $t0, $t1
    sw $t2, -28($fp)
    lw $t0, -28($fp)
    bne $t0, $zero, foreach_body_7
    j foreach_end_9
foreach_body_7:
    la $t0, numbers
    lw $t1, -80($fp)
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -48($fp)
    lw $t0, -48($fp)
    sw $t0, -64($fp)
    lw $t0, -84($fp)
    lw $t1, -64($fp)
    addu $t2, $t0, $t1
    sw $t2, -72($fp)
    lw $t0, -72($fp)
    sw $t0, -84($fp)
foreach_continue_8:
    lw $t0, -80($fp)
    li $t1, 1
    addu $t2, $t0, $t1
    sw $t2, -80($fp)
    j foreach_start_6
foreach_end_9:
    lw $v0, -84($fp)
    j sumNumbers__epilogue
sumNumbers__epilogue:
    lw $ra, 84($sp)
    lw $fp, 80($sp)
    addiu $sp, $sp, 88
    jr $ra

buildSeries:
    addiu $sp, $sp, -64
    sw $ra, 60($sp)
    sw $fp, 56($sp)
    move $fp, $sp
    sw $a0, -16($fp)
    lw $t0, -16($fp)
    li $t1, 3
    sle $t2, $t0, $t1
    sw $t2, -20($fp)
    lw $t0, -20($fp)
    bne $t0, $zero, if_true_10
    j if_end_12
if_true_10:
    li $a0, 20
    li $v0, 9
    syscall
    sw $v0, -36($fp)
    lw $t0, -36($fp)
    sw $t0, -40($fp)
    lw $t0, -40($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    li $t2, 7
    sw $t2, 0($t0)
    lw $t0, -40($fp)
    li $t1, 1
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    li $t2, 14
    sw $t2, 0($t0)
    lw $t0, -40($fp)
    li $t1, 2
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    li $t2, 21
    sw $t2, 0($t0)
    lw $t0, -40($fp)
    li $t1, 3
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    move $t2, $zero
    sw $t2, 0($t0)
    lw $t0, -40($fp)
    li $t1, 4
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    move $t2, $zero
    sw $t2, 0($t0)
    lw $v0, -40($fp)
    j buildSeries__epilogue
    j if_end_12
if_end_12:
    li $a0, 20
    li $v0, 9
    syscall
    sw $v0, -56($fp)
    lw $t0, -56($fp)
    sw $t0, -60($fp)
    lw $t0, -60($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    li $t2, 7
    sw $t2, 0($t0)
    lw $t0, -60($fp)
    li $t1, 1
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    li $t2, 14
    sw $t2, 0($t0)
    lw $t0, -60($fp)
    li $t1, 2
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    li $t2, 21
    sw $t2, 0($t0)
    lw $t0, -60($fp)
    li $t1, 3
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    li $t2, 28
    sw $t2, 0($t0)
    lw $t0, -60($fp)
    li $t1, 4
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    li $t2, 35
    sw $t2, 0($t0)
    lw $v0, -60($fp)
    j buildSeries__epilogue
buildSeries__epilogue:
    lw $ra, 60($sp)
    lw $fp, 56($sp)
    addiu $sp, $sp, 64
    jr $ra

main:
    addiu $sp, $sp, -720
    sw $ra, 716($sp)
    sw $fp, 712($sp)
    move $fp, $sp
    la $t0, str_3
    sw $t0, -16($fp)
    li $t0, 1
    sw $t0, -12($fp)
    lw $a0, -16($fp)
    jal print_string
    la $a0, str_4
    jal print_string
    la $a0, LIMIT
    lw $a0, 0($a0)
    jal print_int
    jal print_newline
    li $a0, 6
    jal factorial
    sw $v0, -32($fp)
    lw $t0, -32($fp)
    sw $t0, -36($fp)
    la $a0, str_5
    jal print_string
    lw $a0, -36($fp)
    jal print_int
    jal print_newline
    li $a0, 7
    jal fibonacci
    sw $v0, -52($fp)
    lw $t0, -52($fp)
    sw $t0, -56($fp)
    la $a0, str_6
    jal print_string
    lw $a0, -56($fp)
    jal print_int
    jal print_newline
    li $t0, 0
    sw $t0, -168($fp)
while_start_13:
    lw $t0, -168($fp)
    li $t1, 6
    slt $t2, $t0, $t1
    sw $t2, -76($fp)
    lw $t0, -76($fp)
    bne $t0, $zero, while_body_14
    j while_end_15
while_body_14:
    lw $t0, -168($fp)
    li $t1, 1
    addu $t2, $t0, $t1
    sw $t2, -96($fp)
    lw $t0, -96($fp)
    sw $t0, -168($fp)
    lw $t0, -168($fp)
    li $t1, 2
    seq $t2, $t0, $t1
    sw $t2, -112($fp)
    lw $t0, -112($fp)
    bne $t0, $zero, if_true_16
    j if_end_18
if_true_16:
    j while_start_13
    j if_end_18
if_end_18:
    lw $t0, -168($fp)
    li $t1, 4
    sgt $t2, $t0, $t1
    sw $t2, -128($fp)
    lw $t0, -128($fp)
    bne $t0, $zero, if_true_19
    j if_end_21
if_true_19:
    j while_end_15
    j if_end_21
if_end_21:
    la $a0, str_7
    jal print_string
    lw $a0, -168($fp)
    jal print_int
    jal print_newline
    j while_start_13
while_end_15:
do_body_22:
    la $a0, str_8
    jal print_string
    lw $a0, -168($fp)
    jal print_int
    jal print_newline
    lw $t0, -168($fp)
    li $t1, 1
    subu $t2, $t0, $t1
    sw $t2, -156($fp)
    lw $t0, -156($fp)
    sw $t0, -168($fp)
do_continue_23:
    lw $t0, -168($fp)
    li $t1, 1
    sgt $t2, $t0, $t1
    sw $t2, -172($fp)
    lw $t0, -172($fp)
    bne $t0, $zero, do_body_22
do_end_24:
    li $t0, 0
    sw $t0, -212($fp)
for_start_25:
    lw $t0, -212($fp)
    li $t1, 4
    slt $t2, $t0, $t1
    sw $t2, -192($fp)
    lw $t0, -192($fp)
    bne $t0, $zero, for_body_26
    j for_end_28
for_body_26:
    la $a0, str_9
    jal print_string
    lw $a0, -212($fp)
    jal print_int
    jal print_newline
for_continue_27:
    lw $t0, -212($fp)
    li $t1, 1
    addu $t2, $t0, $t1
    sw $t2, -216($fp)
    lw $t0, -216($fp)
    sw $t0, -212($fp)
    j for_start_25
for_end_28:
    li $t0, 0
    sw $t0, -364($fp)
    li $t0, 0
    sw $t0, -332($fp)
foreach_start_29:
    lw $t0, -332($fp)
    li $t1, 6
    slt $t2, $t0, $t1
    sw $t2, -244($fp)
    lw $t0, -244($fp)
    bne $t0, $zero, foreach_body_30
    j foreach_end_32
foreach_body_30:
    la $t0, numbers
    lw $t1, -332($fp)
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -264($fp)
    lw $t0, -264($fp)
    sw $t0, -308($fp)
    lw $t0, -308($fp)
    li $t1, 3
    seq $t2, $t0, $t1
    sw $t2, -280($fp)
    lw $t0, -280($fp)
    bne $t0, $zero, if_true_33
    j if_end_35
if_true_33:
    j foreach_continue_31
    j if_end_35
if_end_35:
    lw $t0, -364($fp)
    lw $t1, -308($fp)
    addu $t2, $t0, $t1
    sw $t2, -304($fp)
    lw $t0, -304($fp)
    sw $t0, -364($fp)
    la $a0, str_10
    jal print_string
    lw $a0, -308($fp)
    jal print_int
    jal print_newline
    lw $t0, -364($fp)
    li $t1, 12
    sgt $t2, $t0, $t1
    sw $t2, -324($fp)
    lw $t0, -324($fp)
    bne $t0, $zero, if_true_36
    j if_end_38
if_true_36:
    j foreach_end_32
    j if_end_38
if_end_38:
foreach_continue_31:
    lw $t0, -332($fp)
    li $t1, 1
    addu $t2, $t0, $t1
    sw $t2, -332($fp)
    j foreach_start_29
foreach_end_32:
    la $a0, str_11
    jal print_string
    lw $a0, -364($fp)
    jal print_int
    jal print_newline
    lw $t0, -364($fp)
    li $t1, 6
    seq $t2, $t0, $t1
    sw $t2, -352($fp)
    lw $t0, -352($fp)
    bne $t0, $zero, switch_case_40
    lw $t0, -364($fp)
    li $t1, 15
    seq $t2, $t0, $t1
    sw $t2, -368($fp)
    lw $t0, -368($fp)
    bne $t0, $zero, switch_case_41
    j switch_default_42
switch_case_40:
    la $a0, str_12
    jal print_string
    jal print_newline
    j switch_end_39
switch_case_41:
    la $a0, str_13
    jal print_string
    jal print_newline
    j switch_end_39
switch_default_42:
    la $a0, str_14
    jal print_string
    jal print_newline
    j switch_end_39
switch_end_39:
try_block_43:
    li $t0, 10
    li $t1, 6
    slt $t2, $t0, $t1
    sw $t2, -380($fp)
    lw $t0, -380($fp)
    bne $t0, $zero, bounds_upper_ok_46
    la $t0, str_30
    sw $t0, -432($fp)
    j catch_block_44
bounds_upper_ok_46:
    li $t0, 10
    li $t1, 0
    sge $t2, $t0, $t1
    sw $t2, -400($fp)
    lw $t0, -400($fp)
    bne $t0, $zero, bounds_lower_ok_47
    la $t0, str_30
    sw $t0, -432($fp)
    j catch_block_44
bounds_lower_ok_47:
    la $t0, numbers
    li $t1, 10
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -424($fp)
    lw $t0, -424($fp)
    sw $t0, -428($fp)
    la $a0, str_15
    jal print_string
    lw $a0, -428($fp)
    jal print_int
    jal print_newline
    j try_end_45
catch_block_44:
    la $a0, str_16
    jal print_string
    lw $a0, -432($fp)
    jal print_string
    jal print_newline
try_end_45:
    la $t0, matrix
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -448($fp)
    lw $t0, -448($fp)
    sw $t0, -468($fp)
    la $t0, matrix
    li $t1, 5
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -464($fp)
    lw $t0, -464($fp)
    sw $t0, -472($fp)
    la $a0, str_17
    jal print_string
    lw $a0, -468($fp)
    jal print_int
    la $a0, str_18
    jal print_string
    lw $a0, -472($fp)
    jal print_int
    jal print_newline
    li $a0, 5
    jal buildSeries
    sw $v0, -488($fp)
    lw $t0, -488($fp)
    sw $t0, -484($fp)
    la $a0, str_19
    jal print_string
    lw $t0, -484($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -500($fp)
    lw $a0, -500($fp)
    jal print_int
    jal print_newline
    la $a0, str_20
    jal print_string
    lw $t0, -484($fp)
    li $t1, 4
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, 0($t0)
    sw $t2, -512($fp)
    lw $a0, -512($fp)
    jal print_int
    jal print_newline
    li $a0, 4
    li $v0, 9
    syscall
    sw $v0, -544($fp)
    li $t0, 0
    sw $t0, -532($fp)
    lw $t0, -544($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, -532($fp)
    sw $t2, 0($t0)
    lw $a0, -544($fp)
    li $a1, 5
    jal Counter_constructor
    lw $t0, -544($fp)
    sw $t0, -652($fp)
    li $a0, 4
    li $v0, 9
    syscall
    sw $v0, -576($fp)
    li $t0, 0
    sw $t0, -564($fp)
    lw $t0, -576($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    lw $t2, -564($fp)
    sw $t2, 0($t0)
    lw $a0, -576($fp)
    li $a1, 10
    jal Counter_constructor
    lw $t0, -576($fp)
    sw $t0, -692($fp)
    la $a0, str_21
    jal print_string
    lw $a0, -652($fp)
    jal Counter_label
    sw $v0, -592($fp)
    lw $a0, -592($fp)
    jal print_string
    jal print_newline
    la $a0, str_22
    jal print_string
    lw $a0, -652($fp)
    jal Counter_tick
    sw $v0, -608($fp)
    lw $a0, -608($fp)
    jal print_int
    jal print_newline
    la $a0, str_23
    jal print_string
    lw $a0, -692($fp)
    jal FancyCounter_label
    sw $v0, -624($fp)
    lw $a0, -624($fp)
    jal print_string
    jal print_newline
    la $a0, str_24
    jal print_string
    lw $a0, -692($fp)
    jal FancyCounter_tick
    sw $v0, -640($fp)
    lw $a0, -640($fp)
    jal print_int
    jal print_newline
    lw $t0, -652($fp)
    li $t1, 0
    sll $t1, $t1, 2
    addu $t0, $t0, $t1
    li $t2, 99
    sw $t2, 0($t0)
    la $a0, str_25
    jal print_string
    lw $a0, -652($fp)
    jal Counter_current
    sw $v0, -656($fp)
    lw $a0, -656($fp)
    jal print_int
    jal print_newline
    lw $t0, -692($fp)
    sw $t0, -676($fp)
    la $a0, str_26
    jal print_string
    lw $a0, -676($fp)
    jal FancyCounter_label
    sw $v0, -680($fp)
    lw $a0, -680($fp)
    jal print_string
    jal print_newline
    la $a0, str_27
    jal print_string
    lw $a0, -692($fp)
    jal FancyCounter_flair
    sw $v0, -696($fp)
    lw $a0, -696($fp)
    jal print_string
    jal print_newline
    jal sumNumbers
    sw $v0, -712($fp)
    lw $t0, -712($fp)
    sw $t0, -716($fp)
    la $a0, str_28
    jal print_string
    lw $a0, -716($fp)
    jal print_int
    jal print_newline
    la $a0, str_29
    jal print_string
    jal print_newline
    jal exit_program
main__epilogue:
    lw $ra, 716($sp)
    lw $fp, 712($sp)
    addiu $sp, $sp, 720
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
