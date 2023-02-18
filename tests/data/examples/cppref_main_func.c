// Code is taken from: https://en.cppreference.com/w/c/language/main_function

//////abcdxyz123
#include <stdio.h>
 
int main(int argc, char *argv[])
{
    printf("argc = %d\n", argc);
    for(int ndx = 1; ndx != argc; ++ndx)
        printf("argv[%d] --> %s\n", ndx, argv[ndx]);
    printf("argv[argc] = %p\n", (void*)argv[argc]);
}
