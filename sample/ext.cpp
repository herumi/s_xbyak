#include <stdio.h>

extern "C" {

int g_a[3] = { 1, 2, 3 };
int sum3();
}

int main()
{
	int s = 0;
	for (int i = 0; i < 3; i++) {
		s += g_a[i];
	}
	int t = sum3();
	printf("sum3()=%d %s\n", t, t == s ? "ok" : "ng");
}
