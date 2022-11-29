#include <stdio.h>

const char *f(const char *x) {
    return x;
}

typedef struct { // Struct definition
    int idNum;
    char username[100];
} Thing;

int main() {
    Thing acct = {.idNum = 4596, .username = "JohnDoe92"}; // Named initializer
    const char* b = f("Testing"); // Function argument
    char a = "Hello world!"[5]; // Array index
    char *z = "Hello there, welcome to the program."; // Standard string (char *) definition
    int y = 3;
    char *h = (y > 2) ? "good" : "bad"; // Ternary operator usage
    char i[][6] = {"abcde", "fghij", "klmno", "pqrst", "uvwxy", "z    "}; // Multi-dimensional array
    if ("hello" > "abc") {} // Expression
    if ("hello") {} // If statement
    while (!"hello") {} // While statement
    do {} while (!"hello"); // Do while statement
    char x[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"; // Standard string (char[]) definition
    char w[] = {'\032', '\027', '\045', '\067', '\032', '\0'}; //Already encoded string
    printf("%c\n%s\n%s\n%s\n%s\n%s\n%s\n", a, z, x, h, acct.username, i[3], b);
}