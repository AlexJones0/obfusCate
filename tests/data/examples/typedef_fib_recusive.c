#include <stdio.h>
int typedef number1, number2;
typedef number1 number3;
typedef number3 number5;

number1 attempts = 10;

number5 typedef number4;

number2 fib(number4 n) {
    if (n < 0) {
        return -1;
    } else if (n <= 1) {
        return n;
    } else {
        number3 x = n - 1;
        number2 x_result = fib(x);
        number2 y = n - 2;
        number5 y_result = fib(y);
        return x_result + y_result;
    }
}

number3 main() {
    for (number4 i = 0; i < attempts; i++) {
        printf("%d: %d\n", i + 1, fib(i));
    }
}
