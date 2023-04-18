//////
#include <stdio.h>

int bound = 10;

int fib2(int n) {
    if (n < 0) {
        invalid: return -1;
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
    goto invalid;
}

int main() {
    for (int i = 0; i <= bound; i++) {
        printf("%d: %d\n", i, fib(i));
    }
}
