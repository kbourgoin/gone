#include <stdio.h>

void _print_int(int x) {
  printf("%i\n", x);
}

void _print_float(double x) {
  printf("%f\n", x);
}

void _print_string(char* s) {
  printf("%i\n", s[0]);
}

void _print_bool(int x) {
  printf(x ? "True\n" : "False\n");
}
