// Code is taken (with two code examples combined, and also slightly modified) 
// from: https://en.cppreference.com/w/c/language/array

//////
#include <stdio.h>

void f(int a[], int sz) // actually declares void f(int* a, int sz)
{
    for(int i = 0; i < sz; ++i)
       printf("%d\n", a[i]);
}

int main(void) {
    int n = 1;
label:;
    int a[n]; // re-allocated 10 times, each with a different size
    printf("The array has %zu elements\n", sizeof a / sizeof *a);
    if (n++ < 10) goto label; // leaving the scope of a VLA ends its lifetime
    int b[10] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    f(b, 10); // converts a to int*, passes the pointer
}