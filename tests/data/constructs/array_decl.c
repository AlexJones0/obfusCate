//////
#include <stdio.h>

int f_arr_add(double a[static 3], double b[static 3]) {
    for (int i = 0; i < 3; i++) {
        a[i] += b[i];
    }
}

int main() {
    float *a[12];
    int b[5] = {1, 2, 3};
    double c[] = {1.1, 2.2, 3.3};
    double d[] = {3.3, 2.2, 1.1, 0.0};
    int y1 = b[0] + b[1] + b[2] + b[3] + b[4];
    f_arr_add(c, d);
    float y2 = c[0] + c[1] + c[2];
    printf("%d %f\n", y1, y2);
}