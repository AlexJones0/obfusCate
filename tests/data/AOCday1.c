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

void problem1(char *file) {
    char* line = strsep(&file, "\r");
    int count = 0;
    int max_ = 0;
    while (line != NULL) {
        if (strcmp(line, "") == 0 || strcmp(line, "\n") == 0) {
            max_ = (count > max_) ? count : max_;
            count = 0;
        }
        count += atoi(line);
        line = strsep(&file, "\r");
    }
    max_ = (count > max_) ? count : max_;
    printf("\nProblem 1: %d", max_);
}

void problem2(char *file) {
    char* line = strsep(&file, "\r");
    int count = 0;
    int max_[3] = {0, 0, 0};
    int lastpass = 0;
    while (line != NULL) {
        if (strcmp(line, "") == 0 || strcmp(line, "\n") == 0) {
            if (count > max_[0]) {
                if (count > max_[1]) {
                    max_[0] = max_[1];
                    if (count > max_[2]) {
                        max_[1] = max_[2];
                        max_[2] = count;
                    } else
                        max_[1] = count;
                } else
                    max_[0] = count;
            }
            count = 0;
            if (lastpass)
                break;
        }
        count += atoi(line);
        line = strsep(&file, "\r");
        if (line == NULL)
            lastpass = 1;
    }
    printf("\nProblem 2: %d", max_[0] + max_[1] + max_[2]);
}

int main() {
    char* file = read_input("./Day 1/data.txt"); 
    char* copy = strdup(file);
    problem1(file);
    problem2(copy);
    free(file);
    free(copy);
    printf("\n");
    return 0;
}