// Code is taken (and slightly modified) from: https://en.cppreference.com/w/c/language/compound_literal

//////
#include <stdio.h>
 
int *p = (int[]){2, 4}; // creates an unnamed static array of type int[2]
                        // initializes the array to the values {2, 4}
                        // creates pointer p to point at the first element of
                        // the array
const float *pc = (const float []){1e0, 1e1, 1e2}; // read-only compound literal
 
struct point {double x,y;};
 
void drawline1(struct point from, struct point to)
{
    printf("drawline1: `from` @ {%.2f, %.2f}, `to` @ {%.2f, %.2f}\n",
        from.x, from.y, to.x, to.y);
}
 
void drawline2(struct point *from, struct point *to)
{
    printf("drawline2: `from` @ {%.2f, %.2f}, `to` @ {%.2f, %.2f}\n",
        from->x, from->y, to->x, to->y);
}

int main(void)
{
    int n = 2, *p = &n;
    p = (int [2]){*p}; // creates an unnamed automatic array of type int[2]
                       // initializes the first element to the value formerly
                       // held in *p
                       // initializes the second element to zero
                       // stores the address of the first element in p
 
    drawline1(
        (struct point){.x=1, .y=1},  // creates two structs with block scope and
        (struct point){.x=3, .y=4}); // calls drawline1, passing them by value
    drawline2(
        &(struct point){.x=1, .y=1},  // creates two structs with block scope and
        &(struct point){.x=3, .y=4}); // calls drawline2, passing their addresses
}
