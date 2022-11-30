#include <stdio.h>
#include <time.h>

int vals = 20;
int runs = 10000;

int fib(int n) {
    if (n < 0) {
        return -1;
    } else if (n <= 1) {
        return n;
    } else {
        int x = n - 1;
        int x_result = fib(x);
        int y = n - 2;
        int y_result = fib(y);
        return x_result + y_result;
    }
}

int main() {
    clock_t begin = clock();
    unsigned long long x = 0;
    for (int j = 0; j <= runs; j++) {
        for (int i = 0; i <= vals; i++) {
            x += fib(i);
        }
    }
    clock_t end = clock();
    double time_spent = (double)(end - begin) / CLOCKS_PER_SEC;
    printf("Time elapsed: %f seconds.\n", time_spent);
}