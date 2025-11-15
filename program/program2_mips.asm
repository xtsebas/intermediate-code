.data
str_0: .asciiz "triple(10) = "
str_1: .asciiz "computeValues(7) = "
str_2: .asciiz "triple is larger"
str_3: .asciiz "computeValues is larger"
str_4: .asciiz "counter = "
str_5: .asciiz "do-while counter = "
str_6: .asciiz "for loop i = "
str_7: .asciiz "foreach n = "
str_8: .asciiz "counter is five"
str_9: .asciiz "counter is six"
str_10: .asciiz "counter is something else"
numbers: .word 1, 2, 3
newline_str: .asciiz "\n"

.text
.globl main
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

main:
    addiu $sp, $sp, -248
    sw $ra, 244($sp)
    sw $fp, 240($sp)
    move $fp, $sp
    li $a0, 10
    jal triple
    sw $v0, -16($fp)
    lw $t0, -16($fp)
    sw $t0, -52($fp)
    la $a0, str_0
    jal print_string
    lw $a0, -52($fp)
    jal print_int
    jal print_newline
    li $a0, 7
    jal computeValues
    sw $v0, -36($fp)
    lw $t0, -36($fp)
    sw $t0, -56($fp)
    la $a0, str_1
    jal print_string
    lw $a0, -56($fp)
    jal print_int
    jal print_newline
    lw $t0, -52($fp)
    lw $t1, -56($fp)
    sgt $t2, $t0, $t1
    sw $t2, -60($fp)
    lw $t0, -60($fp)
    bne $t0, $zero, if_true_0
    j if_false_1
if_true_0:
    la $a0, str_2
    jal print_string
    jal print_newline
    j if_end_2
if_false_1:
    la $a0, str_3
    jal print_string
    jal print_newline
if_end_2:
    li $t0, 0
    sw $t0, -240($fp)
while_start_3:
    lw $t0, -240($fp)
    li $t1, 3
    slt $t2, $t0, $t1
    sw $t2, -80($fp)
    lw $t0, -80($fp)
    bne $t0, $zero, while_body_4
    j while_end_5
while_body_4:
    la $a0, str_4
    jal print_string
    lw $a0, -240($fp)
    jal print_int
    jal print_newline
    lw $t0, -240($fp)
    li $t1, 1
    addu $t2, $t0, $t1
    sw $t2, -104($fp)
    lw $t0, -104($fp)
    sw $t0, -240($fp)
    j while_start_3
while_end_5:
do_body_6:
    la $a0, str_5
    jal print_string
    lw $a0, -240($fp)
    jal print_int
    jal print_newline
    lw $t0, -240($fp)
    li $t1, 1
    addu $t2, $t0, $t1
    sw $t2, -128($fp)
    lw $t0, -128($fp)
    sw $t0, -240($fp)
    lw $t0, -240($fp)
    li $t1, 5
    slt $t2, $t0, $t1
    sw $t2, -144($fp)
    lw $t0, -144($fp)
    bne $t0, $zero, do_body_6
    li $t0, 0
    sw $t0, -184($fp)
for_start_7:
    lw $t0, -184($fp)
    li $t1, 2
    slt $t2, $t0, $t1
    sw $t2, -164($fp)
    lw $t0, -164($fp)
    bne $t0, $zero, for_body_8
    j for_end_9
for_body_8:
    la $a0, str_6
    jal print_string
    lw $a0, -184($fp)
    jal print_int
    jal print_newline
    lw $t0, -184($fp)
    li $t1, 1
    addu $t2, $t0, $t1
    sw $t2, -188($fp)
    lw $t0, -188($fp)
    sw $t0, -184($fp)
    j for_start_7
for_end_9:
    li $t0, 1
    sw $t0, -212($fp)
    la $a0, str_7
    jal print_string
    lw $a0, -212($fp)
    jal print_int
    jal print_newline
    li $t0, 2
    sw $t0, -212($fp)
    la $a0, str_7
    jal print_string
    lw $a0, -212($fp)
    jal print_int
    jal print_newline
    li $t0, 3
    sw $t0, -212($fp)
    la $a0, str_7
    jal print_string
    lw $a0, -212($fp)
    jal print_int
    jal print_newline
    lw $t0, -240($fp)
    li $t1, 5
    seq $t2, $t0, $t1
    sw $t2, -228($fp)
    lw $t0, -228($fp)
    bne $t0, $zero, switch_case_11
    lw $t0, -240($fp)
    li $t1, 6
    seq $t2, $t0, $t1
    sw $t2, -244($fp)
    lw $t0, -244($fp)
    bne $t0, $zero, switch_case_12
    j switch_default_13
switch_case_11:
    la $a0, str_8
    jal print_string
    jal print_newline
    j switch_end_10
switch_case_12:
    la $a0, str_9
    jal print_string
    jal print_newline
    j switch_end_10
switch_default_13:
    la $a0, str_10
    jal print_string
    jal print_newline
    j switch_end_10
switch_end_10:
    jal exit_program
main__epilogue:
    lw $ra, 244($sp)
    lw $fp, 240($sp)
    addiu $sp, $sp, 248
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
