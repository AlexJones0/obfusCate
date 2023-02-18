//////
#include <stdio.h>

int hoare_partition(int *arr, int i, int j) {
    int pivot = arr[(i + j) / 2];
    int left_ind = i - 1, right_ind = j + 1;
    while (1) {
        do left_ind++; while (arr[left_ind] < pivot);
        do right_ind--; while (arr[right_ind] > pivot);
        if (left_ind >= right_ind)
            return right_ind;
        int temp = arr[left_ind];
        arr[left_ind] = arr[right_ind];
        arr[right_ind] = temp;
    }
}

void quick_sort_work(int *arr, int i, int j) {
    if (i < 0 || j < 0 || i >= j)
        return;
    int p = hoare_partition(arr, i, j);
    quick_sort_work(arr, i, p);
    quick_sort_work(arr, p + 1, j);
}

void quick_sort(int *arr, const int n) {
    quick_sort_work(arr, 0, n-1);
}

int main() {
    int my_arr[100] = {0, 70, 10, 7, 61, 63, 86, 83, 87, 66, 78, 68, 6, 42, 1, 33, 67, 49, 38, 5, 31, 73, 27, 20, 94, 77, 13, 96, 23, 53, 48, 9, 74, 57, 46, 16, 14, 92, 43, 24, 64, 44, 62, 2, 21, 3, 50, 34, 8, 69, 25, 91, 51, 54, 55, 80, 81, 17, 22, 95, 60, 72, 85, 84, 93, 28, 76, 58, 45, 65, 75, 47, 88, 89, 59, 19, 37, 40, 56, 79, 18, 97, 11, 35, 29, 26, 15, 32, 30, 82, 52, 4, 39, 36, 98, 12, 90, 71, 99, 41};
    quick_sort(my_arr, 100);
    int wrong_order_count = 0;
    for (int i = 0; i < 99; i++) {
        if (my_arr[i] > my_arr[i+1])
            wrong_order_count++;
    }
    printf("%d\n", wrong_order_count);
}
