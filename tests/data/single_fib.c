#include <stdio.h>

int main() {
    long long prevprev = 0;
    long long prev = 1;
    long long n = 3;
    long long fib_n = 1;
    printf("0\n1\n");
    while (n++ < 50) {
        fib_n = prev + prevprev;
        prevprev = prev;
        prev = fib_n;
        printf("%llu\n", fib_n);
    }
}
