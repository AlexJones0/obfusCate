int main() {
    typedef int* whole;
    whole b = {3};
    int z[5];
    z[2] = (int) 3.456f;
    typedef int abc;
    abc x;
    -x;
    +x;
    --x;
    x--;
    ++x;
    x++;
    ~x;
    !x;
    &x;
    *(&x);
    sizeof(x);
    x+x;
    x-x;
    x*x;
    x/x;
    x%x;
    x<<x;
    x>>x;
    x<x;
    x>x;
    x<=x;
    x>=x;
    x==x;
    x!=x;
    x|x;
    x||x;
    x&x;
    x&&x;
    x^x;
    struct abc {int a; float b;};
    struct abc my_struct = {.a = 2, .b = 3};
    my_struct.a + my_struct.a;
    my_struct.a + my_struct.b;
    struct abc *my_struct2 = &my_struct;
    my_struct2->a + my_struct2->a;
    my_struct2->b + my_struct2->a;
    // To consider:
    // Unary and binary operations
    // Casts (and hence type aliasing)
    // Ternary operator
    // Array references
    // Identifier references (need to track scope + type aliasing etc.)
    // Assignments shouldn't be necessary for what I'm doing I don't think
}