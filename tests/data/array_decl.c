#include <stdio.h>

void f_arr_add(double a[static restrict 10], const double b[static restrict 10]) {
    for (int i = 0; i < 10; i++) {
        a[i] += b[i];
    }
}

int main() {
    const int *x[3];
    int a = 2;
    x[0] = x[1] = x[2] = &a;
    double fst[] = {1.2, 3.4, 5.6};
    const double snd[] = {5.6, 3.4, 1.2};
    f_arr_add(fst, snd);
    const int y1 = *x[0] + *x[1] + *x[2];
    double y2 = fst[0] + fst[1] + fst[2];
    printf("%d %lf\n", y1, y2);
}