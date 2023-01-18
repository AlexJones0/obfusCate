#include <stdio.h>
#include <stdlib.h>
#include <time.h>
int rand_num;

int main() {
    srand(time(0));
    rand_num = (int) rand();
    printf("Your random number is: %d\n", rand_num);
}