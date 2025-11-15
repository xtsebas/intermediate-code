.data
str_0: .asciiz "double(3) = "
str_1: .asciiz "mainValue returned: "
newline_str: .asciiz "\n"

.text
.globl main
double:
    addiu $sp, $sp, -24
    sw $ra, 20($sp)
    sw $fp, 16($sp)
    move $fp, $sp
    sw $a0, -20($fp)
    lw $t0, -20($fp)
    lw $t1, -20($fp)
    addu $t2, $t0, $t1
    sw $t2, -24($fp)
    lw $v0, -24($fp)
    j double__epilogue
double__epilogue:
    lw $ra, 20($sp)
    lw $fp, 16($sp)
    addiu $sp, $sp, 24
    jr $ra

mainValue:
    addiu $sp, $sp, -16
    sw $ra, 12($sp)
    sw $fp, 8($sp)
    move $fp, $sp
    li $t0, 7
    sw $t0, -8($fp)
    lw $v0, -8($fp)
    j mainValue__epilogue
mainValue__epilogue:
    lw $ra, 12($sp)
    lw $fp, 8($sp)
    addiu $sp, $sp, 16
    jr $ra

main:
    addiu $sp, $sp, -40
    sw $ra, 36($sp)
    sw $fp, 32($sp)
    move $fp, $sp
    li $a0, 3
    jal double
    sw $v0, -16($fp)
    lw $t0, -16($fp)
    sw $t0, -20($fp)
    la $a0, str_0
    jal print_string
    lw $a0, -20($fp)
    jal print_int
    jal print_newline
    jal mainValue
    sw $v0, -36($fp)
    lw $t0, -36($fp)
    sw $t0, -40($fp)
    la $a0, str_1
    jal print_string
    lw $a0, -40($fp)
    jal print_int
    jal print_newline
    jal exit_program
main__epilogue:
    lw $ra, 36($sp)
    lw $fp, 32($sp)
    addiu $sp, $sp, 40
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
