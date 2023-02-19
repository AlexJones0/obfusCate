//////
#include <stdio.h>
#include <stdlib.h>

int main() {
    double y = 5.4632;
    double z = 3.592;
    int a1 = (int) y * z;
    int a2 = ((int) y) * ((int) z);
    int a3 = (int) (((int) y) * z);
    int a4 = (int) (y * ((int) z));
    typedef double real;
    real **x = (real **) malloc(sizeof(real *) * 40);
    for (int i = 0; i < 40; i++) {
        x[i] = (real *) malloc(sizeof(real) * 30);
    }
    x[19][26] = 5.4639453984539852348239429348;
    double a5 = x[19][26];
    float a6 = (float) x[19][26];
    double a7 = (real) a6;
    int a8 = (int) a6;
    printf("%d %d %d %d %.25f %.25f %.25f %d\n", a1, a2, a3, a4, a5, a6, a7, a8);
    free(x);
}
