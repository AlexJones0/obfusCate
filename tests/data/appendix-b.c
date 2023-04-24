#include <stdio.h>
#include <stdlib.h>

void primes(int max) {
  int *primes = malloc(sizeof(int) * max);
  int n = 1;
  for (int i = 0; i < max; i++) {
    int divisible = 1;
    while (divisible) {
      n++;
      divisible = 0;
      for (int j = 0; j < i; j++) 
        if (n % primes[j] == 0) {
          divisible = 1;
          break;
        }
    }
    printf("Prime %d: %d\n", i+1, n);
    primes[i] = n;
  }
  free(primes);
}

int main(int argc, const char **argv) {
    if (argc < 2)
        return -1;
	primes(atoi(argv[1]));
}