int global = 9;

float my_func(float n) {
    typedef int whole;
    struct my_information {char *important; whole age; float xyz;};
    if (n > 0) {
        struct my_information x = {"hello", (whole) 3.56, 0.0f};
		x.age = 92;
		x.xyz = 14.3456;
		struct my_information z = {.important = "abc", .age=32, .xyz = -2.4f};
    } else if (n == 0) {
        union other_information { whole x; float y;};
        n++;
        goto fastreturn;
    } else {
        enum Boolean {True=1, False=0};
		struct my_information your_information = {"abc", 9.32, 0.0f};
		enum Boolean z = False;
		typedef enum Boolean bool;
		bool fp = False;
		typedef struct lem {whole a; struct lem* zzz;} lem;
		lem zzz = {.a = 32, .zzz = NULL};
		zzz.zzz = &zzz;
		zzz.zzz->zzz = NULL;
		struct {int c; float b; char *a;} abcxyz = {.c = 4, .b = 5.2, .a = NULL};
		abcxyz.c = 5;
		abcxyz.a = NULL;
        return 0.0;
    }
    fastreturn: 
    return n;
}

int main() {
    my_func(4.5);
}


