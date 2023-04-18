// Seed: 54321

int f(void) {return 0;}
int g(int a, ...) {return 1;}
int h() {return 2;}
int i(int a, float b, long c) { return 3;}
int fib(int n);

int main() {
	int a, b, c;
	float x, y;
	f() + g(5) + h();
	i(a, x, 12l);
	fib(12);
}

int fib(int n) {
	if (n <= 1)
		return n;
	else
		return fib(n-1) + fib(n-2);
}