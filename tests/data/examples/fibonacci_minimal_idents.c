//////
#include <stdio.h>
int attempts = 10;

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

int fib2(int n) {
    if (n < 0) {
        return -1;
    } else if (n <= 1) {
        return n;
    } else {
        int x = n - 1;
        int x_result = fib2(x);
        int y = n - 2;
        int y_result = fib2(y);
		int result = x_result + y_result;
        return result;
    }
}

int fib3(int n) {
    if (n < 0) {
        return -1;
    } else if (n <= 1) {
        return n;
    } else {
        int x = n - 1;
        int x_result = fib3(x);
        {int y = n - 2;
        int y_result = fib3(y);
        return x_result + y_result;}
    }
}

int main() {
    for (int i = 0; i < attempts; i++) {
        printf("%d: %d\n", i + 1, fib(i));
		printf("%d: %d\n", i + 1, fib2(i));
		printf("%d: %d\n", i + 1, fib3(i));
    }
}
