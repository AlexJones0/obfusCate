int main() {
    int b = 0;
    int a = 3;
    if (5 > 4) {
        int a = 1;
        if (a > b) {
            int b = 5;
            a += b;
            int a = 4;
        } else {
            int b;
        }
        {
            b += a * 2;
        }
        switch (b) {
            case 1:
            case 2:
            case 3:
            default: b += 1;
        }
        while (b < a)
            b ++;
        do {
            b--;
        } while (b > a);
        for (int i = 0; i < 100; i++) {
            a += 4;
        }
        b += a;
    } else {
        int a = 4;
        b += a;
    }
    b += a;
}