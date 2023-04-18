int main() {
  int i = 2, sum = 0;
  int arr[3][2] = {10, 5, 3, 9, -4, 138};
  for (int i = 0; i < 3; i++) {
    sum += arr[0][i] - arr[1][i];
  }
  return sum + i;
}