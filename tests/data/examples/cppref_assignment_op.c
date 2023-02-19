// Code is taken (with two code examples combined, and also slightly modified) 
// from: https://en.cppreference.com/w/c/language/operator_assignment

//////
#include <stdio.h>
 
int main(void)
{
    // integers
    int i = 1, j = 2, k = 3; // initialization, not assignment
 
    i = j = k;   // values of i and j are now 3
    printf("%d %d %d\n", i, j, k);
 
    // pointers
    const char c = 'A'; // initialization; not assignment
    const char *p = &c;  // initialization; not assignment
    const char **cpp = &p; // initialization; not assignment
 
    *cpp = &c;  // OK, char* is convertible to const char*
    printf("%c \n", **cpp);
    cpp = 0;    // OK, null pointer constant is convertible to any pointer
 
    // arrays
    int arr1[2] = {1,2}, arr2[2] = {3, 4};
    printf("arr1[0]=%d arr1[1]=%d arr2[0]=%d arr2[1]=%d\n",
            arr1[0],   arr1[1],   arr2[0],   arr2[1]);

    // Program 2 starts here
    int x = 10; 
    int hundred = 100; 
    int ten = 10; 
    int fifty = 50; 
 
    printf("%d %d %d %d\n", x, hundred, ten, fifty);
 
    hundred *= x; 
    ten     /= x; 
    fifty   %= x; 
 
    printf("%d %d %d %d\n", x, hundred, ten, fifty);
 
    return 0;
}