//////
#include <stdio.h>
#include <stdlib.h>

int*** f();
int *****g();
double h();

int main() {
    int*** x = f();
    int***** y = g();
    printf("%f\n", ***x + y[0][0][0][0][0] * h());
    free(x);
    free(y);
}

 int*** f() {
    int *x = malloc(sizeof(int));
    int **xp = malloc(sizeof(int*));
    int ***xpp = malloc(sizeof(int**));
    *xp = x;
    *xpp = xp;
    ***xpp = 5;
    return xpp;
}

int *****g() {
    int *x = malloc(sizeof(int));
    int **xp = malloc(sizeof(int*));
    int ***xpp = malloc(sizeof(int**));
    int ****xppp = malloc(sizeof(int***));
    int *****xpppp = malloc(sizeof(int****));
    *xp = x;
    *xpp = xp;
    *xppp = xpp;
    *xpppp = xppp;
    xpppp[0][0][0][0][0] = 19;
    return xpppp;
}

double h() {
    return 4.9632;
}
