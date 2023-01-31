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

int main() {
	int i = 0;
	while (i < attempts) {
        printf("%d: %d\n", i + 1, fib(i));
		i++;
    }
}
