//////
#include <stdio.h>

int main() {
    int x = 2;
    switch (x) {
        case 3: 
        case 4: x = 5;
                break;
        default: x = 4;
        case 6: x = 3;
        case 2: x = 1;
                break;
    }
    char y = 'e';
    switch (y) {
        case 'x': y = 'y';
        case 'y': y = 'z';
        default: y = '3';
        case 'a': y = '9';
        case 'd': y = '7';
    }
    printf("%d %d\n", x, y);
}