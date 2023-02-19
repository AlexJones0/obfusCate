//////
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
int rand_num;

int main() {
    srand(123);
    rand_num = (int) rand();
    printf("Your random number is: %d\n", rand_num);
}