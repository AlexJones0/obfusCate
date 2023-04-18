int global = 9;

float my_func(float n) {
    typedef int whole;
    struct s {char *str; whole age;} x;
    if (n > 0) {
        struct s x = {"abc", (whole) 3.56};
    } else if (n == 0) {
        union u { whole x; float y;} p;
        goto my_label;
    } else {
        enum Bool {True=1, False=0};
        other: return 0.0;
    }
    my_label: return n;
}

int main() {
    my_func(4.5);
}


