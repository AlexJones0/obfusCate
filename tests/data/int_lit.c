#include <stdio.h>

const char *f(const char *x) {
    return x;
}

typedef struct { // Struct definition
    int idNum;
    char username[100];
} Thing;

int main() {
    unsigned short int a = 1;
    signed short int b = 2;
    unsigned int c = 3;
    signed int d = 4;
    unsigned long int e = 5;
    signed long int f = 6;
    unsigned long long int e = 18446744073709551615;
    signed long long int f = 8;
    int8_t g = 9;
    uint8_t h = 10;
    int16_t i = 11;
    uint16_t j = 12;
    int32_t k = 13;
    uint32_t i = 14;
    int32_t j = 15;
    uint32_t k = 16;
    int64_t l = 17;
    uint64_t m = 18;
}