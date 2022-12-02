#include <stdalign.h> // Preprocessor directives
#include <stdarg.h>

const float PI = 3.14159; // Constant

int x = 10; // Global int
float y = 10.0; // Global float

typedef int* dims; // Typdef

typedef struct { // Struct definition
    int idNum;
    char username[100];
} Thing;

union ImportantData {
    int thing1;
    float thing2;
    char *thing3;
    _Bool thing4;
} data; // Union 

union test1del { int thing1; };
enum test2del{X,Y,Z} test3del;

dims do_something(dims x, float y, short *z);
int do_something2();
int do_something3(void);
int do_something4(int x, ...) {}

void start(); // Prototype

// #pragma startup start // Pragma

void start() {
    x = 10;
}

int f(int n, float m) { // Function Declaration + Parameters
    ; // Empty statement (null stmt)
    enum day{Monday, Tuesday, Wednesday, Thursday, Friday=100, Saturday, Sunday}; // Enum
    enum day today = Friday; // Enum reference
    Thing acct = {.idNum = 4596, .username = "JohnDoe92"}; // Named initializer, Struct Ref (?)
    acct.username[0] = 'j';
    struct mything {int first; float second;};
    struct mything yes = {1, 2.0};
    typedef int mything;
    mything abcdungdfg = 4;
    alignas(32) float data[4]; // Alignas
    x = 15 + 4; // Assignment, binary expression
    x = (n < m) ? x + 3 : x - 3; // Ternary operator
    int z[2][3] = {{0, 3, 0}, {0, 0, 0}}; // Array definition, Decl, designated initializer
    dims p = (int[]){2, 4}; // Pointer Decl, Compound literal
    switch (x) { // Switch statement
        case 10: // Case
            x = -1; // Unary Operator
            break; // Break
        default: // Default case
            x += 1;
    }
    while (n) { // While loop
        if (n && m) { // If stmt
            m = 0;
            continue; // Continue
        } else { // Else stmt
            break; // Loop break
        }
    }
    if (n + m < 15) {
        goto out; // GOTO statement
    }
    do { // Do while
        m = (m * -1) + 1;
    } while (m <= 0);
    for (int i = 0; i < 10; ++i) { // For loop
        n = n + 1;
    }
    { // Compound Statement
        int a;
        if (z[0][1]) { // Array reference, if statement
            return 5; // return expression statement
        } else { // else statement
            return; // return void statement
        }
    }
    return 4;
    //static_assert(sizeof(int) == 2 * sizeof(short), "The program requires an integer is the size of 2 shorts.");
    int test = 3 + x + Friday + acct.idNum + (int) 4.56 + f(3,2.4) + z[0][1];
    return n + m;
    out: // Label
    return 4; 
}

void variadic(char *f, ...) { // Elipsis param (variadic function)
    return;
}

int main() {
    f(x, y); // Function call
    do_something4(0, "1", 2, 3.0, 2 + 2); // Variadic function call
    return abs(0);
}