//////
#include <stdio.h>

int main() {
    long long prevprev = 0;
    long long prev = 1;
    long long n = 3;
    long long fib_n = 1;
    printf("1: 0\n2: 1\n");
    while (n++ < 50) {
        fib_n = prev + prevprev;
        prevprev = prev;
        prev = fib_n;
        printf("%d: %llu\n", n - 1, fib_n);
    }
}
