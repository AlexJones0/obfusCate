//////
//////10 5
#include <stdio.h>

int main() {
    int i;
    for (i = 10; i > 0; i--) {
        break;
    }
    while (1) {
        break;
    }
    do {
        break;
    } while (1);
    int x = 3;
    switch (x) {
        case 3: 
        case 4: x = 5;
                break;
        default: x = 4;
    }
    printf("%d %d\n", i, x);
}