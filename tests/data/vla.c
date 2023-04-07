#include <stdio.h>

int bar (int argc) {
    int n = argc;
    int x[n];
    for (int i = 0; i < n; i++) {
        x[i] = i + 1; 
    }
    int sum = 0;
    for (int i = 0; i < n; i++) { 
        sum += x[i];
    }
    printf("Size of x: %lu\n", sizeof(x));
    printf("Sum: %d\n", sum);
    return 0;
}

int main(int argc, char *argv[]) {
    return bar(argc);
}