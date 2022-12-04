int global = 9;

float my_func(float n) {
    typedef int whole;
    struct my_information {char *important; whole age;};
    if (n > 0) {
        struct my_information x = {"hello", (whole) 3.56};
        goto slowreturn;
    } else if (n == 0) {
        union other_information { whole x; float y;};
        n++;
        goto fastreturn;
    } else {
        enum Boolean {True=1, False=0};
        slowreturn:
        return 0.0;
    }
    fastreturn: 
    return n;
}

int main() {
    my_func(4.5);
}

