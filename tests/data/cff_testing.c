#include <stdio.h>
int attempts = 10;

int fib(int n) {
    int x, x_result, y, y_result;
    if (n < 0) {
        return -1;
    } else if (n <= 1) {
        return n;
    } else {
        x = n - 1;
        x_result = fib(x);
        y = n - 2;
        y_result = fib(y);
        return x_result + y_result;
    }
}

int main() {
    int i;
    for (i = 0; i < attempts; i++) {
        printf("%d: %d\n", i + 1, fib(i));
    }
}


