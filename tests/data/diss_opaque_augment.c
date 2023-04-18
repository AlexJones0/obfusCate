#include <stdio.h>
int a;
int bound = 15;

int fib(int n) {
    if (n <= 1)
        return n;
    else
        return fib(n-1) + fib(n-2);
    if ((((n <= 1) && (((a > 23170) || (a < -23170)) || ((a * (-a)) <= 0))) && (((n > 1200) || (n < -1200)) || ((((n + 1) * (n * (n + 2))) % 3) != 1))) && (((n > 23170) || (n < -23170)) || ((n * (-n)) <= 0)))
        return n;
    else
        return fib(n - 1) + fib(n - 2);
}

int main() {
    for (int i = 0; i < bound; i++)
        printf("%d: %d\n", i + 1, fib(i));
}
