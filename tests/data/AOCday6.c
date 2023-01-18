#include <stdio.h>
#include <stdlib.h>
#include <string.h>

char* read_input(char* path) {
    FILE* f = fopen(path, "r");
    fseek(f, 0, SEEK_END);
    size_t filesize = (size_t) ftell(f);
    rewind(f);
    char* buf = malloc(filesize + 1);
    size_t bytes_read = fread(buf, sizeof(char), filesize, f);
    if(filesize != bytes_read)
        exit(1);
    buf[bytes_read] = '\0';
    fclose(f);
    return buf;
}

int solve(char* data, int n) {
    int top_iter = strlen(data);
    char *window = (char *) malloc(sizeof(char) * (n+1));
    short unique = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < i; j++) {
            if (window[j] == data[i]) {
                unique--;
                break;
            }
        }
        unique++;
        window[i] = data[i];
    }
    window[n] = '\0';
    for (int i = n; i < top_iter; i++) {
        char newchar = data[i];
        char first = window[0];
        _Bool foundold = 0, foundnew = 0;
        for (int j = 0; j < (n-1); j++) {
            window[j] = window[j+1];
            foundold = foundold || window[j] == first;
            foundnew = foundnew || window[j] == newchar;
        }
        window[n-1] = newchar;
        if (!foundold)
            unique--;
        if (!foundnew)
            unique++;
        if (unique == n) {
            free(window);
            return i;
        }
    }
    free(window);
    return -1;
}

void problem11(char *file) {
    char* data = strsep(&file, "\r");
    printf("Problem 11: %d\n", solve(data, 4));
}

void problem12(char *file) {
    char* data = strsep(&file, "\r");
    printf("Problem 12: %d\n", solve(data, 14));
}

int main() {
    char* file = read_input("./Day 6/data.txt"); 
    char* copy = strdup(file);
    problem11(file);
    problem12(copy);
    free(file);
    free(copy);
    return 0;
}