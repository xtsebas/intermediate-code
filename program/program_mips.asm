.data
vtable_Animal: .word Animal_speak
vtable_Dog: .word Dog_speak
newline_str: .asciiz "\n"

.text
.globl main
main:
    addiu $sp, $sp, -16
    sw $ra, 12($sp)
    sw $fp, 8($sp)
    move $fp, $sp
__fn_epilogue:
    lw $ra, 12($sp)
    lw $fp, 8($sp)
    addiu $sp, $sp, 16
    jr $ra

# Runtime helpers would follow here