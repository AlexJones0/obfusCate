//////
//////13 163
#include <stdio.h>

int main() {
    int x = 1;
    x = 2;
    x += 3;
    x -= 4;
    x *= 5;
    x += 6;
    x /= 7;
    x %= 8;
    x <<= 9;
    x >>= 10;
    x &= 11;
    x ^= 12;
    x |= 13;
    int y = x;
    y *= 3;
    y ^= 132;
    printf("%d %d\n", x, y);
}