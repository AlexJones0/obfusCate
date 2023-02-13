//////23 1
#include <stdio.h>

int main() {
    int x = 5;
    int y = 2;
    x = x + y - x * y / y % x & y | x ^ y << x >> y;
    y = x > y < x >= y <= x == y != x && y || x;
    printf("%d %d\n", x, y);
}