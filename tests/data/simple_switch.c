int f() {
    int x = 4;
    switch (x) {
        case 1: x = 2; break;
        case 2: x = 3; break;
        case 3: x = 4; break;
        case 4: x = 1; break;
        default: x = 1;
    }
}

int main() {
    f();
}