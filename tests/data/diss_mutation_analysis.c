int x = 4;

int f() {return x++;}

int main() {
    x+x;
	f() + x;
	(--x + x) + (x + x++);
	x + (x /= 2);
}
