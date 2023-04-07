#include <stdio.h>

int f() {
  struct in my_struct = {4, 13};
  return my_struct.d;
}

struct out {
  int a;
  float b;
  struct in {
    char c;
    short d;
  } e;
};

int main() {
  printf("%d\n", f())
}