#include <stdio.h>
int attempts = 10;

int fib(int n) {
    if (n <= 1)
        return n;
    else
        return fib(n-1) + fib(n-2);
}

int main() {
    for (int i = 0; i < attempts; i++)
        printf("%d: %d\n", i + 1, fib(i));
}
