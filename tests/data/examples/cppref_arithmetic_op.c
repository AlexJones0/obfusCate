// Code is taken (with four code examples combined, and also slightly modified) 
// from: https://en.cppreference.com/w/c/language/operator_arithmetic

//////
#include <stdio.h>
#include <complex.h>
#include <limits.h>
#include <math.h>
#include <stdint.h>
enum {ONE=1, TWO=2};
 
int main(void)
{
    //// Program 1
    char c = 'a';
    printf("sizeof char: %zu sizeof int: %zu\n", sizeof c, sizeof +c);
 
    printf("-1, where 1 is signed: %d\n", -1);
 
    // Defined behavior since arithmetic is performed for unsigned integer.
    // Hence, the calculation is (-1) modulo (2 raised to n) = UINT_MAX, where n is
    // the number of bits of unsigned int. If unsigned int is 32-bit long, then this
    // gives (-1) modulo (2 raised to 32) = 4294967295
    printf("-1, where 1 is unsigned: %u\n", -1u); 
 
    //// Program 2
    double complex z = 1 + 2*I;
    printf("-(1+2i) = %.1f%+.1f\n", creal(-z), cimag(-z));

    double complex z2 = (1 + 0*I) * (INFINITY + I*INFINITY);
    // textbook formula would give
    // (1+i0)(∞+i∞) ⇒ (1×∞ – 0×∞) + i(0×∞+1×∞) ⇒ NaN + I*NaN
    // but C gives a complex infinity
    printf("%f + i*%f\n", creal(z2), cimag(z2));

    //// Program 3
    uint32_t a = 0x12345678;
    uint16_t mask = 0x00f0;
 
    printf("Promoted mask:\t%#010x\n"
           "Value:\t\t%#x\n"
           "Setting bits:\t%#x\n"
           "Clearing bits:\t%#x\n"
           "Selecting bits:\t%#010x\n"
           , mask
           , a
           , a | mask
           , a & ~mask
           , a & mask
    );

    //// Program 4
    char d = 0x10;
    unsigned long long ulong_num = 0x123;
    printf("0x123 << 1  = %#llx\n"
           "0x123 << 63 = %#llx\n"   // overflow truncates high bits for unsigned numbers
           "0x10  << 10 = %#x\n",    // char is promoted to int
           ulong_num << 1, ulong_num << 63, d << 10);
    long long long_num = -1000;
    printf("-1000 >> 1 = %lld\n", long_num >> ONE);  // implementation defined
}