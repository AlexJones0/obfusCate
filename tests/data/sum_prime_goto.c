// Code taken from https://www.sonarsource.com/docs/CognitiveComplexity.pdf
// and translated to C by Alex Jones

#include <stdio.h>

int sumOfPrimes(int max) {
	int total = 0;
	for (int i = 2; i <= max;) {
		for (int j = 2; j < i; ++j) {
			if (i % j == 0) {
				goto OUT;
			}
		}
		total += i;
		OUT: ++i;
	}
	return total;
}


int main() {
	printf("Sum of primes to %d: %d\n", 10, sumOfPrimes(10));
}