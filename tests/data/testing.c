// Functions and vaiables are both just ID types - they can shadow each other, so cannot have the same name
// Structs and (functions/variables) can have the same name, as the struct qualifier is used
// Struct element names also have their own scope in the struct, so can be literally anything not used in the struct.
// ^^ Likewise with union element names
// However, Structs and Unions cannot have the same name (despite being quantified) - they can shadow each other though
// Basically, it seems that:
//      > Structs, Unions and Enums share type systems, and
//      > Variable names, function names, Enumerators and typdefs share systems
//      > Identifiers in the same system cannot be redeclared/redefined in the same scope
//      > Labels have their own system - they are per function, and cannot be shadowed.
//        They also cannot be defined globally.
//      > However, other identifiers in the same system absolutely can be shadowed in a separate scope
#include<stdio.h>

int a() {
    return 3;
}

int main() {
    // typedef int a
    //int a = 4;
    struct a {int a; int b;};
    struct a my_struct = {.a = 2, .b = 3};
    union b {int a; float b; char* c; _Bool d;};
    union b my_union;
    enum c{abc, def, ghi = -1};
    my_union.a = 1;
    int first = a();
    int second = my_struct.a;
    int third = my_union.a;
    typedef int a;
    a fourth = 0;
    enum c fifth = ghi;
    printf("%d\n%d\n%d\n%d\n%d\n", first, second, third, fourth, fifth);
    return 0;
}