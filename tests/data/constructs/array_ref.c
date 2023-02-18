//////
#include <stdio.h>

int main() {
    int arr[10][10];
    for (int i = 0; i < 10; i++) {
        for (int j = 0; j < 10; j++) {
            arr[i][j] = (i+1) * (j+1);
        }
    }
    int sum1 = 0, sum2 = 0;
    for (int i = 0; i < 10; i++) {
        sum1 += arr[i][i];
        sum2 += arr[9-i][i];
    }
    printf("%d %d\n", sum1, sum2);
}