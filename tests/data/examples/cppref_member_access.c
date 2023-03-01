// Code is taken (combining five examples and slightly modifying them) 
// from: https://en.cppreference.com/w/c/language/operator_member_access

//////
#include <stdio.h>

struct s {int x;};
int f(char c) { return c;}
struct s f2(void) { return (struct s){1}; }

int main(void)
{
    //// Program 1
    int a[3] = {1,2,3};
    printf("%d %d\n", a[2],  // n == 3
                      2[a]); // same, n == 3
    a[2] = 7; // subscripts are lvalues
 
    int n[2][3] = {{1,2,3},{4,5,6}};
    int (*p)[3] = &n[1]; // elements of n are arrays
    printf("%d %d %d\n", (*p)[0], p[0][1], p[0][2]); // access n[1][] via p
    int x = n[1][2]; // applying [] again to the array n[1]
    printf("%d\n", x);
 
    printf("%c %c\n", "abc"[2], 2["abc"]); // string literals are arrays too

    //// Program 2
    int n2 = 1;
    int* p2 = &n2;
    printf("*p = %d\n", *p2); // the value of *p is what's stored in n
    *p2 = 7; // *p is lvalue
    printf("*p = %d\n", *p2);

    //// Program 3
    int n3 = 1;
    int *p3 = &n3; // address of object n
    int a2[3] = {1,2,3};
    int *start=a, *end=&a2[3]; // same as end = a+3

    //// Program 4
    struct s s;
    s.x = 1; // ok, changes the member of s
    int n4 = f2().x; // f() is an expression of type struct s
 
    const struct s sc;
 
    union { int x; double d; } u = { 1 };
    u.d = 0.1; // changes the active member of the union
    struct { int x; double d; } stru = {3};
    stru.d = 4.5;

    //// Program 5
    struct s s2={1}, *p4 = &s;
    p4->x = 7; // changes the value of s.x through the pointer
    printf("%d\n", p4->x); // prints 7
}