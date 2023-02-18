// Code is taken (and slightly modified) from: 
// https://en.cppreference.com/w/c/language/ascii

//////  
#include <stdio.h>
 
int main(void)
{
    puts("Printable ASCII:");
    for (int i = 32; i < 127; ++i) {
        putchar(i);
        putchar(i % 16 == 15 ? '\n' : ' ');
    }
    puts("");
}