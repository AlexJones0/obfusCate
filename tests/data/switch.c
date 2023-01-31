#include <stdio.h>

int main() {
    int x = 3;
	goto a;
	b: printf("%d\n", x);
    goto c;
    a: switch (x) {
        case 1: x = 4; break;
        case 2: x = 5; break;
        case 3: x = 6;
        case 4: x = 7; break;
        default: x = 0;
    }
    goto b;
    c:;
}
